import json
import os
import uuid
from datetime import datetime

import pandas as pd

REPORTS_DIR = "reports"
os.makedirs(REPORTS_DIR, exist_ok=True)


def _compute_metrics(metrics: list, df: pd.DataFrame) -> list:
    """Compute metric values from the dataframe if not already provided."""
    for m in metrics:
        col = m.get("column")
        op = m.get("operation", "sum")
        if col and col in df.columns:
            try:
                series = pd.to_numeric(df[col], errors="coerce")
                if op == "sum":
                    m["value"] = round(float(series.sum()), 2)
                elif op == "mean":
                    m["value"] = round(float(series.mean()), 2)
                elif op == "max":
                    m["value"] = round(float(series.max()), 2)
                elif op == "min":
                    m["value"] = round(float(series.min()), 2)
                elif op == "count":
                    m["value"] = int(series.count())
                else:
                    m["value"] = round(float(series.sum()), 2)
            except Exception:
                m["value"] = None
        else:
            m["value"] = None
    return metrics


def build_report(
    file_name: str,
    df: pd.DataFrame,
    analysis: dict,
) -> str:
    """
    Build a JSON report and save it to the reports/ directory.

    Parameters
    ----------
    file_name : str
        Original uploaded file name (e.g. "sales.csv").
    df : pd.DataFrame
        The full parsed dataframe.
    analysis : dict
        JSON returned by analyzer.py (insights, metrics, charts).

    Returns
    -------
    str
        Path to the saved JSON report file.
    """
    report_id = uuid.uuid4().hex[:10]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"report_{timestamp}_{report_id}.json"
    report_path = os.path.join(REPORTS_DIR, report_filename)

    # Compute metric values from the actual dataframe
    metrics = _compute_metrics(analysis.get("metrics", []), df)

    # Serialise dataframe — replace NaN with None for valid JSON
    raw_data = json.loads(df.to_json(orient="records", force_ascii=False, default_handler=str))

    report = {
        "file_name": file_name,
        "generated_at": datetime.now().isoformat(),
        "row_count": len(df),
        "col_count": len(df.columns),
        "insights": analysis.get("insights", ""),
        "metrics": metrics,
        "charts": analysis.get("charts", []),
        "raw_data": raw_data,
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return report_path
