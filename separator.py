"""
separator.py - Audio Separation Module for Stemsplit
Handles audio hashing, caching, CUDA detection, and Demucs stem separation.
"""

import os
import sys
import shutil
import hashlib
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

# Suppress HuggingFace symlink warning on Windows
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

import torch

# Configure simple logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("stemsplit")

# Base directories
BASE_DIR = Path(__file__).resolve().parent
OUTPUTS_DIR = BASE_DIR / "outputs"
SAMPLES_DIR = BASE_DIR / "samples"

OUTPUTS_DIR.mkdir(exist_ok=True)
SAMPLES_DIR.mkdir(exist_ok=True)

# Required stems from htdemucs_6s
EXPECTED_STEMS = ["piano", "guitar", "drums", "bass", "vocals", "other"]


def get_device() -> str:
    """
    Check if CUDA is available on the machine.
    Uses GPU if available (NVIDIA RTX 50-series Blackwell with CUDA 12.8+),
    otherwise falls back to CPU with a warning.
    """
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        logger.info(f"CUDA detected: Using GPU [{gpu_name}] for Demucs separation.")
        return "cuda"
    else:
        logger.warning(
            "WARNING: CUDA was not detected by PyTorch! "
            "Falling back to CPU. Separation will take substantially longer. "
            "Please ensure PyTorch with CUDA support is installed."
        )
        return "cpu"


def calculate_file_hash(file_path: Path) -> str:
    """
    Calculate the SHA-256 hash of a file for caching.
    Reads in 64KB chunks to handle large audio files smoothly.
    """
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
    return sha256.hexdigest()


def is_cached(output_dir: Path) -> bool:
    """
    Check if a song has already been separated and all stem files exist.
    """
    if not output_dir.exists():
        return False

    # Check if the original/full audio exists
    full_audio = list(output_dir.glob("original.*"))
    if not full_audio:
        return False

    # Check that every expected stem exists as .wav or .mp3
    for stem in EXPECTED_STEMS:
        wav_file = output_dir / f"{stem}.wav"
        mp3_file = output_dir / f"{stem}.mp3"
        if not wav_file.exists() and not mp3_file.exists():
            return False

    return True


def get_stem_urls(song_hash: str, output_dir: Path) -> Dict[str, str]:
    """
    Generate the web-accessible URLs for the separated audio tracks.
    """
    urls: Dict[str, str] = {}

    # Full song track
    full_candidates = list(output_dir.glob("original.*"))
    if full_candidates:
        urls["full"] = f"/outputs/{song_hash}/{full_candidates[0].name}"

    # Stem tracks
    for stem in EXPECTED_STEMS:
        wav_file = output_dir / f"{stem}.wav"
        mp3_file = output_dir / f"{stem}.mp3"
        if wav_file.exists():
            urls[stem] = f"/outputs/{song_hash}/{stem}.wav"
        elif mp3_file.exists():
            urls[stem] = f"/outputs/{song_hash}/{stem}.mp3"

    return urls


def separate_audio(
    input_audio_path: Path,
    original_filename: str,
    model_name: str = "htdemucs_6s",
    segment_length: int = 7,
) -> Dict[str, Any]:
    """
    Separates an audio file into instrument stems using Demucs.
    - Caches results by file hash in outputs/<song-hash>/
    - Uses CUDA GPU if available with --segment chunking for 8GB VRAM (max int <= 7 for HTDemucs)
    - Falls back to CPU if CUDA is not available
    """
    if not input_audio_path.exists():
        raise FileNotFoundError(f"Input audio file not found: {input_audio_path}")

    # 1. Compute file hash
    song_hash = calculate_file_hash(input_audio_path)
    output_dir = OUTPUTS_DIR / song_hash

    # 2. Check if already cached
    if is_cached(output_dir):
        logger.info(f"Cache hit for hash [{song_hash}]. Returning existing stems.")
        stem_urls = get_stem_urls(song_hash, output_dir)
        return {
            "cached": True,
            "hash": song_hash,
            "filename": original_filename,
            "device": "cached",
            "stems": stem_urls,
        }

    # 3. Create output directory for this song
    output_dir.mkdir(parents=True, exist_ok=True)

    # 4. Save a copy of the original audio file
    ext = input_audio_path.suffix.lower()
    saved_original = output_dir / f"original{ext}"
    if not saved_original.exists():
        shutil.copy2(input_audio_path, saved_original)

    # 5. Detect compute device (CUDA vs CPU)
    device = get_device()

    # 6. Run Demucs via subprocess
    # We use Demucs command line interface which handles streaming/segmenting reliably.
    # --segment limits the chunk size in seconds so 8GB VRAM is never exhausted.
    temp_demucs_dir = output_dir / "_temp_demucs"
    temp_demucs_dir.mkdir(exist_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "demucs.separate",
        "-n",
        model_name,
        "--segment",
        str(segment_length),
        "-d",
        device,
        "-o",
        str(temp_demucs_dir),
        str(saved_original),
    ]

    logger.info(f"Running Demucs command: {' '.join(cmd)}")
    try:
        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=True,
        )
        logger.info("Demucs separation completed successfully.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Demucs failed with exit code {e.returncode}:\n{e.output}")
        raise RuntimeError(f"Separation failed: {e.output}") from e

    # 7. Demucs places output in: <temp_demucs_dir>/<model_name>/original/<stem>.wav
    demucs_model_folder = temp_demucs_dir / model_name / saved_original.stem
    if not demucs_model_folder.exists():
        # Fallback search if Demucs used full filename
        possible_folders = list((temp_demucs_dir / model_name).glob("*"))
        if possible_folders:
            demucs_model_folder = possible_folders[0]
        else:
            raise RuntimeError(
                f"Demucs output folder not found inside {temp_demucs_dir / model_name}"
            )

    # Move stem files to the root of output_dir
    for stem_file in demucs_model_folder.glob("*.wav"):
        target_stem = output_dir / stem_file.name
        shutil.move(str(stem_file), str(target_stem))

    # Clean up temporary Demucs directory
    shutil.rmtree(temp_demucs_dir, ignore_errors=True)

    # 8. Return results
    stem_urls = get_stem_urls(song_hash, output_dir)
    return {
        "cached": False,
        "hash": song_hash,
        "filename": original_filename,
        "device": device,
        "stems": stem_urls,
    }

