"""``eif doctor`` — environment and configuration diagnostics."""

from __future__ import annotations

import importlib.util
import os

from ..config import Config
from ..providers.factory import build_llm_provider
from ..storage import open_repository


def _check_import(module: str) -> bool:
    # find_spec imports parent packages and can raise if a parent is missing.
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False


def run_doctor(console, config_path: str | None = None) -> bool:
    from rich.table import Table

    table = Table(title="EIF Doctor")
    table.add_column("check")
    table.add_column("status")
    table.add_column("detail")

    ok = True

    # 1. Configuration.
    try:
        cfg = Config.load(config_path)
        table.add_row("configuration", "[green]ok[/green]", f"org={cfg.organization.id}")
    except Exception as exc:
        table.add_row("configuration", "[red]fail[/red]", str(exc))
        console.print(table)
        return False

    # 2. Default reasoning provider (mock should always work).
    try:
        provider = build_llm_provider(cfg.models.reasoning, private_mode=cfg.private_mode)
        _ = provider.complete("ping")
        offhost = getattr(provider, "sends_data_offhost", True)
        table.add_row(
            "llm provider",
            "[green]ok[/green]",
            f"{provider.name}:{provider.model} offhost={offhost}",
        )
    except Exception as exc:
        ok = False
        table.add_row("llm provider", "[red]fail[/red]", str(exc))

    # 3. Database connectivity.
    try:
        repo = open_repository(cfg)
        stats = repo.stats()
        close = getattr(repo, "close", None)
        table.add_row(
            "database",
            "[green]ok[/green]",
            f"{cfg.storage.database_url} events={stats.events}",
        )
        if callable(close):
            close()
    except Exception as exc:
        ok = False
        table.add_row("database", "[red]fail[/red]", str(exc))

    # 4. Optional parsers.
    for name, module in (("excel (openpyxl)", "openpyxl"), ("pdf (pypdf)", "pypdf")):
        present = _check_import(module)
        table.add_row(
            f"parser: {name}",
            "[green]installed[/green]" if present else "[yellow]optional[/yellow]",
            "available" if present else "not installed (feature disabled)",
        )

    # 5. Optional providers.
    for name, module in (
        ("openai", "openai"),
        ("anthropic", "anthropic"),
        ("gemini", "google.generativeai"),
    ):
        present = _check_import(module)
        table.add_row(
            f"provider: {name}",
            "[green]installed[/green]" if present else "[yellow]optional[/yellow]",
            "available" if present else "not installed",
        )

    # 6. Environment / privacy.
    table.add_row(
        "privacy",
        "[green]ok[/green]",
        f"private_mode={cfg.private_mode} redact_pii={cfg.security.redact_pii}",
    )
    keys = [
        k for k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY") if os.environ.get(k)
    ]
    table.add_row("api keys present", "[green]ok[/green]", ", ".join(keys) or "none (offline mode)")

    console.print(table)
    console.print(
        "[green]All required checks passed.[/green]" if ok else "[red]Some checks failed.[/red]"
    )
    return ok
