from pathlib import Path

import streamlit as st

st.title("Help")
st.caption("Project documentation from README.md")

readme_path = Path(__file__).resolve().parent.parent / "README.md"

if readme_path.exists():
    st.markdown(readme_path.read_text(encoding="utf-8"))
else:
    st.warning("README.md was not found in the project root.")
