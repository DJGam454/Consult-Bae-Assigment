"""
Audio metadata extraction and analysis module.

Extracts audio file metadata including duration, sample rate, bitrate, and loudness.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

try:
    import librosa
    import soundfile as sf
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False


def check_ffmpeg_available() -> bool:
    """Check if FFmpeg is installed and available."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def extract_audio_metadata(file_path: Path) -> dict[str, Any]:
    """
    Extract metadata from audio file.
    
    Returns:
        Dictionary with keys: duration_seconds, sample_rate_khz, bitrate_kbps, 
        loudness_db, noise_quality_estimate, file_format, error
    """
    metadata = {
        "file_format": None,
        "duration_seconds": None,
        "sample_rate_khz": None,
        "bitrate_kbps": None,
        "loudness_db": None,
        "noise_quality_estimate": None,
        "error": None,
    }
    
    # Determine file format
    suffix = file_path.suffix.lower()
    metadata["file_format"] = suffix.lstrip(".")
    
    # Supported formats
    supported_formats = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".webm"}
    if suffix not in supported_formats:
        metadata["error"] = f"Unsupported audio format: {suffix}. Supported: {', '.join(supported_formats)}"
        return metadata
    
    try:
        # Try using librosa first (most reliable)
        if LIBROSA_AVAILABLE:
            try:
                y, sr = librosa.load(str(file_path), sr=None)
                metadata["sample_rate_khz"] = sr / 1000.0
                metadata["duration_seconds"] = float(librosa.get_duration(y=y, sr=sr))
                
                # Calculate loudness (simple LUFS-like estimation)
                S = librosa.feature.melspectrogram(y=y, sr=sr)
                S_db = librosa.power_to_db(S, ref=1.0)
                loudness = float(S_db.mean())
                metadata["loudness_db"] = loudness
                
                # Noise quality estimate
                metadata["noise_quality_estimate"] = estimate_noise_quality(y, sr)
                
                # Try to get bitrate from file
                bitrate = estimate_bitrate(file_path, metadata["duration_seconds"])
                if bitrate:
                    metadata["bitrate_kbps"] = bitrate
                
                return metadata
                
            except Exception as e:
                if not PYDUB_AVAILABLE:
                    metadata["error"] = f"Librosa failed and pydub not available: {str(e)}"
                    return metadata
                # Fall through to pydub
        
        # Try pydub as fallback
        if PYDUB_AVAILABLE:
            try:
                audio = AudioSegment.from_file(str(file_path))
                metadata["duration_seconds"] = float(audio.duration_seconds)
                metadata["sample_rate_khz"] = audio.frame_rate / 1000.0
                
                # Calculate bitrate
                file_size_mb = file_path.stat().st_size / (1024 * 1024)
                if metadata["duration_seconds"] > 0:
                    metadata["bitrate_kbps"] = int(
                        (file_size_mb * 8192) / metadata["duration_seconds"]
                    )
                
                # Simple loudness estimation from pydub
                loudness = audio.dBFS if hasattr(audio, "dBFS") else -20.0
                metadata["loudness_db"] = float(loudness)
                
                return metadata
                
            except Exception as e:
                metadata["error"] = f"Pydub failed: {str(e)}"
                return metadata
        
        # Fallback: use basic file size estimation
        if not LIBROSA_AVAILABLE and not PYDUB_AVAILABLE:
            file_size = file_path.stat().st_size
            # Basic estimation: assume 128 kbps as average
            estimated_duration = file_size / (128000 / 8)
            metadata["duration_seconds"] = float(estimated_duration)
            metadata["bitrate_kbps"] = 128
            metadata["sample_rate_khz"] = 44.1  # Common default
            metadata[
                "error"
            ] = "Warning: Using estimated metadata (librosa/pydub not available)"
            return metadata
            
    except Exception as e:
        metadata["error"] = f"Unexpected error during metadata extraction: {str(e)}"
        return metadata
    
    return metadata


def estimate_noise_quality(y: Any, sr: int) -> str:
    """
    Estimate audio noise/quality level.
    
    Returns: 'high', 'medium', or 'low'
    """
    try:
        # Simple estimation based on spectral characteristics
        S = librosa.feature.melspectrogram(y=y, sr=sr)
        S_db = librosa.power_to_db(S, ref=1.0)
        
        # Calculate spectral flux (noise indicator)
        spectral_flux = librosa.onset.onset_strength(S=S_db)
        flux_mean = spectral_flux.mean()
        
        if flux_mean > 50:
            return "low"  # High flux suggests noise/distortion
        elif flux_mean > 20:
            return "medium"
        else:
            return "high"
            
    except Exception:
        return "unknown"


def estimate_bitrate(file_path: Path, duration_seconds: float | None) -> int | None:
    """Estimate bitrate from file size and duration."""
    try:
        if not duration_seconds or duration_seconds <= 0:
            return None
            
        file_size_bytes = file_path.stat().st_size
        # Bitrate = (file_size_bytes * 8) / duration_seconds / 1000
        bitrate_kbps = int((file_size_bytes * 8) / duration_seconds / 1000)
        return max(8, min(320, bitrate_kbps))  # Clamp to reasonable range
        
    except Exception:
        return None


def validate_audio_file(
    file_path: Path,
    max_size_mb: int = 50,
) -> tuple[bool, str]:
    """
    Validate audio file.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check file exists
    if not file_path.exists():
        return False, "File does not exist"
    
    # Check file size
    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    if file_size_mb > max_size_mb:
        return False, f"File size ({file_size_mb:.1f} MB) exceeds limit ({max_size_mb} MB)"
    
    # Check file format
    suffix = file_path.suffix.lower()
    supported_formats = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".webm"}
    if suffix not in supported_formats:
        return False, f"Unsupported format. Supported: {', '.join(supported_formats)}"
    
    # Try to extract metadata
    metadata = extract_audio_metadata(file_path)
    if metadata["error"]:
        return False, f"Invalid audio file: {metadata['error']}"
    
    if not metadata["duration_seconds"] or metadata["duration_seconds"] <= 0:
        return False, "Could not determine audio duration"
    
    # Reasonable duration limits
    if metadata["duration_seconds"] < 1:
        return False, "Audio must be at least 1 second long"
    
    if metadata["duration_seconds"] > 3600:  # 1 hour max
        return False, "Audio must be less than 1 hour long"
    
    return True, ""


def get_audio_info_string(metadata: dict[str, Any]) -> str:
    """Format metadata as readable string for display."""
    parts = []
    
    if metadata.get("duration_seconds"):
        mins = int(metadata["duration_seconds"] // 60)
        secs = int(metadata["duration_seconds"] % 60)
        parts.append(f"Duration: {mins}:{secs:02d}")
    
    if metadata.get("sample_rate_khz"):
        parts.append(f"Sample Rate: {metadata['sample_rate_khz']:.1f} kHz")
    
    if metadata.get("bitrate_kbps"):
        parts.append(f"Bitrate: {metadata['bitrate_kbps']} kbps")
    
    if metadata.get("loudness_db"):
        parts.append(f"Loudness: {metadata['loudness_db']:.1f} dB")
    
    if metadata.get("noise_quality_estimate"):
        parts.append(f"Quality: {metadata['noise_quality_estimate']}")
    
    return " | ".join(parts)
