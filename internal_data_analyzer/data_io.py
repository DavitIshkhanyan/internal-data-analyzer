from __future__ import annotations

import pandas as pd


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

