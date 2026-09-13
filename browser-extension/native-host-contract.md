# relAIon Browser Native Host Contract

The browser extension is not an authority engine and MUST NOT directly execute effectful actions that bypass relAIon/VALO.

## Transport

Browser extension -> browser native messaging host -> relAIon local node -> VALO/REHT -> browser capability provider -> receipt.

Native host name: `com.relaion.node`.

## Request

```json
{
  "type": "authorize_and_invoke",
  "effect": {
    "request_id": "uuid",
    "actor_id": "browser-extension",
    "principal_id": "local-user",
    "surface": "BROWSER_EXTENSION",
    "capability_id": "browser:submit-form",
    "provider_id": "browser",
    "target": "https://example.test/form",
    "purpose": "user-requested-browser-action",
    "mandate_ref": "browser:interactive",
    "parameters": {},
    "requested_at": "RFC3339",
    "browser_context": {
      "tab_id": 1,
      "url": "https://example.test/form",
      "title": "Example"
    }
  }
}
```

## Response

```json
{
  "request_id": "uuid",
  "decision_id": "...",
  "disposition": "ALLOW|DENY|ESCALATE",
  "invoked": false,
  "effect_digest": "...",
  "receipt_digest": "...",
  "reasons": ["..."]
}
```

## Invariants

1. Discovery/visibility is not authority.
2. Browser host permissions are not Handlingsrett.
3. Extension-side code MUST NOT treat `activeTab`, scripting permission, DOM access, cookies, downloads, clipboard, navigation or native messaging access as authorization to create an effect.
4. DENY and ESCALATE MUST never reach the effect provider.
5. The exact target, parameters and browser context relevant to the consequence MUST be included in the normalized effect digest.
6. Authority is resolved at commit time, not at page-load or extension-install time.
7. A receipt is returned for every attempted effect routed through relAIon.
8. Direct browser APIs that can create consequences MUST be wrapped behind the local relAIon provider when enabled.

## Browser packaging

- Chromium-family browsers: Manifest V3 + Native Messaging.
- Firefox: WebExtensions + Native Messaging equivalent.
- Safari: Safari Web Extension wrapper around the shared extension logic.

The shared logical contract remains identical across browsers.