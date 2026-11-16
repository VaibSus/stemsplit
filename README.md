# Stemsplit

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.4+-EE4C2C.svg)](https://pytorch.org)
[![Demucs](https://img.shields.io/badge/Demucs-v4-blueviolet.svg)](https://github.com/facebookresearch/demucs)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A minimal, local web application that separates music tracks into isolated instrument stems using **Meta Demucs (`htdemucs_6s`)** and **FastAPI**.

Runs completely offline on your own machine with GPU acceleration and automatic CPU fallback.

---

## Features

- **6-Stem Separation**: Splits audio into **Piano**, **Guitar**, **Drums**, **Bass**, **Vocals**, and **Other**, alongside the full mix.
- **Hardware Acceleration**: Built for NVIDIA GPUs (CUDA 12.8+ / RTX series), with automatic CPU fallback.
- **VRAM Chunking**: Uses optimized segment lengths (`--segment 7`) to run smoothly within 8 GB VRAM without out-of-memory errors.
- **Instant Hash Caching**: Computes SHA-256 hashes for all processed songs. Repeat files load instantly from disk without re-running separation.
- **Persistent Library**: Uploaded songs automatically persist in your local library and populate the dropdown menu.
- **Clean Utility UI**: Lightweight vanilla HTML5/CSS/JavaScript interface with synchronized seek bars, real-time timers, and individual track downloads.

---

## Project Structure

```
stemsplit/
├── static/
│   ├── index.html       # Single-page UI
│   ├── style.css        # Clean, neutral styling
│   └── app.js           # Audio player and API interaction
├── samples/             # Sample audio files and persistent library
├── outputs/             # Cached stem output folders (<hash>/)
├── separator.py         # Demucs runner, CUDA detection, and hash caching
├── main.py              # FastAPI server (API and static hosting)
├── requirements.txt     # Python dependencies
├── LICENSE              # MIT License
└── README.md
```

---

## Getting Started

### 1. Prerequisites

- **Python 3.10+**
- **FFmpeg** (Required by Demucs for audio encoding and decoding)

#### Install FFmpeg on Windows
```powershell
winget install Gyan.FFmpeg
```
*(Or download directly from [gyan.dev/ffmpeg/builds](https://www.gyan.dev/ffmpeg/builds/) and add its `bin` folder to your system PATH).*

#### Install FFmpeg on macOS / Linux
```bash
# macOS
brew install ffmpeg

# Ubuntu / Debian
sudo apt update && sudo apt install ffmpeg
```

---

### 2. Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/VaibSus/stemsplit.git
   cd stemsplit
   ```

2. **Create and activate a virtual environment:**
   ```bash
   # Windows (PowerShell)
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

   # Linux / macOS
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install PyTorch with CUDA (Optional, for NVIDIA GPUs):**
   ```bash
   # For CUDA 12.8 / RTX 50-series and newer:
   pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128
   ```

4. **Install required packages:**
   ```bash
   pip install -r requirements.txt
   ```

---

### 3. Running the App

Start the application with a single command:
```bash
python main.py
```

Then open your browser at:
**http://localhost:8000**

---

## Supported Audio Formats

- `.mp3`
- `.wav`
- `.flac`
- `.m4a`

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgements

- [Demucs](https://github.com/facebookresearch/demucs) by Meta AI Research.
- [FastAPI](https://fastapi.tiangolo.com/) for the web framework.
