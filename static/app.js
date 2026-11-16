// Stemsplit Frontend Logic

document.addEventListener("DOMContentLoaded", () => {
  const fileInput = document.getElementById("file-input");
  const dropZone = document.getElementById("drop-zone");
  const sampleSelect = document.getElementById("sample-select");
  const btnLoadSample = document.getElementById("btn-load-sample");
  const statusBox = document.getElementById("status-box");
  const statusText = document.getElementById("status-text");
  const errorBox = document.getElementById("error-box");
  const errorText = document.getElementById("error-text");
  const songNameDisplay = document.getElementById("song-name-display");
  const trackRows = document.querySelectorAll(".track-row");

  // Keep track of active audio elements
  const tracks = {};

  // Initialize track rows
  trackRows.forEach((row) => {
    const stem = row.getAttribute("data-stem");
    const audio = row.querySelector("audio");
    const playBtn = row.querySelector(".btn-play");
    const seekBar = row.querySelector(".seek-bar");
    const timeDisplay = row.querySelector(".time-display");
    const downloadBtn = row.querySelector(".btn-download");

    tracks[stem] = {
      row,
      audio,
      playBtn,
      seekBar,
      timeDisplay,
      downloadBtn,
      isSeeking: false,
    };

    // Play / Pause toggle
    playBtn.addEventListener("click", () => {
      if (audio.paused) {
        // Pause other tracks to avoid cacophony unless desired
        Object.values(tracks).forEach((t) => {
          if (t.audio !== audio && !t.audio.paused) {
            t.audio.pause();
          }
        });
        audio.play().catch((err) => console.error("Playback error:", err));
      } else {
        audio.pause();
      }
    });

    audio.addEventListener("play", () => {
      playBtn.textContent = "Pause";
    });

    audio.addEventListener("pause", () => {
      playBtn.textContent = "Play";
    });

    audio.addEventListener("ended", () => {
      playBtn.textContent = "Play";
      seekBar.value = 0;
      updateTimeDisplay(timeDisplay, 0, audio.duration);
    });

    // Time update and seek bar sync
    audio.addEventListener("timeupdate", () => {
      if (!tracks[stem].isSeeking && audio.duration) {
        const progress = (audio.currentTime / audio.duration) * 100;
        seekBar.value = progress;
        updateTimeDisplay(timeDisplay, audio.currentTime, audio.duration);
      }
    });

    audio.addEventListener("loadedmetadata", () => {
      updateTimeDisplay(timeDisplay, 0, audio.duration);
    });

    // Seek bar user interaction
    seekBar.addEventListener("input", () => {
      tracks[stem].isSeeking = true;
      if (audio.duration) {
        const targetTime = (seekBar.value / 100) * audio.duration;
        updateTimeDisplay(timeDisplay, targetTime, audio.duration);
      }
    });

    seekBar.addEventListener("change", () => {
      if (audio.duration) {
        audio.currentTime = (seekBar.value / 100) * audio.duration;
      }
      tracks[stem].isSeeking = false;
    });
  });

  // Format seconds to mm:ss
  function formatTime(seconds) {
    if (isNaN(seconds) || seconds < 0) return "0:00";
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs < 10 ? "0" : ""}${secs}`;
  }

  function updateTimeDisplay(element, current, total) {
    element.textContent = `${formatTime(current)} / ${formatTime(total)}`;
  }

  // Load sample songs from backend
  async function loadSamples() {
    try {
      const res = await fetch("/api/samples");
      if (!res.ok) throw new Error("Failed to load samples list");
      const samples = await res.json();

      sampleSelect.innerHTML = '<option value="">-- Choose a sample --</option>';
      samples.forEach((sample) => {
        const opt = document.createElement("option");
        opt.value = sample;
        opt.textContent = sample;
        sampleSelect.appendChild(opt);
      });
    } catch (err) {
      console.error(err);
    }
  }

  sampleSelect.addEventListener("change", () => {
    btnLoadSample.disabled = !sampleSelect.value;
  });

  btnLoadSample.addEventListener("click", () => {
    if (sampleSelect.value) {
      processSample(sampleSelect.value);
    }
  });

  // Drag and drop handlers
  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("dragover");
  });

  dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("dragover");
  });

  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      uploadFile(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener("change", () => {
    if (fileInput.files && fileInput.files.length > 0) {
      uploadFile(fileInput.files[0]);
    }
  });

  // UI state management
  function setLoading(loading, message = "Separating...") {
    if (loading) {
      statusText.textContent = message;
      statusBox.classList.remove("hidden");
      errorBox.classList.add("hidden");
      fileInput.disabled = true;
      btnLoadSample.disabled = true;
      sampleSelect.disabled = true;
    } else {
      statusBox.classList.add("hidden");
      fileInput.disabled = false;
      sampleSelect.disabled = false;
      btnLoadSample.disabled = !sampleSelect.value;
    }
  }

  function showError(message) {
    errorText.textContent = message;
    errorBox.classList.remove("hidden");
  }

  function hideError() {
    errorBox.classList.add("hidden");
  }

  // Handle uploaded file
  async function uploadFile(file) {
    hideError();
    setLoading(true, `Separating "${file.name}" (running Demucs)...`);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("/api/separate/upload", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Failed to separate audio file.");
      }

      applySeparationResults(data);

      // Refresh the song dropdown and select the newly uploaded song
      await loadSamples();
      sampleSelect.value = data.filename;
      btnLoadSample.disabled = false;
    } catch (err) {
      showError(err.message);
    } finally {
      setLoading(false);
      fileInput.value = "";
    }
  }

  // Handle sample file
  async function processSample(filename) {
    hideError();
    setLoading(true, `Separating sample "${filename}"...`);

    try {
      const res = await fetch("/api/separate/sample", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Failed to process sample song.");
      }

      applySeparationResults(data);
    } catch (err) {
      showError(err.message);
    } finally {
      setLoading(false);
    }
  }

  // Update tracks with returned audio URLs
  function applySeparationResults(data) {
    songNameDisplay.textContent = `${data.filename} ${data.cached ? "(Cached)" : ""}`;

    const stems = data.stems || {};

    Object.keys(tracks).forEach((stemKey) => {
      const track = tracks[stemKey];
      const url = stems[stemKey];

      if (url) {
        track.row.style.display = "flex";
        track.audio.src = url;
        track.audio.load();

        track.playBtn.disabled = false;
        track.playBtn.textContent = "Play";
        track.seekBar.disabled = false;
        track.seekBar.value = 0;
        track.timeDisplay.textContent = "0:00 / 0:00";

        track.downloadBtn.href = url;
        track.downloadBtn.setAttribute("download", `${data.filename}_${stemKey}.wav`);
        track.downloadBtn.classList.remove("disabled");
      } else {
        // If stem not available, disable controls
        track.playBtn.disabled = true;
        track.seekBar.disabled = true;
        track.downloadBtn.classList.add("disabled");
      }
    });
  }

  // Initial load
  loadSamples();
});

