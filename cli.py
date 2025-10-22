#!/usr/bin/env python3
"""
FreeHekim RAG Interactive CLI

Interactive terminal interface for querying the FreeHekim RAG system.
Uses arrow keys for navigation and Enter/Space for selection.
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import (
    Dimension,
    FormattedTextControl,
    HSplit,
    Layout,
    VSplit,
    Window,
)
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import TextArea
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

# Add fastapi to path
sys.path.insert(0, str(Path(__file__).parent / "fastapi"))

from config import Settings
from rag.pipeline import retrieve_answer
try:
    import httpx  # type: ignore
except Exception:
    httpx = None  # type: ignore

# ============================================================================
# Configuration
# ============================================================================

console = Console()
settings = Settings()

# History / export paths
HISTORY_FILE = Path.home() / ".freehekim_rag_history.txt"
EXPORT_DIR = Path.cwd() / "docs" / "cli-exports"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

# Optional remote API config via env (can be overridden with args)
DEFAULT_REMOTE_URL = os.environ.get("RAG_API_URL", "").strip()
DEFAULT_API_KEY = os.environ.get("RAG_API_KEY", "").strip()


# ============================================================================
# Styles
# ============================================================================

cli_style = Style.from_dict(
    {
        "header": "bg:#2196F3 #ffffff bold",
        "footer": "bg:#424242 #ffffff",
        "status": "bg:#4CAF50 #ffffff",
        "input-area": "bg:#1e1e1e #ffffff",
        "result-area": "bg:#121212 #e0e0e0",
        "button": "bg:#1976D2 #ffffff bold",
        "button.focused": "bg:#2196F3 #ffffff bold underline",
    }
)


# ============================================================================
# CLI Application
# ============================================================================


class FreeHekimCLI:
    """Interactive CLI for FreeHekim RAG"""

    def __init__(self, remote_url: str = "", api_key: str = "", timeout: float = 15.0):
        self.question_buffer = Buffer()
        self.result_text = ""
        self.status_text = "🟢 Hazır - Sorunuzu yazın..."
        self.query_history: list[dict[str, Any]] = []
        self.remote_url = remote_url.strip()
        self.api_key = api_key.strip()
        self.timeout = timeout
        self.load_history()

        # Key bindings
        self.kb = KeyBindings()
        self._setup_keybindings()

        # Layouts
        self.layout = self._create_layout()

        # Application
        self.app = Application(
            layout=self.layout,
            key_bindings=self.kb,
            style=cli_style,
            full_screen=True,
            mouse_support=True,
        )

    def _setup_keybindings(self):
        """Setup keyboard shortcuts"""

        @self.kb.add("c-c")
        @self.kb.add("c-q")
        def _(event):
            """Exit application"""
            event.app.exit()

        @self.kb.add("c-r")
        def _(event):
            """Send query (Ctrl+R for Run)"""
            self.send_query()

        @self.kb.add("c-h")
        def _(event):
            """Show history"""
            self.show_history()

        @self.kb.add("c-l")
        def _(event):
            """Clear screen"""
            self.result_text = ""
            self.question_buffer.text = ""
            self.status_text = "🟢 Hazır - Yeni soru..."
            self.app.invalidate()

        @self.kb.add("f1")
        def _(event):
            """Show help"""
            self.show_help()

        @self.kb.add("c-s")
        def _(event):
            """Export last result to markdown"""
            self.export_last()

    def _create_layout(self):
        """Create the application layout"""

        # Header
        header = Window(
            content=FormattedTextControl(
                text=lambda: [
                    ("class:header", " 🏥 FreeHekim RAG - Interactive CLI "),
                    ("", " " * 18),
                    (
                        "class:header",
                        (
                            f" MODE=REMOTE {self.remote_url} "
                            if self.remote_url
                            else f" MODE=LOCAL  ENV={settings.env.upper()} "
                        ),
                    ),
                ]
            ),
            height=Dimension.exact(1),
            style="class:header",
        )

        # Question input area
        question_area = TextArea(
            buffer=self.question_buffer,
            prompt="❓ Soru: ",
            multiline=False,
            wrap_lines=False,
            style="class:input-area",
        )

        # Result display area
        result_window = Window(
            content=FormattedTextControl(text=lambda: self.result_text),
            wrap_lines=True,
            style="class:result-area",
            scrollbar=True,
        )

        # Status bar
        status_bar = Window(
            content=FormattedTextControl(text=lambda: self.status_text),
            height=Dimension.exact(1),
            style="class:status",
        )

        # Footer with shortcuts
        footer = Window(
            content=FormattedTextControl(
                text=" [Ctrl+R] Gönder  [Ctrl+H] Geçmiş  [Ctrl+L] Temizle  [F1] Yardım  [Ctrl+Q] Çıkış "
            ),
            height=Dimension.exact(1),
            style="class:footer",
        )

        # Main layout
        layout = Layout(
            HSplit(
                [
                    header,
                    Window(height=Dimension.exact(1)),  # Spacer
                    question_area,
                    Window(height=Dimension.exact(1)),  # Spacer
                    result_window,
                    status_bar,
                    footer,
                ]
            )
        )

        return layout

    def send_query(self):
        """Send query to RAG pipeline"""
        question = self.question_buffer.text.strip()

        if not question:
            self.status_text = "⚠️  Lütfen bir soru girin"
            self.app.invalidate()
            return

        try:
            # Update status
            self.status_text = f"🔄 İşleniyor: {question[:50]}..."
            self.result_text = "\n⏳ Cevap oluşturuluyor...\n"
            self.app.invalidate()

            # Query RAG
            if self.remote_url:
                result = self._request_remote(question)
            else:
                result = retrieve_answer(question)

            # Format result
            self.result_text = self._format_result(result)

            # Save to history
            self.save_query(question, result)

            # Update status
            tokens = result.get("metadata", {}).get("tokens_used", 0)
            self.status_text = f"✅ Tamamlandı - {tokens} token kullanıldı"

        except Exception as e:
            self.result_text = f"\n❌ Hata:\n{str(e)}\n"
            self.status_text = f"❌ Hata: {str(e)[:50]}"

        self.app.invalidate()

    def _export_markdown(self, result: dict[str, Any]) -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = EXPORT_DIR / f"rag_cli_{ts}.md"
        lines = [f"# FreeHekim RAG — {ts}", "", f"**Soru:** {result.get('question','')}", "", result.get("answer", "")]
        sources = result.get("sources", [])
        if sources:
            lines.append("")
            lines.append("## Kaynaklar")
            for i, s in enumerate(sources, 1):
                lines.append(f"- [Kaynak {i}] ({s.get('source')}): {s.get('text','')}")
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return str(path)

    def export_last(self):
        try:
            q = self.question_buffer.text.strip()
            if not q:
                self.status_text = "ℹ️  Soru boş; dışa aktarma atlandı"
                self.app.invalidate()
                return
            res = self._request_remote(q) if self.remote_url else retrieve_answer(q)
            out = self._export_markdown(res)
            self.status_text = f"💾 Dışa aktarıldı: {out}"
        except Exception as e:
            self.status_text = f"❌ Dışa aktarma hatası: {e}"
        self.app.invalidate()

    def _format_result(self, result: dict[str, Any]) -> str:
        """Format RAG result for terminal display"""
        lines = []

        lines.append("\n" + "=" * 80)
        lines.append("📋 SORU:")
        lines.append("-" * 80)
        lines.append(result.get("question", ""))
        lines.append("")

        lines.append("💡 CEVAP:")
        lines.append("-" * 80)
        lines.append(result.get("answer", "Cevap bulunamadı"))
        lines.append("")

        # Sources
        sources = result.get("sources", [])
        if sources:
            lines.append("📚 KAYNAKLAR:")
            lines.append("-" * 80)
            for i, source in enumerate(sources, 1):
                lines.append(f"\n[Kaynak {i}] ({source['source']}) - Score: {source['score']}")
                lines.append(f"  {source['text']}")
                lines.append("")

        # Metadata
        metadata = result.get("metadata", {})
        lines.append("ℹ️  METAVERİ:")
        lines.append("-" * 80)
        lines.append(f"Model: {metadata.get('model', 'N/A')}")
        lines.append(f"Tokens: {metadata.get('tokens_used', 0)}")
        lines.append(f"Internal hits: {metadata.get('internal_hits', 0)}")
        lines.append(f"External hits: {metadata.get('external_hits', 0)}")
        lines.append(f"Fused results: {metadata.get('fused_results', 0)}")
        lines.append("=" * 80 + "\n")

        return "\n".join(lines)

    def _request_remote(self, question: str) -> dict[str, Any]:
        if not self.remote_url:
            raise RuntimeError("Remote URL tanımlı değil")
        if httpx is None:
            raise RuntimeError("httpx kurulu değil (pip install httpx)")
        url = self.remote_url.rstrip("/") + "/rag/query"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-Api-Key"] = self.api_key
        with httpx.Client(timeout=self.timeout) as client:
            r = client.post(url, headers=headers, json={"q": question})
            if r.status_code == 200:
                return r.json()
            try:
                data = r.json()
            except Exception:
                data = {"error": r.text}
            raise RuntimeError(f"API {r.status_code}: {data.get('error','bilinmeyen hata')}")

    def show_history(self):
        """Show query history"""
        if not self.query_history:
            self.result_text = "\n📭 Geçmiş boş\n"
            self.status_text = "ℹ️  Henüz soru sorulmadı"
            self.app.invalidate()
            return

        lines = ["\n📜 SON SORULAR:\n", "=" * 80]

        for i, entry in enumerate(reversed(self.query_history[-10:]), 1):
            lines.append(f"\n{i}. {entry['timestamp']}")
            lines.append(f"   ❓ {entry['question'][:60]}...")
            lines.append(f"   📊 {entry.get('tokens', 0)} tokens")

        lines.append("\n" + "=" * 80 + "\n")

        self.result_text = "\n".join(lines)
        self.status_text = f"📜 Geçmiş gösteriliyor ({len(self.query_history)} toplam)"
        self.app.invalidate()

    def show_help(self):
        """Show help screen"""
        help_text = """
╔════════════════════════════════════════════════════════════════════════════╗
║                      🏥 FreeHekim RAG - YARDIM                            ║
╚════════════════════════════════════════════════════════════════════════════╝

📖 KLAVYE KISAYOLLARI:

  Ctrl+R        → Soruyu gönder ve cevap al
  Ctrl+H        → Soru geçmişini görüntüle
  Ctrl+L        → Ekranı temizle
  F1            → Bu yardım ekranını göster
  Ctrl+Q / Ctrl+C → Çıkış

💡 KULLANIM:

  1. Soru kutusuna sağlık ile ilgili sorunuzu yazın
  2. Ctrl+R ile gönderin
  3. Cevap, kaynaklar ve metadata görüntülenecek

⚕️  DİKKAT:

  Bu sistem tıbbi bilgilendirme amaçlıdır.
  Teşhis veya tedavi için mutlaka hekiminize danışın.

🔧 YAPILANDIRMA:

  Ortam: {env}
  Model: {model}
  Embedding: {embedding}

══════════════════════════════════════════════════════════════════════════════
""".format(
            env=settings.env,
            model="GPT-4",
            embedding=settings.openai_embedding_model,
            remote_url=self.remote_url or "(kapalı)",
            api_key_mask=("***" if self.api_key else "(yok)"),
        )

        self.result_text = help_text
        self.status_text = "ℹ️  Yardım gösteriliyor"
        self.app.invalidate()

    def load_history(self):
        """Load query history from file"""
        if HISTORY_FILE.exists():
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        parts = line.strip().split("|", 2)
                        if len(parts) == 3:
                            self.query_history.append(
                                {
                                    "timestamp": parts[0],
                                    "tokens": int(parts[1]) if parts[1].isdigit() else 0,
                                    "question": parts[2],
                                }
                            )
            except Exception as e:
                console.print(f"[yellow]Warning: Could not load history: {e}[/yellow]")

    def save_query(self, question: str, result: dict[str, Any]):
        """Save query to history"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        tokens = result.get("metadata", {}).get("tokens_used", 0)

        entry = {"timestamp": timestamp, "tokens": tokens, "question": question}
        self.query_history.append(entry)

        # Save to file
        try:
            with open(HISTORY_FILE, "a", encoding="utf-8") as f:
                f.write(f"{timestamp}|{tokens}|{question}\n")
        except Exception as e:
            console.print(f"[yellow]Warning: Could not save history: {e}[/yellow]")

    def run(self):
        """Run the CLI application"""
        # Show welcome message
        self.show_help()

        # Run app
        self.app.run()


# ============================================================================
# Simple Mode (Non-interactive)
# ============================================================================


def simple_mode():
    """Simple command-line mode without TUI"""
    console.print(
        Panel.fit(
            "[bold blue]🏥 FreeHekim RAG - Simple Mode[/bold blue]\n"
            "[dim]Ctrl+C to exit[/dim]",
            border_style="blue",
        )
    )

    while True:
        try:
            # Get question
            console.print("\n[bold yellow]❓ Sorunuz:[/bold yellow]", end=" ")
            question = input().strip()

            if not question:
                continue

            # Query RAG
            console.print("\n[dim]⏳ Cevap oluşturuluyor...[/dim]")

            result = retrieve_answer(question)

            # Display result
            console.print("\n[bold green]💡 CEVAP:[/bold green]")
            console.print(Panel(result.get("answer", ""), border_style="green"))

            # Display sources
            sources = result.get("sources", [])
            if sources:
                table = Table(title="📚 Kaynaklar", show_header=True)
                table.add_column("#", style="cyan")
                table.add_column("Kaynak", style="magenta")
                table.add_column("Score", style="yellow")
                table.add_column("Metin", style="white")

                for i, src in enumerate(sources, 1):
                    table.add_row(
                        str(i), src["source"], f"{src['score']:.4f}", src["text"][:80] + "..."
                    )

                console.print(table)

            # Display metadata
            metadata = result.get("metadata", {})
            console.print(
                f"\n[dim]Tokens: {metadata.get('tokens_used', 0)} | "
                f"Model: {metadata.get('model', 'N/A')} | "
                f"Hits: {metadata.get('internal_hits', 0)}+{metadata.get('external_hits', 0)}[/dim]"
            )

        except KeyboardInterrupt:
            console.print("\n\n[yellow]👋 Çıkılıyor...[/yellow]")
            break
        except Exception as e:
            console.print(f"\n[bold red]❌ Hata:[/bold red] {e}")


# ============================================================================
# Main Entry Point
# ============================================================================


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="FreeHekim RAG Interactive CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--simple", action="store_true", help="Use simple mode (no TUI)")
    parser.add_argument(
        "--query",
        "-q",
        type=str,
        help="Single query mode",
    )
    parser.add_argument("--remote-url", type=str, default=DEFAULT_REMOTE_URL, help="Remote API base URL (e.g., https://rag.example.com)")
    parser.add_argument("--api-key", type=str, default=DEFAULT_API_KEY, help="X-Api-Key for remote API (optional)")
    parser.add_argument("--timeout", type=float, default=15.0, help="HTTP timeout (seconds) for remote mode")

    args = parser.parse_args()

    try:
        if args.query:
            # Single query mode
            console.print(f"\n[bold]Soru:[/bold] {args.query}")
            console.print("[dim]⏳ Cevap oluşturuluyor...[/dim]\n")

            if args.remote_url:
                if httpx is None:
                    raise RuntimeError("httpx kurulu değil (pip install httpx)")
                url = args.remote_url.rstrip("/") + "/rag/query"
                headers = {"Content-Type": "application/json"}
                if args.api_key:
                    headers["X-Api-Key"] = args.api_key
                with httpx.Client(timeout=args.timeout) as client:
                    r = client.post(url, headers=headers, json={"q": args.query})
                    r.raise_for_status()
                    result = r.json()
            else:
                result = retrieve_answer(args.query)

            console.print(Markdown(result.get("answer", "")))

        elif args.simple:
            # Simple interactive mode
            simple_mode()
        else:
            # Full TUI mode
            cli = FreeHekimCLI(remote_url=args.remote_url, api_key=args.api_key, timeout=args.timeout)
            cli.run()

    except KeyboardInterrupt:
        console.print("\n\n[yellow]👋 Çıkılıyor...[/yellow]")
    except Exception as e:
        console.print(f"\n[bold red]❌ Fatal Error:[/bold red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
