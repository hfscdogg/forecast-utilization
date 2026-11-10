"""
Flag identifiers in Deluge (.dg) files that are used but never assigned.

Zoho Creator rejects a function on save when it reads a variable that was
never assigned ("Variable 'mns' is not defined", generate_quarterly.dg,
2026-11-10). Nothing in this repo runs Deluge, so the Python mirrors and
their tests cannot see a slip like that. This is a static stand-in for the
save check: it does not parse Deluge, it tracks names.

Reports two things per file:
- undefined: a name that is read and never assigned anywhere in the file,
  or read before its first assignment.
- block_only: a name whose every assignment sits inside a block that the
  read is outside of (assigned in an `if`, read after it). Deluge variables
  are function-scoped, so this saves fine, but the value is null when the
  block did not run. An if/else that assigns in both branches is fine and
  is not reported.

Run: python scripts/lint_deluge.py [files...]   (default: deluge/**/*.dg)
Exit code 1 when anything is undefined.
"""

import re
import sys
from pathlib import Path

KEYWORDS = {
    "if", "else", "for", "each", "in", "return", "try", "catch", "info",
    "sendmail", "invokeurl", "insert", "into", "sort", "by", "desc", "asc",
    "range", "from", "to", "true", "false", "null", "void", "break",
    "continue", "thisapp", "zoho", "input", "alert", "delete",
    # type names (signatures and casts)
    "Map", "List", "String", "string", "map", "list", "int", "bool",
    "Date", "date", "Decimal", "decimal", "Collection",
    # HTTP verbs used bare in invokeurl
    "GET", "POST", "PUT", "PATCH", "DELETE",
}

IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
COMPARE = re.compile(r"\s*(==|!=|>=|<=|<|>)")


def strip_comments_and_strings(src):
    """Blank out comments and string literals, keeping every offset."""
    out = []
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        two = src[i:i + 2]
        if two == "//":
            j = src.find("\n", i)
            j = n if j == -1 else j
            out.append(" " * (j - i))
            i = j
        elif two == "/*":
            j = src.find("*/", i + 2)
            j = n if j == -1 else j + 2
            out.append(re.sub(r"[^\n]", " ", src[i:j]))
            i = j
        elif c in "\"'":
            j = i + 1
            while j < n and src[j] != c:
                j += 2 if src[j] == "\\" else 1
            j = min(j + 1, n)
            out.append(c + re.sub(r"[^\n]", " ", src[i + 1:j - 1]) + c)
            i = j
        else:
            out.append(c)
            i += 1
    return "".join(out)


def lint(src):
    """Return (undefined, block_only): lists of (line, name)."""
    code = strip_comments_and_strings(src)

    # Function parameters: names in the first (...) of the file.
    defs = {}  # name -> list of (pos, block_path)
    sig = re.match(r"\s*[\w.]+\s+[\w.]+\s*\(([^)]*)\)", code)
    body_start = 0
    if sig:
        body_start = sig.end()
        for part in sig.group(1).split(","):
            names = IDENT.findall(part)
            if names:
                defs.setdefault(names[-1], []).append((0, ()))

    # Bracket contexts: "criteria" for Form[...] fetches, "fields" for
    # insert-into / sendmail / invokeurl blocks, "index" otherwise.
    uses = []  # (pos, name, block_path)
    path = []  # stack of block ids
    block_seq = 0
    brackets = []  # stack of bracket kinds
    pending_block_kw = None
    i, n = body_start, len(code)
    prev_sig = ""  # previous significant token text
    prev_prev = ""
    while i < n:
        c = code[i]
        if c.isspace():
            i += 1
            continue
        if c == "{":
            block_seq += 1
            path.append(block_seq)
        elif c == "}":
            if path:
                path.pop()
        elif c == "[":
            if pending_block_kw in ("insert", "sendmail", "invokeurl"):
                brackets.append("fields")
                pending_block_kw = None
            elif IDENT.fullmatch(prev_sig or "") and prev_sig not in KEYWORDS:
                brackets.append("criteria")
            else:
                brackets.append("index")
        elif c == "]":
            if brackets:
                brackets.pop()
        m = IDENT.match(code, i) if (c.isalpha() or c == "_") else None
        if not m:
            if c in "\"'":
                j = code.find(c, i + 1)
                i = (j if j != -1 else n - 1) + 1
                prev_prev, prev_sig = prev_sig, "<str>"
                continue
            prev_prev, prev_sig = prev_sig, c
            i += 1
            continue
        name = m.group(0)
        end = m.end()
        rest = code[end:]
        nxt = rest.lstrip()[:2]
        kind = brackets[-1] if brackets else None

        if name in ("insert", "sendmail", "invokeurl"):
            pending_block_kw = name
        is_member = prev_sig == "."
        is_call = nxt[:1] == "("
        is_form = nxt[:1] == "[" or prev_sig == "into"
        is_key = nxt[:1] == ":" and kind == "fields"
        is_field_assign = (
            kind == "fields" and nxt[:1] == "=" and nxt != "=="
            and prev_sig in ("[", "<str>", ")", "]") or
            (kind == "fields" and nxt[:1] == "=" and nxt != "==")
        )
        is_criteria_field = kind == "criteria" and COMPARE.match(rest) is not None
        is_sort_field = prev_sig == "by" and prev_prev == "sort"

        if name in KEYWORDS or name.isupper() and is_key:
            pass
        elif is_member or is_call or is_form or is_key or is_field_assign \
                or is_criteria_field or is_sort_field:
            pass
        elif prev_sig == "each" or (prev_sig == "(" and prev_prev == "catch"):
            # Loop / catch variables live in the block that follows.
            defs.setdefault(name, []).append((m.start(), tuple(path) + ("next",)))
        elif nxt[:1] == "=" and nxt != "==" and kind is None:
            # Takes effect at the end of the statement, so `x = x + 1`
            # with no earlier assignment is still a read of nothing.
            semi = code.find(";", end)
            defs.setdefault(name, []).append(
                (semi if semi != -1 else m.start(), tuple(path))
            )
        else:
            uses.append((m.start(), name, tuple(path)))
        prev_prev, prev_sig = prev_sig, name
        i = end

    def line_of(pos):
        return code.count("\n", 0, pos) + 1

    undefined, block_only = [], []
    for pos, name, upath in uses:
        dlist = defs.get(name)
        if not dlist or all(dpos > pos for dpos, _ in dlist):
            undefined.append((line_of(pos), name))
            continue
        earlier = [dp for dpos, dp in dlist if dpos < pos]
        visible = False
        for dp in earlier:
            dp_real = tuple(x for x in dp if x != "next")
            if upath[:len(dp_real)] == dp_real:
                visible = True
        if not visible:
            # Assigned in two or more sibling blocks (if/else): fine.
            parents = {tuple(x for x in dp if x != "next")[:-1] for dp in earlier}
            blocks = {tuple(x for x in dp if x != "next") for dp in earlier}
            covered = any(
                upath[:len(p)] == p and sum(1 for b in blocks if b[:-1] == p) >= 2
                for p in parents
            )
            if not covered:
                block_only.append((line_of(pos), name))
    return undefined, block_only


def main(argv):
    root = Path(__file__).resolve().parent.parent
    files = [Path(a) for a in argv] or sorted((root / "deluge").rglob("*.dg"))
    failed = False
    for f in files:
        undefined, block_only = lint(f.read_text())
        for line, name in undefined:
            failed = True
            print(f"{f}:{line}: '{name}' is used but never assigned")
        for line, name in sorted(set(block_only)):
            print(f"{f}:{line}: note: '{name}' is only assigned inside a block it is read outside of")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
