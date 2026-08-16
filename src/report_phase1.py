from __future__ import annotations

from src.database import get_connection


def main() -> None:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Fetch people counts
        cursor.execute("SELECT COUNT(*) AS c FROM people")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) AS c FROM people WHERE skill_category IS NULL")
        unclassified = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) AS c FROM ambiguous_matches")
        ambiguous = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) AS c FROM classification_failures")
        failures = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) AS c FROM people WHERE skill_category IS NOT NULL")
        classified = cursor.fetchone()[0]
        
        processed = classified + failures

        print("=== PEOPLE COUNTS ===")
        print(f"Total people: {total}")
        print(f"Unclassified (skill_category IS NULL): {unclassified}")
        print(f"Ambiguous matches: {ambiguous}")
        print(f"Classification failures: {failures}")

        print("\n=== CLASSIFICATION RUN SUMMARY ===")
        print(f"Processed: {processed}")
        print(f"Successfully classified: {classified}")
        print(f"Failures: {failures}")

        print("\n=== CATEGORY DISTRIBUTION ===")
        cursor.execute(
            """
            SELECT COALESCE(skill_category, 'NULL') AS category, COUNT(*) AS count
            FROM people
            GROUP BY COALESCE(skill_category, 'NULL')
            ORDER BY count DESC
            """
        )
        for row in cursor.fetchall():
            print(f"{row[0]}: {row[1]}")

        print("\n=== SAMPLE PEOPLE ===")
        cursor.execute(
            """
            SELECT id, full_name, email, phone, city, skills, skill_category, source_count
            FROM people
            ORDER BY id
            LIMIT 15
            """
        )
        for row in cursor.fetchall():
            print({
                "id": row[0],
                "full_name": row[1],
                "email": row[2],
                "phone": row[3],
                "city": row[4],
                "skills": row[5],
                "skill_category": row[6],
                "source_count": row[7],
            })
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
