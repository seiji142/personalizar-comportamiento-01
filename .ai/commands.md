# Comandos Personalizados

## Comandos Básicos

| Comando | Descripción |
|---------|-------------|
| `/deploy` | Desplegar a producción |
| `/test` | Ejecutar tests |
| `/lint` | Ejecutar linter |
| `/git-push` | Subir cambios a git |

## Comandos de Memoria

| Comando | Descripción |
|---------|-------------|
| `/memory-save` | Guardar episodio en memoria |
| `/memory-search` | Buscar en memoria |
| `/memory-consolidate` | Consolidar memoria |

## Comandos de Provenance

| Comando | Descripción |
|---------|-------------|
| `/resolve` | Resolver referencia |
| `/handle` | Ver metadatos de handle |
| `/action` | Ejecutar acción con efectos |

## Uso

Los comandos se ejecutan escribiéndolos en el chat del modelo.

## Validacion pre-PR (obligatoria, bloqueante)

NINGUN PR se abre sin completar la checklist de su variante, sin excepciones
por "cambio chico". Este es codigo no visual → **Variante B**.

### Variante B — codigo no visual (scripts, tests, tooling)

1. [ ] Tests offline en verde en local:
   `python -m pytest tests/unit -q`,
   `python tests/scripts/test_validators.py`,
   `python tests/scripts/test_rate_limit_tpd.py`
2. [ ] Lint/typecheck: **N/A por ahora** (ruff en requirements pero sin
   verificación local; agregarlo al gate y al CI cuando se adopte).
3. [ ] Suites con API/MCP (`suite_runner.py`, `quota_probe.py`) NO corren en CI;
   si el cambio las toca, corrida local + evidencia en el PR.
4. [ ] Criterio de aceptacion EXPLICITO del usuario en el chat.
   Sin ese mensaje, NO hay PR.

### Cierre

5. [ ] Abrir el PR via `scripts/gh-publish.ps1` (SIN `-Merge` todavia).
6. [ ] CI en verde en el PR (obligatorio; `main` lo exige por proteccion).
7. [ ] Recien entonces: merge via script (`-Merge`) -> verificar merge.

Regla: el riesgo percibido NUNCA saltea pasos. Lo que no tiene evidencia
(segun su variante + CI verde) se considera NO verificado.

## Publicacion (PRs y merges)

OBLIGATORIO: NUNCA uses `gh pr create` / `gh pr merge` directos.
Todo PR y merge pasa por `scripts/gh-publish.ps1` (ejecutar desde la raiz del repo).

| Tarea | Comando |
|-------|---------|
| PR + merge `feature/x` -> `develop` | `.\scripts\gh-publish.ps1 -Rama feature/x -Base develop -Merge` |
| PR + merge `develop` -> `main` | `.\scripts\gh-publish.ps1 -Merge` |
| Solo crear PR (sin mergear) | Mismo comando sin `-Merge` |

Fuente del flujo: `Proyecto AI/templates/gitflow-scaffold` (kit 2026.09.25).
