import logging
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
from core.exceptions import DatasetValidationError
from services.analysis.statistics import safe_float, compute_correlation_matrix

logger = logging.getLogger("ai_analyst_backend.services.analysis.visualizations")


def generate_chart_recommendations(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Intelligently inspects column data types, cardinalities, and statistical
    properties to recommend the 3-5 most informative visualizations.
    """
    recommendations: List[Dict[str, Any]] = []
    numeric_cols = list(df.select_dtypes(include=[np.number]).columns)
    non_numeric_cols = list(df.select_dtypes(exclude=[np.number]).columns)

    # 1. Detect datetime / temporal columns
    date_col = None
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            date_col = col
            break
        lower = col.lower()
        if any(term in lower for term in ["date", "time", "timestamp", "year", "month"]):
            try:
                converted = pd.to_datetime(df[col], errors="coerce")
                if converted.notna().sum() > len(df) * 0.5:
                    date_col = col
                    break
            except Exception:
                pass

    # Recommendation A: Line Chart for time series
    if date_col and numeric_cols:
        target_num = numeric_cols[0]
        recommendations.append({
            "chart_type": "line",
            "title": f"{target_num.replace('_', ' ').title()} Over Time",
            "x_column": date_col,
            "y_column": target_num,
            "aggregation": "mean",
            "reason": f"Visualizes temporal trajectory and trends of {target_num} across chronological intervals in {date_col}.",
            "config": {"time_series": True, "stroke_color": "#3B82F6"}
        })

    # Recommendation B: Bar Chart for categorical vs numeric
    low_card_cats = [c for c in non_numeric_cols if 1 < df[c].nunique() <= 30]
    if low_card_cats and numeric_cols:
        cat_col = low_card_cats[0]
        num_col = numeric_cols[0]
        recommendations.append({
            "chart_type": "bar",
            "title": f"Total {num_col.replace('_', ' ').title()} by {cat_col.replace('_', ' ').title()}",
            "x_column": cat_col,
            "y_column": num_col,
            "aggregation": "sum",
            "reason": f"Compares aggregate totals of {num_col} across distinct {cat_col} groups.",
            "config": {"layout": "vertical", "fill_color": "#10B981"}
        })
    elif low_card_cats:
        cat_col = low_card_cats[0]
        recommendations.append({
            "chart_type": "bar",
            "title": f"Frequency Distribution of {cat_col.replace('_', ' ').title()}",
            "x_column": cat_col,
            "y_column": None,
            "aggregation": "count",
            "reason": f"Displays the count of occurrences across each distinct category in {cat_col}.",
            "config": {"layout": "vertical", "fill_color": "#6366F1"}
        })

    # Recommendation C: Scatter Plot for two correlated numerics
    if len(numeric_cols) >= 2:
        corr_data = compute_correlation_matrix(df, threshold=0.3)
        pairs = corr_data.get("significant_pairs", [])
        if pairs:
            top_pair = pairs[0]
            col1 = top_pair["column_1"]
            col2 = top_pair["column_2"]
            r = top_pair["correlation"]
            recommendations.append({
                "chart_type": "scatter",
                "title": f"{col1.title()} vs. {col2.title()} (r = {r})",
                "x_column": col1,
                "y_column": col2,
                "aggregation": "none",
                "reason": f"Highlights the {top_pair['strength']} linear relationship (Pearson r={r}) between {col1} and {col2}.",
                "config": {"point_size": 4, "point_color": "#8B5CF6"}
            })
        else:
            recommendations.append({
                "chart_type": "scatter",
                "title": f"{numeric_cols[0].title()} vs. {numeric_cols[1].title()}",
                "x_column": numeric_cols[0],
                "y_column": numeric_cols[1],
                "aggregation": "none",
                "reason": "Explores value clustering and spread between two continuous numeric variables.",
                "config": {"point_size": 4, "point_color": "#8B5CF6"}
            })

    # Recommendation D: Histogram for continuous numeric distribution
    if numeric_cols:
        target_num = numeric_cols[0]
        recommendations.append({
            "chart_type": "histogram",
            "title": f"Distribution of {target_num.replace('_', ' ').title()}",
            "x_column": target_num,
            "y_column": None,
            "aggregation": "count",
            "reason": f"Reveals central tendency, spread, and skewness of {target_num}.",
            "config": {"bins": 15, "fill_color": "#F59E0B"}
        })

    # Recommendation E: Correlation Heatmap for multiple numerics
    if len(numeric_cols) >= 3:
        recommendations.append({
            "chart_type": "heatmap",
            "title": "Numeric Feature Correlation Heatmap",
            "x_column": None,
            "y_column": None,
            "aggregation": "none",
            "reason": f"Displays pairwise Pearson correlations across all {len(numeric_cols)} numeric attributes simultaneously.",
            "config": {"color_scale": "interpolateRdBu"}
        })

    # Recommendation F: Box Plot for spread and outliers
    if numeric_cols:
        target_num = numeric_cols[-1]
        recommendations.append({
            "chart_type": "box",
            "title": f"{target_num.replace('_', ' ').title()} Quartiles & Outlier Box Plot",
            "x_column": low_card_cats[0] if low_card_cats else None,
            "y_column": target_num,
            "aggregation": "none",
            "reason": f"Visualizes median, interquartile range (IQR), and statistical outlier points for {target_num}.",
            "config": {"show_outliers": True, "fill_color": "#EC4899"}
        })

    return recommendations[:5]


def build_visualization_data(
    df: pd.DataFrame,
    chart_type: str,
    x_column: Optional[str] = None,
    y_column: Optional[str] = None,
    aggregation: Optional[str] = "sum",
    group_by_column: Optional[str] = None,
    limit: int = 20
) -> Dict[str, Any]:
    """
    Transforms DataFrame data into frontend-ready chart series for
    bar, line, scatter, histogram, box, and heatmap visualizations.
    """
    valid_charts = {"bar", "line", "scatter", "histogram", "box", "heatmap"}
    if chart_type not in valid_charts:
        raise DatasetValidationError(
            detail=f"Unsupported chart_type '{chart_type}'. Allowed types: {sorted(list(valid_charts))}",
            error_code="INVALID_CHART_TYPE"
        )

    # Validate column references
    if x_column and x_column not in df.columns:
        raise DatasetValidationError(f"Column '{x_column}' not found in dataset.", "COLUMN_NOT_FOUND")
    if y_column and y_column not in df.columns:
        raise DatasetValidationError(f"Column '{y_column}' not found in dataset.", "COLUMN_NOT_FOUND")

    insights: List[str] = []
    warnings: List[str] = []
    chart_data: List[Dict[str, Any]] = []
    title = f"{chart_type.title()} Chart"

    # ==========================
    # 1. BAR CHART
    # ==========================
    if chart_type == "bar":
        if not x_column:
            # Fallback to first non-numeric column
            non_nums = df.select_dtypes(exclude=[np.number]).columns
            x_column = non_nums[0] if len(non_nums) > 0 else df.columns[0]

        title = f"{x_column.replace('_', ' ').title()} Breakdown"

        # Case A: Categorical count
        if not y_column or aggregation == "count":
            val_counts = df[x_column].astype(str).value_counts()
            total_count = val_counts.sum()

            top_slice = val_counts.head(limit)
            for k, count in top_slice.items():
                pct = round((count / total_count) * 100, 1) if total_count > 0 else 0
                chart_data.append({
                    x_column: str(k),
                    "name": str(k),
                    "count": int(count),
                    "value": int(count),
                    "percentage": pct
                })

            if len(val_counts) > limit:
                other_count = int(val_counts.iloc[limit:].sum())
                chart_data.append({
                    x_column: "Other",
                    "name": "Other",
                    "count": other_count,
                    "value": other_count,
                    "percentage": round((other_count / total_count) * 100, 1)
                })
                warnings.append(f"High cardinality: {len(val_counts) - limit} categories grouped into 'Other'.")

            if chart_data:
                top_item = chart_data[0]
                insights.append(f"Category '{top_item[x_column]}' is dominant with {top_item['count']} entries ({top_item['percentage']}% of total).")

        # Case B: Categorical vs Numeric aggregated
        else:
            numeric_y = pd.to_numeric(df[y_column], errors="coerce")
            if numeric_y.dropna().empty:
                raise DatasetValidationError(f"Column '{y_column}' must contain numeric data for aggregation.", "INVALID_COLUMN_TYPE")

            title = f"{aggregation.title()} of {y_column.replace('_', ' ').title()} by {x_column.replace('_', ' ').title()}"
            agg_method = aggregation.lower()
            valid_aggs = {"sum": "sum", "mean": "mean", "min": "min", "max": "max", "median": "median"}
            agg_func = valid_aggs.get(agg_method, "sum")

            temp_df = pd.DataFrame({x_column: df[x_column], y_column: numeric_y}).dropna()
            grouped = temp_df.groupby(x_column)[y_column].agg(agg_func).reset_index()
            grouped = grouped.sort_values(by=y_column, ascending=False)

            top_slice = grouped.head(limit)
            total_sum = grouped[y_column].sum()

            for _, row in top_slice.iterrows():
                val = safe_float(row[y_column])
                chart_data.append({
                    x_column: str(row[x_column]),
                    "name": str(row[x_column]),
                    y_column: val,
                    "value": val
                })

            if len(grouped) > limit:
                remaining_val = safe_float(grouped.iloc[limit:][y_column].agg(agg_func))
                chart_data.append({
                    x_column: "Other",
                    "name": "Other",
                    y_column: remaining_val,
                    "value": remaining_val
                })
                warnings.append(f"High cardinality: {len(grouped) - limit} groups combined into 'Other'.")

            if chart_data and total_sum and total_sum > 0:
                top_val = chart_data[0][y_column] or 0
                pct = round((top_val / total_sum) * 100, 1)
                insights.append(f"Top group '{chart_data[0][x_column]}' represents {pct}% of the aggregate sum.")

    # ==========================
    # 2. LINE CHART
    # ==========================
    elif chart_type == "line":
        if not x_column:
            x_column = df.columns[0]
        if not y_column:
            nums = df.select_dtypes(include=[np.number]).columns
            if len(nums) == 0:
                raise DatasetValidationError("Line chart requires at least one numeric column for the y-axis.", "NO_NUMERIC_COLUMNS")
            y_column = nums[0]

        title = f"{y_column.replace('_', ' ').title()} over {x_column.replace('_', ' ').title()}"

        numeric_y = pd.to_numeric(df[y_column], errors="coerce")
        clean_df = pd.DataFrame({x_column: df[x_column], y_column: numeric_y}).dropna().copy()

        # Sort by x_column
        try:
            clean_df[x_column] = pd.to_datetime(clean_df[x_column], errors="ignore")
        except Exception:
            pass
        clean_df = clean_df.sort_values(by=x_column)

        if len(clean_df) > limit * 3:
            step = max(1, len(clean_df) // 100)
            sample_df = clean_df.iloc[::step]
            warnings.append(f"Dataset downsampled from {len(clean_df)} to {len(sample_df)} points for smooth rendering.")
        else:
            sample_df = clean_df

        for _, row in sample_df.iterrows():
            val = safe_float(row[y_column])
            chart_data.append({
                x_column: str(row[x_column]),
                "name": str(row[x_column]),
                y_column: val,
                "value": val
            })

        if len(chart_data) > 1:
            first_val = chart_data[0]["value"]
            last_val = chart_data[-1]["value"]
            if first_val and last_val and first_val != 0:
                pct_change = round(((last_val - first_val) / abs(first_val)) * 100, 1)
                direction = "increased" if pct_change > 0 else "decreased"
                insights.append(f"Over the recorded sequence, {y_column} {direction} by {abs(pct_change)}%.")

    # ==========================
    # 3. SCATTER PLOT
    # ==========================
    elif chart_type == "scatter":
        numeric_cols = list(df.select_dtypes(include=[np.number]).columns)
        if len(numeric_cols) < 1:
            raise DatasetValidationError("Scatter plot requires numeric columns.", "INSUFFICIENT_NUMERIC_COLUMNS")

        x_col = x_column or numeric_cols[0]
        y_col = y_column or (numeric_cols[1] if len(numeric_cols) > 1 else numeric_cols[0])

        x_series = pd.to_numeric(df[x_col], errors="coerce")
        y_series = pd.to_numeric(df[y_col], errors="coerce")

        # If user picked a non-numeric column, fallback gracefully to valid numeric columns
        if x_series.dropna().empty:
            x_col = numeric_cols[0]
            x_series = pd.to_numeric(df[x_col], errors="coerce")
            warnings.append(f"X-axis fallback: selected column '{x_column}' was non-numeric, defaulted to '{x_col}'.")

        if y_series.dropna().empty:
            y_col = numeric_cols[1] if len(numeric_cols) > 1 else numeric_cols[0]
            y_series = pd.to_numeric(df[y_col], errors="coerce")
            warnings.append(f"Y-axis fallback: selected column '{y_column}' was non-numeric, defaulted to '{y_col}'.")

        title = f"{x_col.replace('_', ' ').title()} vs {y_col.replace('_', ' ').title()}"

        clean_df = pd.DataFrame({x_col: x_series, y_col: y_series}).dropna()
        if len(clean_df) > 500:
            clean_df = clean_df.sample(n=500, random_state=42)
            warnings.append(f"Sampled 500 points from {len(df)} total rows to preserve chart responsiveness.")

        for _, row in clean_df.iterrows():
            xv = safe_float(row[x_col])
            yv = safe_float(row[y_col])
            chart_data.append({
                x_col: xv,
                y_col: yv,
                "x": xv,
                "y": yv
            })

        if len(clean_df) > 1 and clean_df[x_col].std() > 0 and clean_df[y_col].std() > 0:
            corr = safe_float(clean_df[x_col].corr(clean_df[y_col]))
            if corr is not None:
                insights.append(f"Pearson correlation coefficient between {x_col} and {y_col} is {corr}.")

        x_column = x_col
        y_column = y_col

    # ==========================
    # 4. HISTOGRAM
    # ==========================
    elif chart_type == "histogram":
        col = x_column or y_column
        if not col or pd.to_numeric(df[col], errors="coerce").dropna().empty:
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) == 0:
                raise DatasetValidationError("Histogram requires a numeric column.", "NO_NUMERIC_COLUMNS")
            col = numeric_cols[0]

        series = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(series) == 0:
            raise DatasetValidationError(f"Column '{col}' has no valid numeric values.", "EMPTY_NUMERIC_SERIES")

        title = f"Distribution of {col.replace('_', ' ').title()}"
        num_bins = 15
        counts, bin_edges = np.histogram(series, bins=num_bins)

        for i in range(len(counts)):
            b_start = safe_float(bin_edges[i])
            b_end = safe_float(bin_edges[i + 1])
            chart_data.append({
                "bin_start": b_start,
                "bin_end": b_end,
                "bin_label": f"{b_start} - {b_end}",
                "name": f"{b_start} - {b_end}",
                "bin": f"{b_start} - {b_end}",
                "count": int(counts[i]),
                "value": int(counts[i])
            })

        max_bin_idx = int(np.argmax(counts))
        modal_range = f"{safe_float(bin_edges[max_bin_idx])} to {safe_float(bin_edges[max_bin_idx + 1])}"
        modal_pct = round((counts[max_bin_idx] / len(series)) * 100, 1)
        insights.append(f"The highest density bin is {modal_range}, containing {counts[max_bin_idx]} observations ({modal_pct}% of records).")
        x_column = col

    # ==========================
    # 5. BOX PLOT
    # ==========================
    elif chart_type == "box":
        col = y_column or x_column
        if not col or pd.to_numeric(df[col], errors="coerce").dropna().empty:
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            col = numeric_cols[0] if len(numeric_cols) > 0 else df.columns[0]

        series = pd.to_numeric(df[col], errors="coerce").dropna()
        title = f"Box Plot of {col.replace('_', ' ').title()}"

        q25 = safe_float(series.quantile(0.25))
        median = safe_float(series.median())
        q75 = safe_float(series.quantile(0.75))
        iqr = (q75 - q25) if (q25 is not None and q75 is not None) else 0

        lower_bound = q25 - 1.5 * iqr if q25 is not None else 0
        upper_bound = q75 + 1.5 * iqr if q75 is not None else 0

        outliers = series[(series < lower_bound) | (series > upper_bound)].tolist()
        chart_data.append({
            "column": col,
            "min": safe_float(series.min()),
            "q1": q25,
            "q25": q25,
            "median": median,
            "q3": q75,
            "q75": q75,
            "max": safe_float(series.max()),
            "iqr": safe_float(iqr),
            "outliers_count": len(outliers),
            "outliers": [safe_float(o) for o in outliers[:25]],
            "sample_outliers": [safe_float(o) for o in outliers[:25]]
        })

        if len(outliers) > 0:
            insights.append(f"Detected {len(outliers)} statistical outliers outside 1.5x IQR boundaries.")
        else:
            insights.append("No statistical outliers detected beyond 1.5x IQR boundaries.")
        y_column = col

    # ==========================
    # 6. HEATMAP (Correlations)
    # ==========================
    elif chart_type == "heatmap":
        title = "Correlation Heatmap"
        corr_res = compute_correlation_matrix(df, threshold=0.0)
        matrix = corr_res.get("matrix", {})

        for col_x, row_dict in matrix.items():
            for col_y, r_val in row_dict.items():
                chart_data.append({
                    "x": col_x,
                    "y": col_y,
                    "correlation": r_val,
                    "value": r_val
                })

        sig_pairs = corr_res.get("significant_pairs", [])
        if sig_pairs:
            strongest = sig_pairs[0]
            insights.append(f"Strongest relationship: {strongest['column_1']} and {strongest['column_2']} (r = {strongest['correlation']}).")

    return {
        "chart_type": chart_type,
        "title": title,
        "x_column": x_column,
        "y_column": y_column,
        "data": chart_data,
        "insights": insights,
        "warnings": warnings
    }


# ==============================================================================
# FILE SUMMARY: backend/services/analysis/visualizations.py
# ==============================================================================
# WHAT THIS FILE CONTAINS AND DOES:
# This file provides the Visualization Recommendation and Data Preparation Engine:
#   1. generate_chart_recommendations(): Analyzes column types and distributions to recommend
#      the top 3-5 visual charts (Bar, Line, Scatter, Histogram, Box, Heatmap) with clear rationales.
#   2. build_visualization_data(): Transforms tabular data into frontend-ready JSON series
#      suitable for Recharts, Plotly, or ECharts.
#      - Applies aggregation functions ('sum', 'mean', 'count', 'min', 'max', 'median').
#      - Enforces guardrails: caps high cardinality with an 'Other' bucket and downsamples scatter points.
#      - Extracts automated statistical observations and insights from the visual series.
#
# HOW IT CONNECTS TO OTHER FILES:
# - Invoked by 'backend/api/datasets.py' endpoint POST /datasets/{dataset_id}/visualizations.
# - Leverages 'compute_correlation_matrix' from 'backend/services/analysis/statistics.py'.
# - Returns dictionaries matching 'VisualizationResponse' in 'backend/models/schemas.py'.
# ==============================================================================
