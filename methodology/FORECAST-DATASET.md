# Forecast Dataset Specification

## Purpose

The Forecast Dataset provides evidence-based forecasts of agentic AI incident occurrence and impact over various time horizons. Forecasts are strictly empirical - derived from incident corpus data, never speculated or invented.

## Dataset Structure

### Forecast Record Schema

```yaml
forecast:
  forecast_id: string              # Format: FCST-YYYY-XXXX
  creation_date: date
  forecast_horizon: enum           # 3m|6m|9m|12m
  reference_date: date             # Date from which forecast begins
  
  # Forecast dimensions
  forecasts:
    incident_count:
      expected_incidents: number
      confidence_interval:
        lower_95: number
        upper_95: number
        lower_50: number
        upper_50: number
      basis: array[string]         # Reasons for this forecast
      
    severity_distribution:
      critical:
        probability: number        # 0.0-1.0
        expected_count: number
        basis: string
      high:
        probability: number
        expected_count: number
        basis: string
      medium:
        probability: number
        expected_count: number
        basis: string
      low:
        probability: number
        expected_count: number
        basis: string
      negligible:
        probability: number
        expected_count: number
        basis: string
    
    systemic_cascades:
      probability_of_cascade_event: number
      expected_severity: enum
      potential_sectors_affected: array[string]
      basis: string
    
    sector_exposure:
      finance:
        risk_level: enum
        exposure_score: number
        basis: string
      healthcare:
        risk_level: enum
        exposure_score: number
        basis: string
      transportation:
        risk_level: enum
        exposure_score: number
        basis: string
      energy:
        risk_level: enum
        exposure_score: number
        basis: string
      technology:
        risk_level: enum
        exposure_score: number
        basis: string
    
    economic_impact:
      expected_financial_damage:
        lower_estimate: number
        central_estimate: number
        upper_estimate: number
        currency: string  # USD
        basis: string
    
    governance_readiness:
      overall_score: number  # 0-100
      critical_gaps_remaining: number
      regulatory_actions_pending: number
      sector_coverage:
        adequate: array[string]
        partial: array[string]
        inadequate: array[string]
        missing: array[string]
      basis: string
  
  # Methodology
  methodology:
    base_data_sources: array[string]  # AER incident IDs, external sources
    statistical_methods: array[string]
    assumptions: array[string]
    known_unknowns: array[string]
    
  # Validation
  validation:
    backtesting_results: string
    peer_review: string
    confidence_level: enum  # high|medium|low
    
  # Metadata
  created_by: string
  reviewed_by: array[string]
  last_updated: date
  status: enum  # draft|published|superseded
  superseded_by: string
```

## Forecast Methodology

### Base Rate Calculation

1. **Historical Incident Analysis**
   - Count incidents by time period in corpus
   - Calculate base rate of incidents per year
   - Account for reporting bias and detection improvements
   - Adjust for increased agent deployment

2. **Deployment Trajectory Analysis**
   - Track industry reports on AI agent deployment growth
   - Estimate agent population growth
   - Apply incident rate per agent to project counts
   - Account for potential improvements in safety over time

3. **Severity Trend Analysis**
   - Calculate distribution of severities historically
   - Identify trend toward more or less severe incidents
   - Consider deployment in higher-risk sectors
   - Factor in improved safety measures

4. **Systemic Risk Projection**
   - Monitor concentration metrics
   - Track cross-sector dependencies
   - Identify correlation trends
   - Model cascade potential

### Confidence Intervals

All forecasts include:
- **95% confidence interval**: Wide range for high uncertainty
- **50% confidence interval**: Narrower range for more likely outcomes
- **Point estimate**: Central forecast value

Confidence intervals widen with:
- Longer time horizons
- Greater uncertainty in deployment trends
- Limited historical data
- Rapidly changing technology

### Assumptions

Every forecast explicitly states:
- What is assumed about deployment growth
- What is assumed about technology evolution
- What is assumed about regulatory action
- What is assumed about industry cooperation
- What is assumed about no black swan events

### Known Unknowns

Every forecast documents:
- Factors that could dramatically change outcomes
- Uncertainties in base data
- Areas where evidence is weak
- Potential for paradigm shifts

## Time Horizons

### 3-Month Forecast
**Characteristics:**
- High confidence, narrow intervals
- Based primarily on recent trends
- Limited disruption expected
- Useful for operational planning

**Data sources:**
- Recent incident trends (last 6 months)
- Current deployment metrics
- Known upcoming events (regulatory actions, product launches)

### 6-Month Forecast
**Characteristics:**
- Medium-high confidence
- Moderate intervals
- Incorporates announced trends
- Useful for tactical planning

**Data sources:**
- Medium-term deployment projections
- Known regulatory timelines
- Industry trend analysis
- Technology roadmap knowledge

### 9-Month Forecast
**Characteristics:**
- Medium confidence
- Wider intervals
- More uncertain about new deployments
- Useful for strategic planning

**Data sources:**
- All 6-month sources
- Economic projections
- Research progress indicators
- Regulatory consultation timelines

### 12-Month Forecast
**Characteristics:**
- Medium-low confidence
- Wide intervals
- Many assumptions required
- Useful for high-level strategic planning

**Data sources:**
- All 9-month sources
- Annual industry reports
- Long-term deployment forecasts
- Macro-economic projections

## Validation

### Backtesting

Every forecast is validated by:
1. Comparing earlier forecasts to actual outcomes
2. Calculating forecast accuracy over time
3. Identifying systematic errors
4. Adjusting methodology accordingly

### Peer Review

Forecasts undergo:
1. Methodological review by domain experts
2. Statistical review by quantitative analysts
3. Cross-validation against alternative approaches
4. Documentation review for clarity

### Continuous Improvement

Forecast methodology is refined through:
1. Analysis of forecast errors
2. Incorporation of new data sources
3. Adoption of better statistical methods
4. Learning from comparable forecast domains

## Integration with Incident Corpus

Forecasts are grounded in corpus data:
- All base rates computed from canonical incidents
- Severity distributions based on actual incident data
- Sector exposure computed from incident geography
- Governance gaps informed by incident analysis

## Use Cases

### For Enterprises
- Budget for incident response capabilities
- Plan governance investments
- Assess risk exposure over time
- Benchmark against industry expectations

### For Regulators
- Prioritize regulatory resources
- Plan inspection schedules
- Allocate enforcement capacity
- Inform policy timing

### For Insurers
- Assess AI-related risk pools
- Price insurance products
- Identify emerging risk areas
- Model claim trajectories

### For Investors
- Assess AI company risk profiles
- Evaluate governance quality impact
- Identify sector-specific risks
- Model potential shocks

## Publication

Forecasts are published:
- Quarterly for 3-month horizon
- Semi-annually for 6-month horizon
- Annually for 9 and 12-month horizons
- As special reports for significant events

## Ethical Considerations

Forecasts must:
- Clearly distinguish evidence from speculation
- Avoid causing unnecessary panic
- Not be used to justify premature regulation without evidence
- Be transparent about uncertainty
- Consider potential impact of forecast publication
