from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st


st.set_page_config(page_title="Internal Data Analyzer", layout="wide")


def read_uploaded_file(uploaded_file) -> pd.DataFrame:
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    if name.endswith(".xlsx"):
        return pd.read_excel(uploaded_file, engine="openpyxl")
    if name.endswith(".xls"):
        return pd.read_excel(uploaded_file, engine="xlrd")
    raise ValueError("Unsupported file format. Use CSV or Excel.")


def detect_date_columns(df: pd.DataFrame) -> list[str]:
    candidates = [col for col in df.columns if "date" in col.lower() or "time" in col.lower()]
    detected: list[str] = []
    for column in candidates:
        try:
            parsed = pd.to_datetime(df[column], errors="coerce")
        except Exception:
            continue
        if parsed.notna().sum() > 0:
            detected.append(column)
    return detected


def numeric_columns(df: pd.DataFrame) -> list[str]:
    return df.select_dtypes(include="number").columns.tolist()


def categorical_columns(df: pd.DataFrame) -> list[str]:
    cols = df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
    return [col for col in cols if df[col].nunique(dropna=True) > 1]


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


st.title("Internal Data Analyzer")
st.caption("Upload a CSV or Excel file, explore the data, filter it, and export the result.")

uploaded = st.file_uploader("Upload file", type=["csv", "xlsx", "xls"])

if uploaded is None:
    st.info("Upload a file to start.")
    st.stop()

try:
    raw_df = read_uploaded_file(uploaded)
except Exception as exc:
    st.error(str(exc))
    st.stop()

if raw_df.empty:
    st.warning("The uploaded file contains no rows.")
    st.stop()

df = raw_df.copy()
date_candidates = detect_date_columns(df)
numeric_cols = numeric_columns(df)
category_cols = categorical_columns(df)

st.sidebar.header("Filters")
text_filter = st.sidebar.text_input("Search text across all columns")
category_col = st.sidebar.selectbox("Category filter", ["None"] + category_cols)
category_value = "All"
if category_col != "None":
    category_value = st.sidebar.selectbox(
        "Category value",
        ["All"] + sorted(df[category_col].astype(str).fillna("Missing").unique().tolist()),
    )
numeric_col = st.sidebar.selectbox("Numeric filter", ["None"] + numeric_cols)
numeric_min = numeric_max = None
if numeric_col != "None":
    numeric_series = pd.to_numeric(df[numeric_col], errors="coerce").dropna()
    if not numeric_series.empty:
        min_val = float(numeric_series.min())
        max_val = float(numeric_series.max())
        numeric_min, numeric_max = st.sidebar.slider(
            f"{numeric_col} range",
            min_value=min_val,
            max_value=max_val,
            value=(min_val, max_val),
        )
    else:
        st.sidebar.warning("Selected numeric column does not contain valid values.")
date_col = st.sidebar.selectbox("Date filter", ["None"] + date_candidates)
date_range = None
selected_time_col = None
if date_col != "None":
    parsed_dates = pd.to_datetime(df[date_col], errors="coerce").dropna()
    if not parsed_dates.empty:
        date_range = st.sidebar.date_input(
            "Date range",
            value=(parsed_dates.min().date(), parsed_dates.max().date()),
        )
        if isinstance(date_range, tuple) and len(date_range) == 2:
            date_range = (
                datetime.combine(date_range[0], datetime.min.time()),
                datetime.combine(date_range[1], datetime.max.time()),
            )
        else:
            date_range = None
    else:
        st.sidebar.warning("Selected date column could not be parsed.")

sort_col = st.sidebar.selectbox("Sort by", ["None"] + list(df.columns))
sort_desc = st.sidebar.checkbox("Descending sort", value=True)

filtered_df, applied_filters = sorted_filtered_df(
    df=df,
    text_filter=text_filter,
    category_col=None if category_col == "None" else category_col,
    category_value=category_value,
    numeric_col=None if numeric_col == "None" else numeric_col,
    numeric_min=numeric_min,
    numeric_max=numeric_max,
    date_col=None if date_col == "None" else date_col,
    date_range=date_range,
    sort_col=None if sort_col == "None" else sort_col,
    sort_desc=sort_desc,
)

metric_options = numeric_cols or df.columns.tolist()
metric = st.selectbox("Metric for analysis", metric_options)
group_col = st.selectbox("Group by column", ["None"] + list(df.columns))

col1, col2, col3, col4 = st.columns(4)
col1.metric("Rows", len(filtered_df))
col2.metric("Columns", len(filtered_df.columns))
col3.metric("Missing values", int(filtered_df.isna().sum().sum()))
col4.metric("Detected date columns", len(date_candidates))

st.subheader("Data preview")
st.dataframe(filtered_df.head(10), use_container_width=True)

preview_tab, analysis_tab, insights_tab, export_tab = st.tabs(["Overview", "Analytics", "Insights", "Export"])

with preview_tab:
    left, right = st.columns(2)
    with left:
        st.write("**Columns**")
        st.write(list(filtered_df.columns))
    with right:
        st.write("**Data types**")
        st.dataframe(pd.DataFrame({"column": filtered_df.dtypes.index, "dtype": filtered_df.dtypes.astype(str).values}))

    st.write("**Missing values**")
    missing = filtered_df.isna().sum().reset_index()
    missing.columns = ["column", "missing_values"]
    st.dataframe(missing.sort_values("missing_values", ascending=False), use_container_width=True)

with analysis_tab:
    left, right = st.columns(2)
    with left:
        st.write("**Summary statistics**")
        st.dataframe(filtered_df.describe(include="all").transpose(), use_container_width=True)

    with right:
        if metric in filtered_df.columns and pd.api.types.is_numeric_dtype(filtered_df[metric]):
            st.write(f"**Top and worst rows by {metric}**")
            ranked = filtered_df.sort_values(by=metric, ascending=False).head(5)
            worst = filtered_df.sort_values(by=metric, ascending=True).head(5)
            st.write("Top 5")
            st.dataframe(ranked, use_container_width=True)
            st.write("Worst 5")
            st.dataframe(worst, use_container_width=True)
        else:
            st.info("Select a numeric metric to see top and worst rows.")

    if group_col != "None" and group_col in filtered_df.columns:
        st.write(f"**Grouping by {group_col}**")
        grouped = filtered_df.groupby(group_col, dropna=False).size().reset_index(name="rows")
        if metric in filtered_df.columns and pd.api.types.is_numeric_dtype(filtered_df[metric]):
            metric_means = filtered_df.groupby(group_col, dropna=False)[metric].mean().reset_index(name=f"{metric}_mean")
            grouped = grouped.merge(metric_means, on=group_col, how="left")
        st.dataframe(grouped.sort_values("rows", ascending=False), use_container_width=True)

    if date_candidates:
        selected_time_col = st.selectbox("Time series column", date_candidates, key="time_series_col")
        if selected_time_col in filtered_df.columns:
            time_df = filtered_df.copy()
            time_df[selected_time_col] = pd.to_datetime(time_df[selected_time_col], errors="coerce")
            time_df = time_df.dropna(subset=[selected_time_col]).sort_values(selected_time_col)
            if metric in time_df.columns and pd.api.types.is_numeric_dtype(time_df[metric]):
                daily = time_df.set_index(selected_time_col)[metric].resample("D").sum().reset_index()
                st.line_chart(daily, x=selected_time_col, y=metric, use_container_width=True)
            else:
                st.info("Pick a numeric metric to show a time trend.")

with insights_tab:
    st.write("**Simple insights**")
    for insight in build_insights(
        filtered_df,
        metric=metric if metric in filtered_df.columns else None,
        group_col=None if group_col == "None" else group_col,
        date_col=selected_time_col or (date_candidates[0] if date_candidates else None),
    ):
        st.write(f"- {insight}")

with export_tab:
    st.write("**Applied filters**")
    st.write(applied_filters or ["No filters applied"])

    csv_bytes = to_csv_bytes(filtered_df)
    st.download_button(
        "Download filtered dataset (CSV)",
        data=csv_bytes,
        file_name="filtered_dataset.csv",
        mime="text/csv",
    )

    report = make_text_report(
        filtered_df,
        title="Internal Data Report",
        filters=applied_filters,
        metric=metric if metric in filtered_df.columns else None,
        group_col=None if group_col == "None" else group_col,
    )
    st.download_button(
        "Download simple report (TXT)",
        data=report.encode("utf-8"),
        file_name="data_report.txt",
        mime="text/plain",
    )

st.subheader("Filtered table")
st.dataframe(filtered_df, use_container_width=True)
