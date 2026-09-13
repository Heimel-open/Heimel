# Document evidence ingest

Relygon treats document parsing as a replaceable perception capability, not as an authority or decision layer.

Canonical flow:

`document -> parser -> typed located blocks -> raw evidence -> governed interpretation -> authority/policy -> action`

The parser may extract structure, text, tables, layout, coordinates, confidence and source metadata. Every parsed block must retain enough provenance to trace an interpretation back to a concrete source location and source-integrity reference.

Parser output MUST NOT by itself:

- become canonical durable personal state;
- establish truth, authority, entitlement or policy;
- authorize disclosure to another capability;
- trigger an external effect.

All parser providers are adapters behind the same narrow contract. Provider-native payloads are not canonical state. Routing may select different parsers by document or page based on cost, latency or expected quality without changing downstream governance semantics.

This deliberately separates cheap, improving document perception from the governed questions Relygon must answer: what the evidence means, whether it is sufficient, what purpose permits its use, what authority is operative now, and what action is admissible.
