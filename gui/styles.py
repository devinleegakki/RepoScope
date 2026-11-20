"""Compatibility stylesheet constant for integrations using the old import."""

from pathlib import Path

APP_STYLE = Path(__file__).with_name("style.qss").read_text(encoding="utf-8")
