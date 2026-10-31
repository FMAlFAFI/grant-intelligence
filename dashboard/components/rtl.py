import html
import re

import streamlit as st

ARABIC = re.compile(r"[؀-ۿ]")

STYLE = """
<style>
.source-text { font-size: 0.9rem; line-height: 1.6; }
.source-text div { margin: 0.1rem 0; unicode-bidi: plaintext; }
.source-text .rtl { direction: rtl; text-align: right; }
</style>
"""


def is_arabic(text):
    return bool(ARABIC.search(str(text)))


def inject_css():
    st.markdown(STYLE, unsafe_allow_html=True)


def text_block(lines):
    rows = []
    for line in lines:
        css = "rtl" if is_arabic(line) else "ltr"
        rows.append(f'<div class="{css}" dir="auto">{html.escape(line)}</div>')
    st.markdown(f'<div class="source-text">{"".join(rows)}</div>', unsafe_allow_html=True)


def labelled(label, value):
    direction = "rtl" if is_arabic(value) else "ltr"
    st.markdown(f'**{html.escape(label)}**  \n<span dir="{direction}">{html.escape(str(value))}</span>',
                unsafe_allow_html=True)
