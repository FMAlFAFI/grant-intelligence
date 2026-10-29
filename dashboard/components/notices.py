import streamlit as st

from dashboard.data.contracts import ContractError
from dashboard.data.loaders import MissingOutput


def show_problem(error):
    if isinstance(error, MissingOutput):
        st.warning(f"Missing output: `{error.path.name}`. Run this from the repo root, then reload:\n\n"
                   f"```\n{error.command}\n```", icon=":material/folder_off:")
    elif isinstance(error, ContractError):
        st.error(f"`{error.name}` does not have the expected columns: {', '.join(error.missing)}",
                 icon=":material/error:")
    else:
        raise error


def guarded(loader, *args):
    try:
        return loader(*args)
    except (MissingOutput, ContractError) as error:
        show_problem(error)
        return None


def pending_panel(output, title, will_show):
    with st.container(border=True):
        st.subheader(f":material/hourglass_top: {title}: not finished yet")
        st.markdown(f"This part belongs to **{output.owner}** and its output is not on `main` yet. What is missing:")
        st.markdown("\n".join(f"- {item}" for item in output.missing))
        st.markdown("When the file is in place this page will show:")
        st.markdown("\n".join(f"- {item}" for item in will_show))
