#!/usr/bin/env python3
"""
Qdrant koleksiyon/dim doğrulama aracı

Amaç: Mevcut koleksiyonların vektör boyutu, kullanılan embedding modeline (1536/3072)
uygun mu kontrol eder. Uyuşmazlık varsa exit code 1 ile çıkar.

Kullanım:
  python3 tools/qdrant_verify.py

Çıktı örneği:
  ✓ Beklenen dim: 1536
  ✓ freehekim_internal: 1536 dims, 12000 points
  ✓ freehekim_external: 1536 dims, 8540 points
  ✓ Hepsi uyumlu
"""

from __future__ import annotations

from pathlib import Path

# Yerel modülleri çözümlemek için fastapi dizinini path'e ekleyin
REPO_ROOT = Path(__file__).resolve().parents[1]
FASTAPI_DIR = REPO_ROOT / "fastapi"
import sys as _sys

_sys.path.insert(0, str(FASTAPI_DIR))

from rag.client_qdrant import (  # type: ignore  # noqa: E402
    EXTERNAL,
    INTERNAL,
    get_qdrant_client,
)
from rag.embeddings import get_embedding_dimension  # type: ignore  # noqa: E402


def main() -> int:
    expected = get_embedding_dimension()
    print(f"✓ Beklenen dim: {expected}")

    client = get_qdrant_client()

    def info(name: str) -> tuple[int, int]:
        meta = client.get_collection(name)
        # qdrant_client 1.9.0: vectors config altından boyut
        size = meta.config.params.vectors.size  # type: ignore[attr-defined]
        points = meta.points_count
        return int(size), int(points)

    ok = True
    for name in (INTERNAL, EXTERNAL):
        try:
            size, count = info(name)
            status = "✓" if size == expected else "✗"
            print(f"{status} {name}: {size} dims, {count} points")
            if size != expected:
                ok = False
        except Exception as e:
            print(f"✗ {name}: erişilemedi ({e})")
            ok = False

    if not ok:
        print("✗ Uyuşmazlık tespit edildi veya koleksiyonlara erişilemedi.")
        print("› Not: Boyut düzeltmek için: python3 tools/qdrant_reset.py --yes")
        return 1

    print("✓ Hepsi uyumlu")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
