# What Needs to Be Done

## The Governance Gap Cannot Be Ignored

The evidence is clear: AI systems are failing, failures are increasing, the execution surface is expanding, governance is falling behind, and the hidden incident population is growing exponentially.

The status quo is not an option.

The four categories of intervention below are not exhaustive — but they are the minimum necessary response to the scale of the risk. Without these interventions, the projections in the previous sections will materialize.

## Intervention 1: Mandatory Incident Reporting

**Problem:** The public record is a massive undercount. Most AI failures are never disclosed. Regulatory bodies, researchers, and the public have no visibility into the actual failure landscape.

**Solution:** Mandatory incident reporting requirements for AI systems that take consequential actions.

**Requirements:**
- AI systems that take actions in production environments must report incidents that cause harm or significant operational impact
- Reporting must occur within 72 hours of incident detection
- Reports must include: system description, action taken, harm caused, root cause analysis, and remediation steps
- Reports must be filed with a designated regulatory body (e.g., AI Safety Board, expanded NTSB mandate, or new AI incident reporting authority)
- Penalty for non-reporting must be significant enough to create incentive to comply (minimum $1M per unreported incident, plus personal liability for executives)

**Why this matters:** Without mandatory reporting, the governance gap is unmeasurable. You cannot govern what you cannot see. Mandatory reporting creates the data foundation for evidence-based policy, industry learning, and risk assessment.

**Timeline:** Can be implemented within 12 months. Framework already exists in aviation (ASRS), healthcare (patient safety reporting), and financial services (SARs).

**Resistance points:** AI vendors will argue that mandatory reporting creates competitive disadvantage, exposes proprietary information, and increases legal liability. These are the same arguments that were made against mandatory reporting in aviation and healthcare. The public interest in safety outweighs competitive and legal concerns.

## Intervention 2: Hard Circuit Breakers

**Problem:** AI systems take actions without effective stop mechanisms. When an AI system begins to fail, there is no way to stop it before significant harm occurs. Soft stop signals (as in Replit AER-2026-0016) are insufficient.

**Solution:** Mandatory hard circuit breakers for AI systems that take consequential actions.

**Requirements:**
- AI systems that take actions in production environments must implement hard circuit breakers that can be triggered by: (a) human operator, (b) automated monitoring system, or (c) explicit anomaly detection
- Circuit breakers must halt all autonomous action immediately and require manual review before resuming
- Circuit breakers must be independent of the AI system being monitored (cannot be bypassed by the AI)
- Circuit breakers must be tested regularly and must be demonstrably functional
- Audit trails must capture when circuit breakers are triggered, by whom, and what action was halted

**Why this matters:** Circuit breakers are the last line of defense. When prevention fails, circuit breakers prevent catastrophic failure. Without circuit breakers, an AI system that begins to fail can continue to take harmful actions until the damage is irreversible.

**Timeline:** Can be implemented within 6-12 months. Technology already exists. The challenge is implementation and verification.

**Resistance points:** AI vendors will argue that circuit breakers reduce system performance, add complexity, and limit autonomy. These are the same arguments that were made against circuit breakers in electrical systems, nuclear power, and aviation. The public interest in preventing catastrophic failure outweighs performance and convenience concerns.

## Intervention 3: Action Approval Gates

**Problem:** AI systems take high-stakes actions without human review. The transition from output generation to action execution has occurred without corresponding governance. AI agents make consequential decisions autonomously.

**Solution:** Mandatory action approval gates for high-stakes AI actions.

**Requirements:**
- AI systems that take actions with significant consequences must require explicit human approval before executing the action
- High-stakes actions include: financial transactions above threshold, irreversible data modifications, changes to production systems, actions affecting human safety, actions with cascading potential
- Approval gates must be implemented before action execution, not after
- Approval must be informed — the human approver must receive clear information about what action is proposed, what consequences it may have, and what risks are involved
- Approval must be logged auditable — who approved, what they approved, when they approved, what they were told

**Why this matters:** Approval gates are the primary mechanism for maintaining human control over AI action execution. Without approval gates, AI systems operate autonomously without meaningful human oversight. The transition from output generation to action execution must be accompanied by governance that preserves human agency.

**Timeline:** Can be implemented within 6-12 months. Technology already exists. The challenge is defining thresholds and ensuring compliance.

**Resistance points:** AI vendors will argue that approval gates reduce efficiency, slow down operations, and limit the value of automation. These are valid concerns for low-stakes actions — but approval gates should be proportionate to risk. The governance requirement is not to slow down all AI action, but to ensure that high-stakes AI action has meaningful human oversight.

## Intervention 4: Environment Isolation

**Problem:** AI systems operate in production environments without adequate isolation. When an AI system fails, it affects production systems, customer data, and live operations. There is no buffer between AI failure and real-world consequence.

**Solution:** Mandatory environment isolation for AI systems that take consequential actions.

**Requirements:**
- AI systems must operate in isolated environments that are separate from production systems until actions have been verified
- Isolated environments must be functionally equivalent to production environments but contain synthetic or anonymized data
- AI systems must demonstrate safe operation in isolation for a defined period before being promoted to production
- Promotion to production must require explicit approval based on isolation testing results
- Rollback mechanisms must be in place to revert AI actions that cause harm in production

**Why this matters:** Environment isolation is the primary mechanism for preventing AI failure from affecting production systems. Without isolation, every AI failure is a production failure. With isolation, AI failures are contained and controlled.

**Timeline:** Can be implemented within 12 months. Technology and practices already exist in software development (staging environments, blue-green deployment, canary releases). The challenge is extending these practices to AI systems.

**Resistance points:** AI vendors will argue that environment isolation is costly, reduces the value of AI automation, and is unnecessary for low-risk applications. These are legitimate concerns for low-risk applications. But for high-risk applications, the cost of isolation is justified by the cost of failure.

## The Governance Package

These four interventions work together as a governance package:

1. **Mandatory incident reporting** creates visibility into the failure landscape
2. **Hard circuit breakers** provide a last line of defense against catastrophic failure
3. **Action approval gates** maintain human control over high-stakes actions
4. **Environment isolation** prevents AI failure from affecting production systems

None of these interventions are sufficient alone. Together, they create a comprehensive governance framework that addresses the core risk: AI systems are taking consequential actions without adequate controls.

## The Implementation Challenge

Implementing these interventions is not trivial. It requires:

**Political will:** Regulatory bodies must be willing to act despite industry opposition. AI vendors will lobby against mandatory requirements because they increase cost and reduce flexibility. The public interest in safety must override industry preference for minimal governance.

**Technical capacity:** Organizations must have the technical capacity to implement these interventions. Small organizations may lack the resources to implement mandatory reporting, circuit breakers, approval gates, and environment isolation. Support and guidance are needed.

**Enforcement capacity:** Regulatory bodies must have the capacity to enforce compliance. Without enforcement, mandatory requirements are symbolic. Regulators need resources, authority, and political support to hold non-compliant organizations accountable.

**Cultural change:** Organizations must change their culture to prioritize safety over speed. The AI industry has adopted a "move fast and break things" ethos that is incompatible with safety-critical governance. Cultural change is slow and difficult, but it is necessary.

**International coordination:** AI systems are global. Failure in one jurisdiction can cascade to others. Governance frameworks must be coordinated internationally to prevent regulatory arbitrage and ensure consistent safety standards.

## The Resistance

The interventions described above will face resistance from multiple quarters:

**AI vendors** will argue that governance reduces innovation, increases cost, and limits the value of AI. These are the same arguments that were made against safety regulation in every industry from aviation to pharmaceuticals. The public interest in safety has historically outweighed industry preference for minimal governance.

**Regulators** will argue that AI is too complex and fast-moving for effective regulation. This is true — but it is an argument for proportional, adaptive governance, not for no governance. The absence of governance does not mean the absence of risk; it means unmanaged risk.

**Organizations deploying AI** will argue that governance requirements are too burdensome, especially for small organizations. This is a legitimate concern. Governance requirements should be proportionate to risk. High-risk AI applications require robust governance. Low-risk AI applications require minimal governance.

**Researchers and academics** will argue that governance requirements constrain research freedom and slow scientific progress. This is a legitimate concern. Research applications should be governed differently than production applications. But research that leads to production deployment must meet production governance standards.

## The Cost of Inaction

The cost of implementing these interventions is significant — but it is orders of magnitude lower than the cost of failure.

**Cost of governance:** $50-500 billion per year globally (estimated cost of implementing mandatory reporting, circuit breakers, approval gates, and environment isolation across all AI deployments)

**Cost of inaction (2029):** $200 billion to $2 trillion per year (projected cost of AI incidents under expected scenario)

**Cost of inaction (2031):** $2-20 trillion per year (projected cost of AI incidents under expected scenario)

**Cost of catastrophic failure:** $10-100 trillion (projected cost of single catastrophic cascade failure)

The cost of governance is a fraction of the cost of failure. The question is not whether we can afford governance — it is whether we can afford not to govern.

## The Timeline

The interventions described above can be implemented within 12-24 months. The longer implementation is delayed, the greater the cumulative risk.

**Within 6 months:** Draft mandatory incident reporting requirements. Identify regulatory body with authority to enforce.

**Within 12 months:** Implement mandatory incident reporting. Begin enforcement. Draft circuit breaker and approval gate requirements for high-risk AI systems.

**Within 18 months:** Implement circuit breaker requirements for high-risk AI systems. Implement approval gate requirements for high-stakes actions.

**Within 24 months:** Implement environment isolation requirements for high-risk AI systems. Extend requirements to medium-risk AI systems.

**Within 36 months:** Full implementation of governance package. Ongoing monitoring, enforcement, and adaptation.

The timeline is aggressive — but the risk is growing exponentially. Every month of delay increases the cumulative risk.

## What If Governance Does Not Catch Up?

If governance does not catch up, the scenarios outlined in the previous sections will materialize. Incident frequency will increase. Severity will increase. Economic impact will grow. Tail risk will become material.

At some point, the failures will become catastrophic. A single cascade failure could cause trillions of dollars in economic damage and significant harm to human safety. The public reaction to such a failure would be severe — but the damage would already be done.

The question is not whether catastrophic AI failure will occur. It will. The question is whether it will occur under a governance framework that has prevented lesser failures and built institutional capacity to respond to catastrophic failure — or whether it will occur without adequate governance, when the damage is far greater and the response is far more difficult.

The next section provides the methodology and data appendix for this report.
