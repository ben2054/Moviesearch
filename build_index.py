"""Build a FAISS cosine-similarity index from a folder-per-movie image library."""
import argparse
import json
from pathlib import Path
import faiss
from PIL import Image, UnidentifiedImageError
from embedder import embed_pil_images

EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--library", required=True, help="Root folder; each movie should have its own subfolder")
    parser.add_argument("--output", default="index", help="Output directory")
    parser.add_argument("--batch-size", type=int, default=16)
    args = parser.parse_args()

    library = Path(args.library).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    paths = sorted(p for p in library.rglob("*") if p.is_file() and p.suffix.lower() in EXTENSIONS)
    if not paths:
        raise SystemExit(f"No supported images found under {library}")

    metadata = []
    vectors = []
    batch_images, batch_meta = [], []

    def flush():
        if not batch_images:
            return
        vectors.append(embed_pil_images(batch_images))
        metadata.extend(batch_meta)
        batch_images.clear()
        batch_meta.clear()

    for path in paths:
        try:
            with Image.open(path) as im:
                batch_images.append(im.convert("RGB").copy())
            rel = path.relative_to(library)
            movie = rel.parts[0] if len(rel.parts) > 1 else path.stem
            batch_meta.append({"movie": movie, "file": str(rel)})
            if len(batch_images) >= args.batch_size:
                flush()
        except (UnidentifiedImageError, OSError) as exc:
            print(f"Skipping unreadable image {path}: {exc}")
    flush()

    if not vectors:
        raise SystemExit("No readable images found.")
    import numpy as np
    matrix = np.concatenate(vectors).astype("float32")
    index = faiss.IndexFlatIP(matrix.shape[1])
    index.add(matrix)
    output.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(output / "faiss.index"))
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Indexed {len(metadata)} images for {len(set(m['movie'] for m in metadata))} movie labels.")
    print(f"Saved index to {output}")

if __name__ == "__main__":
    main()
