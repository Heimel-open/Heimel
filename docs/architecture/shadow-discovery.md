# Shadow Discovery

Shadow Discovery is a customer-authorized discovery mode inside Factory OS. It is not a new architecture layer and it does not grant execution authority.

The purpose is to let a specialized swarm understand a customer before proposing what should be built. The operating analogy is a scalable Forward Deployed Engineering team: observe how the business actually works, preserve evidence, identify opportunities, and return with a concrete proposal.

## Customer consent

The customer explicitly chooses `Allow Shadow Discovery` and supplies a bounded grant:

- customer identity
- allowed data/system sources
- allowed shadow roles
- start and expiry time
- prohibited data classes
- whether the grant is one-time or continuous

Shadow Discovery v1 is read-only. A grant with write access is invalid. Access to a system, repository, ticket store, document collection, log stream or process map never becomes permission to change it.

## Default shadow swarm

The default role set is:

- process-shadow: observes how work actually moves through the organization
- software-shadow: maps code, applications and technical constraints
- integration-shadow: maps system boundaries, APIs, events and manual handoffs
- data-shadow: maps data sources, transformations, duplication and provenance
- human-work-shadow: identifies repetitive/manual work and judgment bottlenecks
- risk-security-shadow: captures constraints, risks and consequence surfaces
- product-shadow: maps customer/user needs and product opportunities
- economics-shadow: estimates cost, value, leverage and prioritization

Roles are collection/analysis roles only. They cannot authorize outreach, change systems, enter contracts, deploy code or charge the customer.

## Output

The discovery swarm produces evidence-backed opportunities. A downstream proposal can contain:

- problem statement
- supporting evidence
- proposed outcome
- scope
- acceptance criteria
- architecture/integration plan where relevant
- customer actions required
- price
- delivery time
- estimated value and uncertainty

The customer can then approve a proposal and move into the existing customer-order/POC/factory path.

## Continuous Shadow

A customer may explicitly opt into a continuous grant. Continuous mode does not broaden authority; it only extends read-only observation within the same bounded sources/roles until expiry or revocation.

This allows the factory to detect new inefficiencies, changed workflows, system drift, new product opportunities or support needs and prepare proposals such as:

`observed change -> evidence -> opportunity -> scope/price/time proposal -> customer approval -> factory mission`

No proposal is self-executing. Consequence-bearing actions still traverse the canonical governance boundary.
