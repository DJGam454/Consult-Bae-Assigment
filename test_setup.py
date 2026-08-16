"""
Test script to verify Flask app setup and database connection
"""

from __future__ import annotations

import sys
from pathlib import Path

def test_imports():
    """Test if all required modules can be imported"""
    print("Testing imports...")
    
    required_modules = [
        'flask',
        'psycopg2',
        'dotenv',
        'pandas',
        'rapidfuzz',
    ]
    
    optional_modules = [
        'librosa',
        'soundfile',
        'pydub',
    ]
    
    failed = []
    for module in required_modules:
        try:
            __import__(module)
            print(f"  ✓ {module}")
        except ImportError as e:
            print(f"  ✗ {module}: {e}")
            failed.append(module)
    
    print("\nOptional audio processing modules:")
    for module in optional_modules:
        try:
            __import__(module)
            print(f"  ✓ {module}")
        except ImportError:
            print(f"  ✗ {module} (optional)")
    
    if failed:
        print(f"\n❌ Missing required modules: {', '.join(failed)}")
        return False
    
    print("\n✅ All required modules present")
    return True


def test_file_structure():
    """Test if all required files exist"""
    print("\nTesting file structure...")
    
    required_files = [
        'app/app.py',
        'app/templates/base.html',
        'app/templates/index.html',
        'app/templates/submissions.html',
        'src/database.py',
        'src/audio_metadata.py',
        'src/ingest.py',
        '.env',
        'requirements.txt',
        '.gitignore',
    ]
    
    failed = []
    for file_path in required_files:
        path = Path(file_path)
        if path.exists():
            print(f"  ✓ {file_path}")
        else:
            print(f"  ✗ {file_path} NOT FOUND")
            failed.append(file_path)
    
    if failed:
        print(f"\n❌ Missing files: {', '.join(failed)}")
        return False
    
    print("\n✅ All required files present")
    return True


def test_env_variables():
    """Test if environment variables are configured"""
    print("\nTesting environment variables...")
    
    try:
        from dotenv import load_dotenv
        import os
        
        load_dotenv()
        
        required_vars = [
            'DB_HOST',
            'DB_PORT',
            'DB_NAME',
            'DB_USER',
            'DB_PASSWORD',
        ]
        
        failed = []
        for var in required_vars:
            value = os.getenv(var)
            if value:
                # Show masked value for security
                masked = value[:3] + '*' * (len(value) - 6) if len(value) > 6 else '*' * len(value)
                print(f"  ✓ {var}={masked}")
            else:
                print(f"  ✗ {var} NOT SET")
                failed.append(var)
        
        if failed:
            print(f"\n⚠️  Missing environment variables: {', '.join(failed)}")
            return False
        
        print("\n✅ All required environment variables configured")
        return True
        
    except Exception as e:
        print(f"❌ Error checking env variables: {e}")
        return False


def test_database_connection():
    """Test database connection"""
    print("\nTesting database connection...")
    
    try:
        from src.database import get_connection
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"  ✓ Connected to PostgreSQL")
        print(f"    Version: {version[:50]}...")
        
        # Check if tables exist
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name IN ('people', 'audio_submissions')
        """)
        tables = cursor.fetchall()
        
        print(f"\n  Tables in database:")
        if any('people' in t for t in tables):
            print(f"    ✓ people table exists")
        else:
            print(f"    ✗ people table NOT FOUND")
        
        if any('audio_submissions' in t for t in tables):
            print(f"    ✓ audio_submissions table exists")
        else:
            print(f"    ✗ audio_submissions table NOT FOUND (needs creation)")
        
        cursor.close()
        conn.close()
        print("\n✅ Database connection successful")
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 70)
    print("ConsultBae Flask Audio App - Setup Verification")
    print("=" * 70)
    
    results = {
        "Imports": test_imports(),
        "File Structure": test_file_structure(),
        "Environment Variables": test_env_variables(),
        "Database Connection": test_database_connection(),
    }
    
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 70)
    if all_passed:
        print("✅ All tests passed! Flask app is ready to run.")
        print("\nTo start the app, run:")
        print("  python app/app.py")
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        sys.exit(1)
    print("=" * 70)


if __name__ == "__main__":
    main()
