#!/usr/bin/env python3
"""Test PostgreSQL connection with credentials from .env"""

import os
from dotenv import load_dotenv
import psycopg2

# Load .env variables
load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "ConsultBae")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

print(f"Testing PostgreSQL connection...")
print(f"  Host: {DB_HOST}")
print(f"  Port: {DB_PORT}")
print(f"  Database: {DB_NAME}")
print(f"  User: {DB_USER}")

try:
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    version = cursor.fetchone()
    print(f"\n✅ Connection successful!")
    print(f"   PostgreSQL version: {version[0]}")
    
    cursor.close()
    conn.close()
except Exception as e:
    print(f"\n❌ Connection failed!")
    print(f"   Error: {e}")
    print(f"\n⚠️  Make sure:")
    print(f"   1. PostgreSQL server is running")
    print(f"   2. Database '{DB_NAME}' exists")
    print(f"   3. .env file has correct credentials")
