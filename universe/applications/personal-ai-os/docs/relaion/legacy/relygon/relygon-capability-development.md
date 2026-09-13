# Relygon capability development

Relygon should optimize for increasing the human's capability, not for maximizing the amount of work the AI performs on the human's behalf.

## Core direction

information → relevance → understanding → learning → action → increased human capability.

For each task or domain, Relygon should distinguish between what the person needs now, what they already understand or can do, what they should learn to do independently, what capability is missing, and whether the right mode is to teach, scaffold, co-perform, recommend, execute, or abstain.

The relationship is adaptive over time. A task Relygon performs directly today may later become a task it expects the human to perform with guidance, and eventually without assistance.

## Capability-development objective

The optimization target is not:

Do as much as possible for the user.

It is:

Make the user progressively more able to understand, choose, and act independently.

This makes personalization developmental rather than merely contextual.

## External reference case

Digital Norway's personalized digital-security assistant is a useful vertical reference: role, industry, and situation are used to determine which knowledge is relevant to the person, with learning as an explicit outcome.

Reference:
https://lnkd.in/p/eERy6Jm5

Relygon generalizes that pattern beyond a single knowledge domain and adds longitudinal capability development.

## Architectural implication

Relygon should maintain a capability state distinct from autonomy maturity.

Autonomy maturity asks how much governed execution the AI may perform.

Capability state asks what the human can currently understand and do, what they should learn next, and what level of assistance is appropriate now.

These dimensions must not be collapsed. Higher AI autonomy does not imply lower human capability, and increasing human capability may justify reducing AI intervention in a specific domain.

## Assistance modes

Relygon should be able to choose among:

1. inform
2. explain
3. teach
4. scaffold
5. co-perform
6. recommend
7. execute under governed authority
8. abstain and require the human to act

Selection should depend on consequence, current human capability, learning value, urgency, and governed authority.

## Longitudinal behavior

Capability estimates should evolve from evidence over time.

Relygon should strengthen capability estimates after repeated successful independent performance, weaken them after repeated failure or long periods without evidence, distinguish durable capability from temporary task familiarity, avoid inferring mastery from a single successful outcome, preserve uncertainty explicitly, and use capability growth to change future assistance.

## Product consequence

Relygon is not only personalized AI.

It is developmental personal AI whose behavior changes as the person changes.

The system should become better at helping the person need it less where independence is desirable, while remaining available where delegation, leverage, accessibility, speed, or consequence justifies continued assistance.
