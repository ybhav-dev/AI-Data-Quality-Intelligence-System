# AI Data Quality Intelligence System

A Flask-based application for analyzing dataset quality and assisting with data cleaning.

## Run locally
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000

## Theme
- Cherry Cola: `#9A0002`
- Cream Vanilla: `#EFE6DE`
\n## Current features\n- Dashboard UI with Cherry Cola / Cream Vanilla theme\n- CSV and Excel upload endpoint\n- Initial profiling for row/column count, missing values, duplicates, and quality dimensions\n\n## Data quality checks (current milestone)\n- Missing and placeholder values\n- Duplicate rows\n- Email, date, age, rating, quantity and negative price/amount validation\n- City/state mismatch and basic formatting consistency checks\n- Isolation Forest-based numeric anomaly flagging\n- Quality score dimensions and issue counts\n
## Detailed Data Analysis page\n- Open /analysis after uploading a dataset\n- Browse findings by issue type and search across row, column, value, and reason\n- Dataset metadata is held in the Flask session for the local workflow\n

## Milestone 5 — AI Recommendations & Cleaning Preview
- Open `/recommendations` after uploading a dataset.
- Recommendations are generated locally using deterministic data-quality rules (no external AI API required).
- Select safe fixes for missing values, whitespace/capitalization consistency, and exact duplicates.
- Preview selected changes before applying.
- Apply selected fixes to a separate cleaned CSV; the original upload is unchanged.
- Download the cleaned CSV from the recommendations page.
- Invalid values and anomalies are surfaced for manual review rather than guessed corrections.
- Dashboard issue distribution now includes Consistency as its own category.


## Milestone 6 — Data Cleaning Workspace
- Open `/cleaning` after uploading a CSV or Excel dataset.
- Preview the original dataset (first 10 rows) and basic quality counts.
- Select operations: fill missing values (median/mode), trim whitespace, standardize categorical text case, remove exact duplicates, or drop rows with missing values.
- Preview before/after row, missing-cell, and duplicate counts plus a sample of the transformed data.
- Apply operations to a separate cleaned CSV and download it.
- The original uploaded dataset remains unchanged; email/URL/ID-like fields are excluded from title-case normalization.


## Milestone 7 — Interactive Data Table
- Search across all dataset columns, paginate records, and sort by a selected column.
- Click a column header to view its profile (type, missing/unique counts, frequent values, and numeric summary).
- Double-click a cell to edit it in a separate working copy.
- Undo the most recent cell edit or reset the working copy to the original upload.
- Cleaning preview/apply uses the working copy when edits exist; the original upload is preserved.


## Milestone 8 – Data table enhancements
- Removed accidental sequential index columns (such as `Unnamed: 0`) when loading datasets.
- Added sticky table headers, improved column sizing, and compact non-wrapping cell display.
- Added row selection with select-page support and CSV export for selected rows.
- Added export of the current working dataset as CSV.
- Added column profiling visualization for the most frequent values.
- Preserved editable working-copy behavior, undo, reset, and existing cleaning workflows.


## Milestone 9 – Interactive column visualizations
- Added an analysis-page chart panel with a column selector.
- Numeric columns render interactive histograms and summary statistics (count, mean, median, min, max).
- Categorical columns render top-value frequency charts and distinct-value counts.
- Charts use the existing Plotly dependency and adapt responsively.
- Profile data is computed from the active dataset on the server and safely serialized for the page.

## Milestone 10 – Data Cleaning Workspace Improvements

- Removes accidental blank/NaN and sequential index columns from dataset previews and the cleaning workspace while preserving legitimate columns.
- Normalizes blank/duplicate column labels for stable table and profiling behavior.
- Refines the interactive table with sticky row selectors/index columns, compact column widths, improved horizontal scrolling, and clearer cell truncation.
- Column profiling now treats common blank placeholders as missing and provides numeric histogram bins alongside descriptive statistics; categorical columns show their most common values.
- Selected-row CSV export uses the dataset's actual row index, avoiding incorrect exports after filtering or sorting.
- Existing search, sorting, cell editing, undo/reset, cleaning preview/apply, and working CSV export remain available.

### Validation

Python modules compile and the cleaning JavaScript passes Node syntax validation. Install the dependencies in `requirements.txt` before running the Flask application.


## Milestone 11 – Visualization usability
- Added a column selector directly to the Column visualizations panel.
- The visualization now profiles the first available column on initial load instead of showing an empty panel.
- Selecting a column from the dropdown or clicking a table header updates its profile and distribution chart.
- The selector is repopulated safely when the table reloads and preserves a valid selection.

## Milestone 12 – Dataset-level visual analytics
- Added an interactive numeric correlation heatmap to the Data Analysis page.
- Numeric columns are identified from numeric types and safely coercible numeric fields; constant columns are excluded.
- The heatmap is capped at 12 numeric columns to keep rendering responsive and displays correlation coefficients from −1 to +1.
- Added explanatory guidance that correlation does not imply causation.
- Existing per-column numeric histograms and categorical frequency charts remain available.

### Validation
- Python compilation passed.
- Analysis JavaScript syntax validation passed.
- Flask runtime route testing requires installing the packages listed in `requirements.txt`.


## Milestone 15 – Custom validation rules
- Added a rule builder to the Data Analysis page.
- Supported checks: non-empty, unique, email format, numeric minimum/maximum/range, and regex pattern.
- Runs checks against the uploaded dataset and displays violation counts plus example row/value details.
- Validation is read-only and does not modify source data.
- Rule builder supports up to 30 rules per run.


### Milestone 16 — Business Insights & Recommendations
- Added a separate report section to Data Analysis with plain-English, dataset-derived findings.
- Highlights missing values, common categories, potential IQR outliers, and strong numeric correlations when available.
- Generates practical recommendations for reviewing data quality, category imbalance, outliers, and relationships.
- Findings are deterministic/statistical (no external AI service) and include a correlation-not-causation note.

### Milestone 16 upgrade — Business analytics report
- Split the report into **Data Quality Insights** and **Business Insights & Recommendations**.
- Business metrics are inferred from descriptive column names (revenue/order amount, quantity, category/product, city/state/region, customer, rating, and date fields).
- When fields exist, reports totals and averages, top/low groups by value, quantity/value association, repeat customer activity, rating summary, period-over-period changes, and strong numeric relationships.
- Recommendations are generated only for detected patterns; calculations use available non-missing values. Column-role detection is heuristic, so confirm that detected fields match the dataset's business definitions.
