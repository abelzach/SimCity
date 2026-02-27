"""
Agent 5: Impact Analysis Agent
Quantifies the before/after delta across all key metrics.
"""
import logging
from typing import Dict, Any

from core.state import SimCityState

logger = logging.getLogger(__name__)


def _severity(delta_pct: float, direction: str = "lower_is_better") -> str:
    """Categorize impact severity."""
    if direction == "lower_is_better":
        if delta_pct < -15:
            return "highly_positive"
        elif delta_pct < -5:
            return "positive"
        elif delta_pct < 5:
            return "neutral"
        elif delta_pct < 15:
            return "negative"
        else:
            return "highly_negative"
    else:  # higher_is_better
        if delta_pct > 15:
            return "highly_positive"
        elif delta_pct > 5:
            return "positive"
        elif delta_pct > -5:
            return "neutral"
        elif delta_pct > -15:
            return "negative"
        else:
            return "highly_negative"


def impact_analysis_agent(state: SimCityState) -> Dict[str, Any]:
    """Compute quantified impact scores comparing baseline vs. post-policy."""
    logger.info("Impact Analysis Agent: computing deltas")

    try:
        baseline = state["baseline_metrics"]
        sim_results = state.get("simulation_results", {})
        post = sim_results.get("post_policy_metrics", {})
        citizen_profiles = state.get("citizen_profiles", [])

        def pct_change(before, after):
            if before == 0:
                return 0
            return round((after - before) / before * 100, 1)

        # Core traffic metrics
        congestion_delta = pct_change(
            baseline.get("avg_congestion_ratio", 0),
            post.get("avg_congestion_ratio", 0),
        )
        travel_time_delta = pct_change(
            baseline.get("avg_travel_time_min", 0),
            post.get("avg_travel_time_min", 0),
        )
        co2_delta = pct_change(
            baseline.get("daily_co2_kg", 0),
            post.get("daily_co2_kg", 0),
        )
        economic_delta = pct_change(
            baseline.get("economic_loss_inr_per_day", 0),
            post.get("economic_loss_inr_per_day", 0),
        )
        severe_congestion_delta = pct_change(
            baseline.get("severe_congestion_pct", 0),
            post.get("severe_congestion_pct", 0),
        )

        # Absolute changes
        travel_time_abs = round(
            post.get("avg_travel_time_min", 0) - baseline.get("avg_travel_time_min", 0), 2
        )
        co2_abs = round(post.get("daily_co2_kg", 0) - baseline.get("daily_co2_kg", 0), 1)
        economic_abs = round(
            post.get("economic_loss_inr_per_day", 0) - baseline.get("economic_loss_inr_per_day", 0)
        )

        # Citizen satisfaction composite score
        citizen_impact = []
        overall_satisfaction = 0
        if citizen_profiles:
            for profile in citizen_profiles:
                score = profile.get("impact_score", 0)
                pop = profile.get("affected_population", 0)
                citizen_impact.append({
                    "group": profile.get("group"),
                    "impact_score": score,
                    "sentiment": profile.get("impact_sentiment", "neutral"),
                    "key_concern": profile.get("key_concern", ""),
                    "affected_population": pop,
                })
            # Weighted average
            total_pop = sum(c.get("affected_population", 1) for c in citizen_profiles)
            if total_pop > 0:
                overall_satisfaction = sum(
                    p.get("impact_score", 0) * p.get("affected_population", 0)
                    for p in citizen_profiles
                ) / total_pop

        impact_scores = {
            "congestion": {
                "before": baseline.get("avg_congestion_ratio", 0),
                "after": post.get("avg_congestion_ratio", 0),
                "delta_pct": congestion_delta,
                "severity": _severity(congestion_delta, "lower_is_better"),
                "label": "Average Congestion",
                "unit": "%",
            },
            "travel_time": {
                "before": baseline.get("avg_travel_time_min", 0),
                "after": post.get("avg_travel_time_min", 0),
                "delta_pct": travel_time_delta,
                "delta_abs": travel_time_abs,
                "severity": _severity(travel_time_delta, "lower_is_better"),
                "label": "Avg Travel Time",
                "unit": "min",
            },
            "co2_emissions": {
                "before": baseline.get("daily_co2_kg", 0),
                "after": post.get("daily_co2_kg", 0),
                "delta_pct": co2_delta,
                "delta_abs": co2_abs,
                "severity": _severity(co2_delta, "lower_is_better"),
                "label": "Daily CO₂ Emissions",
                "unit": "kg",
            },
            "economic_loss": {
                "before": baseline.get("economic_loss_inr_per_day", 0),
                "after": post.get("economic_loss_inr_per_day", 0),
                "delta_pct": economic_delta,
                "delta_abs": economic_abs,
                "severity": _severity(economic_delta, "lower_is_better"),
                "label": "Economic Loss",
                "unit": "INR/day",
            },
            "severe_congestion_roads": {
                "before": baseline.get("severe_congestion_pct", 0),
                "after": post.get("severe_congestion_pct", 0),
                "delta_pct": severe_congestion_delta,
                "severity": _severity(severe_congestion_delta, "lower_is_better"),
                "label": "Severely Congested Roads",
                "unit": "%",
            },
            "citizen_satisfaction": {
                "score": round(overall_satisfaction, 2),
                "max_score": 10,
                "severity": _severity(-overall_satisfaction * 10, "lower_is_better"),
                "label": "Citizen Satisfaction",
                "unit": "/ 10",
                "by_group": citizen_impact,
            },
        }

        log_msg = (
            f"Impact Analysis: congestion {congestion_delta:+.1f}%, "
            f"travel time {travel_time_delta:+.1f}%, "
            f"CO₂ {co2_delta:+.1f}%, "
            f"economic impact ₹{economic_abs:+,.0f}/day"
        )
        logger.info(log_msg)

        return {
            "impact_scores": impact_scores,
            "agent_logs": state.get("agent_logs", []) + [log_msg],
            "status": "running",
        }
    except Exception as e:
        err = f"Impact Analysis Agent error: {e}"
        logger.error(err)
        return {
            "status": "error",
            "error": err,
            "agent_logs": state.get("agent_logs", []) + [err],
        }
