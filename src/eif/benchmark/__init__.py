"""Open benchmark framework: cases, runner, reporting, synthetic data."""

from __future__ import annotations

from .generate import generate_canonical, generate_variants
from .model import BenchmarkCase, RealizedLabel, TraditionalLabel, load_case, load_suite
from .report import render_comparison_text, render_suite_text, suite_to_dict
from .runner import CaseResult, SuiteResult, run_case, run_suite

__all__ = [
    "BenchmarkCase",
    "CaseResult",
    "RealizedLabel",
    "SuiteResult",
    "TraditionalLabel",
    "generate_canonical",
    "generate_variants",
    "load_case",
    "load_suite",
    "render_comparison_text",
    "render_suite_text",
    "run_case",
    "run_suite",
    "suite_to_dict",
]
