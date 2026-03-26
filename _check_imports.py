"""Temporary script to check for undefined critical names in Python files."""

import ast
import os

skip_dirs = {
    ".venv",
    "node_modules",
    "__pycache__",
    ".git",
    "ml_models",
    "backups",
    "data",
    "static",
    "templates",
    "migrations",
    "QR_Kodlari",
    "xss",
    "docs",
    "initdb",
}

important_names = {"logger", "db", "text"}
results = []

for root, dirs, files in os.walk("."):
    dirs[:] = [d for d in dirs if d not in skip_dirs]
    for f in files:
        if not f.endswith(".py"):
            continue
        fpath = os.path.join(root, f)
        try:
            with open(fpath, "r", encoding="utf-8-sig", errors="ignore") as fh:
                source = fh.read()
            tree = ast.parse(source, fpath)
        except SyntaxError as e:
            results.append(f"SYNTAX: {fpath}:{e.lineno} - {e.msg}")
            continue

        defined = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    defined.add(alias.asname or alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.names:
                    for alias in node.names:
                        defined.add(alias.asname or alias.name)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                defined.add(node.name)
            elif isinstance(node, ast.ClassDef):
                defined.add(node.name)
            elif isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        defined.add(t.id)

        used = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in important_names:
                used.add(node.id)

        missing = used - defined
        for m in sorted(missing):
            results.append(f"UNDEFINED: {fpath} uses '{m}' without import/definition")

for r in sorted(set(results)):
    print(r)
if not results:
    print("All clear!")
