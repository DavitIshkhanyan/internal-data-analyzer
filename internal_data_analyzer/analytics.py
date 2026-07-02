from __future__ import annotations

import pandas as pd


def summary_statistics(df: pd.DataFrame) -> pd.DataFrame:
    return df.describe(include="all").transpose()


def top_and_worst(df: pd.DataFrame, metric: str, limit: int = 5) -> tuple[pd.DataFrame, pd.DataFrame]:
    ranked = df.sort_values(by=metric, ascending=False).head(limit)
    worst = df.sort_values(by=metric, ascending=True).head(limit)
    return ranked, worst


def grouped_analysis(df: pd.DataFrame, group_col: str, metric: str | None = None) -> pd.DataFrame:
    grouped = df.groupby(group_col, dropna=False).size().reset_index(name="rows")
    if metric and metric in df.columns and pd.api.types.is_numeric_dtype(df[metric]):
        metric_means = df.groupby(group_col, dropna=False)[metric].mean().reset_index(name=f"{metric}_mean")
        grouped = grouped.merge(metric_means, on=group_col, how="left")
    return grouped.sort_values("rows", ascending=False)


def time_trend(df: pd.DataFrame, date_col: str, metric: str) -> pd.DataFrame:
    time_df = df.copy()
    time_df[date_col] = pd.to_datetime(time_df[date_col], errors="coerce")
    time_df = time_df.dropna(subset=[date_col]).sort_values(date_col)
    if metric not in time_df.columns or not pd.api.types.is_numeric_dtype(time_df[metric]):
        return pd.DataFrame(columns=[date_col, metric])
    return time_df.set_index(date_col)[metric].resample("D").sum().reset_index()


def build_insights(df: pd.DataFrame, metric: str | None, group_col: str | None, date_col: str | None) -> list[str]:
    insights: list[str] = []
    if df.empty:
        return ["No data after filtering."]

    if metric and metric in df.columns and pd.api.types.is_numeric_dtype(df[metric]):
        start = df[metric].iloc[0]
        end = df[metric].iloc[-1]
        if pd.notna(start) and pd.notna(end):
            change = end - start
            pct = (change / start * 100) if start not in (0, None) else None
            if pct is not None and pd.notna(pct):
                insights.append(f"{metric} changed by {change:,.2f} ({pct:,.1f}%) from first to last row.")
            else:
                insights.append(f"{metric} changed by {change:,.2f} from first to last row.")

        top = df[metric].max()
        low = df[metric].min()
        insights.append(f"{metric} ranges from {low:,.2f} to {top:,.2f}.")

    if group_col and group_col in df.columns:
        top_group = df[group_col].astype("object").fillna("Missing").value_counts().head(1)
        if not top_group.empty:
            label = top_group.index[0]
            count = int(top_group.iloc[0])
            insights.append(f"Most common {group_col} is {label} with {count} rows.")

    if date_col and date_col in df.columns:
        temp = df[[date_col]].dropna().copy()
        if not temp.empty:
            temp[date_col] = pd.to_datetime(temp[date_col], errors="coerce")
            temp = temp.dropna().sort_values(date_col)
            if len(temp) > 1:
                insights.append(
                    f"Date coverage spans from {temp[date_col].min().date()} to {temp[date_col].max().date()}."
                )
    return insights or ["No obvious insight detected."]

