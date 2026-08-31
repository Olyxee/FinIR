"""Synthetic financial models for benchmarking (item 23).

Builds models of a controlled size and shape: ``segments`` independent business
units, each a ``depth``-long arithmetic chain, plus a top-level aggregate. Changing
one segment's input dirties only that segment and the aggregate — which is exactly
where dependency-aware incremental execution should win.
"""

from __future__ import annotations

from ..model import FinancialModel


def build_segmented_model(
    segments: int = 20, depth: int = 5, currency: str = "ZAR"
) -> FinancialModel:
    """A model with ``segments * (depth+1) + 1`` nodes (roughly)."""
    model = FinancialModel(name=f"synthetic_{segments}x{depth}")
    seg_outputs = []
    for s in range(segments):
        base = f"seg{s}_in"
        model.input(base, 1_000_000 + s * 1000, currency=currency)
        prev = base
        for d in range(depth):
            node = f"seg{s}_n{d}"
            if d % 2 == 0:
                model.define(node, f"{prev} * 1.05")
            else:
                model.define(node, f"{prev} - {base} * 0.01")
            prev = node
        seg_outputs.append(prev)
    # Aggregate all segment tails.
    expr = " + ".join(seg_outputs)
    model.define("total", expr, output=True)
    return model


def node_count(model: FinancialModel) -> int:
    return len(model.module.nodes)


def input_names(model: FinancialModel) -> list[str]:
    return [i.name for i in model.module.inputs()]
