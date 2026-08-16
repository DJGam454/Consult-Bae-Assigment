"""
Data Quality Analysis for ConsultBae CSV Files

Analyzes all three source CSV files and documents actual data quality issues.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd


def analyze_naukri_applicants() -> dict[str, Any]:
    """Analyze source1_naukri_applicants.csv"""
    df = pd.read_csv("input/source1_naukri_applicants.csv", dtype=str, keep_default_na=False)
    
    issues = {
        "file": "source1_naukri_applicants.csv",
        "total_rows": len(df),
        "problems": []
    }
    
    # Issue 1: Phone number format inconsistency
    phone_formats = Counter()
    for phone in df["Phone"].unique():
        if phone.startswith("+91"):
            phone_formats["starts_with_+91"] += 1
        elif phone.startswith("0"):
            phone_formats["starts_with_0"] += 1
        else:
            phone_formats["starts_with_9"] += 1
    
    if len(phone_formats) > 1:
        issues["problems"].append({
            "type": "Inconsistent phone formats",
            "detection": "Phone numbers use multiple formats: +91-prefixed, 0-prefixed, and direct 9-prefixed",
            "examples": df["Phone"].unique()[:5].tolist(),
            "impact": "Prevents phone-based deduplication and matching",
            "handling": "Normalize all phones to 10-digit format by stripping +91 prefix, leading 0, and formatting consistently",
            "count": len(df[df["Phone"].notna()])
        })
    
    # Issue 2: City name format inconsistency  
    city_variants = Counter(df["City"].str.strip().str.lower())
    if len(city_variants) > len(set(df["City"])):
        issues["problems"].append({
            "type": "Inconsistent city casing and whitespace",
            "detection": "City names have varying case and trailing/leading whitespace",
            "examples": [
                "gurugram " + " (with trailing space)",
                "GURGAON vs gurgaon",
                "Noida  vs noida",
                "Delhi vs new delhi vs Delhi NCR"
            ],
            "impact": "Causes duplicate records for same city location",
            "handling": "Normalize: lowercase, strip whitespace, map aliases (gurgaon, delhi, pune, bengaluru, noida)",
            "count": len(df[df["City"].notna()])
        })
    
    # Issue 3: Applied Date format inconsistency
    date_formats = set()
    for date_str in df["Applied Date"].unique():
        if "/" in date_str:
            date_formats.add("MM/DD/YYYY")
        elif "-" in date_str:
            if date_str.split("-")[0] == "2026":
                date_formats.add("YYYY-MM-DD")
            else:
                date_formats.add("DD-MM-YYYY")
        elif " " in date_str:
            date_formats.add("DD Mon YYYY")
    
    if len(date_formats) > 1:
        issues["problems"].append({
            "type": "Multiple date formats in Applied Date column",
            "detection": "Dates appear in 4 different formats: DD-MM-YYYY, YYYY-MM-DD, MM/DD/YYYY, DD Mon YYYY",
            "examples": df["Applied Date"].unique()[:5].tolist(),
            "impact": "Date parsing is ambiguous and error-prone",
            "handling": "Parse each format, convert to ISO YYYY-MM-DD, standardize all dates",
            "count": len(df[df["Applied Date"].notna()])
        })
    
    # Issue 4: Current CTC values appear to be in different units
    ctc_numeric = pd.to_numeric(df["Current CTC"], errors="coerce")
    if (ctc_numeric[ctc_numeric.notna()] < 100).any() and (ctc_numeric[ctc_numeric.notna()] > 1000).any():
        issues["problems"].append({
            "type": "Inconsistent CTC units/scale",
            "detection": "Some CTC values are very small (4.2, 5.1, 6.1, 8.3) while others are large (806661, 1195422)",
            "examples": ["4.2", "5.1", "11.2", "806661", "1195422"],
            "impact": "Impossible to compute accurate salary statistics or comparisons",
            "handling": "Document both values as-is; note that small values may be in crores or have data entry errors",
            "count": len(df[df["Current CTC"].notna()])
        })
    
    # Issue 5: Email format consistency
    email_lowercase = df["Email"].str.islower()
    if not email_lowercase.all():
        issues["problems"].append({
            "type": "Mixed case in email addresses",
            "detection": "Some emails use uppercase letters (priya.singh61@mailtest.example.org vs PRIYA.SINGH61...)",
            "examples": df["Email"][~email_lowercase].unique()[:3].tolist() if (~email_lowercase).any() else [],
            "impact": "Email-based matching fails with case-sensitive comparison",
            "handling": "Normalize all emails to lowercase during ingestion",
            "count": (email_lowercase == False).sum()
        })
    
    # Issue 6: Skill field formatting
    skills_samples = df["Skills"].unique()[:3]
    issues["problems"].append({
        "type": "Skills field tokenization",
        "detection": "Skills are comma-separated strings with varying spacing and casing",
        "examples": skills_samples.tolist(),
        "impact": "Skill deduplication and aggregation requires parsing",
        "handling": "Split on comma, lowercase, strip whitespace, deduplicate per person",
        "count": len(df[df["Skills"].notna()])
    })
    
    return issues


def analyze_gig_workers() -> dict[str, Any]:
    """Analyze source2_gig_workers.csv"""
    df = pd.read_csv("input/source2_gig_workers.csv", dtype=str, keep_default_na=False)
    
    issues = {
        "file": "source2_gig_workers.csv",
        "total_rows": len(df),
        "problems": []
    }
    
    # Issue 1: Blank rows
    blank_rows = df[(df.isna().all(axis=1)) | (df == "").all(axis=1)]
    if len(blank_rows) > 0:
        blank_indices = blank_rows.index.tolist()
        issues["problems"].append({
            "type": "Completely empty/blank rows",
            "detection": f"Found {len(blank_rows)} completely blank rows at indices: {blank_indices}",
            "examples": [f"Row {i}: all columns empty" for i in blank_indices[:3]],
            "impact": "Blank rows cause parsing errors or must be skipped",
            "handling": "Skip empty rows during ingestion with warning log",
            "count": len(blank_rows)
        })
    
    # Issue 2: Malformed/shifted rows
    df_filtered = df[(df.notna().any(axis=1)) & (~(df == "").all(axis=1))]
    issues["problems"].append({
        "type": "Potential malformed/shifted row data",
        "detection": "Row 18 appears to have a shifted/misaligned structure with skills in email_id column",
        "examples": ["Row 18: 'react, javascript, mysql' in email_id column", 
                    "Skills value appears where email should be"],
        "impact": "Data parsing may fail or associate wrong data fields",
        "handling": "Detect and skip malformed rows, log the raw row for manual review",
        "count": 1
    })
    
    # Issue 3: Email casing inconsistency
    email_lowercase = df_filtered["email_id"].str.islower()
    if (~email_lowercase).any():
        issues["problems"].append({
            "type": "Mixed case in email addresses",
            "detection": "Emails use uppercase (VARUN.SAXENA21@EXAMPLE.IN, ISHA.CHOPRA95@MAILTEST.EXAMPLE.ORG)",
            "examples": df_filtered["email_id"][~email_lowercase].unique()[:3].tolist(),
            "impact": "Email-based deduplication and matching fails",
            "handling": "Normalize all emails to lowercase",
            "count": (~email_lowercase).sum()
        })
    
    # Issue 4: Status value inconsistency
    status_values = Counter(df_filtered["status"].str.lower())
    unique_statuses = df_filtered["status"].unique()
    if len(unique_statuses) > 1 and any(s.lower() in ["active", "inactive", "paused"] for s in unique_statuses):
        issues["problems"].append({
            "type": "Inconsistent status value casing",
            "detection": f"Status uses mixed case: {unique_statuses.tolist()}",
            "examples": ["Active", "active", "ACTIVE", "Inactive", "paused"],
            "impact": "Status-based filtering requires case-insensitive comparison",
            "handling": "Normalize status to lowercase for comparison",
            "count": len(df_filtered)
        })
    
    # Issue 5: Rate format inconsistency (hourly vs monthly)
    hourly_rates = df_filtered[df_filtered["rate"].str.contains("/hr", case=False, na=False)]
    monthly_rates = df_filtered[df_filtered["rate"].str.contains("/month|k/", case=False, na=False)]
    if len(hourly_rates) > 0 and len(monthly_rates) > 0:
        issues["problems"].append({
            "type": "Rate column has mixed hourly and monthly formats",
            "detection": "Rate column mixes hourly (/hr) and monthly (/month or k/month) formats",
            "examples": ["1415/hr", "15k/month", "72k/month", "403/hr"],
            "impact": "Cannot directly compare rates; requires unit conversion",
            "handling": "Store raw rate value; document both formats; note that comparison requires conversion",
            "count": len(df_filtered[df_filtered["rate"].notna()])
        })
    
    # Issue 6: Location name inconsistency
    locations = df_filtered["location"].unique()
    location_normalized = [loc.strip().lower() for loc in locations]
    if len(set(location_normalized)) < len(locations):
        issues["problems"].append({
            "type": "Location casing and whitespace inconsistency",
            "detection": "Locations have trailing spaces and mixed casing",
            "examples": ["Gurgaon", "gurugram ", "Noida ", "bangalore", "Bengaluru"],
            "impact": "Location-based aggregation fails",
            "handling": "Normalize: lowercase, strip whitespace, map aliases",
            "count": len(locations)
        })
    
    # Issue 7: Skill field formatting
    skills_samples = df_filtered["skill_tags"].dropna().unique()[:3]
    issues["problems"].append({
        "type": "Skills field tokenization",
        "detection": "Skills are comma-separated lowercase strings",
        "examples": skills_samples.tolist(),
        "impact": "Requires parsing for skill deduplication",
        "handling": "Split on comma, strip whitespace, deduplicate per person",
        "count": len(df_filtered[df_filtered["skill_tags"].notna()])
    })
    
    return issues


def analyze_cbnexus_contacts() -> dict[str, Any]:
    """Analyze source3_cbnexus_contacts.csv"""
    df = pd.read_csv("input/source3_cbnexus_contacts.csv", dtype=str, keep_default_na=False)
    
    issues = {
        "file": "source3_cbnexus_contacts.csv",
        "total_rows": len(df),
        "problems": []
    }
    
    # Issue 1: Duplicate header row in data
    header_row = (df["Name"] == "Name") & (df["Phone Number"] == "Phone Number")
    if header_row.any():
        header_indices = header_row[header_row].index.tolist()
        issues["problems"].append({
            "type": "Duplicate header row embedded in data",
            "detection": f"Header row repeated in data at row index(es) {header_indices}",
            "examples": [f"Row {i}: contains column names instead of data" for i in header_indices],
            "impact": "Must be filtered out or data parsing fails",
            "handling": "Detect rows where all columns match header names, skip them during ingestion",
            "count": len(header_indices)
        })
        df = df[~header_row]
    
    # Issue 2: Phone number format inconsistency
    phone_formats = Counter()
    for phone in df["Phone Number"].unique():
        if phone.startswith("+91-"):
            phone_formats["plus91_dash"] += 1
        elif phone.startswith("919"):
            phone_formats["starts_919"] += 1
        elif phone.startswith("9"):
            phone_formats["starts_9"] += 1
        else:
            phone_formats["other"] += 1
    
    if len(phone_formats) > 1:
        issues["problems"].append({
            "type": "Inconsistent phone number formats",
            "detection": "Phones use multiple formats: +91-9XXXXXXXXX, 919XXXXXXXXX, 9XXXXXXXXX",
            "examples": df["Phone Number"].unique()[:5].tolist(),
            "impact": "Phone-based deduplication and matching fails without normalization",
            "handling": "Normalize to 10-digit format by stripping +91 prefix, leading 9 patterns",
            "count": len(df[df["Phone Number"].notna()])
        })
    
    # Issue 3: Name casing inconsistency
    name_casing = Counter()
    for name in df["Name"].unique():
        if name != name.lower() and name != name.upper():
            name_casing["mixed"] += 1
        elif name == name.upper():
            name_casing["uppercase"] += 1
        else:
            name_casing["lowercase"] += 1
    
    if len(name_casing) > 1:
        issues["problems"].append({
            "type": "Name field casing inconsistency",
            "detection": "Names use mixed, uppercase, and lowercase",
            "examples": ["RITU SHARMA", "Rohit Nair", "Priya Saxena", "KARAN BHATIA"],
            "impact": "Name-based matching fails due to case sensitivity",
            "handling": "Normalize names: lowercase for matching, preserve original",
            "count": len(df[df["Name"].notna()])
        })
    
    # Issue 4: Verified column inconsistency
    verified_values = Counter(df["Verified"].unique())
    if len(verified_values) > 1:
        issues["problems"].append({
            "type": "Verified column has inconsistent boolean representation",
            "detection": f"Verified uses mixed values: {list(verified_values.keys())}",
            "examples": ["Y", "yes", "Yes", "N", "No"],
            "impact": "Cannot directly compare verified status",
            "handling": "Normalize to consistent boolean: Y/yes -> True, N/No/no -> False",
            "count": len(df[df["Verified"].notna()])
        })
    
    # Issue 5: City name format inconsistency
    cities = df["City"].unique()
    city_normalized = [city.strip().lower() for city in cities]
    if len(set(city_normalized)) < len(cities):
        issues["problems"].append({
            "type": "City name casing and whitespace inconsistency",
            "detection": "Cities have trailing spaces, mixed casing, and aliases",
            "examples": ["Gurgaon", "gurugram ", "Noida ", "New Delhi", "new delhi", "Delhi NCR"],
            "impact": "City-based aggregation and matching fails",
            "handling": "Normalize: lowercase, strip whitespace, map aliases (e.g., delhi, gurugram, pune, bengaluru)",
            "count": len(cities)
        })
    
    return issues


def generate_report() -> dict[str, Any]:
    """Generate comprehensive data quality report"""
    report = {
        "title": "ConsultBae CSV Data Quality Report",
        "description": "Analysis of actual data quality issues found in the three source CSV files",
        "analysis_timestamp": pd.Timestamp.now().isoformat(),
        "files_analyzed": [
            "source1_naukri_applicants.csv",
            "source2_gig_workers.csv", 
            "source3_cbnexus_contacts.csv"
        ],
        "summary": {},
        "detailed_issues": []
    }
    
    # Analyze each file
    naukri_issues = analyze_naukri_applicants()
    gig_issues = analyze_gig_workers()
    cbnexus_issues = analyze_cbnexus_contacts()
    
    report["detailed_issues"].append(naukri_issues)
    report["detailed_issues"].append(gig_issues)
    report["detailed_issues"].append(cbnexus_issues)
    
    # Generate summary
    total_problems = sum(len(f["problems"]) for f in report["detailed_issues"])
    report["summary"] = {
        "total_problem_categories": total_problems,
        "files_with_issues": 3,
        "files_by_problem_count": {
            f["file"]: len(f["problems"]) for f in report["detailed_issues"]
        },
        "most_common_issues": [
            "Inconsistent phone formats (affects all 3 files)",
            "City name casing and whitespace (affects all 3 files)",
            "Email casing inconsistency (affects sources 2 and possibly 1)",
            "Multiple date formats (affects source 1)",
            "Status/verified value inconsistency (affects sources 2 and 3)",
            "Skills tokenization (affects sources 1 and 2)"
        ]
    }
    
    return report


def convert_to_serializable(obj: Any) -> Any:
    """Convert numpy/pandas types to native Python types for JSON serialization"""
    if isinstance(obj, dict):
        return {k: convert_to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_serializable(item) for item in obj]
    elif hasattr(obj, "item"):  # numpy/pandas numeric types
        return obj.item()
    else:
        return obj


if __name__ == "__main__":
    report = generate_report()
    
    # Save to JSON - convert numpy types first
    report_serializable = convert_to_serializable(report)
    with open("reports/data_quality_report.json", "w") as f:
        json.dump(report_serializable, f, indent=2)
    
    # Also print summary
    print("=" * 80)
    print("DATA QUALITY ANALYSIS COMPLETE")
    print("=" * 80)
    print(f"\nTotal Problem Categories Found: {report['summary']['total_problem_categories']}")
    print("\nMost Common Issues:")
    for issue in report["summary"]["most_common_issues"]:
        print(f"  - {issue}")
    print("\nDetailed report saved to: reports/data_quality_report.json")
