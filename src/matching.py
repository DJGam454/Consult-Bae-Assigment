from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from rapidfuzz import fuzz


@dataclass
class MatchDecision:
    status: str  # new | matched | ambiguous
    person_id: int | None
    reason: str
    candidate_ids: list[int]


def resolve_match(
    record: dict[str, Any],
    people_index_by_email: dict[str, int],
    people_index_by_phone: dict[str, int],
    people: dict[int, dict[str, Any]],
) -> MatchDecision:
    email = record.get("email")
    phone = record.get("phone")
    name = record.get("normalized_name")
    city = record.get("city")

    candidates: set[int] = set()
    reasons: list[str] = []

    if email and email in people_index_by_email:
        candidates.add(people_index_by_email[email])
        reasons.append("email")
    if phone and phone in people_index_by_phone:
        candidates.add(people_index_by_phone[phone])
        reasons.append("phone")

    if len(candidates) == 1:
        return MatchDecision("matched", next(iter(candidates)), "+".join(reasons), sorted(candidates))
    if len(candidates) > 1:
        return MatchDecision("ambiguous", None, "conflicting email/phone", sorted(candidates))

    # Conservative name-based matching only when contact details are missing.
    if name and (not email or not phone):
        possible: list[tuple[int, str]] = []
        for pid, person in people.items():
            pname = person.get("normalized_name")
            pcity = person.get("city")
            if not pname:
                continue

            # never merge if both phone numbers exist and conflict
            if phone and person.get("phone") and phone != person.get("phone"):
                continue
            if email and person.get("email") and email != person.get("email"):
                continue

            if name == pname and (not city or not pcity or city == pcity):
                possible.append((pid, "exact name + compatible city"))
                continue

            score = fuzz.ratio(name.lower(), str(pname).lower())
            if score >= 96 and city and pcity and city == pcity:
                possible.append((pid, f"fuzzy name {score:.1f} + same city"))

        if len(possible) == 1:
            pid, reason = possible[0]
            return MatchDecision("matched", pid, reason, [pid])
        if len(possible) > 1:
            return MatchDecision("ambiguous", None, "multiple name matches", [pid for pid, _ in possible])

    return MatchDecision("new", None, "no reliable match", [])
