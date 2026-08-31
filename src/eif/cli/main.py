"""The ``eif`` command-line interface.

A thin, polished wrapper over the facade and benchmark framework. Requires the
optional ``[cli]`` extra (``typer`` + ``rich``); a clear message is shown if it
is missing. All commands work offline with the deterministic default provider.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    import typer
    from rich.console import Console
    from rich.table import Table
except ImportError:  # pragma: no cover - optional dep
    sys.stderr.write(
        "The EIF CLI requires the optional 'cli' extra. "
        "Install with: pip install 'economic-intelligence-framework[cli]'\n"
    )
    raise

from ..config import Config
from ..domain import EconomicEvent, RealizedOutcome
from ..facade import EIF
from ..storage.base import EventQuery
from ..version import __version__

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Economic Intelligence Framework — turn business evidence into economic events.",
)
benchmark_app = typer.Typer(no_args_is_help=True, help="Run and manage benchmarks.")
app.add_typer(benchmark_app, name="benchmark")

console = Console()
err_console = Console(stderr=True)


def _load_config(config_path: str | None) -> Config:
    return Config.load(config_path)


def _make_eif(config_path: str | None, database_url: str | None) -> EIF:
    cfg = _load_config(config_path)
    if database_url:
        cfg.storage.database_url = database_url
    cfg.logging.level = "ERROR"  # keep CLI output clean; use --config for verbose
    return EIF(cfg)


def _event_row(ev: EconomicEvent) -> list[str]:
    impact = ev.primary_impact()
    impact_str = "—"
    if impact is not None:
        est = impact.estimate
        impact_str = f"{impact.metric} {impact.direction} {est.point:,.0f} {est.unit or ''}".strip()
    return [
        ev.id,
        ev.event_type,
        str(ev.status),
        str(ev.materiality),
        f"{ev.confidence.score:.2f}",
        impact_str,
    ]


@app.command()
def version() -> None:
    """Print the EIF version."""
    console.print(f"Economic Intelligence Framework v{__version__}")


@app.command()
def analyze(
    sources: list[str] = typer.Argument(..., help="Files or directories to analyze."),
    config: str | None = typer.Option(None, "--config", "-c", help="Path to config file."),
    database_url: str | None = typer.Option(None, "--db", help="Override database URL."),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Analyze evidence and produce economic events."""
    eif = _make_eif(config, database_url)
    try:
        result = eif.analyze(list(sources))
    except Exception as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    if as_json:
        payload = {
            "run_id": result.run_id,
            "evidence": len(result.evidence),
            "observations": len(result.observations),
            "events": [e.model_dump(mode="json") for e in result.events],
        }
        console.print_json(json.dumps(payload))
        return

    console.print(
        f"[bold]Run[/bold] {result.run_id} — "
        f"{len(result.evidence)} evidence, {len(result.observations)} observations, "
        f"{len(result.events)} events"
    )
    _print_events(result.events)


@app.command()
def events(
    config: str | None = typer.Option(None, "--config", "-c"),
    database_url: str | None = typer.Option(None, "--db"),
    event_type: str | None = typer.Option(None, "--type", help="Filter by event type."),
    status: str | None = typer.Option(None, "--status", help="Filter by status."),
    limit: int = typer.Option(50, "--limit"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """List stored economic events."""
    eif = _make_eif(config, database_url)
    query = EventQuery(event_type=event_type, status=status, limit=limit)
    items = eif.repo.list_events(query).items
    if as_json:
        console.print_json(json.dumps([e.model_dump(mode="json") for e in items]))
        return
    _print_events(items)


@app.command("event")
def event_show(
    event_id: str = typer.Argument(..., help="Event id."),
    config: str | None = typer.Option(None, "--config", "-c"),
    database_url: str | None = typer.Option(None, "--db"),
) -> None:
    """Show a single event with full provenance as JSON."""
    eif = _make_eif(config, database_url)
    ev = eif.get_event(event_id)
    if ev is None:
        err_console.print(f"[red]Not found:[/red] {event_id}")
        raise typer.Exit(code=1)
    console.print_json(json.dumps(ev.model_dump(mode="json")))


@app.command()
def entities(
    config: str | None = typer.Option(None, "--config", "-c"),
    database_url: str | None = typer.Option(None, "--db"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """List resolved economic entities."""
    eif = _make_eif(config, database_url)
    items = eif.entities()
    if as_json:
        console.print_json(json.dumps([e.model_dump(mode="json") for e in items]))
        return
    table = Table(title="Entities")
    for col in ("id", "type", "name", "aliases"):
        table.add_column(col)
    for e in items:
        table.add_row(e.id, e.entity_type, e.name, ", ".join(e.aliases))
    console.print(table)


@app.command("outcome")
def record_outcome(
    event_id: str = typer.Argument(...),
    metric: str = typer.Option(..., "--metric", help="Metric key, e.g. cost_of_goods_sold."),
    value: float = typer.Option(..., "--value", help="Realized value."),
    config: str | None = typer.Option(None, "--config", "-c"),
    database_url: str | None = typer.Option(None, "--db"),
) -> None:
    """Record a realized outcome for an event (feedback loop)."""
    eif = _make_eif(config, database_url)
    outcome = RealizedOutcome(event_id=event_id, realized_metrics={metric: value})
    ev = eif.record_outcome(outcome)
    if ev is None:
        err_console.print(f"[red]Event not found:[/red] {event_id}")
        raise typer.Exit(code=1)
    console.print(f"Recorded outcome; event {ev.id} status -> {ev.status}")


@app.command()
def doctor(
    config: str | None = typer.Option(None, "--config", "-c"),
) -> None:
    """Verify configuration, providers, database, parsers, and environment."""
    from .doctor import run_doctor

    ok = run_doctor(console, config)
    raise typer.Exit(code=0 if ok else 1)


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8000, "--port"),
    config: str | None = typer.Option(None, "--config", "-c"),
) -> None:
    """Start the optional FastAPI server (requires the 'api' extra)."""
    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover - optional dep
        err_console.print(
            "The API server requires the 'api' extra: "
            "pip install 'economic-intelligence-framework[api]'"
        )
        raise typer.Exit(code=1) from exc
    if config:
        import os

        os.environ["EIF_CONFIG_FILE"] = config
    uvicorn.run("eif.api.app:app", host=host, port=port, factory=False)


# --------------------------------------------------------------------- benchmark
@benchmark_app.command("generate")
def benchmark_generate(
    output: str = typer.Argument("benchmarks/cases", help="Output directory."),
    variants: int = typer.Option(0, "--variants", help="Extra seeded variants to add."),
    seed: int = typer.Option(1234, "--seed"),
) -> None:
    """Generate the synthetic benchmark cases."""
    from ..benchmark import generate_canonical, generate_variants

    paths = generate_canonical(output)
    if variants:
        paths += generate_variants(output, n=variants, seed=seed)
    console.print(f"Wrote {len(paths)} synthetic cases to [bold]{output}[/bold]")


@benchmark_app.command("run")
def benchmark_run(
    cases: str = typer.Option("benchmarks/cases", "--cases", help="Cases directory."),
    baseline: bool = typer.Option(False, "--baseline", help="Structured-only baseline condition."),
    as_json: bool = typer.Option(False, "--json"),
    config: str | None = typer.Option(None, "--config", "-c"),
) -> None:
    """Run the benchmark suite and print a report."""
    from ..benchmark import render_suite_text, run_suite, suite_to_dict

    if not Path(cases).exists():
        err_console.print(f"[red]No cases at[/red] {cases}. Run: eif benchmark generate {cases}")
        raise typer.Exit(code=1)
    cfg = _load_config(config)
    suite = run_suite(
        cases,
        config=cfg,
        condition="baseline" if baseline else "eif",
        structured_only=baseline,
    )
    if as_json:
        console.print_json(json.dumps(suite_to_dict(suite)))
    else:
        console.print(render_suite_text(suite))


@benchmark_app.command("report")
def benchmark_report(
    cases: str = typer.Option("benchmarks/cases", "--cases"),
    as_json: bool = typer.Option(False, "--json"),
    config: str | None = typer.Option(None, "--config", "-c"),
) -> None:
    """Run both conditions and print the baseline-vs-EIF comparison."""
    from ..benchmark import render_comparison_text, run_suite, suite_to_dict

    if not Path(cases).exists():
        err_console.print(f"[red]No cases at[/red] {cases}. Run: eif benchmark generate {cases}")
        raise typer.Exit(code=1)
    cfg = _load_config(config)
    eif_suite = run_suite(cases, config=cfg, condition="eif")
    base_suite = run_suite(cases, config=cfg, condition="baseline", structured_only=True)
    if as_json:
        console.print_json(
            json.dumps({"baseline": suite_to_dict(base_suite), "eif": suite_to_dict(eif_suite)})
        )
    else:
        console.print(render_comparison_text(base_suite, eif_suite))


def _print_events(items: list[EconomicEvent]) -> None:
    if not items:
        console.print("[dim]No events.[/dim]")
        return
    table = Table(show_lines=False)
    for col in ("id", "type", "status", "materiality", "conf", "primary impact"):
        table.add_column(col)
    for ev in items:
        table.add_row(*_event_row(ev))
    console.print(table)


if __name__ == "__main__":  # pragma: no cover
    app()
