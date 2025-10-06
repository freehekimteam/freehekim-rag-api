import numpy as np
from config import Settings

settings = Settings()

DIM = 1536

def _fake_vec():
    # deterministic placeholder vector for scaffolding
    return [0.0] * DIM

# TODO: implement real providers

def embed(text: str):
    if settings.embed_provider == "openai":
        # call OpenAI embeddings here
        return _fake_vec()
    elif settings.embed_provider == "bge-m3":
        # call local embedding model here
        return _fake_vec()
    return _fake_vec()
