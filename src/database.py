from __future__ import annotations

import os
from typing import Any

import psycopg2
from dotenv import load_dotenv
from psycopg2.extensions import connection as pg_connection
from psycopg2.extras import RealDictCursor

# Load environment variables from .env file
load_dotenv()


def get_connection() -> pg_connection:
    """Get PostgreSQL connection using environment variables."""
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "postgres"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
        sslmode="require",  # Required for Supabase
    )
    return conn


def recreate_schema(conn: pg_connection) -> None:
    """Recreate database schema for PostgreSQL."""
    cursor = conn.cursor()
    try:
        # Drop tables if they exist
        cursor.execute("DROP TABLE IF EXISTS person_sources CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS ambiguous_matches CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS classification_failures CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS people CASCADE;")

        # Create people table
        cursor.execute(
            """
            CREATE TABLE people (
                id SERIAL PRIMARY KEY,
                normalized_name TEXT,
                full_name TEXT,
                email TEXT UNIQUE,
                phone TEXT UNIQUE,
                city TEXT,
                skills TEXT,
                experience_years REAL,
                current_ctc REAL,
                applied_date TEXT,
                gig_rate_raw TEXT,
                gig_status TEXT,
                verified INTEGER,
                projects_completed INTEGER,
                skill_category TEXT CHECK (skill_category IN ('automation-heavy','web dev','data','AI/ML','other') OR skill_category IS NULL),
                source_count INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
            """
        )

        # Create indexes
        cursor.execute(
            """
            CREATE INDEX idx_people_email ON people(email) 
            WHERE email IS NOT NULL;
            """
        )
        cursor.execute(
            """
            CREATE INDEX idx_people_phone ON people(phone) 
            WHERE phone IS NOT NULL;
            """
        )

        # Create person_sources table
        cursor.execute(
            """
            CREATE TABLE person_sources (
                id SERIAL PRIMARY KEY,
                person_id INTEGER REFERENCES people(id) ON DELETE CASCADE,
                source_file TEXT NOT NULL,
                source_row_number INTEGER NOT NULL,
                source_system TEXT NOT NULL,
                match_status TEXT NOT NULL,
                match_reason TEXT,
                raw_payload TEXT NOT NULL,
                cleaned_payload TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
            """
        )

        # Create ambiguous_matches table
        cursor.execute(
            """
            CREATE TABLE ambiguous_matches (
                id SERIAL PRIMARY KEY,
                source_file TEXT NOT NULL,
                source_row_number INTEGER NOT NULL,
                normalized_name TEXT,
                email TEXT,
                phone TEXT,
                candidate_person_ids TEXT NOT NULL,
                reason TEXT NOT NULL,
                raw_payload TEXT NOT NULL,
                cleaned_payload TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
            """
        )

        # Create classification_failures table
        cursor.execute(
            """
            CREATE TABLE classification_failures (
                id SERIAL PRIMARY KEY,
                person_id INTEGER REFERENCES people(id) ON DELETE CASCADE,
                llm_output TEXT,
                reason TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
            """
        )

        # Create audio_submissions table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS audio_submissions (
                id SERIAL PRIMARY KEY,
                person_id INTEGER REFERENCES people(id) ON DELETE CASCADE,
                matched_name TEXT,
                matched_phone TEXT,
                audio_file_path TEXT NOT NULL,
                file_size_bytes INTEGER,
                file_format TEXT,
                duration_seconds REAL,
                sample_rate_khz REAL,
                bitrate_kbps INTEGER,
                loudness_db REAL,
                noise_quality_estimate TEXT,
                submission_status TEXT DEFAULT 'submitted',
                error_message TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
            """
        )

        # Create index for audio_submissions
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_audio_submissions_person_id ON audio_submissions(person_id) 
            WHERE person_id IS NOT NULL;
            """
        )

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()