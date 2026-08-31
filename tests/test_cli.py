"""CLI tests using Typer's CliRunner."""

from __future__ import annotations

import json

import pytest

pytest.importorskip("typer")
from typer.testing import CliRunner

from finir.cli.main import app

runner = CliRunner()

MODEL = """
model company {
  input revenue: money[ZAR]
  input cogs: money[ZAR]
  gross_profit = revenue - cogs
  gross_margin = gross_profit / revenue
  output gross_margin
  output gross_profit
}
"""


@pytest.fixture
def model_file(tmp_path):
    p = tmp_path / "company.finir"
    p.write_text(MODEL, encoding="utf-8")
    return str(p)


def test_version():
    r = runner.invoke(app, ["version"])
    assert r.exit_code == 0 and "FinIR" in r.stdout


def test_run(model_file):
    r = runner.invoke(
        app, ["run", model_file, "--set", "revenue=500000000", "--set", "cogs=300000000", "--json"]
    )
    assert r.exit_code == 0, r.output
    out = json.loads(r.stdout)
    assert out["gross_profit"] == 200_000_000


def test_inspect(model_file):
    r = runner.invoke(app, ["inspect", model_file])
    assert r.exit_code == 0
    assert "gross_margin" in r.stdout and "ratio" in r.stdout


def test_compile(model_file):
    r = runner.invoke(app, ["compile", model_file, "--show-passes"])
    assert r.exit_code == 0
    assert "type_check" in r.stdout


def test_graph_dot(model_file):
    r = runner.invoke(app, ["graph", model_file, "--format", "dot"])
    assert r.exit_code == 0 and "digraph" in r.stdout


def test_doctor():
    r = runner.invoke(app, ["doctor"])
    assert r.exit_code == 0 and "numpy" in r.stdout


def test_benchmark_runs():
    r = runner.invoke(app, ["benchmark", "--quick"])
    assert r.exit_code == 0
    assert "speedup" in r.stdout
