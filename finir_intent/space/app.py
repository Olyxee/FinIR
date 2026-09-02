"""FinIR-Intent -- minimal Hugging Face Space.

Flow: natural-language instruction -> FinIR-Intent baseline -> canonical envelope
(validated against the core `finir` package's JSON Schema) -> real FinIR runtime
execution -> result. This file contains no financial computation and no execution
logic of its own -- it only calls `finir.intent` / `finir.FinancialModel`.

    python space/app.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")
os.environ.setdefault("HF_HUB_OFFLINE", "1")

import gradio as gr
from finir import __version__ as FINIR_RUNTIME_VERSION
from finir.intent import (
    SCHEMA_VERSION,
    FinIRIntent,
    IntentValidationError,
    execute_intent,
    json_schema,
)

try:
    # Normal case once `finir-intent` is pip-installed (e.g. from requirements.txt
    # in a real Space, or `pip install -e .` locally).
    from finir_intent import build_reference_model, compile_intent
    from finir_intent._version import FINIR_RUNTIME_COMPATIBLE
    from finir_intent._version import __version__ as FINIR_INTENT_VERSION
except ImportError:
    # Fallback for running straight out of this repo layout before the package is
    # published -- see README.md "Packaging note". Only touches sys.path when the
    # normal import actually fails, so an installed package is never shadowed.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
    from finir_intent import build_reference_model, compile_intent
    from finir_intent._version import FINIR_RUNTIME_COMPATIBLE
    from finir_intent._version import __version__ as FINIR_INTENT_VERSION

_SCHEMA_VALIDATOR = None  # lazily built (jsonschema is optional at Space runtime)


def _schema_errors(envelope: dict) -> list[str]:
    global _SCHEMA_VALIDATOR
    try:
        import jsonschema
    except ImportError:
        return []
    if _SCHEMA_VALIDATOR is None:
        _SCHEMA_VALIDATOR = jsonschema.Draft202012Validator(json_schema())
    return [e.message for e in _SCHEMA_VALIDATOR.iter_errors(envelope)]


_MODEL = build_reference_model()
_MODEL.evaluate()  # warm the runtime's incremental cache; result is not used here

_VERSION_BANNER = (
    f"**FinIR-Intent** `{FINIR_INTENT_VERSION}` &nbsp;|&nbsp; "
    f"**Intent schema** `{SCHEMA_VERSION}` &nbsp;|&nbsp; "
    f"**Compatible FinIR runtime** `{FINIR_RUNTIME_COMPATIBLE}` &nbsp;|&nbsp; "
    f"**Installed finir** `{FINIR_RUNTIME_VERSION}`"
)

_REFERENCE_MODEL_NOTE = """
Reference model (fixture data, not a real company): revenue, cogs, opex,
payment_terms, accounts_payable, inventory, capex, debt, interest_rate, cash, price,
volume -- all ZAR except where noted. See `src/finir_intent/reference_model.py`.
"""


def run(text: str) -> tuple[str, str, str]:
    if not text or not text.strip():
        return "", "", "Enter a natural-language financial instruction above."

    envelope = compile_intent(text)  # AI interpretation layer -- no financial math here
    envelope_json = json.dumps(envelope, indent=2)

    errors = _schema_errors(envelope)
    if errors:
        # Should never happen for this baseline; surfaced rather than hidden.
        return envelope_json, "", "Schema validation failed:\n" + "\n".join(errors)

    status = envelope["status"]
    if status != "valid":
        reason = envelope.get("reason", "(no reason given)")
        label = {"ambiguous": "Ambiguous", "unsupported": "Unsupported"}.get(status, status)
        return envelope_json, "", f"**{label}** -- not executed.\n\n{reason}"

    try:
        FinIRIntent.from_obj(envelope)  # structural validation (core package)
        execution = execute_intent(_MODEL, envelope)  # real FinIR runtime execution
    except IntentValidationError as exc:
        return envelope_json, "", f"Rejected at execution (semantic validation failed):\n\n{exc}"

    if execution.scenario_results is not None:
        lines = ["| scenario | ebitda | gross_margin |", "|---|---|---|"]
        for name, result in execution.scenario_results.items():
            lines.append(
                f"| {name} | R{float(result['ebitda']):,.0f} | {float(result['gross_margin']):.3f} |"
            )
        result_md = "\n".join(lines)
    else:
        r = execution.result
        is_batch = any(op.get("operation") == "range" for op in envelope.get("operations", []))
        if is_batch:
            ebitda = r["ebitda"]
            lines = [
                f"- **ebitda range**: R{float(ebitda.min()):,.0f} .. R{float(ebitda.max()):,.0f}",
                f"- **batch size**: {ebitda.size:,}",
            ]
        else:
            lines = [
                f"- **ebitda**: R{float(r['ebitda']):,.0f}",
                f"- **gross_margin**: {float(r['gross_margin']):.3f}",
            ]
            if "interest_expense" in r:
                lines.append(f"- **interest_expense**: R{float(r['interest_expense']):,.0f}")
            if "net_cash_position" in r:
                lines.append(f"- **net_cash_position**: R{float(r['net_cash_position']):,.0f}")
        lines.append(f"- recomputed: `{sorted(r.recomputed)}`")
        lines.append(f"- reused: `{sorted(r.reused)}`")
        result_md = "\n".join(lines)

    return envelope_json, result_md, "Executed against the real FinIR runtime."


_EXAMPLES = [
    "Increase COGS by 4%.",
    "Increase opex by R5,000,000.",
    "Extend payment terms to 60 days.",
    "Revenue falls 8%, COGS rises 3%, and extend payment terms to 60 days.",
    "Improve margins next year.",
    "Acquire our largest competitor.",
    "Increase revenue by USD 2,000,000.",
    "Sweep COGS from 300,000,000 to 400,000,000 in 100 steps.",
    "Base scenario: no changes. Upside scenario: revenue grows 10%. Downside scenario: revenue falls 8% and COGS rises 5%.",
]

with gr.Blocks(title="FinIR-Intent", analytics_enabled=False) as demo:
    gr.Markdown("# FinIR-Intent")
    gr.Markdown(_VERSION_BANNER)
    gr.Markdown(
        "Natural language -> structured **FinIR Intent Contract** envelope -> validated "
        "-> executed by the real FinIR runtime. Ambiguous or unsupported requests are "
        "refused rather than guessed."
    )
    with gr.Row():
        inp = gr.Textbox(
            label="Financial instruction", placeholder="e.g. Increase COGS by 4%.", lines=2
        )
    run_btn = gr.Button("Compile & execute", variant="primary")
    gr.Examples(examples=_EXAMPLES, inputs=inp)
    with gr.Row():
        envelope_out = gr.Code(label="FinIR Intent envelope (schema v1.0)", language="json")
        result_out = gr.Markdown(label="Execution result")
    status_out = gr.Markdown()
    gr.Markdown(_REFERENCE_MODEL_NOTE)

    run_btn.click(run, inputs=inp, outputs=[envelope_out, result_out, status_out])
    inp.submit(run, inputs=inp, outputs=[envelope_out, result_out, status_out])

if __name__ == "__main__":
    demo.launch()
