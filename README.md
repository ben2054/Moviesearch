# Movie Recognizer (Web + Android)

A starter project that compares camera screenshots with a reference library of movie frames and returns the three closest movie guesses.

## Important
- This is a visual similarity demo, not a guarantee of exact movie identification.
- You must build a reference index from movie screenshots/frames you are allowed to use.
- The backend downloads model weights the first time it runs and needs a capable internet connection. CPU inference works but can be slow; a GPU is recommended for larger libraries.
- Do not use this project to distribute copyrighted movie files. Keep your frame library lawful and private.
- The Android app is a source project; it is not a signed APK yet.

## 1. Backend setup

Requires Python 3.10 or 3.11. From the `backend` directory:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
```

Create a library with one folder per movie, for example:

```text
movie-library/
  The Matrix/
    frame001.jpg
    frame002.jpg
  Inception/
    frame001.jpg
    frame002.jpg
```

You can use your own permitted screenshots, or frames from material you have rights to use. Then build the index:

```bash
python build_index.py --library ../movie-library --output index
```

Start the API:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Health check: `http://127.0.0.1:8000/health`
API docs: `http://127.0.0.1:8000/docs`

The first run downloads CLIP weights. The generated `backend/index/` directory contains the FAISS index and metadata.

## 2. Web app

Serve the web folder over HTTP(S), rather than opening the HTML file directly. For example, from the project root:

```bash
python -m http.server 8080
```

Open `http://localhost:8080/web/` on the same computer. Camera access normally requires HTTPS or localhost.

In the web app, enter the backend URL:
- Same computer: `http://127.0.0.1:8000`
- Android phone on same Wi-Fi: `http://YOUR-COMPUTER-LAN-IP:8000`

If testing on a physical phone, the phone and computer must be on the same Wi-Fi and your firewall must allow port 8000. A hosted web page cannot call `127.0.0.1` on your computer from the phone; use the computer's LAN IP or a properly deployed HTTPS API.

## 3. Android app

Open the `android/` folder in Android Studio. Let Gradle sync, then run on a physical Android phone or emulator.

Set the API base URL in `android/app/src/main/java/com/example/movierecognizer/MainActivity.kt`:
- Android emulator talking to backend on your computer: `http://10.0.2.2:8000/`
- Physical phone on same Wi-Fi: `http://YOUR-COMPUTER-LAN-IP:8000/`
- Deployed server: use your HTTPS API URL.

The starter allows cleartext HTTP for local development. For a public release, use HTTPS and remove the cleartext setting. Camera permission is requested at runtime. The app captures 10 photos and uploads them to `POST /identify`.

## API

`POST /identify` accepts 1–10 image files as multipart field `images` and returns up to three guesses:

```json
{
  "guesses": [
    {"movie": "Example Movie", "score": 0.82, "matches": 4}
  ]
}
```

`score` is a relative similarity score, not a calibrated probability. Results depend heavily on the quality and coverage of your reference library.

## Troubleshooting

- `Index not found`: run `build_index.py` first and ensure `backend/index/faiss.index` and `metadata.json` exist.
- Empty results: add more representative frames and rebuild the index.
- Slow first request: CLIP weights are being loaded/downloaded; CPU processing can take time.
- Android cannot connect: check API URL, same Wi-Fi, firewall, and that Uvicorn is bound to `0.0.0.0`.
- Browser camera blocked: use localhost or HTTPS and grant camera permission.
