import streamlit as st


def share_text(value, total):
    return f"{value / total:.0%} of {total}" if total else "no records"


def tile(label, value, total, note=None, page=None):
    with st.container(border=True):
        st.metric(label, f"{value} / {total}")
        st.caption(note or share_text(value, total))
        if page:
            st.page_link(page, label="Open", icon=":material/arrow_forward:")


def value_tile(label, text, note, page=None):
    with st.container(border=True):
        st.metric(label, text)
        st.caption(note)
        if page:
            st.page_link(page, label="Open", icon=":material/arrow_forward:")


def big_number(label, value, note, page=None):
    with st.container(border=True, height="stretch"):
        st.metric(label, value)
        st.caption(note)
        if page:
            st.page_link(page, label="Open", icon=":material/arrow_forward:")


def tile_row(count):
    return st.columns(count, gap="small")
