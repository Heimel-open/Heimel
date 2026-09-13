package governed

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"sort"
	"strings"
	"time"
)

const (
	AuthorizeContract        = "valo.governed-egress.authorize.v1"
	DecisionContract         = "valo.governed-egress.decision.v1"
	ResponseContract         = "valo.governed-egress.response.v1"
	ResponseDecisionContract = "valo.governed-egress.response-decision.v1"
)

type Identity struct {
	MissionID        string
	PrincipalID      string
	AuthorityGrantID string
}

type TransportSignals struct {
	Adapter            string
	StaticRuleDecision string
	JudgeDecision      string
}

type Client struct {
	GateURL         string
	SharedToken     string
	Identity        Identity
	HTTPClient      *http.Client
	MaxGateResponse int64
	MaxRequestBody  int64
	MaxResponseBody int64
}

type Snapshot struct {
	RequestID string
	Digest    string
	Metadata  map[string]any
	Body      []byte
}

type Decision struct {
	Contract                 string `json:"contract"`
	RequestID                string `json:"request_id"`
	MissionID                string `json:"mission_id"`
	Decision                 string `json:"decision"`
	ReasonCode               string `json:"reason_code"`
	RequestDigest            string `json:"request_digest"`
	ReplacementRequestDigest string `json:"replacement_request_digest,omitempty"`
}

type ResponseDecision struct {
	Contract                string   `json:"contract"`
	RequestID               string   `json:"request_id"`
	MissionID               string   `json:"mission_id"`
	RequestDigest           string   `json:"request_digest"`
	ResponseDigest          string   `json:"response_digest"`
	Decision                string   `json:"decision"`
	ReasonCodes             []string `json:"reason_codes"`
	StripHeaderNames        []string `json:"strip_header_names"`
	ReplacementBodyB64      string   `json:"replacement_body_b64,omitempty"`
	ReplacementBodySHA256   string   `json:"replacement_body_sha256,omitempty"`
	ReplacementBodySizeByte int      `json:"replacement_body_size_bytes,omitempty"`
}

type BlockedError struct {
	Phase  string
	Reason string
}

func (e *BlockedError) Error() string {
	return fmt.Sprintf("governed egress %s blocked: %s", e.Phase, e.Reason)
}

func (c *Client) defaults() {
	if c.HTTPClient == nil {
		c.HTTPClient = &http.Client{Timeout: 10 * time.Second}
	}
	if c.MaxGateResponse <= 0 {
		c.MaxGateResponse = 1 << 20
	}
	if c.MaxRequestBody <= 0 {
		c.MaxRequestBody = 10 << 20
	}
	if c.MaxResponseBody <= 0 {
		c.MaxResponseBody = 1 << 20
	}
}

func canonicalJSON(value any) ([]byte, error) {
	return json.Marshal(value)
}

func sha256HexBytes(value []byte) string {
	digest := sha256.Sum256(value)
	return hex.EncodeToString(digest[:])
}

func validateIdentity(identity Identity) error {
	if identity.MissionID == "" || identity.PrincipalID == "" || identity.AuthorityGrantID == "" {
		return errors.New("mission, principal and authority grant are required")
	}
	return nil
}

func normalizeSignals(signals TransportSignals) (TransportSignals, error) {
	if signals.Adapter == "" {
		signals.Adapter = "crabtrap"
	}
	signals.StaticRuleDecision = strings.ToUpper(signals.StaticRuleDecision)
	if signals.StaticRuleDecision == "" {
		signals.StaticRuleDecision = "NO_MATCH"
	}
	switch signals.StaticRuleDecision {
	case "ALLOW", "DENY", "NO_MATCH":
	default:
		return signals, errors.New("static rule decision must be ALLOW, DENY or NO_MATCH")
	}
	signals.JudgeDecision = strings.ToUpper(signals.JudgeDecision)
	if signals.JudgeDecision == "" {
		signals.JudgeDecision = "UNKNOWN"
	}
	switch signals.JudgeDecision {
	case "ALLOW", "DENY", "UNKNOWN":
	default:
		return signals, errors.New("judge decision must be ALLOW, DENY or UNKNOWN")
	}
	return signals, nil
}

func RequestSnapshot(requestID string, req *http.Request, body []byte) (Snapshot, error) {
	if requestID == "" {
		return Snapshot{}, errors.New("request id is required")
	}
	if req == nil || req.URL == nil {
		return Snapshot{}, errors.New("request and URL are required")
	}
	if req.URL.Scheme != "http" && req.URL.Scheme != "https" {
		return Snapshot{}, errors.New("request URL must be absolute HTTP(S)")
	}
	if req.URL.Host == "" || req.URL.User != nil {
		return Snapshot{}, errors.New("request URL host is required and credentials are forbidden")
	}

	headerSet := make(map[string]struct{}, len(req.Header))
	for name := range req.Header {
		headerSet[strings.ToLower(strings.TrimSpace(name))] = struct{}{}
	}
	headerNames := make([]string, 0, len(headerSet))
	for name := range headerSet {
		if name != "" {
			headerNames = append(headerNames, name)
		}
	}
	sort.Strings(headerNames)
	websocket := strings.EqualFold(req.Header.Get("Upgrade"), "websocket")
	metadata := map[string]any{
		"method":          strings.ToUpper(req.Method),
		"url":             req.URL.String(),
		"header_names":    headerNames,
		"body_sha256":     sha256HexBytes(body),
		"body_size_bytes": len(body),
		"content_type":    nullableString(req.Header.Get("Content-Type")),
		"websocket":       websocket,
	}
	encoded, err := canonicalJSON(metadata)
	if err != nil {
		return Snapshot{}, fmt.Errorf("canonical request metadata: %w", err)
	}
	return Snapshot{
		RequestID: requestID,
		Digest:    sha256HexBytes(encoded),
		Metadata:  metadata,
		Body:      append([]byte(nil), body...),
	}, nil
}

func nullableString(value string) any {
	if value == "" {
		return nil
	}
	return value
}

func (c *Client) Authorize(ctx context.Context, snapshot Snapshot, signals TransportSignals) (Decision, error) {
	c.defaults()
	if err := validateIdentity(c.Identity); err != nil {
		return Decision{}, err
	}
	if int64(len(snapshot.Body)) > c.MaxRequestBody {
		return Decision{}, &BlockedError{Phase: "request", Reason: "REQUEST_BODY_EXCEEDS_BINDING_LIMIT"}
	}
	normalizedSignals, err := normalizeSignals(signals)
	if err != nil {
		return Decision{}, err
	}
	metadata := cloneMap(snapshot.Metadata)
	metadata["request_digest"] = snapshot.Digest
	payload := map[string]any{
		"contract":           AuthorizeContract,
		"request_id":         snapshot.RequestID,
		"mission_id":         c.Identity.MissionID,
		"principal_id":       c.Identity.PrincipalID,
		"authority_grant_id": c.Identity.AuthorityGrantID,
		"request":            metadata,
		"transport": map[string]any{
			"adapter":              normalizedSignals.Adapter,
			"static_rule_decision": normalizedSignals.StaticRuleDecision,
			"judge_decision":       normalizedSignals.JudgeDecision,
		},
	}
	var decision Decision
	if err := c.postJSON(ctx, "/v1/authorize", payload, &decision); err != nil {
		return Decision{}, err
	}
	if decision.Contract != DecisionContract {
		return Decision{}, errors.New("gate returned unexpected decision contract")
	}
	if decision.RequestID != snapshot.RequestID || decision.MissionID != c.Identity.MissionID {
		return Decision{}, errors.New("gate decision identity mismatch")
	}
	if decision.RequestDigest != snapshot.Digest {
		return Decision{}, errors.New("gate decision request digest mismatch")
	}
	switch decision.Decision {
	case "ALLOW", "DENY", "MODIFY":
	default:
		return Decision{}, errors.New("gate returned invalid decision")
	}
	return decision, nil
}

func VerifyBeforeForward(snapshot Snapshot, req *http.Request, body []byte) error {
	current, err := RequestSnapshot(snapshot.RequestID, req, body)
	if err != nil {
		return err
	}
	if current.Digest != snapshot.Digest || !bytes.Equal(body, snapshot.Body) {
		return &BlockedError{Phase: "request", Reason: "REQUEST_CHANGED_AFTER_AUTHORIZATION"}
	}
	return nil
}

func (c *Client) InspectResponse(ctx context.Context, snapshot Snapshot, response *http.Response, body []byte) (ResponseDecision, error) {
	c.defaults()
	if response == nil {
		return ResponseDecision{}, errors.New("response is required")
	}
	if int64(len(body)) > c.MaxResponseBody {
		return ResponseDecision{}, &BlockedError{Phase: "response", Reason: "RESPONSE_EXCEEDS_INSPECTION_LIMIT"}
	}
	headerNames := make([]string, 0, len(response.Header))
	for name := range response.Header {
		headerNames = append(headerNames, strings.ToLower(name))
	}
	sort.Strings(headerNames)
	payload := map[string]any{
		"contract":       ResponseContract,
		"request_id":     snapshot.RequestID,
		"mission_id":     c.Identity.MissionID,
		"request_digest": snapshot.Digest,
		"response": map[string]any{
			"status_code":      response.StatusCode,
			"header_names":     headerNames,
			"body_sha256":      sha256HexBytes(body),
			"body_size_bytes":  len(body),
			"content_type":     nullableString(response.Header.Get("Content-Type")),
			"content_encoding": nullableString(response.Header.Get("Content-Encoding")),
			"body_sample_b64":  base64.StdEncoding.EncodeToString(body),
			"sample_truncated": false,
		},
	}
	var decision ResponseDecision
	if err := c.postJSON(ctx, "/v1/evaluate-response", payload, &decision); err != nil {
		return ResponseDecision{}, err
	}
	if decision.Contract != ResponseDecisionContract || decision.RequestID != snapshot.RequestID || decision.RequestDigest != snapshot.Digest {
		return ResponseDecision{}, errors.New("response decision binding mismatch")
	}
	switch decision.Decision {
	case "ALLOW", "DENY", "REDACT":
	default:
		return ResponseDecision{}, errors.New("gate returned invalid response decision")
	}
	return decision, nil
}

func ApplyResponseDecision(response *http.Response, body []byte, decision ResponseDecision) error {
	if response == nil {
		return errors.New("response is required")
	}
	for _, name := range decision.StripHeaderNames {
		response.Header.Del(name)
	}
	switch decision.Decision {
	case "ALLOW":
		response.Body = io.NopCloser(bytes.NewReader(body))
		response.ContentLength = int64(len(body))
		return nil
	case "REDACT":
		replacement := body
		if decision.ReplacementBodyB64 != "" {
			decoded, err := base64.StdEncoding.DecodeString(decision.ReplacementBodyB64)
			if err != nil {
				return errors.New("invalid replacement response body")
			}
			if sha256HexBytes(decoded) != decision.ReplacementBodySHA256 || len(decoded) != decision.ReplacementBodySizeByte {
				return errors.New("replacement response body binding mismatch")
			}
			replacement = decoded
			response.Header.Del("Content-Encoding")
		}
		response.Body = io.NopCloser(bytes.NewReader(replacement))
		response.ContentLength = int64(len(replacement))
		response.Header.Set("Content-Length", fmt.Sprintf("%d", len(replacement)))
		return nil
	case "DENY":
		return &BlockedError{Phase: "response", Reason: strings.Join(decision.ReasonCodes, ",")}
	default:
		return errors.New("invalid response decision")
	}
}

func ReadBoundedBody(body io.ReadCloser, max int64) ([]byte, error) {
	if body == nil {
		return nil, nil
	}
	defer body.Close()
	reader := &io.LimitedReader{R: body, N: max + 1}
	data, err := io.ReadAll(reader)
	if err != nil {
		return nil, err
	}
	if int64(len(data)) > max {
		return nil, &BlockedError{Phase: "response", Reason: "RESPONSE_EXCEEDS_INSPECTION_LIMIT"}
	}
	return data, nil
}

func (c *Client) postJSON(ctx context.Context, path string, payload any, output any) error {
	if c.GateURL == "" {
		return errors.New("gate URL is required")
	}
	base, err := url.Parse(strings.TrimRight(c.GateURL, "/"))
	if err != nil || (base.Scheme != "http" && base.Scheme != "https") || base.Host == "" {
		return errors.New("gate URL must be absolute HTTP(S)")
	}
	body, err := json.Marshal(payload)
	if err != nil {
		return err
	}
	request, err := http.NewRequestWithContext(ctx, http.MethodPost, base.String()+path, bytes.NewReader(body))
	if err != nil {
		return err
	}
	request.Header.Set("Content-Type", "application/json")
	request.Header.Set("Accept", "application/json")
	if c.SharedToken != "" {
		request.Header.Set("Authorization", "Bearer "+c.SharedToken)
	}
	response, err := c.HTTPClient.Do(request)
	if err != nil {
		return fmt.Errorf("gate unavailable: %w", err)
	}
	defer response.Body.Close()
	limited := &io.LimitedReader{R: response.Body, N: c.MaxGateResponse + 1}
	responseBody, err := io.ReadAll(limited)
	if err != nil {
		return err
	}
	if int64(len(responseBody)) > c.MaxGateResponse {
		return errors.New("gate response exceeds configured limit")
	}
	if response.StatusCode != http.StatusOK {
		return fmt.Errorf("gate HTTP %d: %s", response.StatusCode, truncate(responseBody, 500))
	}
	if err := json.Unmarshal(responseBody, output); err != nil {
		return errors.New("gate returned invalid JSON")
	}
	return nil
}

func cloneMap(source map[string]any) map[string]any {
	copy := make(map[string]any, len(source)+1)
	for key, value := range source {
		copy[key] = value
	}
	return copy
}

func truncate(value []byte, max int) string {
	if len(value) <= max {
		return string(value)
	}
	return string(value[:max])
}
