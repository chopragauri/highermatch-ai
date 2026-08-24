from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    # Cached as a singleton so the ~80MB model loads once per process, not per request.
    # In the Docker image this model is pre-downloaded at build time (see Dockerfile),
    # so this call never hits the network at runtime/demo time.
    return SentenceTransformer(MODEL_NAME)


def embed_text(text: str) -> np.ndarray:
    model = get_model()
    return model.encode(text or "", convert_to_numpy=True)


def cosine_similarity(a, b) -> float:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)
