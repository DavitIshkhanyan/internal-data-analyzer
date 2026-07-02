# Internal Data Analyzer

Small Streamlit tool for business users to upload a CSV or Excel file, inspect the data, filter and sort it, and export the result.

## Stack

- Python
- Streamlit
- Pandas

## Project structure

- `app.py` — Streamlit entry point
- `internal_data_analyzer/data_io.py` — file reading and column detection
- `internal_data_analyzer/filters.py` — filtering and sorting
- `internal_data_analyzer/analytics.py` — summary stats, grouping, insights, time trend
- `internal_data_analyzer/export.py` — CSV and report export
- `internal_data_analyzer/ui.py` — page layout

## What is implemented

- File upload for CSV and Excel
- Data preview with rows, columns, dtypes, and missing values
- Summary statistics
- Top and worst rows by a selected metric
- Grouping by a selected column
- Time-based view when a date column exists
- Search, category, numeric, date, and sort filters
- Export of filtered data as CSV
- Export of a simple text report

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Limits

- The tool is optimized for simple internal analysis, not large-scale BI workloads.
- Date detection is heuristic and works best when a column name contains `date` or `time`.
- Report export is intentionally simple (text).

## What I would improve with more time

- Add richer charts and metric selection logic
- Support PDF report export
- Add persistent saved views and reusable filter presets
- Add better file validation and schema inference
