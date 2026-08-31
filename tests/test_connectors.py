"""Connector tests."""

from __future__ import annotations

import pytest

from eif.connectors import ConnectorContext, default_registry
from eif.connectors.structured import CsvConnector, JsonConnector
from eif.connectors.text import EmailConnector, TextConnector
from eif.domain.enums import Modality
from eif.exceptions import SecurityError, UnsupportedModalityError


def test_text_connector_inline_string():
    reg = default_registry()
    ev = reg.load("hello world")
    assert len(ev) == 1 and ev[0].content == "hello world"


def test_text_connector_file(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("some content", encoding="utf-8")
    ev = TextConnector().load(str(p))
    assert ev[0].modality == Modality.TEXT
    assert ev[0].source == "a.txt"


def test_json_connector_dict():
    ev = JsonConnector().load({"a": 1, "b": [1, 2]})
    assert ev[0].modality == Modality.JSON
    assert '"a"' in ev[0].content


def test_csv_connector_renders_table(tmp_path):
    p = tmp_path / "t.csv"
    p.write_text("h1,h2\n1,2\n3,4\n", encoding="utf-8")
    ev = CsvConnector().load(str(p))
    assert ev[0].modality == Modality.TABLE
    assert ev[0].metadata["rows"] == "2"
    assert "h1 | h2" in ev[0].content


def test_email_connector(tmp_path):
    p = tmp_path / "m.eml"
    p.write_text(
        "From: a@b.com\nSubject: Hi there\nDate: Wed, 03 Sep 2026 10:00:00 +0000\n\nBody text.",
        encoding="utf-8",
    )
    ev = EmailConnector().load(str(p))[0]
    assert ev.modality == Modality.EMAIL
    assert ev.created_at is not None
    assert "Body text" in ev.content


def test_registry_directory(tmp_path):
    (tmp_path / "a.txt").write_text("supplier note", encoding="utf-8")
    (tmp_path / "b.csv").write_text("x,y\n1,2\n", encoding="utf-8")
    reg = default_registry()
    ev = reg.load(str(tmp_path))
    assert len(ev) == 2


def test_unsupported_source_raises():
    reg = default_registry()
    with pytest.raises(UnsupportedModalityError):
        reg.load(12345)  # not a str/dict/list/path


def test_file_size_limit(tmp_path):
    ctx = ConnectorContext()
    ctx.security.max_file_bytes = 5
    p = tmp_path / "big.txt"
    p.write_text("way too long", encoding="utf-8")
    with pytest.raises(SecurityError):
        TextConnector(ctx).load(str(p))


def test_pii_redaction(tmp_path):
    ctx = ConnectorContext()
    ctx.security.redact_pii = True
    ev = TextConnector(ctx).make_text_evidence("contact me at john@example.com", source="x")
    assert "john@example.com" not in ev.content
    assert ev.security.contains_pii is True
