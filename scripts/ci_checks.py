"""CI mínimo de artefactos (docs-only): JSON válido + frontmatter de skills.

Uso: python scripts/ci_checks.py (cero dependencias, stdlib).
Falla (exit 1) con la lista de errores; verde = todo OK.
"""
import importlib
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
        body = f.read_text(encoding="utf-8")[m.end():]
        for n in range(1, 9):
            if not re.search(rf"^## {n}\.", body, re.M):
                errors.append(f"spec {f.name}: falta sección ## {n}")
        estado = re.search(r"^estado:\s*(\S+)", m.group(1), re.M)
        if not estado or estado.group(1) not in (
            "borrador",
            "aprobado",
            "implementado",
        ):
            errors.append(f"spec {f.name}: estado inválido o ausente")
        elif estado.group(1) == "implementado" and re.search(
            r"^-(?: Fix aplicado(?:\s*\[.*\])?"
            r"|Qué sección de este spec cambia por el fix"
            r"|Test anti-regresión que lo cubre):\s*$",
            body,
            re.M,
        ):
            errors.append(f"spec {f.name}: §8 con placeholders vacíos")


def _issue_state():
    """La capa de issues es opcional: el modulo solo existe si se adopto."""
    module = ROOT / "scripts" / "issue_state.py"
    if not module.exists():
        return None
    sys.path.insert(0, str(module.parent))
    return importlib.import_module("issue_state")


def check_issue_registry():
    """El registro es la unica fuente de "que esta abierto". Las reglas viven en
    `scripts/issue_state.py`; aca solo se exige que el documento las cumpla."""
    st = _issue_state()
    if st is None:
        return  # proyecto sin la capa: no aplica
    issue_dir = ROOT / "docs" / "issue"
    file = issue_dir / st.REGISTRY
    if not file.exists():
        return
    reg = st.load(file)
    errors.extend(f"issue: {e}" for e in st.validate(reg, issue_dir))
    if st.current_block(reg.text) != st.render_block(reg):
        errors.append(
            "issue: el bloque generado no coincide; corre "
            "python scripts/issue_state.py --write"
        )


def check_issue_routing():
    """El registro solo sirve si alguien lo lee: la skill y el ruteo en AGENTS.md."""
    st = _issue_state()
    if st is None:
        return
    if not (ROOT / "docs" / "issue" / st.REGISTRY).exists():
        return
    skill = ROOT / ".agents" / "skills" / "fx-issue" / "SKILL.md"
    if not skill.exists():
        errors.append(".agents/skills/fx-issue/SKILL.md no existe")
    agents = ROOT / "AGENTS.md"
    if agents.exists() and "docs/issue/LISTA-ISSUES.md" not in agents.read_text(
        encoding="utf-8"
    ):
        errors.append("AGENTS.md no rutea a docs/issue/LISTA-ISSUES.md")


check_opencode()
check_skills()
check_docs_index()
check_specs()
check_issue_registry()
check_issue_routing()

if errors:
    print("CI ROJO:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
print("CI VERDE: opencode.json + skills + índice docs OK")
