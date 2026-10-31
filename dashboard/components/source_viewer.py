import streamlit as st

from dashboard.components.rtl import text_block
from dashboard.data.sources import document_lines, sources_for


def source_viewer(grant_id):
    sources = sources_for(grant_id)
    if not sources:
        st.info("No documents found for this grant. Run `python -m app.ingestion.pseudonymiser` to prepare them.")
        return
    private = [source for source in sources if source["private"]]
    if private:
        st.caption(f"Reviewer forms: {len(private)}. They are not shown, because individual reviewer scores "
                   "and comments stay private.")
    for number, source in enumerate(source for source in sources if not source["private"]):
        path = source["path"]
        with st.expander(f"{source['label']}: {path.name}"):
            st.download_button("Download the Word file", data=path.read_bytes(), file_name=path.name,
                               mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                               key=f"download_{grant_id}_{number}", icon=":material/download:")
            text_block(document_lines(path))
