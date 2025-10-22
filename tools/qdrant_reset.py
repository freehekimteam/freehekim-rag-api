#!/usr/bin/env python3
"""
Qdrant collections reset tool for FreeHekim RAG

Deletes and recreates the expected collections with the correct
vector dimension inferred from application settings.

Usage:
  python tools/qdrant_reset.py --yes

Options:
  --collections freehekim_internal,freehekim_external  Comma-separated list (default)
  --dimension 1536                                      Override vector size (default: from model)
  --distance cosine|dot|euclid                          Vector distance (default: cosine)
  -y, --yes                                             Skip confirmation prompt

Notes:
  - Reads config from repo .env via Settings (fastapi/config.py)
  - Requires Qdrant to be reachable (docker compose up)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add fastapi to path (so we can import Settings and helpers)
sys.path.insert(0, str(Path(__file__).parent.parent / "fastapi"))

from config import Settings  # type: ignore
from rag.embeddings import get_embedding_dimension  # type: ignore

from qdrant_client import QdrantClient  # type: ignore
from qdrant_client.models import Distance, VectorParams  # type: ignore


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Reset Qdrant collections for FreeHekim RAG")
    p.add_argument(
        "--collections",
        type=str,
        default="freehekim_internal,freehekim_external",
        help="Comma-separated collection names",
    )
    p.add_argument(
        "--dimension",
        type=int,
        default=0,
        help="Vector dimension override (default: infer from model)",
    )
    p.add_argument(
        "--distance",
        type=str,
        choices=["cosine", "dot", "euclid"],
        default="cosine",
        help="Vector distance (default: cosine)",
    )
    p.add_argument("-y", "--yes", action="store_true", help="Skip confirmation prompt")
    return p.parse_args()


def to_distance(name: str) -> Distance:
    name = name.lower().strip()
    if name == "cosine":
        return Distance.COSINE
    if name in ("dot", "dotproduct", "dot_product"):
        return Distance.DOT
    if name in ("euclid", "euclidean"):
        return Distance.EUCLID
    return Distance.COSINE


def main() -> int:
    args = parse_args()

    settings = Settings()
    cols = [c.strip() for c in args.collections.split(",") if c.strip()]
    dim = args.dimension or get_embedding_dimension()
    dist = to_distance(args.distance)

    print("Qdrant reset plan:")
    print(f"- Host: {settings.qdrant_host}:{settings.qdrant_port} (https={settings.use_https})")
    print(f"- Collections: {', '.join(cols)}")
    print(f"- Dimension: {dim}")
    print(f"- Distance: {args.distance}")

    if not args.yes:
        ans = input("This will DELETE and RECREATE the collections. Continue? (yes/NO) ").strip().lower()
        if ans != "yes":
            print("Aborted.")
            return 1

    # Build client with fallback for host network context (host vs container)
    def build_client(host: str) -> QdrantClient:
        return QdrantClient(
            host=host,
            port=settings.qdrant_port,
            api_key=settings.get_qdrant_api_key(),
            https=settings.use_https,
            timeout=settings.qdrant_timeout,
        )

    client: QdrantClient
    try:
        client = build_client(settings.qdrant_host)
        # quick probe
        client.get_collections()
    except Exception:
        if settings.qdrant_host != "127.0.0.1":
            print("Primary host not reachable, trying 127.0.0.1 …")
            client = build_client("127.0.0.1")
            client.get_collections()
        else:
            raise

    # Drop and recreate
    for name in cols:
        try:
            print(f"Deleting collection: {name} …")
            client.delete_collection(name)
        except Exception as e:
            print(f"  (skip) delete failed or not exists: {e}")

        print(f"Creating collection: {name} (dim={dim}, distance={args.distance}) …")
        client.recreate_collection(
            collection_name=name,
            vectors_config=VectorParams(size=dim, distance=dist),
        )
        print(f"  OK: {name}")

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
