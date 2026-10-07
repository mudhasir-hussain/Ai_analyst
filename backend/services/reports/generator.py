import uuid
import datetime
import logging
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
from pydantic import UUID4
from core.config import settings
from core.supabase_client import supabase
from core.exceptions import ResourceNotFoundError, DatabaseStorageError
from models.schemas import (
    ReportCreateRequest,
    ReportResponse,
    InsightItem
)
from services.profiling import evaluate_dataset_health, generate_extended_profile
from services.analysis.statistics import calculate_dataset_statistics
from services.analysis.visualizations import generate_chart_recommendations
from services.reports.insights import generate_narrative_insights
from services.ai.provider import get_llm_provider, MockLLMProvider
from services.ai.planner import extract_and_parse_json

logger = logging.getLogger("ai_analyst_backend.services.reports.generator")

_DEV_REPORTS_CACHE: Dict[str, Dict[str, Any]] = {}


def render_markdown_report(
    title: str,
    executive_summary: str,
    health_score: int,
    rating: str,
    row_count: int,
    column_count: int,
    version_number: int,
    insights: List[Dict[str, Any]],
    recommended_charts: List[Dict[str, Any]]
) -> str:
    """
    Renders a comprehensive, GitHub-Flavored Markdown report.
    """
    lines = [
        f"# {title}",
        f"**Generated:** {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')} | **Version:** v{version_number}\n",
        "---",
        "## Executive Summary",
        f"{executive_summary}\n",
        "### Key Metrics",
        f"- **Total Rows:** {row_count:,}",
        f"- **Total Columns:** {column_count}",
        f"- **Data Health Score:** {health_score}/100 ({rating.upper()})\n",
        "---",
        "## Key Findings & Narrative Insights"
    ]

    for item in insights:
        lines.append(f"### [{item.get('category', 'Finding').upper()}] {item.get('title')}")
        lines.append(f"**Observation:** {item.get('observation')}")
        if item.get("implication"):
            lines.append(f"> **Implication:** {item.get('implication')}")
        lines.append("")

    if recommended_charts:
        lines.append("---")
        lines.append("## Recommended Visualizations")
        for idx, chart in enumerate(recommended_charts, 1):
            lines.append(f"{idx}. **{chart.get('title')}** ({chart.get('chart_type').title()} Chart)")
            lines.append(f"   - *Rationale:* {chart.get('reason')}")
            if chart.get("x_column"):
                lines.append(f"   - *X-Axis:* `{chart.get('x_column')}` | *Y-Axis:* `{chart.get('y_column', 'None')}`")
        lines.append("")

    lines.append("---")
    lines.append("## Analytical Limitations & Disclaimers")
    lines.append("- Correlation observations do not establish causation.")
    lines.append("- This report reflects the immutable snapshot of this version; future transformations will produce updated summaries.")

    return "\n".join(lines)


def render_html_report(
    title: str,
    executive_summary: str,
    health_score: int,
    rating: str,
    row_count: int,
    column_count: int,
    version_number: int,
    insights: List[Dict[str, Any]],
    recommended_charts: List[Dict[str, Any]]
) -> str:
    """
    Renders a self-contained, beautifully styled modern HTML document.
    """
    rating_color = "#10B981" if health_score >= 80 else ("#F59E0B" if health_score >= 60 else "#EF4444")

    insights_html = ""
    for item in insights:
        cat = item.get("category", "info").upper()
        implication_html = f"<div class='implication'><strong>Implication:</strong> {item.get('implication')}</div>" if item.get("implication") else ""
        insights_html += f"""
        <div class="insight-card">
            <span class="badge badge-{item.get('category', 'info')}">{cat}</span>
            <h4>{item.get('title')}</h4>
            <p>{item.get('observation')}</p>
            {implication_html}
        </div>
        """

    charts_html = ""
    for idx, chart in enumerate(recommended_charts, 1):
        charts_html += f"""
        <div class="chart-item">
            <strong>{idx}. {chart.get('title')}</strong> <em>({chart.get('chart_type').title()})</em>
            <p>{chart.get('reason')}</p>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: #F8FAFC;
            color: #0F172A;
            line-height: 1.6;
            margin: 0;
            padding: 40px 20px;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: #FFFFFF;
            border-radius: 12px;
            padding: 40px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }}
        h1 {{ margin-top: 0; color: #1E293B; font-size: 28px; }}
        .meta {{ color: #64748B; font-size: 14px; margin-bottom: 24px; }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 32px;
        }}
        .metric-card {{
            background: #F1F5F9;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        .metric-card .val {{ font-size: 24px; font-weight: bold; color: #0F172A; }}
        .metric-card .lbl {{ font-size: 13px; color: #64748B; text-transform: uppercase; }}
        .executive-box {{
            background: #EFF6FF;
            border-left: 4px solid #3B82F6;
            padding: 16px 20px;
            border-radius: 4px;
            margin-bottom: 32px;
        }}
        .insight-card {{
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 16px 20px;
            margin-bottom: 16px;
        }}
        .insight-card h4 {{ margin: 8px 0; font-size: 16px; }}
        .badge {{
            display: inline-block;
            font-size: 11px;
            font-weight: 700;
            padding: 2px 8px;
            border-radius: 4px;
            text-transform: uppercase;
        }}
        .badge-quality {{ background: #DCFCE7; color: #166534; }}
        .badge-risk {{ background: #FEE2E2; color: #991B1B; }}
        .badge-distribution {{ background: #FEF3C7; color: #92400E; }}
        .badge-correlation {{ background: #E0E7FF; color: #3730A3; }}
        .badge-trend {{ background: #F3E8FF; color: #6B21A8; }}
        .implication {{
            background: #F8FAFC;
            padding: 8px 12px;
            border-radius: 4px;
            font-size: 13px;
            color: #475569;
            margin-top: 8px;
        }}
        .chart-item {{
            padding: 12px 0;
            border-bottom: 1px solid #F1F5F9;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #E2E8F0;
            font-size: 12px;
            color: #94A3B8;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        <div class="meta">
            Generated on {datetime.datetime.now(datetime.timezone.utc).strftime('%B %d, %Y at %H:%M UTC')} &bull; Version v{version_number}
        </div>

        <div class="metrics-grid">
            <div class="metric-card">
                <div class="val">{row_count:,}</div>
                <div class="lbl">Rows</div>
            </div>
            <div class="metric-card">
                <div class="val">{column_count}</div>
                <div class="lbl">Columns</div>
            </div>
            <div class="metric-card">
                <div class="val" style="color: {rating_color};">{health_score}/100</div>
                <div class="lbl">Health Score ({rating})</div>
            </div>
        </div>

        <div class="executive-box">
            <h3 style="margin-top:0;">Executive Summary</h3>
            <p style="margin-bottom:0;">{executive_summary}</p>
        </div>

        <h2>Key Findings & Insights</h2>
        {insights_html}

        <h2>Recommended Visualizations</h2>
        {charts_html}

        <div class="footer">
            Generated by AI Data Analyst Platform &bull; Immutable Version Audit v{version_number} &bull; Non-causal observations
        </div>
    </div>
</body>
</html>
"""
    return html


def generate_ai_executive_summary_and_insights(
    df: pd.DataFrame,
    health: Dict[str, Any],
    stats: Dict[str, Any],
    profile: Dict[str, Any],
    title: str
) -> Optional[Tuple[str, List[Dict[str, Any]]]]:
    """
    Attempts to prompt the configured LLM (Ollama/Qwen/LLaMA/OpenAI) to generate
    an executive-ready narrative summary and strategic business insights.
    Falls back to None if the model is unreachable, times out, or fails.
    """
    try:
        import os
        if os.environ.get("PYTEST_CURRENT_TEST") or settings.ENVIRONMENT == "test":
            return None
        provider = get_llm_provider(timeout=15)
        # If it's the mock rule-based parser in offline test mode (not fallback), skip to preserve fast testing
        if isinstance(provider, MockLLMProvider) and "fallback" not in getattr(provider, "model", ""):
            return None

        health_score = health.get("health_score", 100)
        rating = health.get("rating", "good")
        issues = health.get("issues", [])
        issue_strs = [f"- [{i.get('level', 'warning').upper()}]: {i.get('message')} ({i.get('recommendation', '')})" for i in issues[:4]]

        numeric_summary = stats.get("numeric_summary", {})
        num_strs = []
        for col, m in list(numeric_summary.items())[:6]:
            num_strs.append(
                f"- {col}: mean={m.get('mean')}, median={m.get('median')}, min={m.get('min')}, max={m.get('max')}, skew={m.get('skewness')}"
            )

        cat_summary = stats.get("categorical_summary", {})
        cat_strs = []
        for col, c in list(cat_summary.items())[:4]:
            top_cats = c.get("top_categories", [])
            top_desc = f"dominant='{top_cats[0].get('value')}' ({top_cats[0].get('percentage')}%)" if top_cats else "distributed"
            cat_strs.append(f"- {col}: {c.get('unique_count')} unique categories, {top_desc}")

        correlations = stats.get("correlations", {}).get("significant_pairs", [])
        corr_strs = [
            f"- {p.get('column_1')} vs {p.get('column_2')}: Pearson r={p.get('correlation')} ({p.get('strength')})"
            for p in correlations[:3]
        ]

        system_prompt = """You are a Principal Data Scientist and Chief Analytics Officer.
Analyze the provided dataset profile and produce an executive-ready business intelligence report.
Output MUST be ONLY a single valid JSON object, without markdown formatting or preamble, conforming strictly to this schema:
{
  "executive_summary": "2-3 comprehensive, analytical paragraphs synthesizing operational metrics, business health, critical data hygiene risks, and high-level strategic takeaways.",
  "insights": [
    {
      "category": "strategic" | "risk" | "opportunity" | "quality",
      "title": "Concise business-focused headline",
      "observation": "Empirical observation backed by statistics in the dataset",
      "implication": "Strategic consequence and concrete actionable recommendation for leadership",
      "confidence": "high" | "medium"
    }
  ]
}
"""

        user_prompt = f"""REPORT TITLE: {title}
DATASET OVERVIEW:
- Total Records: {len(df):,}, Total Variables: {len(df.columns)}
- Data Health Hygiene Score: {health_score}/100 ({rating.upper()})
- Quality Flags:
{chr(10).join(issue_strs) if issue_strs else "- No severe data hygiene defects detected"}

NUMERIC ATTRIBUTES:
{chr(10).join(num_strs) if num_strs else "- None"}

CATEGORICAL DISTRIBUTIONS:
{chr(10).join(cat_strs) if cat_strs else "- None"}

CORRELATIONS:
{chr(10).join(corr_strs) if corr_strs else "- No significant pairwise correlations"}

Please synthesize this into an executive summary and strategic findings."""

        logger.info(f"Prompting LLM ({type(provider).__name__}) for AI-enhanced executive report")
        raw_response = provider.generate(system_prompt=system_prompt, user_prompt=user_prompt)
        parsed = extract_and_parse_json(raw_response)

        exec_sum = parsed.get("executive_summary")
        insights = parsed.get("insights", [])

        if exec_sum and isinstance(insights, list) and len(insights) > 0:
            formatted_insights = []
            for item in insights:
                formatted_insights.append({
                    "category": item.get("category", "strategic"),
                    "title": item.get("title", "Key Finding"),
                    "observation": item.get("observation", ""),
                    "implication": item.get("implication", ""),
                    "confidence": item.get("confidence", "high"),
                    "supporting_metrics": item.get("supporting_metrics", {})
                })
            return str(exec_sum).strip(), formatted_insights

    except Exception as e:
        logger.warning(f"AI executive report generation failed or timed out: {e}. Falling back to deterministic statistical engine.")

    return None


def generate_dataset_report(
    df: pd.DataFrame,
    dataset_id: UUID4,
    version_id: UUID4,
    version_number: int,
    user_id: UUID4,
    request: ReportCreateRequest,
    profile: Optional[Dict[str, Any]] = None,
    health: Optional[Dict[str, Any]] = None,
    stats: Optional[Dict[str, Any]] = None
) -> ReportResponse:
    """
    Coordinates end-to-end report generation across JSON, Markdown, or HTML formats.
    Attempts AI-enhanced intelligence first, gracefully falling back to deterministic heuristics.
    """
    logger.info(f"Generating report for dataset {dataset_id} in format '{request.format}'")
    report_id = uuid.uuid4()
    now = datetime.datetime.now(datetime.timezone.utc)
    title = request.title or f"Executive Data Analysis Report - v{version_number}"

    if profile is None:
        profile = generate_extended_profile(df)
    if health is None:
        health = evaluate_dataset_health(df, profile)
    if stats is None:
        stats = calculate_dataset_statistics(df)

    health_score = health.get("health_score", 100)
    rating = health.get("rating", "good")

    # 1. Attempt AI-enhanced report generation
    ai_result = generate_ai_executive_summary_and_insights(
        df=df,
        health=health,
        stats=stats,
        profile=profile,
        title=title
    )

    if ai_result:
        executive_summary, insights_dicts = ai_result
        logger.info("Successfully generated AI-enhanced executive summary and narrative insights.")
    else:
        logger.info("Using deterministic statistical engine for executive report.")
        # Fallback to deterministic narrative insights
        insights_dicts = generate_narrative_insights(df, health=health, stats=stats, profile=profile)
        executive_summary = (
            f"This dataset contains {len(df):,} records and {len(df.columns)} variables with an overall "
            f"data hygiene score of {health_score}/100 ({rating.capitalize()}). "
            f"Analysis revealed {len(insights_dicts)} key findings across data quality, value distributions, "
            f"and feature correlations."
        )

    insight_items = [InsightItem(**item) for item in insights_dicts]

    # Generate chart recommendations if requested
    recommended_charts = generate_chart_recommendations(df) if request.include_charts else []

    rendered_content: Optional[str] = None
    fmt = request.format.lower()

    if fmt == "markdown":
        rendered_content = render_markdown_report(
            title=title,
            executive_summary=executive_summary,
            health_score=health_score,
            rating=rating,
            row_count=len(df),
            column_count=len(df.columns),
            version_number=version_number,
            insights=insights_dicts,
            recommended_charts=recommended_charts
        )
    elif fmt == "html":
        rendered_content = render_html_report(
            title=title,
            executive_summary=executive_summary,
            health_score=health_score,
            rating=rating,
            row_count=len(df),
            column_count=len(df.columns),
            version_number=version_number,
            insights=insights_dicts,
            recommended_charts=recommended_charts
        )

    report_record = {
        "id": str(report_id),
        "dataset_id": str(dataset_id),
        "version_id": str(version_id),
        "version_number": version_number,
        "title": title,
        "format": fmt,
        "executive_summary": executive_summary,
        "health_score": health_score,
        "insights": insights_dicts,
        "content": rendered_content,
        "created_at": now.isoformat(),
        "created_by": str(user_id)
    }

    if settings.SUPABASE_URL == "https://your-supabase-project.supabase.co":
        _DEV_REPORTS_CACHE[str(report_id)] = report_record
    else:
        try:
            supabase.table("reports").insert(report_record).execute()
        except Exception as e:
            logger.warning(f"Could not persist report to Supabase: {e}. Storing in dev cache.")
            _DEV_REPORTS_CACHE[str(report_id)] = report_record

    return ReportResponse(
        id=report_id,
        dataset_id=dataset_id,
        version_id=version_id,
        version_number=version_number,
        title=title,
        format=fmt,
        executive_summary=executive_summary,
        health_score=health_score,
        insights=insight_items,
        content=rendered_content,
        created_at=now,
        created_by=user_id
    )


def get_dataset_report(report_id: UUID4) -> ReportResponse:
    """
    Retrieves a previously generated report by ID.
    """
    report_data = _DEV_REPORTS_CACHE.get(str(report_id))
    if not report_data:
        if settings.SUPABASE_URL != "https://your-supabase-project.supabase.co":
            res = supabase.table("reports").select("*").eq("id", str(report_id)).execute()
            if res.data:
                report_data = res.data[0]

    if not report_data:
        raise ResourceNotFoundError(f"Report with ID '{report_id}' not found.", "REPORT_NOT_FOUND")

    created_at = report_data.get("created_at")
    if isinstance(created_at, str):
        created_at = datetime.datetime.fromisoformat(created_at)

    return ReportResponse(
        id=UUID4(str(report_data["id"])),
        dataset_id=UUID4(str(report_data["dataset_id"])),
        version_id=UUID4(str(report_data["version_id"])),
        version_number=report_data.get("version_number", 1),
        title=report_data.get("title", "Executive Report"),
        format=report_data.get("format", "json"),
        executive_summary=report_data.get("executive_summary", ""),
        health_score=report_data.get("health_score", 100),
        insights=[InsightItem(**i) for i in report_data.get("insights", [])],
        content=report_data.get("content"),
        created_at=created_at or datetime.datetime.now(datetime.timezone.utc),
        created_by=UUID4(str(report_data["created_by"]))
    )


# ==============================================================================
# FILE SUMMARY: backend/services/reports/generator.py
# ==============================================================================
# WHAT THIS FILE CONTAINS AND DOES:
# This file provides the Executive Report Generation Engine:
#   1. render_markdown_report(): Compiles structured insights, metrics, and chart specs
#      into clean GitHub-Flavored Markdown.
#   2. render_html_report(): Generates standalone, responsive HTML reports with CSS badges,
#      metric cards, and printable styling.
#   3. generate_dataset_report(): Master coordinator generating JSON, Markdown, or HTML reports,
#      persisting records, and returning 'ReportResponse'.
#   4. get_dataset_report(): Fetches a previously generated report by UUID.
#
# HOW IT CONNECTS TO OTHER FILES:
# - Invoked by endpoints POST /datasets/{dataset_id}/reports and GET /reports/{report_id}
#   in 'backend/api/datasets.py'.
# - Consumes 'generate_narrative_insights' from 'backend/services/reports/insights.py'.
# - Consumes 'calculate_dataset_statistics' and 'generate_chart_recommendations'
#   from 'backend/services/analysis/'.
# - Returns Pydantic models from 'backend/models/schemas.py' ('ReportResponse', 'InsightItem').
# ==============================================================================
