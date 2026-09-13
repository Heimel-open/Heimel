# Customer Software Factory

This is a product/intake surface inside Factory OS, not a vertical architecture.

The market boundary is intentionally broad: if a customer has software and a software problem, they can be a customer. Industry, company size and geography are routing/evidence attributes, not product boundaries.

The ordering model is deliberately like a food menu:

- Ready menu: choose a reusable software recipe and configure its allowed options.
- Custom menu: describe the desired outcome, requirements, integrations, constraints and acceptance criteria from scratch.
- Hybrid: start from one or more ready recipes and add bespoke requirements.

The initial horizontal menu contains reusable recipes for workflow automation, system integration, AI agents, internal applications, customer-facing applications, and data/reporting products. These are starting recipes only. They are not verticals and do not restrict what the factory can build.

Customer flow:

`customer need -> ready/custom/hybrid order -> resolved software spec -> POC terms -> explicit customer acceptance -> bounded POC mission -> build -> independent QC -> customer approval -> payment -> accepted production spec -> production build -> deployment -> service/support -> repeat`

A menu recipe shortens discovery and production time by providing known defaults, acceptance criteria and implementation patterns. Custom requirements override or extend the recipe only where explicitly captured in the order. The customer can also submit a fully custom order with no menu recipe at all.

The customer module captures:

- desired outcome
- selected menu recipes and configurable options
- custom requirements
- integrations
- data inputs
- deployment preferences
- constraints
- acceptance criteria

It does not decide authority, price, contractual acceptance or deployment permission. Customer acceptance is separate evidence. Factory OS turns an accepted order into the existing `CommercialMissionSpec` / `BuildOrderV1` path. Consequence-bearing actions still use the canonical VAIG -> REHT -> RACS boundary.

The product thesis is therefore not "software for industry X". It is a configurable custom-software production system with reusable menu recipes where repetition exists and a custom path everywhere else.
