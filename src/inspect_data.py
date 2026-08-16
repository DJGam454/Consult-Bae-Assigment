from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

from src.clean_data import normalize_email, normalize_phone, normalize_skill_list

INPUT_DIR = Path("input")
REPORT_PATH = Path("reports") / "data_profile.json"


def infer_column_type(series: pd.Series) -> str:
    s = series.dropna().astype(str).str.strip()
    if s.empty:
        return "unknown"

    numeric = pd.to_numeric(s, errors="coerce").notna().mean()
    if numeric >= 0.8:
        return "numeric"

    date_like = pd.to_datetime(s, errors="coerce", dayfirst=True).notna().mean()
    if date_like >= 0.8:
        return "date"

    return "text"


def inspect_file(path: Path) -> dict[str, Any]:
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    raw_rows = len(df)

    # Replace empty strings with NA for consistent missing calculation.
    missing_df = df.replace(r"^\s*$", pd.NA, regex=True)

    profile: dict[str, Any] = {
        "filename": path.name,
        "rows": raw_rows,
        "columns": list(df.columns),
        "missing_values": missing_df.isna().sum().to_dict(),
        "duplicate_rows": int(df.duplicated().sum()),
        "column_types_inferred": {
            col: infer_column_type(missing_df[col]) for col in df.columns
        },
        "quality_issues": {},
    }

    quality_issues: dict[str, Any] = {}

    if "Name" in df.columns and "Phone Number" in df.columns:
        repeated_header_count = int(
            ((df["Name"].str.strip() == "Name") & (df["Phone Number"].str.strip() == "Phone Number")).sum()
        )
        if repeated_header_count:
            quality_issues["repeated_header_rows"] = repeated_header_count

    for col in df.columns:
        if missing_df[col].dtype == object:
            values = missing_df[col].dropna().astype(str)
            if values.empty:
                continue

            leading_trailing_spaces = int((values != values.str.strip()).sum())
            if leading_trailing_spaces:
                quality_issues[f"{col}_leading_or_trailing_spaces"] = leading_trailing_spaces

            normalized_lower = values.str.strip().str.lower()
            case_variants = (
                pd.DataFrame({"raw": values, "norm": normalized_lower})
                .drop_duplicates()
                .groupby("norm")
                .size()
            )
            inconsistent_case_count = int((case_variants > 1).sum())
            if inconsistent_case_count:
                quality_issues[f"{col}_inconsistent_casing_groups"] = inconsistent_case_count

        col_l = col.lower()
        if "email" in col_l:
            invalid = int(
                missing_df[col]
                .dropna()
                .astype(str)
                .map(lambda v: normalize_email(v) is None)
                .sum()
            )
            if invalid:
                quality_issues[f"{col}_invalid_email_like_values"] = invalid

        if "phone" in col_l:
            invalid_phone = int(
                missing_df[col]
                .dropna()
                .astype(str)
                .map(lambda v: normalize_phone(v) is None)
                .sum()
            )
            if invalid_phone:
                quality_issues[f"{col}_invalid_phone_like_values"] = invalid_phone

        if "skill" in col_l:
            skill_sets = missing_df[col].dropna().astype(str).map(normalize_skill_list)
            token_count = int(skill_sets.map(len).sum())
            quality_issues[f"{col}_total_skill_tokens"] = token_count

    if "email_id" in df.columns and "worker_name" in df.columns:
        malformed = int(
            (
                df["email_id"].astype(str).str.contains(",")
                | (~df["email_id"].astype(str).str.contains(r"@", regex=True))
            ).sum()
        )
        if malformed:
            quality_issues["rows_suspected_shifted_columns"] = malformed

    profile["quality_issues"] = quality_issues
    return profile


def inspect_all(input_dir: Path = INPUT_DIR) -> dict[str, Any]:
    report: dict[str, Any] = {"files": [], "summary": {}}
    total_rows = 0
    for path in sorted(input_dir.glob("*.csv")):
        file_report = inspect_file(path)
        report["files"].append(file_report)
        total_rows += file_report["rows"]

    report["summary"] = {
        "file_count": len(report["files"]),
        "total_rows": total_rows,
    }
    return report


def main() -> None:
    report = inspect_all()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Inspection report written to: {REPORT_PATH}")
    for file_report in report["files"]:
        print(f"\n[{file_report['filename']}] rows={file_report['rows']} columns={len(file_report['columns'])}")
        print(f"Columns: {', '.join(file_report['columns'])}")
        print(f"Missing: {file_report['missing_values']}")
        print(f"Duplicate rows: {file_report['duplicate_rows']}")
        if file_report["quality_issues"]:
            print("Quality issues:")
            for key, value in file_report["quality_issues"].items():
                print(f"  - {key}: {value}")


if __name__ == "__main__":
    main()
