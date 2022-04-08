import difflib
import re
import uuid
from pydoc import pager as show_in_pager

import typer
from requests.compat import urljoin

RFC_INDEX = "https://www.rfc-editor.org/rfc/rfc-index.txt"
RFC_BASE_URL = "https://www.rfc-editor.org/rfc/"
DRAFTS_BASE_URL = 'https://www.ietf.org/id/'
USER_AGENT = f"wasi_master/rfc-cli/{uuid.UUID(int=uuid.getnode()).hex.rstrip('0')}"

rfc_regex = re.compile(r'<li><a href=".+">\s*([^<]+?)<\/a><\/li>')
draft_rfc_regex = re.compile(r'<a href=".+?">(draft-[a-zA-Z-0-9]+)[\.\w]+?<\/a>')

app = typer.Typer()

try:
    from requests_cache.session import CachedSession
except ImportError:
    from requests import Session

    session = Session()
    session.headers.update({"User-Agent": USER_AGENT})
else:
    import os.path

    cache_path = os.path.join(os.path.dirname(__file__), "cache", "requests")
    session = CachedSession(
        cache_path,
        backend="sqlite",
        urls_expire_after={
            "https://www.rfc-editor.org/rfc/rfc[0-9][0-9][0-9][0-9].@(txt|json|html)": 21600,
            "https://www.ietf.org/id/*": 10800,
            "https://www.rfc-editor.org/rfc/rfc-index.txt": 86400,
        },
        headers={"User-Agent": USER_AGENT},
        cache_control=True,
    )


def removeprefix(string: str, prefix: str) -> str:
    """
    Remove prefix from a string or return a copy otherwise.
    """
    if string.startswith(prefix):
        return string[len(prefix):]
    return string


def get_all_drafts():
    r = session.get(DRAFTS_BASE_URL)
    content = r.text
    return list(set(draft_rfc_regex.findall(content)))


def get_all_rfcs():
    r = session.get(RFC_BASE_URL)
    content = r.text
    return [i for i in list(set(rfc_regex.findall(content))) if not i.endswith('/')]


@app.command()
def show(
    rfc: str = typer.Argument(str, help="The RFC id as a number"),
    pager: bool = typer.Option(False, help="Whether to use a pager or not")
):
    if rfc.startswith('draft-'):
        return show_draft(rfc, pager)
    r = session.get(urljoin(RFC_BASE_URL, f"rfc{rfc}.txt"))
    if r.status_code == 200:
        if pager:
            show_in_pager(r.text)
        else:
            print(r.text)
    else:
        print("Error", r.status_code)

@app.command()
def show_draft(
    draft_rfc: str = typer.Argument(str, help="The draft RFC name as a number"),
    pager: bool = typer.Option(False, help="Whether to use a pager or not")
):
    if not draft_rfc.startswith('draft-'):
        draft_rfc = 'draft-' + draft_rfc
    r = session.get(urljoin(DRAFTS_BASE_URL, f"{draft_rfc}.txt"))
    if r.status_code == 200:
        if pager:
            show_in_pager(r.text)
        else:
            print(r.text)
    elif r.status_code == 404:
        possible_drafts = difflib.get_close_matches(draft_rfc, get_all_drafts())
        if possible_drafts:
            print("Draft not found, possible matches include:")
            print("  -", "\n  - ".join(removeprefix(i, 'draft-') for i in possible_drafts))
        else:
            print("No draft matching", draft_rfc, "Found, no close matches were also found")
    else:
        print("Error", r.status_code)

@app.callback()
def _main(cache: bool = typer.Option(False, help="Whether to use cache or not")):
    if not cache:
        from requests import Session

        session = Session()
        session.headers.update({"User-Agent": USER_AGENT})
