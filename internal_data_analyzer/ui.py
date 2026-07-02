from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from .analytics import build_insights, grouped_analysis, summary_statistics, time_trend, top_and_worst
from .data_io import categorical_columns, detect_date_columns, numeric_columns, read_uploaded_file
from .export import make_text_report, to_csv_bytes
from .filters import sorted_filtered_df


def render_app() -> None:
    st.set_page_config(page_title="Internal Data Analyzer", layout="wide")

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
            st.dataframe(
                pd.DataFrame({"column": filtered_df.dtypes.index, "dtype": filtered_df.dtypes.astype(str).values})
            )

        st.write("**Missing values**")
        missing = filtered_df.isna().sum().reset_index()
        missing.columns = ["column", "missing_values"]
        st.dataframe(missing.sort_values("missing_values", ascending=False), use_container_width=True)

    with analysis_tab:
        left, right = st.columns(2)
        with left:
            st.write("**Summary statistics**")
            st.dataframe(summary_statistics(filtered_df), use_container_width=True)

        with right:
            if metric in filtered_df.columns and pd.api.types.is_numeric_dtype(filtered_df[metric]):
                st.write(f"**Top and worst rows by {metric}**")
                ranked, worst = top_and_worst(filtered_df, metric)
                st.write("Top 5")
                st.dataframe(ranked, use_container_width=True)
                st.write("Worst 5")
                st.dataframe(worst, use_container_width=True)
            else:
                st.info("Select a numeric metric to see top and worst rows.")

        if group_col != "None" and group_col in filtered_df.columns:
            st.write(f"**Grouping by {group_col}**")
            st.dataframe(grouped_analysis(filtered_df, group_col, metric), use_container_width=True)

        if date_candidates:
            selected_time_col = st.selectbox("Time series column", date_candidates, key="time_series_col")
            if selected_time_col in filtered_df.columns:
                daily = time_trend(filtered_df, selected_time_col, metric)
                if not daily.empty and metric in daily.columns:
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

        st.download_button(
            "Download filtered dataset (CSV)",
            data=to_csv_bytes(filtered_df),
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
