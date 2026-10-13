"""FastAPI endpoint for identifying movies from up to 10 screenshots."""
import json
import os
from pathlib import Path
from collections import defaultdict
from io import BytesIO

import faiss
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, UnidentifiedImageError

from embedder import embed_pil_images

BASE_DIR = Path(__file__).resolve().parent
INDEX_DIR = Path(os.getenv("MOVIE_INDEX_DIR", BASE_DIR / "index"))
INDEX_PATH = INDEX_DIR / "faiss.index"
METADATA_PATH = INDEX_DIR / "metadata.json"

app = FastAPI(title="Movie Recognizer API", version="1.0.0")
# For production, replace "*" with the exact web-app origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

def load_index():
    if not INDEX_PATH.exists() or not METADATA_PATH.exists():
        return None, None
    return faiss.read_index(str(INDEX_PATH)), json.loads(METADATA_PATH.read_text(encoding="utf-8"))

@app.get("/health")
def health():
    index, metadata = load_index()
    return {"ok": True, "index_ready": index is not None, "reference_images": len(metadata or [])}

@app.post("/identify")
async def identify(images: list[UploadFile] = File(...)):
    if len(images) < 1 or len(images) > 10:
        raise HTTPException(status_code=400, detail="Upload between 1 and 10 images.")
    index, metadata = load_index()
    if index is None:
        raise HTTPException(status_code=503, detail="Movie index is not ready. Run build_index.py first.")

    pil_images = []
    for upload in images:
        if upload.content_type and not upload.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail=f"{upload.filename} is not an image.")
        try:
            raw = await upload.read()
            if len(raw) > 12 * 1024 * 1024:
                raise HTTPException(status_code=413, detail="Each image must be 12 MB or smaller.")
            with Image.open(BytesIO(raw)) as im:
                pil_images.append(im.convert("RGB").copy())
        except (UnidentifiedImageError, OSError):
            raise HTTPException(status_code=400, detail=f"Could not read image {upload.filename}.")

    query_vectors = embed_pil_images(pil_images)
    # Inner product is cosine similarity because CLIP embeddings are normalized.
    scores, ids = index.search(query_vectors, min(5, index.ntotal))
    aggregate = defaultdict(lambda: {"scores": [], "matches": 0})
    for row_scores, row_ids in zip(scores, ids):
        seen_in_image = set()
        for score, idx in zip(row_scores, row_ids):
            if idx < 0:
                continue
            movie = metadata[int(idx)]["movie"]
            if movie not in seen_in_image:
                aggregate[movie]["scores"].append(float(score))
                aggregate[movie]["matches"] += 1
                seen_in_image.add(movie)

    ranked = []
    for movie, item in aggregate.items():
        # Mean of the strongest per-image matches helps reduce duplicate-frame bias.
        avg = sum(item["scores"]) / len(item["scores"])
        ranked.append({"movie": movie, "score": round(avg, 4), "matches": item["matches"]})
    ranked.sort(key=lambda x: (x["score"], x["matches"]), reverse=True)
    return {"guesses": ranked[:3], "images_received": len(pil_images)}
