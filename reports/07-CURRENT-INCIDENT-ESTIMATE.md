# Current Incident Estimate

## The Public Record Shows 16 Incidents

This report has documented 16 canonical incidents of AI action execution failures between 2024 and 2026.

But the public record is not the total population.

As documented in Chapter 4, the public record represents only the visible surface of a much larger set of incidents. Most AI failures are never publicly disclosed. They are resolved internally, settled confidentially, categorized as software bugs, or simply not detected.

The question is not whether there are more incidents — there clearly are. The question is: how many more?

## The Visibility Rate

To estimate the total population of AI incident failures, we need to estimate the visibility rate — what percentage of actual incidents become part of the public record?

### Visibility Rates in Comparable Domains

We can estimate AI incident visibility by examining visibility rates in other high-stakes technical domains:

**Aviation safety:**
- Visibility rate: 1-10%
- Mandatory reporting exists, but near-misses and minor incidents are underreported
- Cultural barriers to reporting persist despite safety management systems
- Estimate based on: FAA and EMEA reporting compliance studies, academic analyses of reporting rates

**Healthcare adverse events:**
- Visibility rate: 10-20%
- Mandatory reporting exists for certain event categories
- Voluntary reporting systems capture additional events
- Studies suggest only 10-20% of adverse events are reported even in systems with reporting infrastructure
- Estimate based on: Institute of Medicine studies, WHO patient safety reports, academic meta-analyses

**Financial services operational failures:**
- Visibility rate: 5-15%
- Regulatory reporting requirements exist but are limited in scope
- Many incidents are resolved internally without regulatory notification
- Public disclosure depends on materiality thresholds and legal obligations
- Estimate based on: SEC enforcement actions, academic studies of operational risk disclosure rates

**Software industry security incidents:**
- Visibility rate: 1-5%
- No mandatory reporting requirements in most jurisdictions
- Disclosure is voluntary and often delayed
- Many incidents are never publicly disclosed
- Estimate based on: Verizon DBIR studies, academic analyses of disclosure rates

**AI incident reporting (estimated):**
- Visibility rate: 2-20%
- No mandatory reporting requirements
- Disclosure is voluntary and often suppressed for competitive or legal reasons
- Cultural barriers to reporting are high
- Detection infrastructure is immature
- Estimate based on: comparison with above domains, analysis of disclosure patterns

## The Total Population

Using these visibility rates, we can estimate the total population of AI incident failures:

### Conservative Estimate (2% visibility rate)

If only 2% of AI incidents become part of the public record, the total population is:

**Total incidents: 800**

Calculation: 16 documented incidents ÷ 0.02 visibility rate = 800 total incidents

### Mid-Range Estimate (5% visibility rate)

If 5% of AI incidents become part of the public record, the total population is:

**Total incidents: 320**

Calculation: 16 documented incidents ÷ 0.05 visibility rate = 320 total incidents

### High-End Estimate (20% visibility rate)

If 20% of AI incidents become part of the public record, the total population is:

**Total incidents: 80**

Calculation: 16 documented incidents ÷ 0.20 visibility rate = 80 total incidents

## The Reasonable Range

Based on comparison with analogous domains and analysis of disclosure incentives, the reasonable estimate for the total population of AI incident failures is:

**80 to 800 incidents**

The mid-point estimate is approximately 320 incidents.

This range reflects uncertainty about the true visibility rate. The lower bound (80 incidents) assumes relatively high visibility (20%), comparable to regulated domains with mandatory reporting. The upper bound (800 incidents) assumes very low visibility (2%), comparable to domains with minimal reporting infrastructure.

## The Severity Distribution

If the total population is 80-800 incidents, what is the severity distribution?

We can use the severity distribution of documented incidents to estimate the severity distribution of the total population:

**Documented incidents (n=16):**
- Critical: 4 incidents (25%)
- High: 6 incidents (37.5%)
- Moderate: 4 incidents (25%)
- Low: 2 incidents (12.5%)

**Estimated total population (conservative, n=800):**
- Critical: 200 incidents
- High: 300 incidents
- Moderate: 200 incidents
- Low: 100 incidents

**Estimated total population (mid-range, n=320):**
- Critical: 80 incidents
- High: 120 incidents
- Moderate: 80 incidents
- Low: 40 incidents

**Estimated total population (high-end, n=80):**
- Critical: 20 incidents
- High: 30 incidents
- Moderate: 20 incidents
- Low: 10 incidents

## The Implications

These estimates have significant implications for risk assessment:

### 1. The Frequency of Failure Is Much Higher Than the Public Record Suggests

The public record of 16 incidents creates the impression that AI failures are rare events. The estimated total population of 80-800 incidents over a 2-year period indicates that AI failures are occurring regularly — potentially multiple times per week.

Even at the high-end estimate (80 incidents), failures are occurring approximately once per week. At the mid-range estimate (320 incidents), failures are occurring approximately 3 times per week. At the conservative estimate (800 incidents), failures are occurring approximately 8 times per week.

### 2. The Frequency of Critical Failures Is Significant

Even at the high-end estimate, there have been approximately 20 critical AI incidents (complete system destruction, irreversible harm, catastrophic failures) over the past 2 years. This is not a negligible number.

At the mid-range estimate, there have been approximately 80 critical incidents. At the conservative estimate, there have been approximately 200 critical incidents.

The public record shows only 4 critical incidents. The reality is likely 5-50× worse.

### 3. The Trend Is Likely Accelerating

The execution surface is expanding rapidly (Chapter 5). AI systems are gaining more tools, more permissions, more autonomy, longer operation duration, greater financial authority, and physical-world access.

If incident frequency scales with execution surface expansion, and execution surface is growing at 10-20× per year, then incident frequency is likely growing at a similar rate.

This means that the 80-800 incidents documented for 2024-2026 are likely just the beginning. The next 2 years (2026-2028) may see 10-20× more incidents — potentially 800-16,000 incidents.

### 4. The Tail Risk Is Material

The conservative estimate of 200 critical incidents (complete system destruction, irreversible harm) indicates that tail risk is material. Organizations deploying AI systems are not just facing operational risk — they are facing catastrophic risk.

The probability of catastrophic failure is not negligible. It is material, and it is likely increasing as the execution surface expands.

### 5. The Economic Impact Is Likely Significant

If we assume an average economic impact per incident:
- Critical: $500 million (complete system destruction, major data breaches, financial fraud)
- High: $50 million (significant operational disruption, data loss, remediation costs)
- Moderate: $5 million (moderate disruption, partial data loss)
- Low: $500,000 (minor disruption, limited data loss)

**Conservative estimate (800 incidents):**
- Economic impact: $200B + $150B + $10B + $0.5B = $360.5 billion

**Mid-range estimate (320 incidents):**
- Economic impact: $80B + $60B + $4B + $0.2B = $144.2 billion

**High-end estimate (80 incidents):**
- Economic impact: $20B + $15B + $1B + $0.05B = $36.05 billion

Even at the high-end estimate, the economic impact is likely in the tens of billions of dollars. At the conservative estimate, the economic impact is likely in the hundreds of billions of dollars.

## The Uncertainty

These estimates are subject to significant uncertainty:

### Visibility Rate Uncertainty

The visibility rate is estimated at 2-20%, but the true rate may be outside this range. If visibility is lower than 2%, the total population may be larger than 800. If visibility is higher than 20%, the total population may be smaller than 80.

### Severity Distribution Uncertainty

The severity distribution is estimated based on the documented incidents, but the severity distribution of undocumented incidents may be different. If undocumented incidents are more severe (because they are harder to detect and more likely to be suppressed), the total critical incident count may be higher. If undocumented incidents are less severe (because they are minor incidents that were not worth disclosing), the total critical incident count may be lower.

### Economic Impact Uncertainty

The average economic impact per incident is estimated based on public examples, but the true economic impact may be higher or lower. If incidents are more costly than public examples suggest (because they include reputational damage, regulatory penalties, or long-term operational disruption), the total economic impact may be higher. If incidents are less costly (because they are minor incidents with limited impact), the total economic impact may be lower.

## The Bottom Line

The public record of 16 incidents is not the total population. The estimated total population is 80-800 incidents, with a mid-point estimate of 320 incidents.

The frequency of failure is much higher than the public record suggests. The frequency of critical failure is significant. The trend is likely accelerating. The tail risk is material. The economic impact is likely significant.

The governance gap is not a theoretical risk. It is a material, ongoing failure that is causing significant harm.

The next section examines what happens if the current trajectory continues.

---

**Next:** What Happens If the Trend Continues
