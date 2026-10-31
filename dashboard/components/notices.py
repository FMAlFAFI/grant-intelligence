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


def missing_outputs(outputs):
    commands = sorted({output.command for output in outputs if not output.ready})
    if not commands:
        return False
    st.warning("Run this from the repo root, then reload the page:\n\n```\n" + "\n".join(commands) + "\n```",
               title="The progress results are not there yet", icon=":material/folder_off:")
    return True
