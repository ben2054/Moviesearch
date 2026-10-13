"""CLIP image encoder shared by index builder and API."""
from functools import lru_cache
import numpy as np
import open_clip
import torch
from PIL import Image

MODEL_NAME = "ViT-B-32"
PRETRAINED = "laion2b_s34b_b79k"

@lru_cache(maxsize=1)
def _load_model():
    model, _, preprocess = open_clip.create_model_and_transforms(
        MODEL_NAME, pretrained=PRETRAINED
    )
    model.eval()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = model.to(device)
    return model, preprocess, device

def embed_pil_images(images):
    """Return normalized float32 CLIP embeddings for a list of PIL images."""
    if not images:
        return np.empty((0, 512), dtype="float32")
    model, preprocess, device = _load_model()
    batch = torch.stack([preprocess(img.convert("RGB")) for img in images]).to(device)
    with torch.no_grad():
        features = model.encode_image(batch)
        features = features / features.norm(dim=-1, keepdim=True).clamp(min=1e-12)
    return features.cpu().numpy().astype("float32")
