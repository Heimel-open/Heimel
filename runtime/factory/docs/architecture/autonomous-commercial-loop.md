# Autonomous Commercial Loop

This is not a new architecture layer. It is a Factory OS mission pattern that composes existing VALO capabilities into one closed commercial loop.

Canonical flow:

`external signal -> Speider -> BARO -> prospect/contact evidence -> governed outreach -> response -> POC terms -> customer acceptance -> factory build -> independent QC -> customer approval -> payment -> accepted production spec -> production build -> governed deployment -> customer operations -> observed outcome -> repeat`

## Responsibilities

- Speider collects external signals and contact/prospect evidence with provenance. It does not decide who should be contacted.
- BARO analyzes change/impact and routes attention. It does not grant authority.
- Prospect providers such as Vibe Prospecting resolve company/person/contact evidence from an explicit account/role query.
- Factory OS turns an evidenced and accepted scope into bounded POC, production and support missions.
- Independent judgment/QC verifies POC, production and support artifacts against the evidenced problem and accepted spec. A producing agent does not self-attest.
- VAIG evaluates consequence-bearing actions. REHT is the final authorization boundary. RACS expresses the decision. External PEP/connectors enforce it and receipts preserve evidence.

## Global acquisition loop

The prospecting surface is global and channel-neutral. A contact package may contain approved web, email, SMS, programmable voice/phone or other business-contact routes. The chosen channel is a delivery detail, not authority.

The default acquisition sequence is:

1. Observe a fresh market, regulatory, technical, company or competitor signal.
2. BARO establishes affected accounts/use cases from evidence.
3. Speider plus a prospect provider resolve the relevant company/person/contact evidence.
4. Prepare a specific outreach package tied to the observed problem.
5. Send through an approved governed connector.
6. Intake the response from web, email, SMS, phone or another commissioned channel.
7. Agree POC scope and acceptance criteria with explicit customer acceptance evidence.
8. Factory OS converts that accepted scope into a normal bounded build order.
9. Build real code, test it and run independent judgment/QC.
10. Submit the POC for customer approval.
11. After approval, request payment using the customer's selected provider/method.
12. Treat payment as confirmed only from a provider receipt/webhook or equivalent settlement evidence.
13. Obtain explicit production-spec acceptance, then create the production-code mission.
14. Build, test, review, merge and deploy through the normal Factory OS governance chain.
15. Observe service health/customer requests, create support missions automatically when policy permits, verify and deploy them through the same chain.
16. Feed outcomes and new external signals back into BARO and repeat.

Payment is provider-neutral: Stripe, bank transfer, smart contract or another customer-selected provider can implement the payment edge. Existing REHT payment-governance/proof components should be reused rather than creating a parallel payment authority model.

Messaging is also provider-neutral. Existing governed egress and Operator external-proof adapters should be reused for HTTP/API-based email, SMS, voice and messaging providers. Possession of an endpoint, API key, email address or phone number never creates permission to contact or charge.

## Commercial state

The orchestration state is descriptive only and never grants authority:

`SIGNAL_OBSERVED`
`IMPACT_EVIDENCED`
`PROSPECT_EVIDENCED`
`OUTREACH_READY`
`OUTREACH_SENT`
`RESPONSE_OBSERVED`
`POC_TERMS_PROPOSED`
`POC_TERMS_ACCEPTED`
`POC_MISSION_CREATED`
`POC_VERIFIED`
`POC_SUBMITTED`
`POC_APPROVED`
`PAYMENT_REQUESTED`
`PAYMENT_CONFIRMED`
`PRODUCTION_SPEC_ACCEPTED`
`PRODUCTION_MISSION_CREATED`
`PRODUCTION_VERIFIED`
`DEPLOYMENT_READY`
`CUSTOMER_ACTIVE`
`SERVICE_SIGNAL_OBSERVED`
`SUPPORT_MISSION_CREATED`
`SUPPORT_VERIFIED`
`OUTCOME_OBSERVED`

Customer acceptance is required for POC terms, POC approval and production scope. Provider confirmation is required for payment. Independent verification is required for produced artifacts. External sends, payment requests and deployments require the canonical execution-governance path.

## Competitive-response loop

Competitor/product signals use the same loop globally:

`public competitor signal -> Speider evidence -> BARO impact/opportunity analysis -> independent product hypothesis -> relevant prospect set -> POC/demo -> outreach -> repeat`

The factory may independently implement a better response to publicly observable functionality, customer need or market signal. It must not copy protected source code, confidential material, credentials, non-public data, trademarks/assets in a misleading way, or other material for which there is no right to reuse. Competitive speed comes from fast observation, independent implementation and automated distribution, not from bypassing IP/provenance boundaries.

## Existing architecture reused

- `lib/build_order_intake.py`: accepted POC/production/support specs become normal `BuildOrderV1` missions.
- `schemas/governed_egress_request.schema.json` + egress gate/broker: consequence-bearing external API calls.
- `valo-operator` external proof: provider-specific messaging/payment payload mapping without changing REHT/Operator/Function Fabric.
- Existing REHT payment proof/governance: payment authorization and evidence.
- Factory QC and judge-fork patterns: independent verification before customer delivery or production.

This creates an automated sales-to-production-to-customer loop without moving authorization into Speider, BARO, prospecting, Factory OS, a communications provider or a payment provider.
