"""The ``finir`` command-line interface.

Typer + Rich are core dependencies, so the ``finir`` command works out of the box
after ``pip install finir``. All commands run offline; nothing here needs a network
or a GPU.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    import typer
    from rich.console import Console
    from rich.table import Table
except ImportError:  # pragma: no cover - defensive; typer/rich are core deps
    sys.stderr.write(
        "The finir CLI needs Typer and Rich. They ship with finir; reinstall with "
        "'pip install --force-reinstall finir' if they are missing.\n"
    )
    raise

from ..backends.dispatch import BackendPlanner, WorkloadProfile
from ..backends.gpu import gpu_available
from ..compiler import compile_module
from ..graphviz import to_dot, to_graph_json
from ..ir.parser import parse_module
from ..ir.typeinfer import infer_module_types
from ..kernels.registry import default_registry
from ..model import FinancialModel
from ..version import __version__

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="FinIR — a financial IR and incremental execution runtime.",
)
console = Console()
err = Console(stderr=True)


def _load_module(path: str):
    text = Path(path).read_text(encoding="utf-8")
    return parse_module(text, name=Path(path).stem)


def _apply_sets(model: FinancialModel, sets: list[str]) -> None:
    for pair in sets:
        if "=" not in pair:
            raise typer.BadParameter(f"--set expects name=value, got {pair!r}")
        name, value = pair.split("=", 1)
        model.set(name.strip(), float(value))


@app.command()
def version() -> None:
    """Print the FinIR version."""
    console.print(f"FinIR v{__version__}")


@app.command()
def run(
    model_file: str = typer.Argument(..., help="A .finir model file."),
    set_: list[str] = typer.Option([], "--set", help="Set an input: --set revenue=500000000"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Run a model and print its outputs."""
    module = _load_module(model_file)
    model = FinancialModel.from_ir(module)
    _apply_sets(model, set_)
    result = model.evaluate()
    if as_json:
        console.print_json(json.dumps({k: _num(v) for k, v in result.values.items()}))
        return
    table = Table(title=f"{module.name} — outputs")
    for col in ("output", "value"):
        table.add_column(col)
    for name, value in result.values.items():
        table.add_row(name, _fmt(value))
    console.print(table)
    console.print(
        f"[dim]backend={result.stats.backend} "
        f"recomputed={result.stats.nodes_evaluated} reused={result.stats.nodes_reused}[/dim]"
    )


@app.command()
def compile(
    model_file: str = typer.Argument(...),
    show_passes: bool = typer.Option(False, "--show-passes", help="Show each compiler pass."),
) -> None:
    """Compile a model through the pass pipeline."""
    module = _load_module(model_file)
    compiled = compile_module(module)
    console.print(f"[bold]{module.name}[/bold]: compiled ({len(compiled.module.nodes)} nodes)")
    if show_passes:
        table = Table(title="Compiler passes")
        for col in ("pass", "ms", "detail"):
            table.add_column(col)
        for p in compiled.report.passes:
            detail = (
                {k: v for k, v in compiled.report.details[p].items()}
                if isinstance(compiled.report.details.get(p), dict)
                else compiled.report.details.get(p)
            )
            table.add_row(p, f"{compiled.report.timings_ms.get(p, 0):.3f}", str(detail)[:70])
        console.print(table)


@app.command()
def inspect(model_file: str = typer.Argument(...)) -> None:
    """Show nodes, dependencies, types, outputs, backend plan, and cacheable nodes."""
    module = _load_module(model_file)
    types = infer_module_types(module, kernel=default_registry().result_type)
    table = Table(title=f"{module.name}")
    for col in ("node", "kind", "type", "depends on"):
        table.add_column(col)
    from ..ir.module import Computed, Constant, Input

    for node in module.iter_nodes():
        kind = (
            "input"
            if isinstance(node, Input)
            else "const"
            if isinstance(node, Constant)
            else "computed"
        )
        deps = ", ".join(module.dependencies(node.name)) if isinstance(node, Computed) else ""
        ntype = types.get(node.name)
        table.add_row(node.name, kind, ntype.textual() if ntype is not None else "", deps)
    console.print(table)
    console.print(f"outputs: {module.outputs or '(none declared)'}")
    console.print(f"cacheable nodes: {len(module.computed())}")
    plan = BackendPlanner().choose(
        WorkloadProfile(scenario_size=1, node_count=len(module.computed()))
    )
    console.print(f"backend plan (scalar): {plan.backend.name} — {plan.rationale}")


@app.command()
def graph(
    model_file: str = typer.Argument(...),
    format: str = typer.Option("dot", "--format", help="dot | json"),
) -> None:
    """Export the dependency graph (Graphviz DOT or JSON)."""
    module = _load_module(model_file)
    types = infer_module_types(module, kernel=default_registry().result_type)
    if format == "dot":
        print(to_dot(module, types=types))
    elif format == "json":
        print(json.dumps(to_graph_json(module, types=types), indent=2))
    else:
        raise typer.BadParameter("format must be 'dot' or 'json'")


@app.command()
def benchmark(
    quick: bool = typer.Option(True, "--quick/--full", help="Quick run vs full suite."),
) -> None:
    """Run the incremental-vs-recompute benchmark and print results."""
    from ..benchmark import run_incremental_benchmark

    rows = run_incremental_benchmark(quick=quick)
    table = Table(title="Incremental vs full recompute (iterative agent workload)")
    for col in ("model nodes", "turns", "baseline s", "finir s", "speedup", "cache hit%"):
        table.add_column(col)
    for r in rows:
        table.add_row(
            str(r["nodes"]),
            str(r["turns"]),
            f"{r['baseline_s']:.4f}",
            f"{r['finir_s']:.4f}",
            f"{r['speedup']:.2f}x",
            f"{r['cache_hit_ratio'] * 100:.1f}",
        )
    console.print(table)


@app.command()
def doctor() -> None:
    """Check the environment: NumPy, optional GPU, optional CLI/viz extras."""
    table = Table(title="finir doctor")
    for col in ("check", "status", "detail"):
        table.add_column(col)
    import numpy

    table.add_row("numpy", "[green]ok[/green]", numpy.__version__)
    table.add_row("kernels", "[green]ok[/green]", f"{len(default_registry().names())} registered")
    gpu = gpu_available()
    table.add_row(
        "gpu (cupy)",
        "[green]available[/green]" if gpu else "[yellow]not available[/yellow]",
        "CUDA device present" if gpu else "CPU-only (fully supported)",
    )
    for name, mod in (("cli (typer/rich)", "typer"), ("viz (graphviz)", "graphviz")):
        try:
            __import__(mod)
            table.add_row(name, "[green]installed[/green]", "")
        except Exception:
            table.add_row(name, "[yellow]optional[/yellow]", "not installed")
    console.print(table)


def _num(v):
    import numpy as np

    if isinstance(v, np.ndarray):
        return v.tolist()
    return float(v)


def _fmt(v) -> str:
    import numpy as np

    if isinstance(v, np.ndarray):
        return f"array{v.shape}"
    if abs(v) >= 1000:
        return f"{v:,.2f}"
    return f"{v:.4f}"


def main() -> None:
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
