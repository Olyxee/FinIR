"""CLI tests using Typer's CliRunner."""

from __future__ import annotations

import json

import pytest

pytest.importorskip("typer")
from typer.testing import CliRunner

from eif.cli.main import app

runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "Economic Intelligence Framework" in result.stdout


def test_analyze_then_events(tmp_path):
    db = f"sqlite:///{tmp_path / 'cli.db'}"
    email = tmp_path / "e.txt"
    email.write_text(
        "Supplier ABC will raise prices 10% on SKU-A. Annual spend R42,000,000.",
        encoding="utf-8",
    )
    r1 = runner.invoke(app, ["analyze", str(email), "--db", db, "--json"])
    assert r1.exit_code == 0, r1.output
    payload = json.loads(r1.stdout)
    assert payload["events"], "expected at least one event"

    r2 = runner.invoke(app, ["events", "--db", db, "--json"])
    assert r2.exit_code == 0
    events = json.loads(r2.stdout)
    assert any(e["event_type"] == "supplier_price_change" for e in events)


def test_doctor():
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0


def test_benchmark_generate_and_run(tmp_path):
    cases = tmp_path / "cases"
    r1 = runner.invoke(app, ["benchmark", "generate", str(cases)])
    assert r1.exit_code == 0

    r2 = runner.invoke(app, ["benchmark", "run", "--cases", str(cases), "--json"])
    assert r2.exit_code == 0
    report = json.loads(r2.stdout)
    assert report["detection"]["recall"] > 0


def test_benchmark_run_missing_cases(tmp_path):
    result = runner.invoke(app, ["benchmark", "run", "--cases", str(tmp_path / "nope")])
    assert result.exit_code == 1
