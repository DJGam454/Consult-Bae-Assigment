#!/usr/bin/env python
"""Create audio_submissions table in database"""

from src.database import get_connection
import psycopg2

print("Creating audio_submissions table...")

conn = get_connection()
cur = conn.cursor()

# Create audio_submissions table
sql = """
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
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audio_submissions_person_id 
ON audio_submissions(person_id);
"""

try:
    cur.execute(sql)
    conn.commit()
    print("✓ audio_submissions table created successfully")
    
    # Verify table exists
    cur.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_name = 'audio_submissions'
        )
    """)
    exists = cur.fetchone()[0]
    if exists:
        print("✓ Table verified in database")
    
    # Show table structure
    cur.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'audio_submissions'
        ORDER BY ordinal_position
    """)
    
    print("\nTable Structure:")
    for col_name, col_type in cur.fetchall():
        print(f"  - {col_name}: {col_type}")
    
except Exception as e:
    print(f"✗ Error: {e}")
    conn.rollback()
finally:
    cur.close()
    conn.close()

print("\n✅ Database setup complete")
