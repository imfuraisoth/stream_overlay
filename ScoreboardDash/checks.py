#!/usr/bin/env python3
"""Pre-push validation for the stream_overlay project.

Packages the checks that have caught every recent bug class:
  1. Python syntax (py_compile) on every .py
  2. JS syntax (node --check) on every standalone .js
  3. Inline <script> blocks in every .html parse (catches dropped/duplicated
     function headers mid-edit)
  4. <div> balance per page
  5. i18n: en/ja key parity AND every referenced key exists
  6. Endpoint contract: every fetch('/x') in the frontend has a server route
  7. Duplicate top-level function definitions (silent-shadowing bugs)
  8. Line-ending consistency (no mixed CRLF/LF within a file)

Run from the repo root:  python checks.py
Exit code 0 = clean, 1 = problems found. Requires python3 + node on PATH.
"""
import glob
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.abspath(__file__))
SD = os.path.join(REPO, "ScoreboardDash")
SKIP_DIRS = (".git", "node_modules")
SKIP_FILES = ("min.js", "jquery")
# jQuery-era overlays: syntax-checked, but skipped for the deeper heuristics.
LEGACY = ("commentator overlay", "commentator overlay single", "results overlay",
          "versus overlay", "top8 overlay", os.path.join("scoreboard", "_overlays"))

problems = []


def flag(msg):
    problems.append(msg)
    print("  PROBLEM: " + msg)


def _files(pattern):
    for f in glob.glob(os.path.join(REPO, "**", pattern), recursive=True):
        rel = os.path.relpath(f, REPO)
        if any(s in rel for s in SKIP_DIRS):
            continue
        if any(s in os.path.basename(rel).lower() for s in SKIP_FILES):
            continue
        yield f, rel


def _read(path):
    return open(path, newline="", encoding="utf-8", errors="replace").read()


def _node_check(src, label):
    tmp = os.path.join(REPO, "_check_tmp.js")
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(src)
    try:
        r = subprocess.run(["node", "--check", tmp], capture_output=True, text=True)
        if r.returncode != 0:
            err = r.stderr.strip().splitlines()
            flag("%s: JS syntax error: %s" % (label, err[-1] if err else "?"))
    finally:
        os.remove(tmp)


def check_python():
    print("[1] Python syntax")
    import py_compile
    for f, rel in _files("*.py"):
        if os.path.abspath(f) == os.path.abspath(__file__):
            continue
        try:
            py_compile.compile(f, doraise=True)
        except py_compile.PyCompileError as e:
            flag("%s: %s" % (rel, str(e).splitlines()[0]))


def check_js():
    print("[2] JS syntax")
    for f, rel in _files("*.js"):
        _node_check(_read(f), rel)


def _inline_js(src):
    return "\n;\n".join(re.findall(
        r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", src, re.DOTALL | re.I))


def check_html():
    print("[3+4] Inline scripts + div balance")
    for f, rel in _files("*.html"):
        src = _read(f)
        js = _inline_js(src)
        if js.strip():
            _node_check(js, rel + " (inline)")
        if src.count("<div") != src.count("</div>"):
            flag("%s: div imbalance (<div>=%d </div>=%d)"
                 % (rel, src.count("<div"), src.count("</div>")))


def _lang_keys(path):
    return set(re.findall(r"^\s+([a-z][a-z0-9_]*)\s*:", _read(path), re.M))


def check_i18n():
    print("[5] i18n parity + referenced keys")
    en_p = os.path.join(SD, "lang", "en.js")
    ja_p = os.path.join(SD, "lang", "ja.js")
    if not (os.path.exists(en_p) and os.path.exists(ja_p)):
        flag("lang files not found under ScoreboardDash/lang")
        return
    en, ja = _lang_keys(en_p), _lang_keys(ja_p)
    for k in sorted(en - ja):
        flag("i18n: key '%s' in en.js but missing from ja.js" % k)
    for k in sorted(ja - en):
        flag("i18n: key '%s' in ja.js but missing from en.js" % k)
    refs = set()
    for f, rel in _files("*.html"):
        if not rel.startswith("ScoreboardDash"):
            continue
        s = _read(f)
        refs |= set(re.findall(r'data-i18n="([a-z0-9_]+)"', s))
        for spec in re.findall(r'data-i18n-attr="([^"]+)"', s):
            for part in spec.split(";"):
                if ":" in part:
                    refs.add(part.split(":", 1)[1].strip())
        refs |= set(re.findall(r"""window\.t\(\s*['"]([a-z][a-z0-9_]*)['"]""", s))
    for f, rel in _files("*.js"):
        if not rel.startswith("ScoreboardDash") or os.sep + "lang" + os.sep in rel:
            continue
        refs |= set(re.findall(
            r"""window\.t\(\s*['"]([a-z][a-z0-9_]*)['"]""", _read(f)))
    for k in sorted(refs - en):
        flag("i18n: key '%s' referenced but not defined in en.js" % k)


def check_endpoints():
    print("[6] Frontend endpoints vs server routes")
    server_p = os.path.join(SD, "pyserver.py")
    if not os.path.exists(server_p):
        flag("pyserver.py not found")
        return
    ssrc = _read(server_p)
    routes = set(re.findall(r"@api\.route\(['\"]([^'\"]+)['\"]", ssrc))
    routes = {r.split("<")[0].rstrip("/") or r for r in routes}
    for f, rel in _files("*.html"):
        s = _read(f)
        for m in re.finditer(r"""fetch\(\s*['"](/[A-Za-z][^'"?]*)""", s):
            ep = m.group(1).rstrip("/")
            if ep not in routes:
                flag("%s: fetch('%s') has no server route" % (rel, ep))
    for f, rel in _files("*.js"):
        s = _read(f)
        for m in re.finditer(r"""fetch\(\s*['"](/[A-Za-z][^'"?]*)""", s):
            ep = m.group(1).rstrip("/")
            if ep not in routes:
                flag("%s: fetch('%s') has no server route" % (rel, ep))


def check_duplicate_functions():
    print("[7] Duplicate top-level function definitions")
    from collections import Counter
    for f, rel in _files("*.js"):
        if any(rel.startswith(p) for p in LEGACY):
            continue
        names = re.findall(
            r"(?m)^[ \t]{0,4}(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(",
            _read(f))
        for name, n in Counter(names).items():
            if n > 1:
                flag("%s: function %s defined %dx (later silently wins)"
                     % (rel, name, n))
    for f, rel in _files("*.html"):
        if any(rel.startswith(p) for p in LEGACY):
            continue
        names = re.findall(
            r"(?m)^[ \t]{0,6}(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(",
            _inline_js(_read(f)))
        for name, n in Counter(names).items():
            if n > 1:
                flag("%s: function %s defined %dx (later silently wins)"
                     % (rel, name, n))


def check_line_endings():
    print("[8] Line-ending consistency")
    for pattern in ("*.py", "*.js", "*.html", "*.css"):
        for f, rel in _files(pattern):
            d = open(f, "rb").read()
            crlf = d.count(b"\r\n")
            lone = d.count(b"\n") - crlf
            if crlf and lone:
                flag("%s: MIXED line endings (CRLF=%d, lone LF=%d)"
                     % (rel, crlf, lone))


if __name__ == "__main__":
    for fn in (check_python, check_js, check_html, check_i18n,
               check_endpoints, check_duplicate_functions, check_line_endings):
        fn()
    print()
    if problems:
        print("FAILED: %d problem(s) found." % len(problems))
        sys.exit(1)
    print("ALL CHECKS PASSED.")
    sys.exit(0)