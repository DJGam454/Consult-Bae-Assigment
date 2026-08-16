"""
ConsultBae Audio Collection Web Application

Flask app for recording/uploading audio and storing metadata.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request, send_file
from werkzeug.utils import secure_filename

from src.audio_metadata import (
    check_ffmpeg_available,
    extract_audio_metadata,
    get_audio_info_string,
    validate_audio_file,
)
from src.database import get_connection

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app configuration
app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB max upload
app.config["UPLOAD_FOLDER"] = Path("uploads/audio")
app.config["UPLOAD_FOLDER"].mkdir(parents=True, exist_ok=True)

# Allowed audio formats
ALLOWED_EXTENSIONS = {"wav", "mp3", "m4a", "flac", "ogg", "webm"}


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def normalize_phone(phone: str) -> str:
    """Normalize phone number to 10-digit format."""
    # Remove all non-digit characters except leading +
    phone_digits = re.sub(r"[^\d+]", "", phone)
    
    # Remove +91 prefix if present
    if phone_digits.startswith("+91"):
        phone_digits = phone_digits[3:]
    elif phone_digits.startswith("91"):
        phone_digits = phone_digits[2:]
    
    # Remove leading 0 if present
    if phone_digits.startswith("0"):
        phone_digits = phone_digits[1:]
    
    # Return last 10 digits
    return phone_digits[-10:] if len(phone_digits) >= 10 else phone_digits


def find_matching_person(name: str, phone: str) -> dict[str, Any] | None:
    """
    Find a matching person in the database.
    
    Uses phone as primary match (most reliable).
    Falls back to name matching if phone not found.
    
    Returns: person record dict or None if no match found
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        normalized_phone = normalize_phone(phone) if phone else None
        normalized_name = name.strip().lower() if name else None
        
        # Primary: exact phone match
        if normalized_phone:
            cursor.execute(
                """
                SELECT id, full_name, email, phone, city, skills, skill_category 
                FROM people 
                WHERE REGEXP_REPLACE(phone, '[^0-9]', '') LIKE %s
                LIMIT 1
                """,
                (f"%{normalized_phone}%",),
            )
            result = cursor.fetchone()
            if result:
                return {
                    "id": result[0],
                    "full_name": result[1],
                    "email": result[2],
                    "phone": result[3],
                    "city": result[4],
                    "skills": result[5],
                    "skill_category": result[6],
                    "match_type": "phone_match",
                }
        
        # Secondary: fuzzy name match (if phone not provided or not found)
        if normalized_name:
            # Try exact match first
            cursor.execute(
                """
                SELECT id, full_name, email, phone, city, skills, skill_category 
                FROM people 
                WHERE LOWER(normalized_name) LIKE %s OR LOWER(full_name) LIKE %s
                LIMIT 1
                """,
                (f"%{normalized_name}%", f"%{normalized_name}%"),
            )
            result = cursor.fetchone()
            if result:
                return {
                    "id": result[0],
                    "full_name": result[1],
                    "email": result[2],
                    "phone": result[3],
                    "city": result[4],
                    "skills": result[5],
                    "skill_category": result[6],
                    "match_type": "name_match",
                }
        
        return None
        
    except Exception as e:
        logger.error(f"Error finding matching person: {e}")
        return None
    finally:
        if conn:
            conn.close()


def store_audio_submission(
    person_id: int | None,
    matched_name: str,
    matched_phone: str,
    audio_file_path: Path,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    """Store audio submission record in database."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        file_size_bytes = audio_file_path.stat().st_size if audio_file_path.exists() else 0
        
        cursor.execute(
            """
            INSERT INTO audio_submissions 
            (person_id, matched_name, matched_phone, audio_file_path, 
             file_size_bytes, file_format, duration_seconds, sample_rate_khz, 
             bitrate_kbps, loudness_db, noise_quality_estimate, submission_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, created_at
            """,
            (
                person_id,
                matched_name,
                matched_phone,
                str(audio_file_path),
                file_size_bytes,
                metadata.get("file_format"),
                metadata.get("duration_seconds"),
                metadata.get("sample_rate_khz"),
                metadata.get("bitrate_kbps"),
                metadata.get("loudness_db"),
                metadata.get("noise_quality_estimate"),
                "submitted",
            ),
        )
        
        result = cursor.fetchone()
        conn.commit()
        
        return {
            "submission_id": result[0],
            "timestamp": result[1],
            "status": "success",
        }
        
    except Exception as e:
        logger.error(f"Error storing audio submission: {e}")
        if conn:
            conn.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        if conn:
            conn.close()


def get_all_submissions() -> list[dict[str, Any]]:
    """Get all audio submissions with person details."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT 
                a.id, a.person_id, a.matched_name, a.matched_phone,
                a.audio_file_path, a.file_format, a.duration_seconds,
                a.sample_rate_khz, a.bitrate_kbps, a.loudness_db,
                a.noise_quality_estimate, a.created_at,
                p.full_name, p.email, p.skills, p.skill_category
            FROM audio_submissions a
            LEFT JOIN people p ON a.person_id = p.id
            ORDER BY a.created_at DESC
            """
        )
        
        submissions = []
        for row in cursor.fetchall():
            submissions.append({
                "id": row[0],
                "person_id": row[1],
                "matched_name": row[2],
                "matched_phone": row[3],
                "audio_file_path": row[4],
                "file_format": row[5],
                "duration_seconds": row[6],
                "sample_rate_khz": row[7],
                "bitrate_kbps": row[8],
                "loudness_db": row[9],
                "noise_quality_estimate": row[10],
                "created_at": row[11],
                "person_full_name": row[12],
                "person_email": row[13],
                "person_skills": row[14],
                "person_skill_category": row[15],
            })
        
        return submissions
        
    except Exception as e:
        logger.error(f"Error getting submissions: {e}")
        return []
    finally:
        if conn:
            conn.close()


# Routes

@app.route("/")
def index():
    """Home page - audio submission form."""
    ffmpeg_available = check_ffmpeg_available()
    return render_template("index.html", ffmpeg_available=ffmpeg_available)


@app.route("/submissions")
def submissions_page():
    """View all audio submissions."""
    submissions = get_all_submissions()
    return render_template("submissions.html", submissions=submissions)


@app.route("/api/submit-audio", methods=["POST"])
def submit_audio():
    """Handle audio submission via API."""
    try:
        # Get form data
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        
        if not name or not phone:
            return jsonify({"status": "error", "message": "Name and phone are required"}), 400
        
        # Check for file upload
        if "audio_file" not in request.files:
            return jsonify({"status": "error", "message": "No audio file provided"}), 400
        
        file = request.files["audio_file"]
        if file.filename == "":
            return jsonify({"status": "error", "message": "No file selected"}), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                "status": "error",
                "message": f"File type not allowed. Supported: {', '.join(ALLOWED_EXTENSIONS)}",
            }), 400
        
        # Save file with secure filename
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_")
        safe_filename = timestamp + filename
        file_path = app.config["UPLOAD_FOLDER"] / safe_filename
        
        file.save(str(file_path))
        logger.info(f"Audio file saved: {file_path}")
        
        # Validate audio file
        is_valid, error_msg = validate_audio_file(file_path)
        if not is_valid:
            file_path.unlink()  # Delete invalid file
            return jsonify({"status": "error", "message": error_msg}), 400
        
        # Extract metadata
        metadata = extract_audio_metadata(file_path)
        if metadata.get("error"):
            file_path.unlink()  # Delete file if metadata extraction failed
            return jsonify({
                "status": "error",
                "message": f"Failed to extract audio metadata: {metadata['error']}",
            }), 400
        
        # Find matching person
        person = find_matching_person(name, phone)
        person_id = person["id"] if person else None
        
        # Store in database
        result = store_audio_submission(person_id, name, phone, file_path, metadata)
        
        if result["status"] != "success":
            file_path.unlink()  # Delete file if DB storage failed
            return jsonify(result), 500
        
        # Return success response
        return jsonify({
            "status": "success",
            "submission_id": result["submission_id"],
            "message": "Audio submitted successfully",
            "person_matched": person is not None,
            "person_match_type": person.get("match_type") if person else None,
            "metadata": {
                "duration": metadata.get("duration_seconds"),
                "sample_rate": metadata.get("sample_rate_khz"),
                "bitrate": metadata.get("bitrate_kbps"),
                "loudness": metadata.get("loudness_db"),
                "quality": metadata.get("noise_quality_estimate"),
            },
        }), 201
        
    except Exception as e:
        logger.error(f"Error in submit_audio: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/audio/<int:submission_id>")
def get_audio_file(submission_id: int):
    """Serve audio file for playback."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT audio_file_path FROM audio_submissions WHERE id = %s",
            (submission_id,),
        )
        result = cursor.fetchone()
        
        if not result:
            return jsonify({"error": "Submission not found"}), 404
        
        audio_path = Path(result[0])
        if not audio_path.exists():
            return jsonify({"error": "Audio file not found"}), 404
        
        return send_file(str(audio_path), mimetype="audio/mpeg")
        
    except Exception as e:
        logger.error(f"Error getting audio file: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route("/api/health")
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "ffmpeg_available": check_ffmpeg_available(),
    })


@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large error."""
    return jsonify({
        "status": "error",
        "message": "File too large. Maximum 50 MB allowed.",
    }), 413


if __name__ == "__main__":
    logger.info("Starting ConsultBae Audio Collection App")
    logger.info(f"Upload folder: {app.config['UPLOAD_FOLDER']}")
    logger.info(f"FFmpeg available: {check_ffmpeg_available()}")
    app.run(debug=True, port=5000)
