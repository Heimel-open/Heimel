# Gjestfri as an implementation precedent for relAIon

Date: 2026-09-06
Status: Adopted architectural precedent
Track: `Just you. Everywhere.` / relAIon

## Why it matters

Gjestfri demonstrates an emerging decomposition that is useful to relAIon without implying that relAIon should copy a hospitality product.

The important pattern is that durable person-centred context can remain independent of the current interface, model, provider, channel, device, or domain application. Those components can be dynamically bound around a more persistent relational layer.

## Pattern to adopt

```text
person
  -> persistent identity / context / relationships
  -> dynamically bound agent
  -> dynamically bound model/provider
  -> dynamically bound channel/device
  -> dynamically bound capabilities
  -> interaction with other persistent identities
```

Temporary domain objects — for example a booking, property, message, task, payment, transaction, document, vehicle, or order — should be treated as objects mediating interactions between persistent relational identities, not as the identities themselves.

## Architectural consequences for relAIon

1. Persistent identity, context and relationships belong above individual apps, clients, models and channels.
2. Model/provider is replaceable infrastructure. Changing the model must not require changing the person's durable relational identity.
3. Channel and device are replaceable locators/interfaces. The same relational presence should be reachable through whichever appropriate interface is currently available.
4. Capabilities should be dynamically discoverable and bindable rather than permanently embedded in one application.
5. Open interfaces such as API/MCP are useful capability surfaces through which external agents can participate without becoming the durable identity layer.
6. Agent-to-agent interaction is a first-class case: `my agent <-> your agent`, with domain objects created, exchanged or modified within the relationship.
7. Vertical applications are projections over the relational substrate. Hospitality is one projection; commerce, travel, communications, work, finance, mobility and future domains can be others.
8. Do not rebuild Gjestfri. Absorb the decomposition and allow relAIon to use Gjestfri-like products as domain capabilities when useful.

## Relation to existing relAIon direction

This strengthens the existing `Just you. Everywhere.` principle:

```text
stable human / agent identity
!= device
!= application
!= account
!= model
!= provider
!= communication channel
!= current network locator
```

The durable layer is the continuing identity and its relational/contextual history. Everything below it can move.

This is consistent with the identity/locator separation already adopted from HIP/ILNP and generalises the same principle from networking into application, model, agent, device and domain boundaries.

## Boundary

Gjestfri is evidence that parts of this decomposition are appearing in real products. It is not evidence that the complete relAIon architecture has been implemented or validated by Gjestfri.

The adopted lesson is therefore the architectural pattern, not the product form or any claim of equivalence.
