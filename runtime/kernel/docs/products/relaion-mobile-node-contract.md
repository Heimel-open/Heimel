# relAIon Mobile Node Contract

## Scope

relAIon treats phones and tablets as governed capability nodes. Mobile operating systems provide sandboxing, permissions, intents/extensions, background execution rules and device services. They do not by themselves establish Handlingsrett for an effect.

Canonical path:

user intent -> relAIon -> capability discovery -> normalized effect -> VALO fresh authorization -> platform capability -> effect -> receipt

## Platform families

### Android

Primary adapter for AOSP/Google Android and Android-derived OEM distributions.

OEM-specific layers such as Xiaomi HyperOS, OPPO ColorOS, vivo OriginOS and similar Android-based systems reuse the Android adapter unless a vendor-only capability requires an additional provider binding.

### iOS / iPadOS

Apple adapter uses platform-sanctioned surfaces such as App Intents, app extensions, Shortcuts integration, share extensions, notifications and approved background execution. Platform limits are treated as capability constraints, never bypass targets.

### HarmonyOS / OpenHarmony

HarmonyOS is a distinct adapter family. Native bindings may use ArkTS/ArkUI and HarmonyOS kits such as Ability Kit, Background Tasks Kit, Distributed Service Kit, Intents Kit and device/security services. Do not model HarmonyOS as an Android skin.

## Shared invariants

1. OS permission is not authority.
2. Intent registration is not authority.
3. Background execution entitlement is not authority.
4. Cross-device discovery is not authority.
5. No effectful provider call before fresh authorization returns ALLOW.
6. DENY and ESCALATE never invoke the provider.
7. Exact target, action, parameters, purpose and device context are included in the normalized effect.
8. Platform denial or unavailability fails closed.
9. Every attempted governed effect yields replayable evidence.
10. Remote processing is OFF by default unless explicitly authorized.

## Mobile capability classes

Initial portable capability classes:

- notifications.read / notifications.post
- calendar.read / calendar.write
- contacts.read
- files.read / files.write
- camera.capture
- microphone.capture
- location.read
- share.receive / share.send
- browser.open / browser.context
- message.compose
- app.intent
- device.nearby / device.handoff

Capabilities that can create external consequences MUST be normalized and gated independently from read access.

## READY contract

A mobile device may advertise `RELAION_READY` only if:

- device identity is established;
- local protected state is available;
- at least one inference route is operational or a user-approved trusted-node route is available;
- capability registry is operational;
- VALO gate is active;
- a negative test proves DENY does not reach a provider;
- receipt generation passes;
- capability access can be revoked through the OS or relAIon control plane.

## Distribution

Target consumer distribution:

- Android: signed APK/AAB via store or enterprise/direct distribution where permitted.
- iOS/iPadOS: signed App Store/TestFlight/enterprise distribution within Apple platform rules.
- HarmonyOS: signed AppGallery/HarmonyOS package using native HarmonyOS tooling.

No platform adapter may require disabling platform security to reach READY.
