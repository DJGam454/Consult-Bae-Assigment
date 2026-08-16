from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from src.clean_data import (
    merge_skill_lists,
    normalize_city,
    normalize_email,
    normalize_name,
    normalize_phone,
    normalize_skill_list,
    normalize_status,
    normalize_verified,
    parse_date_to_iso,
    parse_float,
    parse_int,
)
from src.database import get_connection, recreate_schema
from src.matching import MatchDecision, resolve_match

INPUT_DIR = Path("input")


@dataclass
class IngestionStats:
    rows_read: int = 0
    rows_skipped_empty: int = 0
    rows_skipped_invalid: int = 0
    duplicates_merged: int = 0
    ambiguous_matches: int = 0
    created_people: int = 0


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def _normalize_row(source_file: str, row: dict[str, Any]) -> dict[str, Any]:
    if source_file == "source1_naukri_applicants.csv":
        return {
            "source_system": "naukri",
            "full_name": normalize_name(row.get("Full Name")),
            "normalized_name": normalize_name(row.get("Full Name")),
            "email": normalize_email(row.get("Email")),
            "phone": normalize_phone(row.get("Phone")),
            "city": normalize_city(row.get("City")),
            "skills": normalize_skill_list(row.get("Skills")),
            "experience_years": parse_float(row.get("Experience (Years)")),
            "current_ctc": parse_float(row.get("Current CTC")),
            "applied_date": parse_date_to_iso(row.get("Applied Date")),
            "gig_rate_raw": None,
            "gig_status": None,
            "verified": None,
            "projects_completed": None,
        }

    if source_file == "source2_gig_workers.csv":
        return {
            "source_system": "gig_workers",
            "full_name": normalize_name(row.get("worker_name")),
            "normalized_name": normalize_name(row.get("worker_name")),
            "email": normalize_email(row.get("email_id")),
            "phone": None,
            "city": normalize_city(row.get("location")),
            "skills": normalize_skill_list(row.get("skill_tags")),
            "experience_years": None,
            "current_ctc": None,
            "applied_date": None,
            "gig_rate_raw": row.get("rate") or None,
            "gig_status": normalize_status(row.get("status")),
            "verified": None,
            "projects_completed": None,
        }

    if source_file == "source3_cbnexus_contacts.csv":
        return {
            "source_system": "cbnexus",
            "full_name": normalize_name(row.get("Name")),
            "normalized_name": normalize_name(row.get("Name")),
            "email": None,
            "phone": normalize_phone(row.get("Phone Number")),
            "city": normalize_city(row.get("City")),
            "skills": [],
            "experience_years": None,
            "current_ctc": None,
            "applied_date": None,
            "gig_rate_raw": None,
            "gig_status": None,
            "verified": normalize_verified(row.get("Verified")),
            "projects_completed": parse_int(row.get("Projects Completed")),
        }

    raise ValueError(f"Unsupported file: {source_file}")


def _is_repeated_header_row(source_file: str, row: dict[str, Any]) -> bool:
    if source_file != "source3_cbnexus_contacts.csv":
        return False
    return (
        str(row.get("Name", "")).strip().lower() == "name"
        and str(row.get("Phone Number", "")).strip().lower() == "phone number"
    )


def _looks_malformed_gig_row(source_file: str, row: dict[str, Any], cleaned: dict[str, Any]) -> bool:
    if source_file != "source2_gig_workers.csv":
        return False
    email_raw = str(row.get("email_id", "")).strip()
    worker_raw = str(row.get("worker_name", "")).strip()
    rate_raw = str(row.get("rate", "")).strip().lower()

    bad_rate = not (
        rate_raw.endswith("/hr")
        or rate_raw.endswith("/month")
        or rate_raw.endswith("k/month")
        or rate_raw == ""
    )
    return (
        "," in email_raw
        or cleaned.get("email") is None
        or worker_raw == ""
        or bad_rate
    ) and cleaned.get("full_name") is None


def _merge_person(existing: dict[str, Any], incoming: dict[str, Any]) -> None:
    if not existing.get("full_name") and incoming.get("full_name"):
        existing["full_name"] = incoming["full_name"]
        existing["normalized_name"] = incoming["normalized_name"]

    # Prefer fuller name over short initials.
    if existing.get("full_name") and incoming.get("full_name"):
        if len(incoming["full_name"].replace(".", "")) > len(existing["full_name"].replace(".", "")):
            existing["full_name"] = incoming["full_name"]
            existing["normalized_name"] = incoming["normalized_name"]

    for key in ["email", "phone", "city", "applied_date", "gig_rate_raw", "gig_status"]:
        if not existing.get(key) and incoming.get(key):
            existing[key] = incoming[key]

    existing["skills"] = merge_skill_lists(existing.get("skills", []), incoming.get("skills", []))

    if incoming.get("experience_years") is not None:
        existing["experience_years"] = max(existing.get("experience_years") or 0, incoming["experience_years"])
    if incoming.get("current_ctc") is not None:
        existing["current_ctc"] = max(existing.get("current_ctc") or 0, incoming["current_ctc"])
    if incoming.get("projects_completed") is not None:
        existing["projects_completed"] = max(existing.get("projects_completed") or 0, incoming["projects_completed"])

    if existing.get("verified") is None and incoming.get("verified") is not None:
        existing["verified"] = incoming["verified"]


def _load_cleaned_records(stats: IngestionStats) -> list[dict[str, Any]]:
    all_records: list[dict[str, Any]] = []

    for path in sorted(INPUT_DIR.glob("*.csv")):
        df = _read_csv(path)
        rows_read = len(df)
        stats.rows_read += rows_read
        logging.info("Read %s rows from %s", rows_read, path.name)

        duplicate_rows = int(df.duplicated().sum())
        if duplicate_rows:
            logging.warning("%s has %s exact duplicate row(s)", path.name, duplicate_rows)

        for idx, row in df.iterrows():
            raw = {k: (None if str(v).strip() == "" else str(v).strip()) for k, v in row.to_dict().items()}
            row_number = idx + 2

            if _is_repeated_header_row(path.name, raw):
                stats.rows_skipped_invalid += 1
                logging.warning("Skipped repeated header row in %s at data row %s", path.name, row_number)
                continue

            cleaned = _normalize_row(path.name, raw)

            if _looks_malformed_gig_row(path.name, raw, cleaned):
                stats.rows_skipped_invalid += 1
                logging.warning("Skipped malformed row in %s at data row %s: %s", path.name, row_number, raw)
                continue

            if not cleaned.get("full_name") and not cleaned.get("email") and not cleaned.get("phone"):
                stats.rows_skipped_empty += 1
                logging.warning("Skipped empty identity row in %s at data row %s", path.name, row_number)
                continue

            all_records.append(
                {
                    "source_file": path.name,
                    "source_row_number": row_number,
                    "raw": raw,
                    "cleaned": cleaned,
                }
            )

    return all_records


def ingest() -> None:
    setup_logging()
    stats = IngestionStats()

    all_records = _load_cleaned_records(stats)

    logging.info("Total usable rows before deduplication: %s", len(all_records))

    people: dict[int, dict[str, Any]] = {}
    people_index_by_email: dict[str, int] = {}
    people_index_by_phone: dict[str, int] = {}
    person_sources_rows: list[dict[str, Any]] = []
    ambiguous_rows: list[dict[str, Any]] = []

    next_person_id = 1

    for record in all_records:
        cleaned = record["cleaned"]
        decision: MatchDecision = resolve_match(cleaned, people_index_by_email, people_index_by_phone, people)

        if decision.status == "new":
            person_id = next_person_id
            next_person_id += 1
            people[person_id] = {
                "id": person_id,
                "normalized_name": cleaned.get("normalized_name"),
                "full_name": cleaned.get("full_name"),
                "email": cleaned.get("email"),
                "phone": cleaned.get("phone"),
                "city": cleaned.get("city"),
                "skills": cleaned.get("skills", []),
                "experience_years": cleaned.get("experience_years"),
                "current_ctc": cleaned.get("current_ctc"),
                "applied_date": cleaned.get("applied_date"),
                "gig_rate_raw": cleaned.get("gig_rate_raw"),
                "gig_status": cleaned.get("gig_status"),
                "verified": cleaned.get("verified"),
                "projects_completed": cleaned.get("projects_completed"),
                "source_count": 1,
            }
            if cleaned.get("email"):
                people_index_by_email[cleaned["email"]] = person_id
            if cleaned.get("phone"):
                people_index_by_phone[cleaned["phone"]] = person_id
            stats.created_people += 1

            person_sources_rows.append(
                {
                    "person_id": person_id,
                    "source_file": record["source_file"],
                    "source_row_number": record["source_row_number"],
                    "source_system": cleaned["source_system"],
                    "match_status": "new",
                    "match_reason": decision.reason,
                    "raw_payload": json.dumps(record["raw"], ensure_ascii=False),
                    "cleaned_payload": json.dumps(cleaned, ensure_ascii=False),
                }
            )
            continue

        if decision.status == "matched" and decision.person_id:
            person_id = decision.person_id
            _merge_person(people[person_id], cleaned)
            people[person_id]["source_count"] += 1

            if cleaned.get("email") and cleaned["email"] not in people_index_by_email:
                people_index_by_email[cleaned["email"]] = person_id
            if cleaned.get("phone") and cleaned["phone"] not in people_index_by_phone:
                people_index_by_phone[cleaned["phone"]] = person_id

            stats.duplicates_merged += 1
            person_sources_rows.append(
                {
                    "person_id": person_id,
                    "source_file": record["source_file"],
                    "source_row_number": record["source_row_number"],
                    "source_system": cleaned["source_system"],
                    "match_status": "matched",
                    "match_reason": decision.reason,
                    "raw_payload": json.dumps(record["raw"], ensure_ascii=False),
                    "cleaned_payload": json.dumps(cleaned, ensure_ascii=False),
                }
            )
            continue

        stats.ambiguous_matches += 1
        ambiguous_rows.append(
            {
                "source_file": record["source_file"],
                "source_row_number": record["source_row_number"],
                "normalized_name": cleaned.get("normalized_name"),
                "email": cleaned.get("email"),
                "phone": cleaned.get("phone"),
                "candidate_person_ids": ",".join(str(x) for x in decision.candidate_ids) or "none",
                "reason": decision.reason,
                "raw_payload": json.dumps(record["raw"], ensure_ascii=False),
                "cleaned_payload": json.dumps(cleaned, ensure_ascii=False),
            }
        )
        person_sources_rows.append(
            {
                "person_id": None,
                "source_file": record["source_file"],
                "source_row_number": record["source_row_number"],
                "source_system": cleaned["source_system"],
                "match_status": "ambiguous",
                "match_reason": decision.reason,
                "raw_payload": json.dumps(record["raw"], ensure_ascii=False),
                "cleaned_payload": json.dumps(cleaned, ensure_ascii=False),
            }
        )

    conn = get_connection()
    cursor = conn.cursor()
    try:
        recreate_schema(conn)

        # Insert people
        for person in people.values():
            cursor.execute(
                """
                INSERT INTO people (
                    normalized_name, full_name, email, phone, city, skills,
                    experience_years, current_ctc, applied_date, gig_rate_raw, gig_status,
                    verified, projects_completed, skill_category, source_count
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NULL, %s)
                """,
                (
                    person["normalized_name"],
                    person["full_name"],
                    person["email"],
                    person["phone"],
                    person["city"],
                    ", ".join(person["skills"]),
                    person["experience_years"],
                    person["current_ctc"],
                    person["applied_date"],
                    person["gig_rate_raw"],
                    person["gig_status"],
                    person["verified"],
                    person["projects_completed"],
                    person["source_count"],
                ),
            )

        # Insert person_sources
        for row in person_sources_rows:
            cursor.execute(
                """
                INSERT INTO person_sources (
                    person_id, source_file, source_row_number, source_system,
                    match_status, match_reason, raw_payload, cleaned_payload
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    row["person_id"],
                    row["source_file"],
                    row["source_row_number"],
                    row["source_system"],
                    row["match_status"],
                    row["match_reason"],
                    row["raw_payload"],
                    row["cleaned_payload"],
                ),
            )

        # Insert ambiguous_matches
        if ambiguous_rows:
            for row in ambiguous_rows:
                cursor.execute(
                    """
                    INSERT INTO ambiguous_matches (
                        source_file, source_row_number, normalized_name, email, phone,
                        candidate_person_ids, reason, raw_payload, cleaned_payload
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        row["source_file"],
                        row["source_row_number"],
                        row["normalized_name"],
                        row["email"],
                        row["phone"],
                        row["candidate_person_ids"],
                        row["reason"],
                        row["raw_payload"],
                        row["cleaned_payload"],
                    ),
                )

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()

    logging.info("Final unique people: %s", len(people))
    logging.info("Duplicates merged: %s", stats.duplicates_merged)
    logging.info("Ambiguous matches flagged: %s", stats.ambiguous_matches)
    logging.info("Rows skipped (empty identity): %s", stats.rows_skipped_empty)
    logging.info("Rows skipped (invalid/malformed): %s", stats.rows_skipped_invalid)
    logging.info("Database written to: PostgreSQL ConsultBae database")


def main() -> None:
    ingest()


if __name__ == "__main__":
    main()
