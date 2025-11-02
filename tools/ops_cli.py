#!/usr/bin/env python3
"""
FreeHekim RAG – Ops CLI

Amaç: Kriz/bakım anında hızlı teşhis ve güvenli operasyon adımları.
Kontroller: Ok tuşları (↑/↓), Enter, Space, Ctrl+C/ Ctrl+Q ile çıkış.
"""

from __future__ import annotations

import sys
import traceback
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from prompt_toolkit import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, Layout, VSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.styles import Style

# Repo içinden import için yol ekle
sys.path.insert(0, str(Path(__file__).parent.parent / "fastapi"))

from config import Settings
from rag.client_qdrant import get_qdrant_client
from rag.pipeline import cache_stats, flush_cache, retrieve_answer

style = Style.from_dict(
    {
        "header": "bg:#1565C0 #ffffff bold",
        "footer": "bg:#263238 #ffffff",
        "menu": "bg:#1e1e1e #e0e0e0",
        "menu.selected": "bg:#37474F #ffffff bold",
        "panel": "bg:#121212 #d0d0d0",
        "ok": "#66BB6A",
        "warn": "#FFA726",
        "err": "#EF5350",
    }
)


class OpsCLI:
    def __init__(self) -> None:
        self.settings = Settings()
        self.menu_items: list[tuple[str, Callable[[], None]]] = [
            ("Genel Durum", self.view_overview),
            ("Sağlık Kontrolleri", self.health_checks),
            ("Qdrant Koleksiyonları", self.view_qdrant_collections),
            ("Qdrant Ayar Önerileri", self.qdrant_tuning_suggestions),
            ("Hızlı RAG Testi", self.quick_rag_test),
            ("Koruma Ayarları (Bilgi)", self.protection_info),
            ("Cache Durumu / Temizle", self.cache_view_flush),
            ("Profil Önerileri (.env yazdır)", self.write_env_profiles),
            ("Çıkış", self.exit_app),
        ]
        self.selected = 0
        self.output_lines: list[str] = []

        self.kb = KeyBindings()
        self._bind_keys()
        self.layout = self._build_layout()
        self.app = Application(
            layout=self.layout, key_bindings=self.kb, full_screen=True, style=style
        )

    def _bind_keys(self) -> None:
        @self.kb.add("up")
        def _(event) -> None:
            self.selected = (self.selected - 1) % len(self.menu_items)
            event.app.invalidate()

        @self.kb.add("down")
        def _(event) -> None:
            self.selected = (self.selected + 1) % len(self.menu_items)
            event.app.invalidate()

        @self.kb.add("enter")
        @self.kb.add(" ")
        def _(event) -> None:
            try:
                self.menu_items[self.selected][1]()
            except Exception as e:
                self.print_err(f"Hata: {e}")
                traceback.print_exc()
            event.app.invalidate()

        @self.kb.add("c-c")
        @self.kb.add("c-q")
        def _(event) -> None:
            event.app.exit()

    def _build_layout(self) -> Layout:
        def header_text() -> list[tuple[str, str]]:
            return [
                (
                    "class:header",
                    f" 🏥 FreeHekim RAG – Ops CLI  |  ENV: {self.settings.env.upper()} ",
                )
            ]

        def footer_text() -> list[tuple[str, str]]:
            return [
                (
                    "class:footer",
                    "  ↑/↓: Seç  ␣/Enter: Çalıştır  Ctrl+Q: Çıkış  ",
                )
            ]

        def menu_text() -> list[tuple[str, str]]:
            parts: list[tuple[str, str]] = []
            for i, (label, _) in enumerate(self.menu_items):
                style_item = "class:menu.selected" if i == self.selected else "class:menu"
                parts.append((style_item, f"  {label}\n"))
            return parts

        def output_text() -> list[tuple[str, str]]:
            body = "\n".join(self.output_lines[-100:])
            return [("class:panel", body)]

        root = HSplit(
            [
                Window(content=FormattedTextControl(header_text), height=1, style="class:header"),
                Window(height=1, char=" "),
                VSplit(
                    [
                        Window(
                            content=FormattedTextControl(menu_text),
                            width=Dimension.exact(28),
                            height=Dimension(weight=1),
                            style="class:menu",
                        ),
                        Window(width=1, char=" "),
                        Window(content=FormattedTextControl(output_text), style="class:panel"),
                    ]
                ),
                Window(height=1, char=" "),
                Window(content=FormattedTextControl(footer_text), height=1, style="class:footer"),
            ]
        )
        return Layout(root)

    # Utilities
    def print_ok(self, msg: str) -> None:
        self.output_lines.append(f"[OK] {msg}")

    def print_warn(self, msg: str) -> None:
        self.output_lines.append(f"[WARN] {msg}")

    def print_err(self, msg: str) -> None:
        self.output_lines.append(f"[ERR] {msg}")

    def clear_output(self) -> None:
        self.output_lines.clear()

    # Actions
    def view_overview(self) -> None:
        self.clear_output()
        s = self.settings
        lines = [
            "GENEL DURUM",
            "-" * 60,
            f"Env: {s.env}",
            f"LLM: {s.llm_model} (temp={s.llm_temperature}, max_tokens={s.llm_max_tokens})",
            f"Embedding: {s.openai_embedding_model} (provider={s.embed_provider})",
            f"Qdrant: {s.qdrant_host}:{s.qdrant_port} (https={s.use_https})",
            f"Search topK: {s.search_topk}",
            f"Context chunks: {s.pipeline_max_context_chunks}",
            f"Rate limit: {s.rate_limit_per_minute}/dk/IP",
            f"Body limit: {s.max_body_size_bytes} bytes",
            f"Cache: {'AÇIK' if s.enable_cache else 'KAPALI'} (ttl={s.cache_ttl_seconds}s)",
        ]
        self.output_lines.extend(lines)

    def health_checks(self) -> None:
        self.clear_output()
        self.output_lines.append("SAĞLIK KONTROLLERİ")
        self.output_lines.append("-" * 60)
        # Health: Uygulama çalışıyorsa OK
        self.print_ok("Uygulama çalışıyor")
        # Ready: Qdrant
        try:
            client = get_qdrant_client()
            cols = client.get_collections().collections
            names = ", ".join([c.name for c in cols]) or "(yok)"
            self.print_ok(f"Qdrant bağlantısı OK, koleksiyonlar: {names}")
        except Exception as e:
            self.print_err(f"Qdrant hazır değil: {e}")

    def view_qdrant_collections(self) -> None:
        self.clear_output()
        self.output_lines.append("QDRANT KOLEKSİYONLARI")
        self.output_lines.append("-" * 60)
        try:
            client = get_qdrant_client()
            for col in client.get_collections().collections:
                info = client.get_collection(col.name)
                line = (
                    f"- {col.name}: points={info.points_count}, vectors_count={info.vectors_count}"
                )
                # Try to show HNSW search params if available
                ef_construct = ef_search = m_degree = None
                try:
                    hnsw = getattr(getattr(info, "config", None), "params", None)
                    if hnsw is not None:
                        hnsw = getattr(hnsw, "hnsw_config", None)
                    if hnsw is None:
                        hnsw = getattr(getattr(info, "config", None), "hnsw_config", None)
                    ef_construct = getattr(hnsw, "ef_construct", None)
                    ef_search = getattr(hnsw, "ef_search", None)
                    m_degree = getattr(hnsw, "m", None)
                except Exception as e:
                    # Optional/shape-changes across qdrant_client versions; ignore
                    self.output_lines.append(f"(bilgi) HNSW detayları okunamadı: {e}")
                if any(x is not None for x in (ef_construct, ef_search, m_degree)):
                    line += (
                        f" | hnsw(ef_search={ef_search}, ef_construct={ef_construct}, m={m_degree})"
                    )
                self.output_lines.append(line)
        except Exception as e:
            self.print_err(f"Listeleme hatası: {e}")

    def qdrant_tuning_suggestions(self) -> None:
        """Show basic ef_search tuning suggestions (bilgi amaçlı)."""
        self.clear_output()
        self.output_lines.append("QDRANT AYAR ÖNERİLERİ (BİLGİ)")
        self.output_lines.append("-" * 60)
        try:
            client = get_qdrant_client()
            cols = client.get_collections().collections
            for col in cols:
                info = client.get_collection(col.name)
                points = getattr(info, "points_count", 0) or 0
                import math

                suggested = int(min(512, max(64, 2 * math.sqrt(max(1, points)))))
                ef_search = None
                try:
                    hnsw = getattr(getattr(info, "config", None), "params", None)
                    if hnsw is not None:
                        hnsw = getattr(hnsw, "hnsw_config", None)
                    if hnsw is None:
                        hnsw = getattr(getattr(info, "config", None), "hnsw_config", None)
                    ef_search = getattr(hnsw, "ef_search", None)
                except Exception as e:
                    self.output_lines.append(f"(bilgi) ef_search okunamadı: {e}")
                self.output_lines.append(
                    f"- {col.name}: points={points} | mevcut ef_search={ef_search} | öneri≈{suggested}"
                )
            self.output_lines.append("")
            self.output_lines.append(
                "Not: Bu değerler genel amaçlıdır. p95 gecikme ve doğruluğu grafikten izleyerek kademeli ayarlayın."
            )
        except Exception as e:
            self.print_err(f"Öneri hesaplanamadı: {e}")

    def quick_rag_test(self) -> None:
        from prompt_toolkit.shortcuts import input_dialog

        q = input_dialog(title="Hızlı RAG Testi", text="Sorunuzu yazın:").run()
        if not q:
            return
        self.clear_output()
        self.output_lines.append("HIZLI RAG TESTİ")
        self.output_lines.append("-" * 60)
        try:
            res = retrieve_answer(q)
            self.output_lines.append(f"Soru: {res.get('question','')}")
            self.output_lines.append("")
            self.output_lines.append("Cevap:")
            self.output_lines.append(res.get("answer", "(yok)"))
            md = res.get("metadata", {})
            self.output_lines.append("")
            self.output_lines.append(
                f"Model={md.get('model','?')} | tokens={md.get('tokens_used',0)} | hits={md.get('internal_hits',0)}+{md.get('external_hits',0)}"
            )
        except Exception as e:
            self.print_err(f"RAG hatası: {e}")

    def protection_info(self) -> None:
        self.clear_output()
        s = self.settings
        lines = [
            "KORUMA AYARLARI (BİLGİ)",
            "-" * 60,
            f"Rate limit: {s.rate_limit_per_minute}/dk/IP",
            f"Body limit: {s.max_body_size_bytes} bytes",
            "Not: Ayar değişiklikleri .env üzerinden yapılmalı, restart gerekir.",
        ]
        self.output_lines.extend(lines)

    def cache_view_flush(self) -> None:
        self.clear_output()
        st = cache_stats()
        self.output_lines.append("CACHE DURUMU")
        self.output_lines.append("-" * 60)
        self.output_lines.append(
            f"Durum: {'AÇIK' if st.get('enabled') else 'KAPALI'} | Boyut: {st.get('size')} | TTL: {st.get('ttl_seconds')}s"
        )
        if st.get("enabled") and st.get("size", 0) > 0:
            self.output_lines.append("")
            self.output_lines.append("Space/Enter ile cache temizlenir…")

            # Bir sonraki Enter/Space çağrısında flush tetikle
            def _flush_once() -> None:
                n = flush_cache()
                self.output_lines.append(f"Temizlendi: {n} kayıt")
                # Eylem bir kez çalışsın; menüyü normale döndür
                self.menu_items[self.selected] = ("Cache Durumu / Temizle", self.cache_view_flush)

            self.menu_items[self.selected] = ("Cache Temizle (Onay)", _flush_once)

    def write_env_profiles(self) -> None:
        """Write cost/performance optimized .env suggestion files."""
        self.clear_output()
        s = self.settings
        now = datetime.now().strftime("%Y%m%d_%H%M")
        outdir = Path(__file__).parent.parent / "docs" / "env-suggestions"
        outdir.mkdir(parents=True, exist_ok=True)

        # Cost-optimized profile
        cost = {
            "# profile": "cost-optimized",
            "LLM_MODEL": "gpt-4o-mini",
            "LLM_MAX_TOKENS": "400",
            "SEARCH_TOPK": "3",
            "PIPELINE_MAX_CONTEXT_CHUNKS": "3",
            "PIPELINE_MAX_SOURCE_DISPLAY": "3",
            "PIPELINE_MAX_SOURCE_TEXT_LENGTH": "200",
            "ENABLE_CACHE": "true",
            "CACHE_TTL_SECONDS": "600",
            # Keep timeouts modest
            "QDRANT_TIMEOUT": str(max(5.0, getattr(s, "qdrant_timeout", 10.0))),
        }
        cost_file = outdir / f"env_suggestion_cost_{now}.env"
        cost_lines = [
            "# Auto-generated .env suggestion (manual apply)",
            f"# {datetime.now().isoformat(timespec='minutes')}",
            "",
        ]
        cost_lines += [f"{k}={v}" for k, v in cost.items()]
        cost_file.write_text("\n".join(cost_lines), encoding="utf-8")

        # Performance-optimized profile
        perf = {
            "# profile": "performance-optimized",
            "LLM_MODEL": s.llm_model if s.llm_model.lower().startswith("gpt-4") else "gpt-4o",
            "LLM_MAX_TOKENS": "700",
            "SEARCH_TOPK": "6",
            "PIPELINE_MAX_CONTEXT_CHUNKS": "6",
            "PIPELINE_MAX_SOURCE_DISPLAY": "4",
            "PIPELINE_MAX_SOURCE_TEXT_LENGTH": "300",
            "ENABLE_CACHE": "true",
            "CACHE_TTL_SECONDS": "180",
            "QDRANT_TIMEOUT": "6.0",
        }
        perf_file = outdir / f"env_suggestion_perf_{now}.env"
        perf_lines = [
            "# Auto-generated .env suggestion (manual apply)",
            f"# {datetime.now().isoformat(timespec='minutes')}",
            "",
        ]
        perf_lines += [f"{k}={v}" for k, v in perf.items()]
        perf_file.write_text("\n".join(perf_lines), encoding="utf-8")

        self.print_ok(f"Maliyet odaklı öneri: {cost_file}")
        self.print_ok(f"Performans odaklı öneri: {perf_file}")
        self.print_warn("Not: Bu dosyalar birer öneridir. Mevcut .env otomatik DEĞİŞTİRİLMEDİ.")

    def exit_app(self) -> None:
        self.app.exit()

    def run(self) -> None:
        # Başlangıç ekranı
        self.view_overview()
        self.app.run()


def main() -> int:
    try:
        OpsCLI().run()
        return 0
    except KeyboardInterrupt:
        return 130
    except Exception as e:
        print(f"Fatal error: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
