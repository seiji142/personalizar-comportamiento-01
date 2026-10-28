---
name: fx-git
description: Antes de cualquier operación git/GitHub decide qué herramienta usar y sus límites. Úsala siempre primero, sin excepción.
---

# fx-git — rutear operaciones git/GitHub

Toda operación git/GitHub pasa por esta tabla antes de ejecutarse. La
regla "MCP en vez de bash" falla cuando el agente no sabe qué usar: esta
skill cierra ese hueco en el momento de actuar.

## Pasos
1. **Clasifica la operación** en la tabla y usa la herramienta indicada.
   No ejecutes nada antes de clasificar.
2. **Si cae en excepción shell**, anota en tu respuesta por qué (1 línea):
   qué pide el MCP que no implementa. Sin justificación, no hay shell.
3. **Verifica después**: `ver_estado` tras push/commit y tras cambiar de rama, `ver_runs` tras
   PR/merge. Una op sin verificación no está terminada.
4. **Reporta**: qué se hizo, con qué tool, qué quedó sin cubrir.

| Operación | Herramienta |
|---|---|
| estado / diff / log / commit+push (sesión actual) | `git_*` MCP (el commit SIEMPRE por MCP; si el push falla por falta de upstream, solo ese `push -u` va por shell) |
| crear rama | `git_crear_rama` MCP (solo crear; borrar queda fuera, orden humana) |
| cambiar de rama | `git_cambiar_rama` MCP (conservador: rehúsa en seco si árbol sucio, sin -f/--merge, sin pull/fetch) |
| listar ramas (`branch -vv`) / stashes | `git_ver_ramas` / `git_stash_listar` MCP (lectura) |
| borrar worktree | `git_worktree_eliminar` MCP (evict + reintentos; rehúsa si sucio; `force` solo con OK humano) |
| runs de CI (`run list`) | `git_ver_runs` MCP (lectura; `gh api` queda puente si el MCP no alcanza) |
| PRs / merges | `gh-publish.ps1` (nunca `gh pr create/merge` directo) |
| lecturas API / permisos (`run view --log-failed`) | `gh api` |
| setup inicial, cross-repo, stash guardar/restaurar | shell (excepción sancionada, justificar) |
| cambios pendientes ajenos a tu rama | no mezclarlos: `stash` + reportar + restaurar al volver (único puente disponible) |
| ramas / protección / Pages / auth | manual humano (emitir checklist, no ejecutar) |

## Límites (lo que esta skill sabe)
- El MCP son 10 tools. Casi todas atadas al cwd de la sesión (sin
  parámetro de ruta): fuera de la sesión actual, shell+`workdir` es el
  único puente. Excepción: `git_worktree_eliminar(directory)` sí recibe
  la ruta del worktree a borrar.
- Token → API (`gh`); SSH → `git push`. Son capas distintas, no sustitutas.
- Prohibidos sin backup + confirmación explícita del humano:
  `push --force`, `reset --hard`, `clean -fd` y `git_worktree_eliminar`
  con `force=true` (borra cambios igual que `clean -fd`). Sin excepción.
- Nunca commitear a `main`; `main` solo vía PR desde `develop`.

## Reglas
- Genérica: sin rutas ni proyectos hardcodeados.
- Una op, una verificación: estado tras mutación, runs tras PR/merge.
- Nunca inventes capacidades: si la tool no existe, dilo y propone el
  puente (shell justificado o tarea manual) antes de actuar.
