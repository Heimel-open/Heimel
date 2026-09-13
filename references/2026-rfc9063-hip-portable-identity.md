# RFC 9063 — Host Identity Protocol as architectural precedent for portable identity

Source: RFC 9063, *Host Identity Protocol Architecture* (IETF, July 2021)

https://www.rfc-editor.org/info/rfc9063/

## Why it matters

RFC 9063 is a strong architectural precedent for the separation we need in the "Just you. Everywhere." / relAIon line.

HIP explicitly separates endpoint identity from network location. In ordinary IP networking, an IP address is overloaded: it is used both to say who/what the endpoint is and where it is currently reachable. HIP introduces a cryptographic Host Identity above the locator layer, allowing the locator to change while the endpoint identity remains stable.

Core separation:

- identity != locator
- identity != interface
- identity != current network
- identity != current IP address
- connection != current IP address

The Host Identifier is cryptographic: control of the corresponding private key is used to demonstrate control of the identity. This makes the identity capable of persisting independently of transient addressing and attachment points.

HIP therefore gives a concrete lower-layer instance of a more general principle:

> Persistent identity should not be coupled to the current transport path or current location.

## Relation to ILNP, eSIM and relAIon

The useful stack is not that these technologies solve the same problem. They solve adjacent separations at different layers.

- ILNP separates identity from location at the internetworking layer.
- HIP separates cryptographic host identity from IP locator and lets transport associations follow the identity.
- eSIM separates subscription/network access from a removable physical SIM and weakens binding between connectivity and one physical token/device arrangement.
- relAIon extends the same architectural direction upward: persistent actor identity, persistent relationships, portable context/history, freshly resolved authority and capability should not be bound to one device, app, account, network, phone number or transport path.

This suggests a layered model:

persistent self
→ persistent relationships
→ portable context / history
→ current authority
→ capability
→ connection
→ transport / network / device

The lower layers may change without redefining the actor.

## Important boundary

HIP does not provide the higher-layer relAIon object. It does not by itself provide relational continuity, portable history/context, delegated authority, consequence-time authorization or application-independent actor continuity.

Its value is architectural precedent: it demonstrates that separating stable identity from transient locator is both coherent and implementable.

## Design implication

Treat network address, device, carrier, account and application endpoint as locators or attachment mechanisms, not as the durable identity itself.

For relAIon, the corresponding invariant is:

> The actor remains the actor while its locators, transports, devices and service attachments change.

This is one of the technical foundations behind the broader hypothesis:

> Just you. Everywhere.

The novelty is not the identity/locator split alone. The novelty is carrying the split consistently upward from networking into relational identity, context, authority and capability.
