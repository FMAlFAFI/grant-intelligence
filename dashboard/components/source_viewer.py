import streamlit as st

from dashboard.components.rtl import text_block
from dashboard.data.sources import document_lines, sources_for


def source_viewer(grant_id):
    sources = sources_for(grant_id)
    if not sources:
        st.info("No Word files found for this grant in the raw data folder.")
        return
    private = [source for source in sources if source["private"]]
    if private:
        st.caption(f"{len(private)} reviewer forms exist. They are not shown: individual reviewer scores "
                   "and comments stay private, only the mean appears above.")
    for number, source in enumerate(source for source in sources if not source["private"]):
        path = source["path"]
        with st.expander(f"{source['label']}: {path.name}"):
            st.download_button("Download the Word file", data=path.read_bytes(), file_name=path.name,
                               mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                               key=f"download_{grant_id}_{number}", icon=":material/download:")
            text_block(document_lines(path))
