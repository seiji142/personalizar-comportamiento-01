"""CI mínimo de artefactos (docs-only): JSON válido + frontmatter de skills.

Uso: python scripts/ci_checks.py (cero dependencias, stdlib).
Falla (exit 1) con la lista de errores; verde = todo OK.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
errors = []


def check_opencode():
    try:
        d = json.loads((ROOT / "opencode.json").read_text(encoding="utf-8"))
    except Exception as e:
        errors.append(f"opencode.json inválido: {e}")
        return
    for key in ("model", "instructions"):
        if key not in d:
            errors.append(f"opencode.json sin clave: {key}")


def check_skills():
    front = re.compile(r"^---\n(.*?)\n---", re.S)
    skills = sorted((ROOT / ".agents" / "skills").glob("*/SKILL.md"))
    if not skills:
        errors.append(".agents/skills sin ningún SKILL.md")
    for f in skills:
        m = front.match(f.read_text(encoding="utf-8"))
        if not m:
            errors.append(f"{f.name}: sin frontmatter ---")
            continue
        for field in ("name:", "description:"):
            if field not in m.group(1):
                errors.append(f"{f.parent.name}: frontmatter sin {field}")


def check_docs_index():
    readme = ROOT / "docs" / "README.md"
    if not readme.exists():
        return  # proyecto sin índice docs: check no aplica
    for target in re.findall(r"\(`([^`]+)`\)", readme.read_text(encoding="utf-8")):
        if target.startswith("http"):
            continue
        if not (ROOT / target).exists():
            errors.append(f"docs/README.md enlaza inexistente: {target}")


REQUIRED_FRONTMATTER = (
    "titulo:",
    "estado:",
    "entradas:",
    "salidas:",
    "dependencias:",
    "criterio_aceptacion:",
)


def check_specs():
    front = re.compile(r"^---\n(.*?)\n---", re.S)
    specs_dir = ROOT / "docs" / "specs"
    if not specs_dir.exists():
        return  # proyecto sin specs: check no aplica
    for f in sorted(specs_dir.glob("*.md")):
        if f.name == "PLANTILLA.md":
            continue
        m = front.match(f.read_text(encoding="utf-8"))
        if not m:
            errors.append(f"spec {f.name}: sin frontmatter ---")
            continue
        for field in REQUIRED_FRONTMATTER:
            if field not in m.group(1):
                errors.append(f"spec {f.name}: frontmatter sin {field}")


check_opencode()
check_skills()
check_docs_index()
check_specs()

if errors:
    print("CI ROJO:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
print("CI VERDE: opencode.json + skills + índice docs OK")
