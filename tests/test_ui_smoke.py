"""Streamlit UI import smoke test (no UI runtime)."""

from __future__ import annotations

import importlib

import pytest

streamlit = pytest.importorskip("streamlit")


def test_ui_modules_import():
    app = importlib.import_module("conductgene.ui.app")
    client = importlib.import_module("conductgene.ui.client")
    assert callable(app.main)
    assert hasattr(client, "ConductGeneClient")
