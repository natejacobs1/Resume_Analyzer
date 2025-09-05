import streamlit as st

def apply_modern_styles():
    st.markdown(
        """
        <style>
            .css-1dp5vir { padding-top: 1rem; }
            body { background-color: #071018; color: #e6eef0; }
            .stMarkdown { color: #e6eef0; }
        </style>
        """,
        unsafe_allow_html=True,
    )

def page_header(title: str, subtitle: str = ""):
    st.markdown(f"## {title}")
    if subtitle:
        st.write(subtitle)