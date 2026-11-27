"""Estado del registro de issues: parseo, validación y bloque generado.

El registro es `docs/issue/LISTA-ISSUES.md`. Su forma y el porqué de cada campo
viven en `odd/tasks/issue-metodologia.md` (S1-S10) y en
`docs/plan/metodologia-issues.md`. Este script no decide nada: hace legible por
máquina lo que el documento ya dice, y falla cuando el documento se contradice.

Uso:
    python scripts/issue_state.py --check     # valida y compara el bloque
    python scripts/issue_state.py --write     # regenera el bloque
    python scripts/issue_state.py --inbox     # archivos sin triagear
    python scripts/issue_state.py --next-id   # próximo I-<n>

Cero dependencias (stdlib). Sale 0 si está todo bien, 1 si hay errores.
"""
import re
import sys
from pathlib import Path

ZONES = ("## Abiertos", "## En verificación", "## Cerrados", "## Descartados")
SECTION_ZONES = ("## Abiertos", "## En verificación")
ZONE_STATE = {"## Abiertos": "abierto", "## En verificación": "arreglado"}
STATES = ("abierto", "arreglado", "cerrado", "descartado")
REQUIRED = ("sev", "estado", "fecha", "repro", "evidencia", "test", "sha", "aceptado")
DASH = "—"
MARK_START = "<!-- generado:inicio -->"
MARK_END = "<!-- generado:fin -->"
REGISTRY = "LISTA-ISSUES.md"
INBOX_EXTS = (".md", ".txt", ".png")
ISSUE_RE = re.compile(r"^## (I-\d+[a-z]?)\s*[·—\-]\s*(.+)$")
FIELD_RE = re.compile(r"^([a-z_]+):[ \t]*(.*)$")
SEV_RE = re.compile(r"^P[0-3]$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ACCEPT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\s+[\"“].+[\"”]$")
RUN_ID_RE = re.compile(r"\b(?:ui|real)-\d{8}-\d{6}")
PNG_RE = re.compile(r"^I-(\d+[a-z]?)-\d+\.png$")


class Issue:
    """Un registro `## I-<n>` con sus campos y su cuerpo en prosa."""

    def __init__(self, iid, title, zone, fields, body):
        self.id = iid
        self.title = title
        self.zone = zone
        self.fields = fields
        self.body = body

    def get(self, name, default=""):
        return self.fields.get(name, default)

    @property
    def estado(self):
        return self.fields.get("estado", "")

    @property
    def number(self):
        m = re.match(r"I-(\d+)([a-z]?)$", self.id)
        return (int(m.group(1)), m.group(2))


class Registry:
    """El documento entero: zonas en orden, secciones, y las dos tablas."""

    def __init__(self, text):
        self.text = text
        self.zones = []
        self.issues = {}
        self.cerrados = []
        self.descartados = []

    def ids(self):
        """Todos los ids registrados, sin importar en qué zona vivan."""
        out = set(self.issues)
        out.update(row[0] for row in self.cerrados if row)
        out.update(row[0] for row in self.descartados if row)
        return out


def _table_rows(lines):
    """Filas de una tabla markdown, sin encabezado ni separador."""
    rows = []
    for line in lines:
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if all(set(c) <= set("-: ") for c in cells):
            continue
        if cells and cells[0].startswith("#"):
            continue
        rows.append(cells)
    return rows


def load(path):
    """Parsea el registro. No valida: eso es `validate`."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    reg = Registry(text)
    current = None
    heads = []
    for i, line in enumerate(lines):
        s = line.strip()
        if s in ZONES:
            reg.zones.append(s)
            current = s
            heads.append((i, "zone", s, None, current))
            continue
        m = ISSUE_RE.match(s)
        if m:
            heads.append((i, "issue", m.group(1), m.group(2).strip(), current))
    heads.append((len(lines), "end", None, None, None))
    for n in range(len(heads) - 1):
        start, kind, iid, title, zone = heads[n]
        end = heads[n + 1][0]
        if kind != "issue":
            continue
        fields = {}
        body_from = start + 1
        for i in range(start + 1, end):
            fm = FIELD_RE.match(lines[i])
            if not fm:
                break
            fields[fm.group(1)] = fm.group(2).strip()
            body_from = i + 1
        body = "\n".join(lines[body_from:end]).strip()
        reg.issues[iid] = Issue(iid, title, zone, fields, body)
    reg.cerrados = _rows_in_zone(lines, "## Cerrados")
    reg.descartados = _rows_in_zone(lines, "## Descartados")
    return reg


def _rows_in_zone(lines, zone):
    inside = False
    out = []
    for line in lines:
        s = line.strip()
        if s == zone:
            inside = True
            continue
        if inside and s in ZONES:
            break
        if inside:
            out.append(line)
    return _table_rows(out)


def counts(reg):
    """Conteo por estado: dos vienen de secciones, dos de las tablas."""
    c = {s: 0 for s in STATES}
    for issue in reg.issues.values():
        if issue.estado in c:
            c[issue.estado] += 1
    c["cerrado"] += len(reg.cerrados)
    c["descartado"] += len(reg.descartados)
    return c


def next_id(reg):
    """Máximo numérico + 1. El sufijo de letra (`I-20b`) no cambia el número."""
    nums = [int(re.match(r"I-(\d+)", i).group(1)) for i in reg.ids()]
    return max(nums) + 1 if nums else 1


def _sorted_issues(reg, estado):
    return sorted(
        (i for i in reg.issues.values() if i.estado == estado),
        key=lambda i: i.number,
    )


def _how_to_check(issue):
    """Con qué se comprueba: el test, o la corrida medida si no hay test aislado."""
    test = issue.get("test", DASH)
    if test != DASH:
        return test
    m = RUN_ID_RE.search(issue.get("repro", ""))
    return f"corrida {m.group(0)}" if m else DASH


def render_block(reg):
    """El bloque generado. Sólo cambia cuando cambia un estado."""
    c = counts(reg)
    total = sum(c.values())
    out = [MARK_START, "### Resumen", "", "| Estado | N |", "|---|---:|"]
    for state in STATES:
        out.append(f"| {state} | {c[state]} |")
    out.append(f"| **total** | {total} |")
    for state, zone, cols in (
        ("abierto", "Abiertos", ("#", "sev", "título")),
        ("arreglado", "En verificación", ("#", "sev", "prueba")),
    ):
        out += ["", f"### {zone}", "", "| " + " | ".join(cols) + " |",
                "|" + "---|" * len(cols)]
        for issue in _sorted_issues(reg, state):
            if state == "abierto":
                out.append(f"| {issue.id} | {issue.get('sev')} | {issue.title} |")
            else:
                out.append(f"| {issue.id} | {issue.get('sev')} | {_how_to_check(issue)} |")
    out += ["", MARK_END]
    return "\n".join(out)


def apply_block(text, block):
    """Reemplaza el bloque entre marcas; si no están, lo inserta antes de la 1ra zona."""
    start = text.find(MARK_START)
    if start != -1:
        end = text.find(MARK_END, start)
        if end == -1:
            raise ValueError(f"falta {MARK_END} en el registro")
        return text[:start] + block + text[end + len(MARK_END):]
    first = min((text.find(z) for z in ZONES if text.find(z) != -1), default=-1)
    if first == -1:
        raise ValueError("el registro no tiene ninguna de las cuatro zonas")
    return text[:first] + block + "\n\n" + text[first:]


def current_block(text):
    start = text.find(MARK_START)
    end = text.find(MARK_END, start) if start != -1 else -1
    if start == -1 or end == -1:
        return ""
    return text[start:end + len(MARK_END)]


def _pngs(issue_dir):
    return sorted(
        p for p in Path(issue_dir).rglob("*") if p.is_file() and p.suffix.lower() == ".png"
    )


def validate(reg, issue_dir):
    """Todas las reglas que hoy sostiene el CI. Devuelve la lista de errores."""
    errors = []
    issue_dir = Path(issue_dir)

    missing = [z for z in ZONES if z not in reg.zones]
    for z in missing:
        errors.append(f"falta la zona {z}")
    if not missing and reg.zones != list(ZONES):
        errors.append("zonas fuera de orden: " + " -> ".join(reg.zones))

    for line in reg.text.split("\n"):
        s = line.strip()
        if s.startswith("## I-") and not ISSUE_RE.match(s):
            errors.append(
                f"cabecera de issue ilegible: '{s[:60]}'"
                " (se espera '## I-<n> · título': sin el título el registro no se valida)"
            )

    for issue in reg.issues.values():
        errors += _validate_issue(issue)

    for row in reg.cerrados:
        if len(row) != 5:
            errors.append(f"fila de cerrado con {len(row)} columnas: {' | '.join(row)}")
            continue
        if not ACCEPT_RE.match(row[4]):
            errors.append(
                f"{row[0]}: un cerrado exige aceptado = fecha + frase entre comillas"
                f" (tiene '{row[4]}')"
            )

    for row in reg.descartados:
        if len(row) != 2 or not row[1] or row[1] == DASH:
            errors.append(f"{row[0]}: un descartado exige motivo")

    errors += _validate_images(reg, issue_dir)
    return errors


def _validate_issue(issue):
    errors = []
    who = issue.id
    for name in REQUIRED:
        if name not in issue.fields:
            errors.append(f"{who}: falta el campo {name}:")
    if "sev" in issue.fields and not SEV_RE.match(issue.get("sev")):
        errors.append(f"{who}: sev inválida '{issue.get('sev')}' (P0..P3)")
    if "fecha" in issue.fields and not DATE_RE.match(issue.get("fecha")):
        errors.append(f"{who}: fecha inválida '{issue.get('fecha')}'")
    if issue.estado and issue.estado not in ZONE_STATE.values():
        errors.append(f"{who}: estado inválido '{issue.estado}'")
    elif issue.zone in ZONE_STATE and issue.estado != ZONE_STATE[issue.zone]:
        errors.append(
            f"{who}: está en '{issue.zone}' pero su estado es '{issue.estado}'"
            f" (la zona manda: {ZONE_STATE[issue.zone]})"
        )
    if issue.estado == "abierto":
        for name in ("esperaba", "paso"):
            if issue.get(name, DASH) == DASH or not issue.get(name):
                errors.append(f"{who}: abierto sin {name} (qué veía vs qué esperaba)")
    if issue.estado == "arreglado":
        if issue.get("test", DASH) == DASH and not RUN_ID_RE.search(issue.get("repro", "")):
            errors.append(
                f"{who}: arreglado sin test ni corrida medida"
                " (test: <suite>#<caso> o repro: con el id ui-<ts> de la corrida)"
            )
        if issue.get("repro", DASH) == DASH:
            errors.append(f"{who}: arreglado sin repro (el humano no sabría cómo probarlo)")
    if issue.get("aceptado", DASH) != DASH:
        errors.append(
            f"{who}: aceptado no vive en una sección; va en la tabla de Cerrados"
        )
    return errors


def _validate_images(reg, issue_dir):
    errors = []
    known = reg.ids()
    per_issue = {}
    for png in _pngs(issue_dir):
        m = PNG_RE.match(png.name)
        if not m:
            errors.append(
                f"{png.name}: nombre inválido (se espera I-<n>-<N>.png; "
                "ver la decisión de alta en odd/tasks/issue-metodologia.md)"
            )
            continue
        iid = "I-" + m.group(1)
        if iid not in known:
            errors.append(f"{png.name}: no existe el registro {iid}")
        per_issue[iid] = per_issue.get(iid, 0) + 1
    for iid, n in sorted(per_issue.items()):
        if n > 3:
            errors.append(f"{iid}: {n} capturas (tope 3; si hace falta otra, son dos issues)")

    for issue in reg.issues.values():
        cited = issue.get("evidencia", DASH)
        if cited == DASH:
            continue
        for name in re.split(r"\s*[·,]\s*", cited):
            if name and not (issue_dir / name).exists():
                errors.append(f"{issue.id}: evidencia inexistente: {name}")
    return errors


def inbox(reg, issue_dir):
    """Archivos de la bandeja: los que ningún registro cita todavía.

    Sin depender de git: funciona con archivos commiteados o no. La cita se
    busca como texto en el registro completo; es suficiente porque los nombres
    del alta no llevan espacios (ver decisión de alta).
    """
    issue_dir = Path(issue_dir)
    out = []
    for f in sorted(issue_dir.rglob("*")):
        if not f.is_file() or f.suffix.lower() not in INBOX_EXTS:
            continue
        if f.name == REGISTRY:
            continue
        if f.name not in reg.text:
            out.append(str(f.relative_to(issue_dir)).replace("\\", "/"))
    return out


def run(argv, root=None):
    """Punto de entrada. `root` existe para que los tests apunten a una temporal."""
    root = Path(root) if root else Path(__file__).resolve().parent.parent
    issue_dir = root / "docs" / "issue"
    file = issue_dir / REGISTRY
    if not file.exists():
        print(f"ROJO: no existe {file}")
        return 1
    reg = load(file)
    mode = argv[0] if argv else "--check"

    if mode == "--next-id":
        print(next_id(reg))
        return 0
    if mode == "--inbox":
        items = inbox(reg, issue_dir)
        if not items:
            print("Bandeja vacía.")
            return 0
        print(f"Bandeja: {len(items)} archivo(s) sin triagear")
        for item in items:
            print(f"  - {item}")
        return 0

    errors = validate(reg, issue_dir)
    if errors:
        print("ROJO:")
        for e in errors:
            print(f"  - {e}")
        return 1

    block = render_block(reg)
    if mode == "--write":
        file.write_text(apply_block(reg.text, block), encoding="utf-8", newline="\n")
        print(f"OK: bloque regenerado ({sum(counts(reg).values())} registros)")
        return 0

    if current_block(reg.text) != block:
        print("ROJO:\n  - el bloque generado no coincide; corré --write y commiteá")
        return 1
    c = counts(reg)
    print(
        "OK: {abierto} abierto(s), {arreglado} en verificación, "
        "{cerrado} cerrado(s), {descartado} descartado(s)".format(**c)
    )
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(run(sys.argv[1:]))
