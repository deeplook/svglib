#!/usr/bin/env python

"""
A demo for using svglib inside a small Streamlit application.

This app running in a webbrowser simply allows to open and edit a SVG source file,
convert it to PDF and display that all on the same page. The PDF rendering happens
via some browser plugin preinstalled in the browser or installed by the user or
Streamlit...

Install Streamlit:

    $ pip install streamlit

Run the app:

    $ streamlit run st_svg2pdf_app.py
"""

import base64
import os
import subprocess
import tempfile

import streamlit as st
import svglib


# config

st.set_page_config(
    page_title="SVG to PDF Converter",
    layout="wide",
    initial_sidebar_state="auto",
)

# sidebar

st.sidebar.header("Settings")
svg_path = st.sidebar.text_input("SVG File Path")
if st.sidebar.button("Read"):
    pass

# main 

st.title('SVG to PDF')

st.markdown(
    "An experimental [streamlit.io](https://streamlit.io) UI "
    "for [svg2pdf](https://github.com/deeplook/svglib) (based "
    "on [reportlab.com](https://reportlab.com))."
)

pdf_path = ""
col1, col2 = st.beta_columns(2)
with col1:
    with st.beta_expander("SVG"):
        svg_code = ""
        if svg_path:
            svg_code = open(svg_path).read()
        svg = st.text_area("Code", value=svg_code, height=400)
        st.markdown(
            "Paste SVG code above or edit it and click below "
            "to convert it!"
        )
        if st.button("Convert", key=2):
            if svg:
                svg_tmp_path = tempfile.mktemp(suffix=".svg")
                with open(svg_tmp_path, "w") as f:
                    f.write(svg)
                pdf_path = os.path.splitext(svg_tmp_path)[0] + ".pdf"
                subprocess.check_call(["svg2pdf", svg_tmp_path])
with col2:
    with st.beta_expander("PDF"):
        if pdf_path:
            pdf_content = open(pdf_path, "rb").read()
            base64_pdf = base64.b64encode(pdf_content).decode("utf-8")
            pdf_display = (
                f'<embed src="data:application/pdf;base64,{base64_pdf}" '
                'width="500" height="400" type="application/pdf">'
            )
            st.markdown(pdf_display, unsafe_allow_html=True)
