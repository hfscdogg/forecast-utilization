"""
Static check on the Deluge files: every name that is read must be assigned.

Nothing in this repo executes Deluge, so the Python mirrors cannot catch a
misspelled variable in a .dg file. Creator can: it rejected
generate_quarterly.dg on save with "Variable 'mns' is not defined"
(2026-11-10). This runs the same kind of check before the paste.

Run: pytest tests/test_deluge_lint.py
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from lint_deluge import lint  # noqa: E402

DG_FILES = sorted((ROOT / "deluge").rglob("*.dg"))


@pytest.mark.parametrize("path", DG_FILES, ids=lambda p: str(p.relative_to(ROOT)))
def test_no_undefined_names_in_deluge(path):
    undefined, _ = lint(path.read_text())
    assert undefined == []


@pytest.mark.parametrize("name", ["generate_quarterly.dg", "send_quarterly_email.dg"])
def test_quarterly_functions_read_nothing_assigned_only_in_a_block(name):
    _, block_only = lint((ROOT / "deluge" / name).read_text())
    assert block_only == []


def test_catches_the_mns_slip():
    src = """void f()
{
    month_names = List();
    for each mn in mns
    {
        info mn;
    }
}"""
    assert lint(src)[0] == [(4, "mns")]


def test_catches_read_before_assignment():
    src = """void f()
{
    total = total + 1;
}"""
    assert lint(src)[0] == [(3, "total")]


def test_parameters_loop_and_catch_variables_are_defined():
    src = """Map f(String week_start, Map time_cards)
{
    out = Map();
    try
    {
        for each k in time_cards.keys()
        {
            out.put(k, week_start);
        }
    }
    catch (e)
    {
        info e.toString();
    }
    return out;
}"""
    assert lint(src) == ([], [])


def test_form_fields_and_statement_keys_are_not_variables():
    src = """void f(String run_id)
{
    cutoff = zoho.currentdate;
    rows = My_Form[Week_End >= cutoff && Status == "Open"] sort by Created_At desc;
    for each r in rows
    {
        // a comment naming nothing_real
        insert into Other_Form
        [
            Run_ID = run_id
            Week = r.Week_End
        ];
        sendmail
        [
            from: zoho.adminuserid
            to: "x@example.com"
            subject: "undefined_in_string " + run_id
            message: r.Notes
        ];
    }
}"""
    assert lint(src) == ([], [])


def test_criteria_value_must_still_be_defined():
    src = """void f()
{
    rows = My_Form[Week_End >= cutof];
}"""
    assert lint(src)[0] == [(3, "cutof")]


def test_block_only_assignment_is_reported_but_if_else_is_fine():
    risky = """void f(Map m)
{
    if(m.size() > 0)
    {
        label = "some";
    }
    info label;
}"""
    assert lint(risky) == ([], [(7, "label")])
    fine = """void f(Map m)
{
    if(m.size() > 0)
    {
        label = "some";
    }
    else
    {
        label = "none";
    }
    info label;
}"""
    assert lint(fine) == ([], [])
