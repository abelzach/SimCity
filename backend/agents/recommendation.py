"""
Agent 6: Recommendation Agent
Synthesizes all agent outputs into a structured policy recommendation report.
"""
import logging
import json
from typing import Dict, Any

from anthropic import Anthropic

from core.state import SimCityState

logger = logging.getLogger(__name__)


def recommendation_agent(state: SimCityState) -> Dict[str, Any]:
    """Generate a structured policy recommendation report using LLM."""
    logger.info("Recommendation Agent: generating final report")

    client = Anthropic()

    policy = state["policy_description"]
    baseline = state["baseline_metrics"]
    impact = state.get("impact_scores", {})
    citizen_profiles = state.get("citizen_profiles", [])
    sim_results = state.get("simulation_results", {})
    policy_params = sim_results.get("policy_params", {})

    # Build concise impact summary for prompt
    impact_summary = {}
    for key, data in impact.items():
        if isinstance(data, dict) and "delta_pct" in data:
            impact_summary[key] = {
                "before": data.get("before"),
                "after": data.get("after"),
                "change": f"{data['delta_pct']:+.1f}%",
                "severity": data.get("severity"),
            }

    citizen_summary = [
        {
            "group": p.get("group"),
            "sentiment": p.get("impact_sentiment"),
            "score": p.get("impact_score"),
            "concern": p.get("key_concern"),
        }
        for p in citizen_profiles
    ]

    prompt = f"""You are a senior urban policy advisor for the Kochi Municipal Corporation.

POLICY PROPOSAL:
"{policy}"

POLICY TYPE: {policy_params.get('policy_type', 'unknown')}
SCOPE: {policy_params.get('scope', 'unknown')}
AREA AFFECTED: {policy_params.get('affected_area', 'Kochi')}

BASELINE CONDITIONS:
- Average congestion: {baseline.get('avg_congestion_ratio', 0):.1%}
- Daily CO₂ emissions: {baseline.get('daily_co2_kg', 0):,.0f} kg
- Daily economic loss from congestion: ₹{baseline.get('economic_loss_inr_per_day', 0):,.0f}

SIMULATED IMPACT:
{json.dumps(impact_summary, indent=2)}

CITIZEN SENTIMENT:
{json.dumps(citizen_summary, indent=2)}

Write a professional policy recommendation report in Markdown with these exact sections:

## Executive Summary
2-3 sentences summarizing the policy and its overall impact.

## Key Findings
3-5 bullet points with the most important quantitative findings.

## Stakeholder Impact Analysis
A brief assessment of how each citizen group is affected.

## Risks & Mitigations
2-3 key risks and practical mitigation strategies.

## Implementation Roadmap
3-4 phased steps for rolling out this policy effectively.

## Final Recommendation
**VERDICT: [GO / NO-GO / MODIFY]**
A clear, evidence-based recommendation with conditions if applicable.

Be specific, cite the numbers from the impact analysis, and keep the total report under 600 words."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        report = response.content[0].text

        log_msg = "Recommendation Agent: policy analysis report generated successfully"
        logger.info(log_msg)

        return {
            "recommendations": report,
            "agent_logs": state.get("agent_logs", []) + [log_msg],
            "status": "completed",
        }
    except Exception as e:
        err = f"Recommendation Agent error: {e}"
        logger.error(err)
        fallback_report = f"""## Policy Analysis: {policy}

**Status**: Analysis completed with limited AI assistance.

### Key Metrics
- Congestion change: {impact.get('congestion', {}).get('delta_pct', 'N/A')}%
- Travel time change: {impact.get('travel_time', {}).get('delta_pct', 'N/A')}%
- CO₂ change: {impact.get('co2_emissions', {}).get('delta_pct', 'N/A')}%

Please review the impact metrics above for a detailed assessment.
"""
        return {
            "recommendations": fallback_report,
            "agent_logs": state.get("agent_logs", []) + [err],
            "status": "completed",
        }
