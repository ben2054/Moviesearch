const video = document.querySelector("#video");
const placeholder = document.querySelector("#cameraPlaceholder");
const startBtn = document.querySelector("#startBtn");
const identifyBtn = document.querySelector("#identifyBtn");
const stopBtn = document.querySelector("#stopBtn");
const statusEl = document.querySelector("#status");
const resultsEl = document.querySelector("#results");
let stream = null;

function apiBase() {
  return document.querySelector("#apiUrl").value.trim().replace(/\/+$/, "");
}
function setStatus(message) { statusEl.textContent = message; }

startBtn.addEventListener("click", async () => {
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: "environment" }, width: { ideal: 1280 }, height: { ideal: 720 } },
      audio: false
    });
    video.srcObject = stream;
    await video.play();
    placeholder.hidden = true;
    startBtn.disabled = true;
    identifyBtn.disabled = false;
    stopBtn.disabled = false;
    setStatus("Camera ready. Point it at a movie scene and tap Capture 10 & identify.");
  } catch (err) {
    setStatus("Camera unavailable: " + err.message + ". Use HTTPS or localhost and allow camera access.");
  }
});

stopBtn.addEventListener("click", stopCamera);
function stopCamera() {
  if (stream) stream.getTracks().forEach(track => track.stop());
  stream = null;
  video.srcObject = null;
  placeholder.hidden = false;
  startBtn.disabled = false;
  identifyBtn.disabled = true;
  stopBtn.disabled = true;
  setStatus("Camera stopped.");
}

identifyBtn.addEventListener("click", async () => {
  if (!video.videoWidth || !video.videoHeight) {
    setStatus("Wait until the camera preview is ready.");
    return;
  }
  identifyBtn.disabled = true;
  resultsEl.replaceChildren();
  try {
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d", { alpha: false });
    const form = new FormData();
    // Ten samples across about 2 seconds. Brief delay allows a new frame to arrive.
    for (let i = 0; i < 10; i++) {
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      const blob = await new Promise(resolve => canvas.toBlob(resolve, "image/jpeg", 0.82));
      if (!blob) throw new Error("Could not capture a camera frame.");
      form.append("images", blob, `frame-${i + 1}.jpg`);
      if (i < 9) await new Promise(resolve => setTimeout(resolve, 180));
    }
    setStatus("Uploading 10 frames and comparing them with the movie library…");
    const response = await fetch(apiBase() + "/identify", { method: "POST", body: form });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.detail || `Server error ${response.status}`);
    renderResults(payload.guesses || []);
    setStatus(`Finished. Processed ${payload.images_received || 10} frames.`);
  } catch (err) {
    setStatus("Could not identify movie: " + err.message + ". Check the API URL and backend.");
  } finally {
    identifyBtn.disabled = false;
  }
});

function renderResults(guesses) {
  resultsEl.replaceChildren();
  if (!guesses.length) {
    const p = document.createElement("p");
    p.className = "hint";
    p.textContent = "No matches yet. Add more reference frames and rebuild the index.";
    resultsEl.append(p);
    return;
  }
  guesses.forEach((guess, i) => {
    const card = document.createElement("div");
    card.className = "guess";
    const name = document.createElement("strong");
    name.textContent = `${i + 1}. ${guess.movie}`;
    const meta = document.createElement("small");
    meta.textContent = `Similarity: ${Number(guess.score).toFixed(3)} · Matching frame hits: ${guess.matches}`;
    card.append(name, meta);
    resultsEl.append(card);
  });
}
