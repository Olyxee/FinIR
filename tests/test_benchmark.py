"""Benchmark framework tests, including the multimodal-advantage claim."""

from __future__ import annotations

import pytest

from eif.benchmark import generate_canonical, load_suite, run_case, run_suite
from eif.config import Config


@pytest.fixture
def cases_dir(tmp_path):
    generate_canonical(tmp_path)
    return tmp_path


def test_generate_and_load(cases_dir):
    suite = load_suite(cases_dir)
    assert len(suite) == 8
    ids = {c.case_id for c in suite}
    assert "supplier_price_increase" in ids
    assert all(c.synthetic for c in suite)


def test_supplier_case_detected(cases_dir):
    case = next(c for c in load_suite(cases_dir) if c.case_id == "supplier_price_increase")
    result = run_case(case, config=Config(), condition="eif")
    assert result.detection.tp == 1
    assert result.detection.fp == 0


def test_benign_case_no_false_positive(cases_dir):
    case = next(c for c in load_suite(cases_dir) if c.case_id == "benign_non_material")
    result = run_case(case, config=Config(), condition="eif")
    # no material event expected; must not raise a false alarm
    assert result.detection.fp == 0


def test_eif_beats_structured_baseline(cases_dir):
    cfg = Config()
    eif = run_suite(cases_dir, config=cfg, condition="eif")
    base = run_suite(cases_dir, config=cfg, condition="baseline", structured_only=True)
    # The core hypothesis: multimodal recall exceeds structured-only recall.
    assert eif.detection().recall > base.detection().recall


def test_eslt_positive_on_average(cases_dir):
    eif = run_suite(cases_dir, config=Config(), condition="eif")
    summary = eif.eslt()
    assert summary.n >= 1
    assert summary.mean_days is not None and summary.mean_days > 0


def test_run_is_reproducible(cases_dir):
    cfg = Config()
    a = run_suite(cases_dir, config=cfg, condition="eif").detection().as_dict()
    b = run_suite(cases_dir, config=cfg, condition="eif").detection().as_dict()
    assert a == b
