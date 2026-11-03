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

## Worktrees (una rama por sesión)

Un checkout tiene **un solo `HEAD`**: si una sesión se cambia a `feature/x`,
la otra commitea sobre esa rama sin enterarse. Por eso toda feature va en un
worktree, que trae carpeta, rama y `HEAD` propios.

- **La carpeta principal vive en `develop`.** No se checkoutea una
  `feature/*` ahí, nunca.
- **Toda `feature/*` se trabaja en un worktree**, y el orden importa:
  1. `worktree_create` (MCP opencode). Nace *detached*: todavía no tiene rama.
  2. `session_move` (MCP opencode) a la carpeta que devolvió. **La sesión se
     muda ahí.** Saltear este paso deja la sesión en la carpeta compartida:
     el `git -C` commitea en la rama correcta mientras las rutas relativas,
     los permisos y `grep`/`glob` siguen apuntando a `develop`.
  3. `git_crear_rama` (MCP git_publisher) ya desde adentro: crea la rama **y**
     posiciona. Desde la carpeta principal ese mismo tool es el que roba el
     `HEAD` de la otra sesión; desde el worktree no toca a nadie.
- **La ruta no se escribe acá**: la resuelve la config global
  (`worktree.directory`). Una ruta hardcodeada se rompe en silencio al mudar
  de máquina.
- **Una tarea por worktree**, una sola rama.
- Trabajos independientes sobre `develop` no necesitan worktree: van en la
  carpeta principal, que ya está en `develop`.

Guard de rama (ver `.ai/rules.md` §10): al empezar, declarar
`git rev-parse --show-toplevel` y `git branch --show-current`; en la carpeta
principal, `git_ver_estado` antes de **cada** commit.

Al cerrar la tarea, el worktree se borra con `git_worktree_eliminar`
(MCP git_publisher): rehúsa por defecto (árbol sucio / carpeta no vacía) y
`force` solo con OK humano. No borrar a mano con `Remove-Item`/`rm`.

**Antes** de borrar, la sesión vuelve a la carpeta principal con
`session_move`. Si no, su cwd vive dentro del worktree y el borrado en Windows
choca con un proceso vivo: la propia tool lo documenta (hace evict de los
hijos que tienen cwd adentro). El orden es: merge → `session_move` → borrar.

## Clasificacion del cambio: ODD por defecto, SDD cuando se dispara

Todo cambio autorizado se clasifica ANTES de escribir codigo. Por defecto va
en modo ODD: la evidencia vive en el commit. La spec
(`docs/specs/<tema>.md`) se escribe solo cuando se dispara. No hay tercera via.

### Prueba de reanudacion (decide; el tamano no)

ODD es el default cuando se cumplen las tres:
1. **Entendido**: no queda ninguna decision de producto abierta.
2. **Riesgo contenido**: no toca ningun escalador duro.
3. **Reanudable**: enumera las decisiones abiertas. Si alguna no se resuelve
   con el pedido o con `git diff` (incluida cualquier convencion que tengas
   que suponer), entonces el cambio no es reanudable.

### Disparador de SDD (dos clausulas, ambas verificables)

El cambio pasa a modo SDD -spec completo, y FICHA si hay entregable- cuando:
1. **Toca un escalador duro** de la lista de abajo, aunque sea una linea; o
2. **Falla alguna** de las tres preguntas de reanudacion.

Ninguna otra cosa dispara SDD: ni el tamano, ni la cantidad de archivos, ni
la sensacion de que el cambio "parece grande".

El conteo de archivos, lineas, tests o tareas NUNCA decide: un cambio de
una linea en auth es SDD; uno de 20 en un README puede ser ODD.

Al partir trabajo para un subagente, la unidad sugerida ronda las 400
lineas: con "cuatro ladrillos" no intenta una torre, hace una casita. Es un
freno a la sobreingenieria, no un limite de calidad ni un gate: una tarea
mas grande no falla el PR, solo se divide.

### Escaladores duros (siempre SDD)

Seguridad/auth, datos o migraciones, contratos de API que otros consumen,
dependencias nuevas, CI/workflows, crypto, permisos de `opencode.json`,
reglas y roles (`.ai/system.md`, `.ai/rules.md`, `.ai/commands.md`,
`.ai/agents.md`) o skills (`.agents/skills/`), operaciones irreversibles,
y `scripts/`.

La lista se cierra con su borde negativo: un escalador **cuenta cuando el
cambio lo modifica**. Si el pedido solo lo **menciona** -preguntar que dice
`.ai/commands.md`, reportar un bug del `ci.yml`, citar un skill para explicar
otra cosa- no es SDD: no hay nada del escalador que cambie. Mover o renombrar
si es SDD: rompe a sus lectores aunque su contenido no cambie.

### Que entrega cada modo

| | SDD | ODD |
|---|---|---|
| Documento | spec + FICHA | ninguno |
| Evidencia | §6, §7 y §8 del spec | commit + resultado observado en el chat |
| Verificacion pre-PR | obligatoria | obligatoria (identica) |
| Auditoria, si el proyecto la define | segun sus disparadores | segun sus disparadores |

La auditoria corre en un **proceso aparte** (rol 3 de `.ai/agents.md`): un
auditor que hereda el contexto del implementador revisa su propia version del
problema. Mientras no exista un agente auditor propio, el aislamiento minimo
es `opencode run --standalone` o una sesion nueva del humano, sin pegarle esta
conversacion.

En ODD la evidencia vive en el commit: asunto en imperativo y en el cuerpo
`ODD: <por que> / <que se observo>`. Sin esa linea no es ODD: es un cambio
sin evidencia.

### Prohibido

- Usar ODD para saltarse el criterio de aceptacion explicito del usuario.
- Declarar ODD despues de implementar para justificar la falta de spec.
- Partir un cambio SDD en varios ODD para esquivar el spec.

## Validacion pre-PR (obligatoria, bloqueante)

NINGUN PR se abre sin completar la checklist de su variante, sin excepciones
por "cambio chico". Este es codigo no visual → **Variante B**.

### Variante B — codigo no visual (scripts, tests, tooling)

1. [ ] Tests offline en verde en local:
   `python -m pytest tests/unit -q`,
   `python tests/scripts/test_validators.py`,
   `python tests/scripts/test_rate_limit_tpd.py`
   1b. [ ] Si el cambio toca dependencias: instalación limpia +
   suite verde (el "verde local" con entorno heredado es falso verde).
   1c. [ ] Si el producto corre en otro SO/entorno: pruebas allí (el
   verde en el SO del agente no transfiere).
2. [ ] Lint/typecheck: **N/A por ahora** (ruff en requirements pero sin
   verificación local; agregarlo al gate y al CI cuando se adopte).
3. [ ] Suites con API/MCP (`suite_runner.py`, `quota_probe.py`) NO corren en CI;
   si el cambio las toca, corrida local + evidencia en el PR.
4. [ ] Criterio de aceptacion EXPLICITO del usuario en el chat.
   Sin ese mensaje, NO hay PR.
   Cuenta: una frase sobre el CAMBIO ("el endpoint devuelve 200", "el
   typo ya no esta", "el kit quedo integrado").
   No cuenta: la orden de publicar ("abre el PR", "mergea", "subilo"):
   autoriza la accion, no acepta el resultado.

### Cierre

5. [ ] Tras cada fix: repetir pruebas afectadas + auditoría si toca sus
   disparadores (ver `.ai/agents.md` rol 3). Un fix sin re-verificación
   no existe.
6. [ ] Abrir el PR via `scripts/gh-publish.ps1` (SIN `-Merge` todavia).
7. [ ] CI en verde en el PR (obligatorio; `main` lo exige por proteccion).
8. [ ] Recien entonces: merge via script (`-Merge`) -> verificar merge ->
   changelog + replan documentado.

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
