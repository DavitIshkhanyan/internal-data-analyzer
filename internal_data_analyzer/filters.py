from __future__ import annotations

from datetime import datetime

import pandas as pd


def sorted_filtered_df(
    df: pd.DataFrame,
    text_filter: str,
    category_col: str | None,
    category_value: str | None,
    numeric_col: str | None,
    numeric_min: float | None,
    numeric_max: float | None,
    date_col: str | None,
    date_range: tuple[datetime, datetime] | None,
    sort_col: str | None,
    sort_desc: bool,
) -> tuple[pd.DataFrame, list[str]]:
    filtered = df.copy()
    applied_filters: list[str] = []

    if text_filter:
        mask = filtered.astype(str).apply(lambda s: s.str.contains(text_filter, case=False, na=False))
        filtered = filtered[mask.any(axis=1)]
        applied_filters.append(f"Text contains '{text_filter}'")

    if category_col and category_value and category_value != "All":
        filtered = filtered[filtered[category_col].astype(str) == category_value]
        applied_filters.append(f"{category_col} = {category_value}")

    if numeric_col and numeric_col in filtered.columns:
        if numeric_min is not None:
            filtered = filtered[filtered[numeric_col] >= numeric_min]
            applied_filters.append(f"{numeric_col} >= {numeric_min}")
        if numeric_max is not None:
            filtered = filtered[filtered[numeric_col] <= numeric_max]
            applied_filters.append(f"{numeric_col} <= {numeric_max}")

    if date_col and date_range and date_col in filtered.columns:
        temp = pd.to_datetime(filtered[date_col], errors="coerce")
        start, end = date_range
        filtered = filtered[temp.between(start, end, inclusive="both")]
        applied_filters.append(f"{date_col} between {start.date()} and {end.date()}")

    if sort_col and sort_col in filtered.columns:
        filtered = filtered.sort_values(by=sort_col, ascending=not sort_desc, na_position="last")
        applied_filters.append(f"Sorted by {sort_col} ({'desc' if sort_desc else 'asc'})")

    return filtered, applied_filters

