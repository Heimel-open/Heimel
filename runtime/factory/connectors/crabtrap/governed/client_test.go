package governed

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func testRequest(t *testing.T) (*http.Request, []byte) {
	t.Helper()
	body := []byte(`{"action":"publish"}`)
	req, err := http.NewRequest(http.MethodPost, "https://api.example.test/v1/actions", nil)
	if err != nil {
		t.Fatal(err)
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer secret")
	return req, body
}

func testClient(serverURL string) *Client {
	return &Client{
		GateURL: serverURL,
		Identity: Identity{
			MissionID:        "mission-1",
			PrincipalID:      "agent-1",
			AuthorityGrantID: "grant-1",
		},
	}
}

func TestAuthorizeBindsRequestDigest(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/v1/authorize" {
			t.Fatalf("unexpected path %s", r.URL.Path)
		}
		var payload map[string]any
		if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
			t.Fatal(err)
		}
		request := payload["request"].(map[string]any)
		if _, exists := request["body"]; exists {
			t.Fatal("raw body entered governance payload")
		}
		response := map[string]any{
			"contract":       DecisionContract,
			"request_id":     payload["request_id"],
			"mission_id":     payload["mission_id"],
			"decision":       "ALLOW",
			"reason_code":    "RACS_ALLOW",
			"request_digest": request["request_digest"],
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(response)
	}))
	defer server.Close()

	req, body := testRequest(t)
	snapshot, err := RequestSnapshot("req-1", req, body)
	if err != nil {
		t.Fatal(err)
	}
	decision, err := testClient(server.URL).Authorize(context.Background(), snapshot, TransportSignals{
		Adapter:            "crabtrap",
		StaticRuleDecision: "ALLOW",
		JudgeDecision:      "ALLOW",
	})
	if err != nil {
		t.Fatal(err)
	}
	if decision.Decision != "ALLOW" || decision.RequestDigest != snapshot.Digest {
		t.Fatalf("unexpected decision: %+v", decision)
	}
}

func TestVerifyBeforeForwardDetectsMutation(t *testing.T) {
	req, body := testRequest(t)
	snapshot, err := RequestSnapshot("req-1", req, body)
	if err != nil {
		t.Fatal(err)
	}
	req.Header.Set("X-New-Header", "changed")
	if err := VerifyBeforeForward(snapshot, req, body); err == nil {
		t.Fatal("expected request mutation to be blocked")
	}
}

func TestInspectResponseRedactsAndStrips(t *testing.T) {
	replacement := []byte(`{"token":"[REDACTED:GITHUB_TOKEN]"}`)
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/v1/evaluate-response" {
			t.Fatalf("unexpected path %s", r.URL.Path)
		}
		var payload map[string]any
		if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
			t.Fatal(err)
		}
		response := map[string]any{
			"contract":                    ResponseDecisionContract,
			"request_id":                  payload["request_id"],
			"mission_id":                  payload["mission_id"],
			"request_digest":              payload["request_digest"],
			"response_digest":             strings.Repeat("a", 64),
			"decision":                    "REDACT",
			"reason_codes":                []string{"GITHUB_TOKEN", "SENSITIVE_RESPONSE_HEADERS"},
			"strip_header_names":          []string{"set-cookie"},
			"replacement_body_b64":        base64.StdEncoding.EncodeToString(replacement),
			"replacement_body_sha256":     sha256HexBytes(replacement),
			"replacement_body_size_bytes": len(replacement),
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(response)
	}))
	defer server.Close()

	req, requestBody := testRequest(t)
	snapshot, err := RequestSnapshot("req-1", req, requestBody)
	if err != nil {
		t.Fatal(err)
	}
	response := &http.Response{
		StatusCode: 200,
		Header: http.Header{
			"Content-Type": []string{"application/json"},
			"Set-Cookie":   []string{"session=secret"},
		},
	}
	body := []byte(`{"token":"` + "ghp_" + strings.Repeat("x", 36) + `"}`)
	decision, err := testClient(server.URL).InspectResponse(context.Background(), snapshot, response, body)
	if err != nil {
		t.Fatal(err)
	}
	if err := ApplyResponseDecision(response, body, decision); err != nil {
		t.Fatal(err)
	}
	if response.Header.Get("Set-Cookie") != "" {
		t.Fatal("sensitive response header was not stripped")
	}
	actual, err := io.ReadAll(response.Body)
	if err != nil {
		t.Fatal(err)
	}
	if string(actual) != string(replacement) {
		t.Fatalf("unexpected replacement body %q", actual)
	}
}

func TestApplyResponseDenyBlocks(t *testing.T) {
	response := &http.Response{Header: make(http.Header)}
	err := ApplyResponseDecision(response, []byte("unsafe"), ResponseDecision{
		Decision:    "DENY",
		ReasonCodes: []string{"PROMPT_INJECTION_PATTERN"},
	})
	var blocked *BlockedError
	if err == nil || !strings.Contains(err.Error(), "PROMPT_INJECTION_PATTERN") || !errors.As(err, &blocked) {
		t.Fatalf("expected blocked error, got %v", err)
	}
}
