#!/usr/bin/env python3
"""Loyiha xaritasi: kod tuzilishi, bog'lanishlar va ehtimoliy zaif joylar.

    python scan.py [REPO] [--out DIR] [--render-only]

Natija (standart: REPO/docs/):
  architecture.json        — AI uchun: modullar, funksiyalar, endpointlar, jadvallar, bog'lanishlar, xavflar
  ARCHITECTURE.html        — odam uchun: interaktiv graf (brauzerda ochiladi)
Qo'lda yuritiladigan qatlam (Claude yozadi, skaner o'chirmaydi):
  architecture.notes.json  — komponentlar, modul/funksiya izohlari, Claude topgan xavflar, xavflarni ko'rib chiqish

Faqat Python standart kutubxonasi. Python — `ast` bilan aniq; Go/TS/JS/Dart — regex bilan (taxminiy).
"""

from __future__ import annotations

import argparse
import ast
import datetime as dt
import fnmatch
import hashlib
import json
import os
import posixpath
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

SCHEMA = "loyiha-xotirasi/architecture@1"
LANGS = {".py": "python", ".go": "go", ".ts": "typescript", ".tsx": "typescript", ".js": "javascript",
         ".jsx": "javascript", ".mjs": "javascript", ".cjs": "javascript", ".dart": "dart", ".sql": "sql"}
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "env", "__pycache__", ".dart_tool", "build", "dist", ".next",
             "out", "coverage", "vendor", ".idea", ".vscode", ".gradle", "Pods", ".mypy_cache", ".pytest_cache",
             "site-packages", ".agent", ".claude", "static", "staticfiles", "media"}
SKIP_SUFFIX = (".min.js", ".g.dart", ".freezed.dart", ".gr.dart", ".mocks.dart", "_pb2.py", ".pb.go", ".d.ts", ".bundle.js")
MAX_BYTES = 400_000
LONG_FN, VERY_LONG_FN, HIGH_FAN_IN = 80, 150, 8

ABOUT = ("Kod xaritasi (avtomatik + Claude izohlari). modules — papka darajasidagi qismlar; functions — har bir "
         "funksiya/metod (calls: chaqiradigan funksiyalar id'lari, fan_in: necha joydan chaqiriladi); endpoints — HTTP "
         "marshrutlar va handler; tables — DB jadvallari; edges — modul/endpoint/jadval bog'lanishlari (kind: imports, "
         "calls, http, db, handles); risks — ehtimoliy zaif joylar (severity high/medium/low, source auto|claude, "
         "status open|confirmed|ok|fixed). Avtomatik xavf — taxmin, kodni o'qib tekshirish kerak.")


# ============================================================ fayllar

def git(root: Path, *args: str) -> str | None:
    try:
        r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout.decode("utf-8", "replace") if r.returncode == 0 else None


def list_files(root: Path) -> list[str]:
    out = git(root, "ls-files", "-co", "--exclude-standard", "-z") if (root / ".git").exists() else None
    if out is not None:
        paths = [p for p in out.split("\0") if p]
    else:
        paths = []
        for d, dirs, files in os.walk(root):
            dirs[:] = [x for x in dirs if x not in SKIP_DIRS and not x.startswith(".")]
            rel = Path(d).relative_to(root).as_posix()
            paths += [f if rel == "." else f"{rel}/{f}" for f in files]
    res = []
    for p in paths:
        ext = os.path.splitext(p)[1].lower()
        if ext not in LANGS or p.endswith(SKIP_SUFFIX) or "zz_agent_spec" in p:
            continue
        if any(part in SKIP_DIRS for part in p.split("/")[:-1]):
            continue
        try:
            if (root / p).stat().st_size > MAX_BYTES:
                continue
        except OSError:
            continue
        res.append(p)
    return sorted(res)


def is_test(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    return bool(re.match(r"^(test_.*\.py|tests?\.py|conftest\.py|.*_test\.(py|go|dart)|.*\.(test|spec)\.[jt]sx?)$", name)) or \
        any(p in ("tests", "test", "__tests__", "testdata", "e2e") for p in path.split("/")[:-1])


def module_of(path: str) -> str:
    d = posixpath.dirname(path)
    return d or "(ildiz)"


# ============================================================ xavf qoidalari (barcha tillar, qator bo'yicha)

R = re.compile
LINE_RULES: list[tuple[str, str, str, re.Pattern, tuple[str, ...]]] = [
    # (kind, severity, sarlavha, regex, tillar — bo'sh: hammasi)
    # Python SQL'i AST bilan tekshiriladi (analyze_python) — bu yerda faqat JS/TS/Dart satr birlashtirish
    ("sql-injection", "high", "SQL so'rov matn birlashtirish bilan tuzilgan (SQL injection xavfi)",
     R(r"""(?i)["'][^"']*\b(?:select\s.+\sfrom|insert\s+into|update\s+\w+\s+set|delete\s+from)\b[^"']*["']\s*\+\s*[a-z_]"""),
     ("javascript", "typescript", "dart")),
    ("sql-injection", "high", "SQL so'rov Sprintf bilan tuzilgan (SQL injection xavfi)",
     R(r"""(?i)fmt\.Sprintf\(\s*["`][^"`]*\b(select|insert|update|delete)\b"""), ("go",)),
    ("sql-injection", "high", "SQL so'rov template string bilan tuzilgan (SQL injection xavfi)",
     R(r"""(?i)`[^`]*\b(select\s.+\sfrom|insert\s+into|update\s+\w+\s+set|delete\s+from)\b[^`]*\$\{"""), ("typescript", "javascript")),
    ("code-exec", "high", "eval/exec — tashqi ma'lumot bilan kod bajarilishi mumkin", R(r"(?<![\w.])(eval|exec)\s*\("), ("python", "javascript", "typescript")),
    ("shell", "high", "Shell buyrug'i (buyruq injection xavfi)", R(r"shell\s*=\s*True|os\.system\(|os\.popen\("), ("python",)),
    ("shell", "high", "Shell orqali buyruq bajarish", R(r"""exec\.Command\(\s*"(sh|bash|cmd)"|child_process|execSync\("""), ("go", "javascript", "typescript")),
    ("secret", "high", "Kod ichida yozilgan maxfiy qiymat (parol/kalit/token)",
     R(r"""(?i)\b(password|passwd|pwd|secret|secret_?key|client_?secret|api_?key|access_?token|auth_?token|refresh_?token|bot_?token|token|private_?key)\b["']?\s*[:=]\s*["'][^"'\s]{8,}["']"""), ()),
    ("tls-off", "high", "TLS sertifikat tekshiruvi o'chirilgan", R(r"InsecureSkipVerify:\s*true|verify\s*=\s*False|rejectUnauthorized:\s*false"), ()),
    ("deserialize", "medium", "Xavfli deserializatsiya (pickle / yaml.load)", R(r"pickle\.loads?\(|yaml\.load\((?![^)]*Loader)"), ("python",)),
    ("xss", "medium", "HTML to'g'ridan-to'g'ri qo'yilmoqda (XSS xavfi)", R(r"dangerouslySetInnerHTML|\.innerHTML\s*=|v-html=|\|\s*safe\b|mark_safe\("), ()),
    ("debug", "medium", "Debug rejimi yoqilgan", R(r"^\s*DEBUG\s*=\s*True"), ("python",)),
    ("cors", "medium", "CORS barcha manbalarga ochiq", R(r"""CORS_ALLOW_ALL_ORIGINS\s*=\s*True|Access-Control-Allow-Origin["']?\s*[,:]\s*["']\*|allow_origins\s*=\s*\[\s*["']\*"""), ()),
    ("swallow", "medium", "Xato jimgina yutib yuborilgan", R(r"except(\s+\w+(\s+as\s+\w+)?)?\s*:\s*pass\b|catch\s*\([^)]*\)\s*\{\s*\}|_\s*=\s*err\b"), ()),
    ("weak-crypto", "low", "md5/sha1 — fayl xeshi uchun normal, lekin parol/imzo uchun yaramaydi", R(r"(?i)\b(md5|sha1)\s*\(|hashlib\.(md5|sha1)|crypto/(md5|sha1)"), ()),
    ("todo", "low", "TODO/FIXME — tugallanmagan joy", R(r"(?://|#)\s*(TODO|FIXME|HACK|XXX)\b"), ()),
]


def stable_id(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:12]


# ============================================================ tahlil natijasi

class FileInfo:
    def __init__(self, path: str, lang: str, text: str):
        self.path, self.lang, self.text = path, lang, text
        self.lines = text.splitlines()
        self.functions: list[dict] = []   # {name, qual, kind, line, end, calls:set}
        self.imports: list[str] = []
        self.routes: list[dict] = []      # {method, path, handler, line}
        self.tables_defined: list[tuple[str, int]] = []
        self.tables_used: set[str] = set()
        self.url_literals: set[str] = set()
        self.risks: list[dict] = []

    def fn_at(self, line: int) -> dict | None:
        best = None
        for f in self.functions:
            if f["line"] <= line <= f["end"] and (best is None or f["line"] >= best["line"]):
                best = f
        return best


SQL_TABLE_USE = R(r"(?i)\b(?:from|join|into|update)\s+[\"`]?([a-z_][a-z0-9_]*)[\"`]?")
SQL_CREATE = R(r"(?i)create\s+table\s+(?:if\s+not\s+exists\s+)?[\"`]?(?:\w+\.)?([a-z_][a-z0-9_]*)")
URL_LIT = R(r"""["'`](/(?:api|v\d)[a-zA-Z0-9_\-/{}:$.]*|/[a-z][a-z0-9_\-]*(?:/[a-zA-Z0-9_\-{}:$.]+)+)["'`]""")
SQL_WORDS = {"select", "where", "set", "values", "the", "a", "an", "to", "and", "or", "on", "as", "if", "not", "exists",
             "lateral", "unnest", "jsonb_array_elements", "generate_series", "only", "this", "that", "with"}


def scan_sql_strings(fi: FileInfo) -> None:
    for m in SQL_CREATE.finditer(fi.text):
        fi.tables_defined.append((m.group(1).lower(), fi.text.count("\n", 0, m.start()) + 1))
    if fi.lang == "sql" or re.search(r"(?i)\b(select|insert|update|delete)\b[^\n]{0,200}\b(from|into|set)\b", fi.text):
        for m in SQL_TABLE_USE.finditer(fi.text):
            name = m.group(1).lower()
            if name not in SQL_WORDS and len(name) > 2:
                fi.tables_used.add(name)


# ------------------------------------------------------------ Python (ast)

def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


SQL_CALLS = {"execute", "executemany", "raw", "text", "exec_driver_sql", "executescript", "extra"}
_SQL_KW = R(r"(?i)\b(select|insert|update|delete|alter|drop|create|where)\b")


def _safe_part(e: ast.AST) -> bool:
    """Formatlangan satrdagi xavfsiz bo'lak: konstanta, KATTA_HARF nom, placeholder yasash (',',join('?' * n))."""
    if isinstance(e, ast.Constant):
        return True
    if isinstance(e, ast.Name):
        return e.id.isupper() or e.id.endswith(("_SQL", "_COLUMNS", "_TABLE"))
    if isinstance(e, ast.Attribute):
        return e.attr.isupper()
    if isinstance(e, ast.Call) and _call_name(e.func) == "join":
        return all(isinstance(x, ast.Constant) and str(x.value).strip() in ("?", "%s", ",", ", ") or isinstance(x, ast.Constant)
                   for a in e.args for x in ast.walk(a) if isinstance(x, ast.Constant)) and \
            any(isinstance(x, ast.Constant) and str(x.value).strip() in ("?", "%s") for a in e.args for x in ast.walk(a))
    return False


def _unsafe_sql(arg: ast.AST) -> bool:
    if isinstance(arg, ast.JoinedStr):
        text = "".join(str(v.value) for v in arg.values if isinstance(v, ast.Constant))
        return bool(_SQL_KW.search(text)) and not all(_safe_part(v.value) for v in arg.values if isinstance(v, ast.FormattedValue))
    if isinstance(arg, ast.BinOp):
        leaves: list[ast.AST] = []
        stack = [arg]
        while stack:  # faqat + / % zanjirining bevosita operandlari
            x = stack.pop()
            if isinstance(x, ast.BinOp):
                stack += [x.left, x.right]
            else:
                leaves.append(x)
        consts = "".join(str(x.value) for x in leaves if isinstance(x, ast.Constant))
        return bool(_SQL_KW.search(consts)) and not all(_safe_part(x) for x in leaves if isinstance(x, (ast.Name, ast.Attribute, ast.Call)))
    if isinstance(arg, ast.Call) and _call_name(arg.func) == "format" and isinstance(arg.func, ast.Attribute) \
            and isinstance(arg.func.value, ast.Constant):
        return bool(_SQL_KW.search(str(arg.func.value.value))) and not all(_safe_part(a) for a in arg.args)
    return False


def analyze_python(fi: FileInfo) -> None:
    try:
        tree = ast.parse(fi.text)
    except SyntaxError:
        return

    def visit(node: ast.AST, prefix: str, in_class: bool) -> None:
        for ch in ast.iter_child_nodes(node):
            if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef)):
                calls = {n for c in ast.walk(ch) if isinstance(c, ast.Call) and (n := _call_name(c.func))}
                fi.functions.append({"name": ch.name, "qual": prefix + ch.name, "kind": "method" if in_class else "function",
                                     "line": ch.lineno, "end": ch.end_lineno or ch.lineno, "calls": calls})
                for dec in ch.decorator_list:  # @app.get("/x"), @router.post(...)
                    if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute) and dec.args \
                            and isinstance(dec.args[0], ast.Constant) and isinstance(dec.args[0].value, str) \
                            and dec.func.attr in ("get", "post", "put", "patch", "delete", "route", "api_route", "websocket"):
                        method = dec.func.attr.upper() if dec.func.attr not in ("route", "api_route") else "ANY"
                        fi.routes.append({"method": method, "path": dec.args[0].value, "handler": ch.name, "line": ch.lineno})
                visit(ch, prefix + ch.name + ".", False)
            elif isinstance(ch, ast.ClassDef):
                fi.functions.append({"name": ch.name, "qual": prefix + ch.name, "kind": "class",
                                     "line": ch.lineno, "end": ch.end_lineno or ch.lineno, "calls": set()})
                bases = {(_call_name(b) or "") for b in ch.bases}
                if any(b in ("Model", "Base", "DeclarativeBase", "SQLModel", "Document") for b in bases):
                    tname = ch.name.lower()
                    for st in ch.body:
                        if isinstance(st, ast.Assign) and any(getattr(t, "id", "") in ("__tablename__", "db_table") for t in st.targets) \
                                and isinstance(st.value, ast.Constant) and isinstance(st.value.value, str):
                            tname = st.value.value
                    fi.tables_defined.append((tname, ch.lineno))
                visit(ch, prefix + ch.name + ".", True)
            else:
                visit(ch, prefix, in_class)

    visit(tree, "", False)
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            fi.imports += [a.name for a in n.names]
        elif isinstance(n, ast.ImportFrom):
            base = "." * n.level + (n.module or "")
            fi.imports.append(base)
            if n.level and not n.module:
                fi.imports += ["." * n.level + a.name for a in n.names]
        elif isinstance(n, ast.Call):
            # Django: path("x/", view)
            if _call_name(n.func) in ("path", "re_path") and len(n.args) >= 2 and isinstance(n.args[0], ast.Constant) \
                    and isinstance(n.args[0].value, str):
                v = n.args[1]
                if isinstance(v, ast.Call) and isinstance(v.func, ast.Attribute) and v.func.attr == "as_view":
                    h = _call_name(v.func.value)  # LoginView.as_view() → LoginView
                else:
                    h = _call_name(v.func) if isinstance(v, ast.Call) else _call_name(v)
                if h and h != "include":
                    fi.routes.append({"method": "ANY", "path": "/" + n.args[0].value.lstrip("^").rstrip("$"),
                                      "handler": h, "line": n.lineno})
            # SQL injection: execute/raw/text(...) ga formatlangan satr
            if _call_name(n.func) in SQL_CALLS and n.args:
                arg = n.args[0]
                # execute(text(f"...")) — ichki text(...) o'zi alohida tekshiriladi, ikki marta yozilmasin
                if not (isinstance(arg, ast.Call) and _call_name(arg.func) == "text") and _unsafe_sql(arg):
                    sev = "low" if "migrations/" in fi.path else "high"
                    fi.risks.append(_risk(fi, "sql-injection", sev,
                                          "SQL so'rov formatlangan satr bilan tuzilgan — qiymatlar parametr sifatida berilishi kerak (SQL injection xavfi)",
                                          n.lineno))
        elif isinstance(n, ast.ExceptHandler) and n.type is None:
            fi.risks.append(_risk(fi, "bare-except", "medium", "`except:` barcha xatolarni (hatto KeyboardInterrupt) ushlaydi", n.lineno))


# ------------------------------------------------------------ qavsli tillar (regex)

def _block_end(lines: list[str], start: int) -> int:
    """`{` bilan boshlangan blok tugaydigan qator (0-index). Satr va izohlarni taxminan hisobga oladi."""
    depth, opened = 0, False
    quote = None
    for i in range(start, min(len(lines), start + 2000)):
        line = lines[i]
        j = 0
        while j < len(line):
            c = line[j]
            if quote:
                if c == "\\":
                    j += 2
                    continue
                if c == quote:
                    quote = None
            elif c in "\"'`":
                quote = c
            elif c == "/" and line[j:j + 2] == "//":
                break
            elif c == "{":
                depth += 1
                opened = True
            elif c == "}":
                depth -= 1
                if opened and depth <= 0:
                    return i
            j += 1
        if quote in ("'", '"'):
            quote = None  # bir qatorli satrlar
        if not opened and i > start + 3:
            return start
    return start


GO_FUNC = R(r"^func\s+(?:\(\s*\w*\s*\*?\s*(\w+)(?:\[[^\]]*\])?\s*\)\s*)?(\w+)\s*[\[(]")
GO_TYPE = R(r"^type\s+(\w+)\s+(struct|interface)\b")
GO_ROUTE = [R(r"""\.(?:HandleFunc|Handle)\(\s*"(?:(GET|POST|PUT|PATCH|DELETE)\s+)?(/[^"]*)"\s*,\s*([\w.]+)"""),
            R(r"""\.(Get|Post|Put|Patch|Delete|GET|POST|PUT|PATCH|DELETE)\(\s*"(/[^"]*)"\s*,\s*(?:[\w.]+\s*,\s*)*([\w.]+)\s*\)""")]
TS_FUNC = [R(r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s*\*?\s*(\w+)\s*[(<]"),
           R(r"^\s*(?:export\s+)?(?:const|let|var)\s+(\w+)\s*(?::[^=]+)?=\s*(?:async\s+)?(?:\([^)]*\)|\w+)\s*(?::[^=]+)?=>"),
           R(r"^\s*(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?function\b")]
TS_CLASS = R(r"^\s*(?:export\s+)?(?:default\s+)?(?:abstract\s+)?class\s+(\w+)")
TS_METHOD = R(r"^\s+(?:public\s+|private\s+|protected\s+|static\s+|async\s+|readonly\s+)*(\w+)\s*(?:<[^>]*>)?\([^)]*\)\s*(?::\s*[^{]+)?\{\s*$")
TS_ROUTE = R(r"""\b(?:app|router|server|api)\.(get|post|put|patch|delete|all)\(\s*["'`](/[^"'`]*)["'`]\s*,\s*(?:[\w.]+\s*,\s*)*([\w.]+)?""")
DART_CLASS = R(r"^\s*(?:abstract\s+)?(?:class|mixin|enum|extension)\s+(\w+)")
DART_FUNC = R(r"^\s*(?:static\s+|external\s+|@override\s+)*(?:[\w<>?,\[\]\s]+?\s+)?(\w+)\s*\([^;{}]*\)\s*(?:async\*?\s*|sync\*\s*)?\{")
KEYWORDS = {"if", "for", "while", "switch", "catch", "return", "function", "else", "do", "try", "with", "new", "await", "super", "this"}


def analyze_braces(fi: FileInfo) -> None:
    L = fi.lines
    cls_stack: list[tuple[str, int]] = []
    for i, line in enumerate(L):
        while cls_stack and i > cls_stack[-1][1]:
            cls_stack.pop()
        name = kind = recv = None
        if fi.lang == "go":
            if m := GO_FUNC.match(line):
                recv, name = m.group(1), m.group(2)
                kind = "method" if recv else "function"
            elif m := GO_TYPE.match(line):
                name, kind = m.group(1), m.group(2)
        elif fi.lang in ("typescript", "javascript"):
            if m := TS_CLASS.match(line):
                name, kind = m.group(1), "class"
            else:
                for p in TS_FUNC:
                    if m := p.match(line):
                        name, kind = m.group(1), "function"
                        break
                if name is None and cls_stack and (m := TS_METHOD.match(line)) and m.group(1) not in KEYWORDS:
                    name, kind = m.group(1), "method"
            if kind == "function" and name and name[0].isupper() and fi.path.endswith((".tsx", ".jsx")):
                kind = "component"
        elif fi.lang == "dart":
            if m := DART_CLASS.match(line):
                name, kind = m.group(1), "class"
            elif (m := DART_FUNC.match(line)) and m.group(1) not in KEYWORDS:
                name, kind = m.group(1), "method" if cls_stack else "function"
        if not name:
            continue
        end = _block_end(L, i)
        qual = f"{recv}.{name}" if recv else (f"{cls_stack[-1][0]}.{name}" if kind == "method" and cls_stack else name)
        body = "\n".join(L[i + 1:end + 1]) if end > i else ""
        calls = {c for c in re.findall(r"\b([A-Za-z_]\w*)\s*\(", body) if c not in KEYWORDS}
        fi.functions.append({"name": name, "qual": qual, "kind": kind, "line": i + 1, "end": end + 1, "calls": calls})
        if kind == "class":
            cls_stack.append((name, end))

    # importlar
    if fi.lang == "go":
        for m in re.finditer(r'import\s*\(([^)]*)\)|import\s+(?:\w+\s+)?"([^"]+)"', fi.text):
            fi.imports += re.findall(r'"([^"]+)"', m.group(1)) if m.group(1) else [m.group(2)]
        # chi: r.Route("/v1", func(r chi.Router) { ... }) — ichidagi marshrutlarga prefiks qo'shiladi
        prefixes: list[tuple[str, int]] = []
        depth = 0
        for i, line in enumerate(L):
            while prefixes and depth < prefixes[-1][1]:
                prefixes.pop()
            m_route = re.search(r"""\.Route\(\s*"(/[^"]*)"\s*,\s*func""", line)
            for p in GO_ROUTE:
                if m := p.search(line):
                    method = (m.group(1) or "ANY").upper()
                    prefix = "".join(x for x, _ in prefixes)
                    fi.routes.append({"method": method, "path": (prefix + m.group(2)).replace("//", "/") or "/",
                                      "handler": m.group(3), "line": i + 1})
                    break
            depth += line.count("{") - line.count("}")
            if m_route:
                prefixes.append((m_route.group(1).rstrip("/"), depth))
    elif fi.lang in ("typescript", "javascript"):
        fi.imports += re.findall(r"""(?:import\s[^'"]*?from\s*|import\s*\(\s*|require\(\s*)["']([^"']+)["']""", fi.text)
        for i, line in enumerate(L):
            if m := TS_ROUTE.search(line):
                fi.routes.append({"method": m.group(1).upper().replace("ALL", "ANY"), "path": m.group(2),
                                  "handler": m.group(3) or "", "line": i + 1})
        # Next.js: app/**/route.ts — eksport qilingan GET/POST
        if re.search(r"(^|/)app/(.+/)?route\.[jt]sx?$", fi.path):
            route = "/" + re.sub(r"(^|.*/)app/", "", posixpath.dirname(fi.path))
            route = re.sub(r"\[([^\]]+)\]", r"{\1}", re.sub(r"/\([^)]*\)", "", route))
            for m in re.finditer(r"export\s+(?:async\s+)?function\s+(GET|POST|PUT|PATCH|DELETE)\b", fi.text):
                fi.routes.append({"method": m.group(1), "path": route, "handler": m.group(1), "line": fi.text.count("\n", 0, m.start()) + 1})
        if m := re.search(r"(^|/)pages/(api/.+)\.[jt]sx?$", fi.path):
            fi.routes.append({"method": "ANY", "path": "/" + re.sub(r"/index$", "", m.group(2)), "handler": "default", "line": 1})
    elif fi.lang == "dart":
        fi.imports += re.findall(r"""import\s+["']([^"']+)["']""", fi.text)


COMMENT_LINE = R(r"^\s*(#|//|/\*|\*|--|<!--)")


def scan_line_risks(fi: FileInfo) -> None:
    for i, line in enumerate(fi.lines):
        if len(line) > 600:
            continue
        is_comment = bool(COMMENT_LINE.match(line))
        for kind, sev, title, pat, langs in LINE_RULES:
            if langs and fi.lang not in langs:
                continue
            if is_comment and kind != "todo":  # izohdagi so'z — kod emas
                continue
            if kind == "secret" and re.search(r"(?i)example|dummy|changeme|your[_-]|xxx|test|placeholder|<|\{\{|getenv|environ", line):
                continue
            if pat.search(line):
                fi.risks.append(_risk(fi, kind, sev, title, i + 1))
                break


def _risk(fi: FileInfo, kind: str, sev: str, title: str, line: int) -> dict:
    snippet = fi.lines[line - 1].strip()[:160] if 0 < line <= len(fi.lines) else ""
    if kind == "secret":  # qiymatni xaritaga ko'chirmaymiz
        snippet = re.sub(r"""(["'])[^"']{4,}(["'])""", r"\1***\2", snippet)
    return {"kind": kind, "severity": sev, "title": title, "file": fi.path, "line": line, "snippet": snippet}


# ============================================================ graf

def resolve_import(spec: str, fi: FileInfo, by_noext: dict[str, str], dir_set: set[str], py_mod: dict[str, list[str]]) -> list[str]:
    here = posixpath.dirname(fi.path)
    if fi.lang == "python":
        if spec.startswith("."):
            lvl = len(spec) - len(spec.lstrip("."))
            base = here
            for _ in range(lvl - 1):
                base = posixpath.dirname(base)
            rest = spec.lstrip(".").replace(".", "/")
            full = posixpath.join(base, rest) if rest else base
            hit = by_noext.get(full) or by_noext.get(full + "/__init__")
            return [hit] if hit else ([full] if full in dir_set else [])
        c = py_mod.get(spec, [])
        return c[:1] if len(c) == 1 else []
    if fi.lang in ("typescript", "javascript"):
        if spec.startswith("."):
            full = posixpath.normpath(posixpath.join(here, spec))
        elif spec.startswith(("@/", "~/")):
            full = spec[2:]
            for cand in (full, "src/" + full):
                if by_noext.get(cand) or by_noext.get(cand + "/index"):
                    full = cand
                    break
        else:
            return []
        hit = by_noext.get(full) or by_noext.get(full + "/index")
        return [hit] if hit else []
    if fi.lang == "go":
        parts = spec.split("/")
        for i in range(len(parts) - 1):
            suf = "/".join(parts[i:])
            ds = [d for d in dir_set if d == suf or d.endswith("/" + suf)]
            if len(ds) == 1:
                return [ds[0]]
        return []
    if fi.lang == "dart":
        s = spec.removesuffix(".dart")
        if s.startswith("package:"):
            rest = s.split("/", 1)[1] if "/" in s else ""
            for cand in ("lib/" + rest, rest):
                if cand in by_noext:
                    return [by_noext[cand]]
            return []
        if s.startswith("dart:"):
            return []
        full = posixpath.normpath(posixpath.join(here, s))
        return [by_noext[full]] if full in by_noext else []
    return []


# Bunday nomli chaqiruvlar boshqa fayldagi shu nomli funksiyaga bog'lanmaydi (ORM/kutubxona metodlari)
GENERIC_NAMES = set("""get set save delete update create list add remove run close open read write send post put patch
filter all first last items keys values append extend pop format join split strip copy clear init new len str int print
render dispatch handle process validate clean to_dict json execute fetch load dump dumps loads parse start stop call apply
map reduce sort find search count exists error string do next reset refresh build serialize is_valid perform_create
get_queryset get_object get_serializer get_context_data as_view setup teardown main handler then catch""".split())


def norm_route(p: str) -> str:
    p = re.sub(r"\{[^}]*\}|:\w+|<[^>]*>|\$\{[^}]*\}|\$\w+", "*", p.split("?")[0])
    return "/" + p.strip("/").lower()


def build(root: Path, files: list[str]) -> dict:
    infos: list[FileInfo] = []
    for p in files:
        try:
            text = (root / p).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if len(text) / max(1, text.count("\n") + 1) > 300:  # minified
            continue
        fi = FileInfo(p, LANGS[os.path.splitext(p)[1].lower()], text)
        if fi.lang == "python":
            analyze_python(fi)
        elif fi.lang in ("go", "typescript", "javascript", "dart"):
            analyze_braces(fi)
        scan_sql_strings(fi)
        if fi.lang != "sql":
            fi.url_literals = set(URL_LIT.findall(text))
            if not is_test(p):
                scan_line_risks(fi)
        infos.append(fi)

    by_path = {f.path: f for f in infos}
    by_noext = {f.path.rsplit(".", 1)[0]: f.path for f in infos}
    dir_set = {posixpath.dirname(f.path) for f in infos}
    py_mod: dict[str, list[str]] = defaultdict(list)
    for f in infos:
        if f.lang == "python":
            parts = f.path.rsplit(".", 1)[0].removesuffix("/__init__").split("/")
            for i in range(len(parts)):
                py_mod[".".join(parts[i:])].append(f.path)

    # ---- funksiyalar
    functions: list[dict] = []
    by_name: dict[str, list[dict]] = defaultdict(list)
    for f in infos:
        for fn in f.functions:
            rec = {"id": f"{f.path}:{fn['qual']}", "name": fn["name"], "qual": fn["qual"], "kind": fn["kind"],
                   "file": f.path, "line": fn["line"], "end": fn["end"], "lines": fn["end"] - fn["line"] + 1,
                   "module": module_of(f.path), "test": is_test(f.path), "_calls": fn["calls"], "calls": [], "fan_in": 0}
            functions.append(rec)
            if fn["kind"] != "class":
                by_name[fn["name"]].append(rec)

    def resolve(name: str, src: dict) -> dict | None:
        cands = by_name.get(name, [])
        if not cands:
            return None
        same_file = [c for c in cands if c["file"] == src["file"]]
        if name.lower() in GENERIC_NAMES:  # .save(), .get() — kutubxona metodi bo'lishi ehtimoli katta
            return same_file[0] if len(same_file) == 1 else None
        if len(cands) == 1:
            return cands[0]
        if len(same_file) == 1:
            return same_file[0]
        same_mod = [c for c in cands if c["module"] == src["module"]]
        return same_mod[0] if len(same_mod) == 1 else None

    mod_edges: Counter = Counter()
    for fn in functions:
        out = []
        for name in sorted(fn.pop("_calls")):
            dst = resolve(name, fn)
            if dst is not None and dst is not fn:
                out.append(dst["id"])
                if not fn["test"]:
                    dst["fan_in"] += 1
                if dst["module"] != fn["module"] and not fn["test"]:
                    mod_edges[(fn["module"], dst["module"], "calls")] += 1
        fn["calls"] = out

    # ---- importlar → modul bog'lanishlari
    for f in infos:
        if is_test(f.path):
            continue
        for spec in f.imports:
            for tgt in resolve_import(spec, f, by_noext, dir_set, py_mod):
                tm = tgt if tgt in dir_set and tgt not in by_path else module_of(tgt)
                if tm != module_of(f.path):
                    mod_edges[(module_of(f.path), tm, "imports")] += 1

    # ---- endpointlar
    all_by_name: dict[str, list[dict]] = defaultdict(list)  # handler klass ham bo'lishi mumkin (Django CBV)
    for fn in functions:
        all_by_name[fn["name"]].append(fn)

    def resolve_handler(expr: str, src: str) -> dict | None:
        parts = [p for p in re.split(r"[.]", expr) if p]
        if not parts:
            return None
        cands = all_by_name.get(parts[-1], [])
        if len(cands) <= 1:
            return cands[0] if cands else None
        same = [x for x in cands if x["file"] == src]
        if len(same) == 1:
            return same[0]
        if len(parts) >= 2:  # d.Hackathons.List → "hackathons" paketi / Hackathons tipi
            hint = parts[-2].lower()
            hits = [x for x in cands if hint in x["module"].lower().rsplit("/", 1)[-1]
                    or hint in x["qual"].lower() or hint in x["file"].lower().rsplit("/", 1)[-1]]
            if len(hits) == 1:
                return hits[0]
            hits = [x for x in hits if x["kind"] in ("method", "function")] or hits
            return hits[0] if hits and len({h["module"] for h in hits}) == 1 else None
        return None

    endpoints = []
    for f in infos:
        for r in f.routes:
            h = resolve_handler(r["handler"], f.path) if r["handler"] else None
            eid = f"endpoint:{r['method']} {r['path']}"
            endpoints.append({"id": eid, "method": r["method"], "path": r["path"], "file": f.path, "line": r["line"],
                              "module": module_of(f.path), "handler": h["id"] if h else None,
                              "handler_module": h["module"] if h else module_of(f.path)})
    seen = set()
    endpoints = [e for e in endpoints if not (e["id"] in seen or seen.add(e["id"]))]
    edges: list[dict] = []
    route_index = defaultdict(list)
    for e in endpoints:
        route_index[norm_route(e["path"])].append(e)
        edges.append({"from": e["id"], "to": e["handler_module"], "kind": "handles", "weight": 1})
    for f in infos:  # frontend → endpoint (URL satrlari bo'yicha)
        if is_test(f.path):
            continue
        for lit in f.url_literals:
            key = norm_route(lit)
            hits = route_index.get(key) or [e for k, es in route_index.items() if k.endswith(key) and key.count("/") >= 2 for e in es]
            for e in hits[:3]:
                if e["module"] != module_of(f.path) and e["handler_module"] != module_of(f.path):
                    edges.append({"from": module_of(f.path), "to": e["id"], "kind": "http", "weight": 1})

    # ---- jadvallar
    tables: dict[str, dict] = {}
    for f in infos:
        for name, line in f.tables_defined:
            tables.setdefault(name, {"id": f"table:{name}", "name": name, "defined_in": f"{f.path}:{line}", "used_by": set()})
    for f in infos:
        if is_test(f.path):
            continue
        for name in f.tables_used:
            if name in tables:
                tables[name]["used_by"].add(module_of(f.path))
    # ORM: model klassi aniqlangan modul va uni nom bilan ishlatgan modullar → jadval
    orm = {}  # klass nomi → jadval
    for f in infos:
        if f.lang == "python":
            for fn in f.functions:
                if fn["kind"] == "class":
                    for name, line in f.tables_defined:
                        if line == fn["line"]:
                            orm[fn["name"]] = name
    if orm:
        pat = R(r"\b(" + "|".join(map(re.escape, sorted(orm, key=len, reverse=True))) + r")\b")
        for f in infos:
            if f.lang != "python" or is_test(f.path) or "migrations/" in f.path:
                continue
            for m in set(pat.findall(f.text)):
                tables[orm[m]]["used_by"].add(module_of(f.path))
    for t in tables.values():
        for m in sorted(t["used_by"]):
            edges.append({"from": m, "to": t["id"], "kind": "db", "weight": 1})
        t["used_by"] = sorted(t["used_by"])

    for (a, b, kind), w in sorted(mod_edges.items()):
        edges.append({"from": a, "to": b, "kind": kind, "weight": w})
    # bir xil juftlik uchun calls + imports → bitta "calls" ustun
    merged: dict[tuple, dict] = {}
    for e in edges:
        k = (e["from"], e["to"], e["kind"])
        if k in merged:
            merged[k]["weight"] += e["weight"]
        else:
            merged[k] = dict(e)
    edges = list(merged.values())

    # ---- modullar
    mods: dict[str, dict] = {}
    for f in infos:
        m = mods.setdefault(module_of(f.path), {"id": module_of(f.path), "path": module_of(f.path), "files": [],
                                                 "lines": 0, "functions": 0, "langs": Counter(), "test_files": 0})
        m["files"].append(f.path)
        m["lines"] += len(f.lines)
        m["functions"] += sum(1 for x in f.functions if x["kind"] != "class")
        m["langs"][f.lang] += 1
        m["test_files"] += is_test(f.path)
    tested_names = set()
    for f in infos:
        if is_test(f.path):
            stem = re.sub(r"^test_|_test$|\.(test|spec)$", "", f.path.rsplit("/", 1)[-1].rsplit(".", 1)[0])
            tested_names.add(stem)
            for spec in f.imports:
                for tgt in resolve_import(spec, f, by_noext, dir_set, py_mod):
                    tested_names.add(tgt if tgt in dir_set else module_of(tgt))
    for m in mods.values():
        m["lang"] = m["langs"].most_common(1)[0][0]
        m["langs"] = dict(m["langs"])
        m["tests"] = m["test_files"] > 0 or m["id"] in tested_names or any(
            p.rsplit("/", 1)[-1].rsplit(".", 1)[0] in tested_names for p in m["files"])
        m["fan_in"] = len({e["from"] for e in edges if e["to"] == m["id"] and e["kind"] in ("calls", "imports")})
        m["fan_out"] = len({e["to"] for e in edges if e["from"] == m["id"] and e["kind"] in ("calls", "imports")})

    # ---- xavflar
    risks: list[dict] = []
    for f in infos:
        for r in f.risks:
            fn = f.fn_at(r["line"])
            r["function"] = fn["qual"] if fn else None
            r["module"] = module_of(f.path)
            r["source"] = "auto"
            r["id"] = stable_id(r["kind"], f.path, r["function"] or "", r["snippet"])
            risks.append(r)
    for fn in functions:
        if fn["test"] or fn["kind"] == "class":
            continue
        if fn["lines"] > LONG_FN:
            sev = "medium" if fn["lines"] > VERY_LONG_FN else "low"
            risks.append({"id": stable_id("long", fn["id"]), "kind": "long-function", "severity": sev,
                          "title": f"Juda uzun funksiya ({fn['lines']} qator) — tushunish va test qilish qiyin",
                          "file": fn["file"], "line": fn["line"], "function": fn["qual"], "module": fn["module"],
                          "snippet": "", "source": "auto"})
        if fn["fan_in"] >= HIGH_FAN_IN:
            risks.append({"id": stable_id("fanin", fn["id"]), "kind": "hotspot", "severity": "low",
                          "title": f"{fn['fan_in']} joydan chaqiriladi — o'zgartirish ko'p joyga ta'sir qiladi",
                          "file": fn["file"], "line": fn["line"], "function": fn["qual"], "module": fn["module"],
                          "snippet": "", "source": "auto"})
    for m in mods.values():
        if not m["tests"] and m["lines"] > 300 and m["test_files"] == 0 and not m["id"].split("/")[0] in ("tests", "test"):
            risks.append({"id": stable_id("notest", m["id"]), "kind": "no-tests", "severity": "low",
                          "title": f"Testlari topilmadi ({m['lines']} qator kod)", "file": m["files"][0], "line": 1,
                          "function": None, "module": m["id"], "snippet": "", "source": "auto"})
    # bir xil turdagi juda ko'p signal (masalan TODO) — xaritani bosmasin
    per_kind = Counter()
    pruned = []
    for r in sorted(risks, key=lambda r: ("high", "medium", "low").index(r["severity"])):
        per_kind[r["kind"]] += 1
        if r["kind"] in ("todo", "hotspot", "long-function") and per_kind[r["kind"]] > 40:
            continue
        pruned.append(r)

    for m in mods.values():
        m.pop("test_files", None)
    return {
        "modules": sorted(mods.values(), key=lambda m: m["id"]),
        "files": [{"path": f.path, "lang": f.lang, "lines": len(f.lines), "module": module_of(f.path), "test": is_test(f.path)} for f in infos],
        "functions": functions,
        "endpoints": endpoints,
        "tables": sorted(tables.values(), key=lambda t: t["name"]),
        "edges": edges,
        "risks": pruned,
    }


# ============================================================ Claude qatlami bilan birlashtirish

def load_notes(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"OGOHLANTIRISH: {path} o'qilmadi ({e}) — izohlarsiz davom etilmoqda", file=sys.stderr)
    return {}


def merge_notes(data: dict, notes: dict) -> None:
    comps = notes.get("components", [])
    for m in data["modules"]:
        m["description"] = notes.get("modules", {}).get(m["id"], "")
        m["component"] = next((c["id"] for c in comps if any(
            fnmatch.fnmatch(m["id"], g.rstrip("/")) or fnmatch.fnmatch(m["id"] + "/x", g) for g in c.get("paths", []))), None)
    fnotes = notes.get("functions", {})
    for fn in data["functions"]:
        if fn["id"] in fnotes:
            fn["description"] = fnotes[fn["id"]]
    data["components"] = comps
    reviews = notes.get("reviews", {})
    for r in notes.get("risks", []):
        r = dict(r)
        r.setdefault("severity", "medium")
        r.setdefault("kind", "claude")
        r["source"] = "claude"
        r.setdefault("module", module_of(r.get("file", "")))
        r.setdefault("id", stable_id("claude", r.get("file", ""), r.get("title", "")))
        data["risks"].append(r)
    for r in data["risks"]:
        rv = reviews.get(r["id"], {})
        r["status"] = rv.get("status", r.get("status", "open"))
        if rv.get("note"):
            r["note"] = rv["note"]
    data["unreviewed_high"] = [r["id"] for r in data["risks"]
                               if r["severity"] == "high" and r["source"] == "auto" and r["status"] == "open"]


def summarize(data: dict, root: Path) -> dict:
    active = [r for r in data["risks"] if r["status"] not in ("ok", "fixed")]
    sev = Counter(r["severity"] for r in active)
    return {
        "files": len(data["files"]),
        "lines": sum(f["lines"] for f in data["files"]),
        "modules": len(data["modules"]),
        "functions": sum(1 for f in data["functions"] if f["kind"] != "class"),
        "endpoints": len(data["endpoints"]),
        "tables": len(data["tables"]),
        "languages": dict(Counter(f["lang"] for f in data["files"]).most_common()),
        "risks": {"high": sev["high"], "medium": sev["medium"], "low": sev["low"]},
        "top_risks": [f"[{r['severity']}] {r['title']} — {r['file']}:{r['line']}" for r in
                      sorted(active, key=lambda r: ("high", "medium", "low").index(r["severity"]))[:10]],
    }


# ============================================================ HTML

def render_html(data: dict, out: Path) -> None:
    tpl = (Path(__file__).parent / "viewer.html").read_text(encoding="utf-8")
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = tpl.replace("__TITLE__", data["project"]["name"]).replace("/*__DATA__*/null", payload)
    out.write_text(html, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repo", nargs="?", default=".")
    ap.add_argument("--out", help="natija papkasi (standart: REPO/docs)")
    ap.add_argument("--render-only", action="store_true", help="faqat mavjud architecture.json + notes'dan HTML")
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    root = Path(args.repo).resolve()
    out = Path(args.out).resolve() if args.out else root / "docs"
    out.mkdir(parents=True, exist_ok=True)
    notes = load_notes(out / "architecture.notes.json")

    if args.render_only and (out / "architecture.json").exists():
        data = json.loads((out / "architecture.json").read_text(encoding="utf-8"))
        data["risks"] = [r for r in data["risks"] if r.get("source") == "auto"]
        for k in ("schema", "about", "project", "summary", "components", "unreviewed_high"):
            data.pop(k, None)  # qayta hisoblanadi
    else:
        data = build(root, list_files(root))
    merge_notes(data, notes)
    commit = (git(root, "rev-parse", "--short", "HEAD") or "").strip() or None
    data = {
        "schema": SCHEMA,
        "about": ABOUT,
        "project": {"name": notes.get("project", root.name), "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
                    "commit": commit},
        "summary": summarize(data, root),
        **data,
    }
    (out / "architecture.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    render_html(data, out / "ARCHITECTURE.html")
    s = data["summary"]
    print(f"✓ {out / 'architecture.json'}\n✓ {out / 'ARCHITECTURE.html'}")
    print(f"  {s['files']} fayl, {s['lines']} qator, {s['modules']} modul, {s['functions']} funksiya, "
          f"{s['endpoints']} endpoint, {s['tables']} jadval")
    print(f"  xavflar: {s['risks']['high']} yuqori, {s['risks']['medium']} o'rta, {s['risks']['low']} past"
          + (f" | ko'rib chiqilmagan yuqori: {len(data['unreviewed_high'])}" if data["unreviewed_high"] else ""))


if __name__ == "__main__":
    main()
