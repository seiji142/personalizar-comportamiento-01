# templates/issues — capa opcional: registro de issues

**No se copia sola.** Es la capa opcional del registro de issues: qué está roto,
cómo se reprodujo y cómo se cerró, con cierre **sólo humano** por frase literal.

## Qué copiar y a dónde

| De acá | Al proyecto | Nota |
|---|---|---|
| `scripts/issue_state.py` | `scripts/issue_state.py` | validador + generador del bloque (stdlib, sin dependencias) |
| `docs/issue/LISTA-ISSUES.md` | `docs/issue/LISTA-ISSUES.md` | registro vacío, ya con el bloque generado |
| `docs/metodologia-issues.md` | `docs/metodologia-issues.md` | la regla que el validador aplica |
| `.agents/skills/fx-issue/SKILL.md` | `.agents/skills/fx-issue/SKILL.md` | el disparador: hace que una tarea futura consulte el registro |
| `tests/test-issue-state.py` | `tests/test-issue-state.py` | 36 tests deterministas del validador, sin red |

Después de copiar:

1. `python scripts/issue_state.py --write` — deja el bloque generado en cero.
2. Agregar la fila de ruteo en `AGENTS.md`:
   `| Issues: qué está abierto y qué se arregló | docs/issue/LISTA-ISSUES.md | cuando la tarea pregunte "qué falta" o "qué está abierto" (skill fx-issue) |`
3. `python scripts/ci_checks.py` tiene que salir en 0. El hook es condicional:
   sin `docs/issue/LISTA-ISSUES.md` no aplica, así que el Núcleo queda verde
   aunque esta capa no se adopte.
4. `python tests/test-issue-state.py` → 36 OK.

## Qué adaptar

- `RUN_ID_RE` en `scripts/issue_state.py`: el formato de tus corridas medidas.
  Es el único punto atado a un proyecto.
- La fila de ruteo en `AGENTS.md`: el CI la exige cuando existe el registro.

## Qué NO trae

La migración de un registro existente ni las capturas: eso es trabajo del
proyecto que adopta la capa.
