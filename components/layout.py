"""Shared layout helpers."""

from pathlib import Path

import streamlit as st


STYLES_DIR = Path(__file__).resolve().parents[1] / "styles"


def inject_styles() -> None:
    """Load version-controlled CSS without coupling it to the app router."""
    css = "\n".join(path.read_text(encoding="utf-8") for path in sorted(STYLES_DIR.glob("*.css")))
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
