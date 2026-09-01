"""FinIR-Intent: the Hugging Face natural-language layer for the FinIR project.

This package *interprets* natural-language financial instructions into the
canonical FinIR Intent Contract (schema version 1.0) defined by the core ``finir``
package (``finir.intent``). It performs no financial computation itself -- that is
the FinIR runtime's job, reached via ``finir.intent.execute_intent`` /
``FinancialModel.apply_intent``.

    from finir_intent import compile_intent
    from finir.intent import FinIRIntent

    envelope = compile_intent("Increase COGS by 4%")
    intent = FinIRIntent.from_obj(envelope)  # structural validation (core package)
"""

from __future__ import annotations

from .baseline import BaselineIntentCompiler, compile_intent
from .reference_model import build_reference_model

__all__ = [
    "BaselineIntentCompiler",
    "build_reference_model",
    "compile_intent",
]
