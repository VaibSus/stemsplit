"""
main.py - FastAPI Application for Stemsplit
Serves both backend separation API and frontend UI in a single command.
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import List, Dict, Any

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

import separator

# Initialize FastAPI app
app = FastAPI(
    title="Stemsplit",
    description="Clean, minimal local music track separation web tool.",
    version="1.0.0",
)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
SAMPLES_DIR = BASE_DIR / "samples"
OUTPUTS_DIR = BASE_DIR / "outputs"

# Allowed audio extensions
ALLOWED_EXTENSIONS = {".mp3", ".wav", ".flac", ".m4a"}

# Mount outputs directory to stream and download separated stems
app.mount("/outputs", StaticFiles(directory=str(OUTPUTS_DIR)), name="outputs")

# Mount static directory for JS and CSS
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class SampleRequest(BaseModel):
    filename: str


@app.on_event("startup")
def startup_event():
    """Verify CUDA and environment setup on app startup."""
    print("==================================================")
    print("Stemsplit backend initializing...")
    device = separator.get_device()
    print(f"Demucs Compute Device: {device.upper()}")
    print(f"Samples directory: {SAMPLES_DIR}")
    print(f"Outputs directory: {OUTPUTS_DIR}")
    print("==================================================")


@app.get("/")
def get_index():
    """Serve the single-page application frontend."""
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(index_file)


@app.get("/api/samples")
def list_samples() -> List[str]:
    """
    List all available sample songs in the samples/ folder.
    """
    if not SAMPLES_DIR.exists():
        return []
    files = [
        f.name
        for f in SAMPLES_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in ALLOWED_EXTENSIONS
    ]
    return sorted(files)


@app.post("/api/separate/upload")
async def separate_upload(file: UploadFile = File(...)):
    """
    Upload an audio file, save it to the samples/ library so it appears in
    the song picker menu, and separate it into instrument stems.
    """
    raw_filename = file.filename or "uploaded_song.mp3"
    filename = Path(raw_filename).name  # Prevent directory traversal
    suffix = Path(filename).suffix.lower()

    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{suffix}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # Save directly to samples/ library so it shows up in the "Pick a song" menu
    saved_path = SAMPLES_DIR / filename
    with open(saved_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # Perform separation (cached if previously processed)
        result = separator.separate_audio(
            input_audio_path=saved_path,
            original_filename=filename,
        )
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/separate/sample")
def separate_sample(payload: SampleRequest):
    """
    Separate a chosen song from the samples/ folder.
    """
    sample_name = payload.filename
    sample_path = SAMPLES_DIR / sample_name

    # Validate that sample exists and doesn't traverse path
    if not sample_path.resolve().is_relative_to(SAMPLES_DIR.resolve()) or not sample_path.exists():
        raise HTTPException(status_code=404, detail=f"Sample '{sample_name}' not found.")

    suffix = sample_path.suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Invalid audio file extension.")

    try:
        result = separator.separate_audio(
            input_audio_path=sample_path,
            original_filename=sample_name,
        )
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    # Run local server on port 8000
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)

