"""
Agent 3: Citizen Proxy Agent
Models 5 demographic groups in Kochi and their transportation behavior.
Uses an LLM to generate contextual citizen profiles for the given policy.
"""
import logging
import json
from typing import Dict, Any

from anthropic import Anthropic

from core.state import SimCityState

logger = logging.getLogger(__name__)

CITIZEN_GROUPS = [
    {
        "group": "Daily Commuters",
        "size": 450000,
        "description": "Office workers, 25-50 age, commute to CBD/Kakkanad IT corridor daily",
        "primary_concern": "travel time",
        "modal_split": {"car": 0.45, "bus": 0.30, "auto": 0.15, "two_wheeler": 0.10},
    },
    {
        "group": "Students",
        "size": 180000,
        "description": "College/school students, peak travel 7-9am and 3-6pm",
        "primary_concern": "affordability and frequency",
        "modal_split": {"bus": 0.55, "auto": 0.20, "two_wheeler": 0.15, "car": 0.10},
    },
    {
        "group": "Elderly & Differently Abled",
        "size": 95000,
        "description": "Seniors and persons with disabilities, needs accessible transport",
        "primary_concern": "accessibility and safety",
        "modal_split": {"bus": 0.40, "auto": 0.35, "car": 0.20, "walk": 0.05},
    },
    {
        "group": "Businesses & Logistics",
        "size": 65000,
        "description": "Goods vehicles, delivery, commercial transport operators",
        "primary_concern": "route reliability and delivery windows",
        "modal_split": {"truck": 0.50, "van": 0.30, "auto": 0.20},
    },
    {
        "group": "Tourists & Visitors",
        "size": 40000,
        "description": "Domestic and international tourists visiting Fort Kochi, backwaters",
        "primary_concern": "ease of navigation and scenic experience",
        "modal_split": {"taxi": 0.40, "auto": 0.30, "bus": 0.20, "ferry": 0.10},
    },
]


def citizen_proxy_agent(state: SimCityState) -> Dict[str, Any]:
    """Generate citizen impact profiles for the proposed policy using LLM."""
    logger.info("Citizen Proxy Agent: modeling demographic responses")

    client = Anthropic()

    policy = state["policy_description"]
    baseline = state["baseline_metrics"]

    prompt = f"""You are a citizen behavior analyst for Kochi, Kerala, India.

A new urban policy is being proposed:
"{policy}"

Current traffic situation:
- Average congestion: {baseline.get('avg_congestion_ratio', 0):.1%}
- Severe congestion on {baseline.get('severe_congestion_pct', 0):.1f}% of roads
- Average travel time: {baseline.get('avg_travel_time_min', 0):.1f} minutes
- Daily economic loss from congestion: ₹{baseline.get('economic_loss_inr_per_day', 0):,.0f}

For each of the following citizen groups in Kochi, provide a brief analysis of how this policy would affect them:

{json.dumps(CITIZEN_GROUPS, indent=2)}

For each group, return a JSON array where each element has:
- group: name
- affected_population: number of people directly affected
- impact_sentiment: "positive" | "negative" | "neutral" | "mixed"
- impact_score: -10 to +10 (negative = harmful, positive = beneficial)
- key_concern: one sentence describing main concern/benefit
- behavioral_change: how will this group adapt their travel behavior

Return ONLY valid JSON array, no other text."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.content[0].text.strip()

        # Clean JSON if wrapped in markdown
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        profiles = json.loads(content)

        log_msg = (
            f"Citizen Proxy: modeled {len(profiles)} demographic groups. "
            f"Groups: {', '.join(p['group'] for p in profiles)}"
        )
        logger.info(log_msg)

        return {
            "citizen_profiles": profiles,
            "agent_logs": state.get("agent_logs", []) + [log_msg],
            "status": "running",
        }
    except Exception as e:
        # Fallback: use static profiles
        logger.warning(f"LLM call failed, using static profiles: {e}")
        fallback_profiles = [
            {**g, "impact_sentiment": "mixed", "impact_score": 0,
             "key_concern": "Impact assessment pending", "behavioral_change": "To be determined",
             "affected_population": g["size"] // 3}
            for g in CITIZEN_GROUPS
        ]
        log_msg = "Citizen Proxy: using fallback static profiles (LLM unavailable)"
        return {
            "citizen_profiles": fallback_profiles,
            "agent_logs": state.get("agent_logs", []) + [log_msg],
            "status": "running",
        }
