"""Test para playwright engine."""
import pytest
from src.scrapers.playwright_engine import PlaywrightEngine

def test_playwright_engine_init():
    engine = PlaywrightEngine(headless=True)
    assert engine.headless is True
    assert engine._playwright is None
    assert engine._browser is None

# Skipping integration tests that require internet/browser installation for now
