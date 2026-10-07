import logging
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from services.analysis.statistics import (
    calculate_numeric_summary,
    calculate_categorical_summary,
    compute_correlation_matrix,
    compute_temporal_trends
)
from services.profiling import evaluate_dataset_health

logger = logging.getLogger("ai_analyst_backend.services.reports.insights")


def generate_narrative_insights(
    df: pd.DataFrame,
    health: Optional[Dict[str, Any]] = None,
    stats: Optional[Dict[str, Any]] = None,
    profile: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Synthesizes multi-dimensional findings from profiling, quality audits,
    descriptive statistics, and correlations into actionable narrative insights.
    Guaranteed to never present correlation as causation.
    """
    insights: List[Dict[str, Any]] = []

    # 1. Quality & Health Insights
    if health is None:
        try:
            health = evaluate_dataset_health(df, profile)
        except Exception:
            health = {}

    health_score = health.get("health_score", 100)
    rating = health.get("rating", "good")
    total_issues = health.get("total_issues", 0)

    insights.append({
        "category": "quality",
        "title": f"Data Quality Health Score: {health_score}/100 ({rating.upper()})",
        "observation": f"The dataset achieved a health score of {health_score} out of 100 with {total_issues} detected quality warnings.",
        "implication": "Review detected issues prior to building downstream predictive models or executive dashboards.",
        "supporting_metrics": {"health_score": health_score, "total_issues": total_issues, "rating": rating},
        "confidence": "high"
    })

    # High missingness warning
    for issue in health.get("issues", []):
        if issue.get("code") == "HIGH_NULL_RATE":
            insights.append({
                "category": "risk",
                "title": f"Significant Missingness in Column '{issue.get('column')}'",
                "observation": issue.get("message"),
                "implication": issue.get("recommendation"),
                "supporting_metrics": {"column": issue.get("column"), "metric_value": issue.get("metric_value")},
                "confidence": "high"
            })
        elif issue.get("code") == "PII_DETECTED":
            insights.append({
                "category": "risk",
                "title": f"Sensitive PII Detected in Column '{issue.get('column')}'",
                "observation": f"Patterns matching {issue.get('message')} were flagged during heuristic scanning.",
                "implication": "Anonymize or drop this column before public export or external sharing.",
                "supporting_metrics": {"column": issue.get("column")},
                "confidence": "high"
            })

    # 2. Distribution Insights
    num_stats = stats.get("numeric_summary") if stats else calculate_numeric_summary(df)
    for col, metrics in num_stats.items():
        skew = metrics.get("skewness")
        if skew is not None and abs(skew) >= 1.5:
            direction = "right-skewed (positive)" if skew > 0 else "left-skewed (negative)"
            insights.append({
                "category": "distribution",
                "title": f"Heavy Asymmetry in '{col}'",
                "observation": f"Column '{col}' exhibits significant {direction} skewness of {round(skew, 2)}.",
                "implication": "Consider using the median instead of the mean for central tendency, or apply log transformation.",
                "supporting_metrics": {"column": col, "skewness": skew, "median": metrics.get("median"), "mean": metrics.get("mean")},
                "confidence": "high"
            })

    # 3. Categorical Dominance / Concentration Insights
    cat_stats = stats.get("categorical_summary") if stats else calculate_categorical_summary(df)
    for col, cat_meta in cat_stats.items():
        top_cats = cat_meta.get("top_categories", [])
        if top_cats and len(top_cats) > 0:
            top_item = top_cats[0]
            pct = top_item.get("percentage", 0)
            if pct >= 50.0:
                insights.append({
                    "category": "distribution",
                    "title": f"Category Concentration in '{col}'",
                    "observation": f"The value '{top_item.get('value')}' constitutes {pct}% of all entries in '{col}'.",
                    "implication": "High concentration reduces diversity across segments; monitor for class imbalance.",
                    "supporting_metrics": {"column": col, "dominant_value": top_item.get("value"), "percentage": pct},
                    "confidence": "high"
                })

    # 4. Correlation Insights (Strictly non-causal)
    corr_data = stats.get("correlations") if stats else compute_correlation_matrix(df, threshold=0.5)
    sig_pairs = corr_data.get("significant_pairs", [])
    for pair in sig_pairs[:3]:
        c1 = pair.get("column_1")
        c2 = pair.get("column_2")
        r = pair.get("correlation")
        strength = pair.get("strength")
        insights.append({
            "category": "correlation",
            "title": f"{strength.title()} Association: {c1} & {c2}",
            "observation": f"A Pearson correlation coefficient of r = {r} was identified between '{c1}' and '{c2}'.",
            "implication": f"While '{c1}' and '{c2}' move in tandem, this indicates statistical correlation rather than direct causation.",
            "supporting_metrics": {"column_1": c1, "column_2": c2, "correlation": r, "strength": strength},
            "confidence": "high"
        })

    # 5. Temporal Trend Insights
    temporal = stats.get("temporal_trends") if stats else compute_temporal_trends(df)
    for t in temporal:
        insights.append({
            "category": "trend",
            "title": f"Temporal Span in '{t.get('column')}'",
            "observation": f"Dataset records span {t.get('span_days')} days from {t.get('min_date')} to {t.get('max_date')}.",
            "implication": "Temporal continuity enables historical time-series forecasting and moving average analysis.",
            "supporting_metrics": t,
            "confidence": "medium"
        })

    return insights


# ==============================================================================
# FILE SUMMARY: backend/services/reports/insights.py
# ==============================================================================
# WHAT THIS FILE CONTAINS AND DOES:
# This file provides the automated narrative insight generation service:
#   1. generate_narrative_insights(): Evaluates quality scores, distribution skewness,
#      category concentration, statistical correlations, and temporal spans.
#   2. Enforces analytical integrity: Formulates non-causal interpretations for
#      correlated numeric variables and flags severe data hygiene risks (PII, nulls).
#   3. Produces structured insight objects conforming to 'InsightItem' in schemas.py.
#
# HOW IT CONNECTS TO OTHER FILES:
# - Invoked by 'backend/services/reports/generator.py' to populate executive report summaries.
# - Utilizes 'calculate_numeric_summary', 'compute_correlation_matrix', and
#   'compute_temporal_trends' from 'backend/services/analysis/statistics.py'.
# - Reads quality evaluation audits from 'backend/services/profiling.py'.
# ==============================================================================
