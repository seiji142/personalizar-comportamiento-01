# Comandos Personalizados

## Herramientas MCP (se invocan por nombre en el chat)

No son comandos slash: son tools del servidor MCP `brain-ai`, registradas como
`<server_name>_<tool_name>`. Se escriben en el chat del modelo.

### Memoria

| Tool | Descripción |
|------|-------------|
| `brain-ai_memory_search` | Buscar episodios, decisiones y conocimiento en memoria |
| `brain-ai_memory_save` | Guardar un episodio en memoria |
| `brain-ai_memory_consolidate` | Consolidar episodios en conocimiento semántico |

### Provenance

| Tool | Descripción |
|------|-------------|
| `brain-ai_resolver_referencia` | Resolver una referencia contra fuentes autorizadas |
| `brain-ai_describir_handle` | Ver metadatos de un handle |
| `brain-ai_ejecutar_accion` | Ejecutar una acción con efectos |

### Ejecución

| Tool | Descripción |
|------|-------------|
| `brain-ai_run_tests` | Ejecutar tests en background |
| `brain-ai_test_status` | Consultar el estado de un task de tests |
| `brain-ai_run_command` | Ejecutar un comando en background |
| `brain-ai_command_status` | Consultar el estado de un task de comando |

## Comandos slash custom

Este proyecto **no define comandos slash**. Crear uno requiere un archivo en
`.opencode/commands/<nombre>.md` o una sección `command` en `opencode.json`; ninguno
de los dos existe. Los built-in de OpenCode son `/init`, `/undo`, `/redo`, `/share`, `/help`.

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
