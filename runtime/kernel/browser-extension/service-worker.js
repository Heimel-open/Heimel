const RELAION_NATIVE_HOST = "com.relaion.node";

function normalizeEffect(message, sender) {
  const tab = sender.tab || {};
  return {
    request_id: crypto.randomUUID(),
    actor_id: "browser-extension",
    principal_id: "local-user",
    surface: "BROWSER_EXTENSION",
    capability_id: message.capability_id,
    provider_id: "browser",
    target: message.target || tab.url || "",
    purpose: message.purpose || "user-requested-browser-action",
    mandate_ref: message.mandate_ref || "browser:interactive",
    parameters: message.parameters || {},
    requested_at: new Date().toISOString(),
    browser_context: {
      tab_id: tab.id ?? null,
      url: tab.url ?? null,
      title: tab.title ?? null
    }
  };
}

async function askrelAIon(effect) {
  return chrome.runtime.sendNativeMessage(RELAION_NATIVE_HOST, {
    type: "authorize_and_invoke",
    effect
  });
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message || message.type !== "relaion.effect") return false;

  const effect = normalizeEffect(message, sender);
  askrelAIon(effect)
    .then((receipt) => sendResponse({ ok: true, receipt }))
    .catch((error) => sendResponse({ ok: false, error: String(error) }));

  return true;
});

chrome.action.onClicked.addListener(async (tab) => {
  await chrome.scripting.executeScript({
    target: { tabId: tab.id },
    func: () => {
      const detail = {
        title: document.title,
        url: location.href,
        selection: String(window.getSelection() || "").slice(0, 8000)
      };
      chrome.runtime.sendMessage({
        type: "relaion.effect",
        capability_id: "browser:inspect-page",
        target: location.href,
        purpose: "inspect-current-page",
        parameters: detail
      });
    }
  });
});
