from __future__ import annotations

import pandas as pd


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def make_text_report(df: pd.DataFrame, title: str, filters: list[str], metric: str | None, group_col: str | None) -> str:
    lines = [
        title,
        "=" * len(title),
        "",
        f"Rows: {len(df)}",
        f"Columns: {len(df.columns)}",
        f"Missing values: {int(df.isna().sum().sum())}",
        "",
        "Applied filters:",
        *(filters or ["- none"]),
        "",
    ]

    if metric and metric in df.columns and pd.api.types.is_numeric_dtype(df[metric]) and not df.empty:
        top_row = df.loc[df[metric].idxmax()]
        worst_row = df.loc[df[metric].idxmin()]
        lines.extend(
            [
                f"Top {metric}: {top_row.to_dict()}",
                f"Worst {metric}: {worst_row.to_dict()}",
                "",
            ]
        )

    if group_col and group_col in df.columns:
        grouped = df.groupby(group_col, dropna=False).size().sort_values(ascending=False).head(10)
        lines.extend(["Top groups:", grouped.to_string(), ""])

    return "\n".join(lines)

