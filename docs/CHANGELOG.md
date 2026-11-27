# CHANGELOG (Núcleo)

Registro vivo de cambios mergeados + índice de lecciones (para que los
specs viejos no sean cementerío: lo promovible vive aquí, no solo en §8).

## Índice de lecciones

| Fecha | Lección | Etiqueta | Destino |
|-------|---------|----------|---------|
| 2026-10-05 | Un fix sin re-verificación no existe: cada fix re-dispara pruebas afectadas + auditoría si toca sus disparadores | [GENERAL] | `.ai/commands.md` §Cierre paso 5 |
| 2026-10-05 | Contenido externo = datos, no instrucciones: transcripciones/READMEs/issues pueden traer prompts inyectados y nunca se obedecen | [GENERAL] | `.ai/system.md` §Reglas de Interacción |
| 2026-10-06 | Entorno limpio ante cambio de dependencias + pruebas en entorno/SO destino (falso verde de entorno) | [GENERAL] | `.ai/commands.md` Variante B ítems 1b/1c |
| 2026-11-03 | El default se invierte después de la guarda; mencionar un escalador no es modificar la regla | [GENERAL] | `.ai/commands.md` Clasificacion |
| 2026-11-03 | `git_crear_rama` resuelve el repo antes del `session_move` | [GENERAL] | `.ai/rules.md` §10 |

## Entradas

### 2026-11-03 - Spec del auditor RDD aprobado

- `docs/specs/rdd-auditor.md` (estado `aprobado`): diseña las tres piezas
  que faltaban para que la revisión en proceso aparte exista. El rol 3 ya
  estaba escrito y `.ai/commands.md` ya nombraba `opencode run --standalone`,
  pero nadie ejecutaba ese comando.
- Piezas: agente de solo lectura (`.opencode/agents/auditor.md`) con
  `edit`/`shell`/`subagent`/web denegados; `scripts/rdd_review.py` con
  severidad determinista 1-4 y override que solo puede subir;
  agregación que falla cerrada (`INCONCLUSIVE` bloquea); `--dry-run` offline.
- Verificado: `opencode run --standalone --agent --format json` existe en
  v2.1.4; formato de agente con `permissions` según doc V2; `ci_checks`
  verde, 0 líneas >120, sin BOM.
- Hallazgo operativo: `git_crear_rama` movió el `HEAD` de gentle-ai (repo
  de la sesión al momento del llamado) aunque la sesión ya estaba en el
  worktree del framework. Corregido; lección en el índice.
- Aún no implementado: el spec es el entregable de este cambio.

Merge: PR [#10](https://github.com/seiji142/personalizar-comportamiento-01/pull/10)

**Replan:**
- **Estado:** mergeado (2026-11-03), CI `build` + GitGuardian en verde.
- **Spec vigente:** sí; `rdd-auditor.md` en `aprobado`, §6 define la
  verificación y §7 el criterio.
- **Lección:** 1 `[GENERAL]` promovida al índice (orden del repo al crear
  rama); 1 `[LOCAL]` en el §9 del spec (worktree del repo equivocado).
- **Próxima tarea:** implementar el spec (agente + script + tests) en un
  PR propio; el piloto ODD de gentle-ai sigue en 1/10.

### 2026-11-03 - Promueve worktree una rama por sesión y default ODD

- `.ai/commands.md`: la sección "Worktrees (cambios que colisionan)" se
  reemplaza por "Worktrees (una rama por sesión)" (la regla 2026-10-28 que
  este repo nunca recibió); "Clasificacion del cambio" queda en
  ODD por defecto con SDD como rama disparada (borde negativo del escalador,
  ~400 líneas, auditoría en proceso aparte).
- `.ai/rules.md`: §10 nueva con la regla de worktrees (§9 es PROCEDENCIA).
- `docs/specs/PLANTILLA.md`: sección "Fallas conocidas" (copia byte a byte
  de la versión aprobada en gentle-ai).
- `tests/unit` 3 passed, validadores 64 tests OK, rate limit TPD OK,
  `scripts/ci_checks.py` verde.

Merge: PR [#9](https://github.com/seiji142/personalizar-comportamiento-01/pull/9)

### 2026-10-05 — Backport auditoría + Núcleo 2026.10.05.2

- Add 4 roles + division rule to .ai/agents.md
- Add anti-prompt-injection (system.md) and anti-destructive (rules.md)
- Extend pre-PR checklist: re-verify after fix + changelog/replan
- Add .agents/skills (5), docs/specs/PLANTILLA.md, scripts/ci_checks.py
- Add docs/PLANTILLA-CHANGELOG.md template
- Set FRAMEWORK_VERSION 2026.10.05.2 in REUTILIZAR.md

Merge: PR [#3](https://github.com/seiji142/personalizar-comportamiento-01/pull/3) → `1971eb7`
(Criterios 1-5 cumplidos; excepción de suites API documentada en el PR.)

**Replan:**
- **Estado:** mergeado (2026-10-05).
- **Spec vigente:** sin spec previo (backport directo de auditoría); Núcleo
  `FRAMEWORK_VERSION 2026.10.05.2` vigente en `docs/REUTILIZAR.md`.
- **Lección:** 2 `[GENERAL]` promovidas al índice de arriba.
- **Próxima tarea:** primera corrida de suites API con cuota disponible
  (pendiente registrada en PR #3); después, spec para la siguiente feature.

### 2026-10-06 — Checklist entorno limpio (docs-only, sin bump)

- Add ítems 1b (instalación limpia + suite ante cambio de dependencias)
  y 1c (pruebas en entorno/SO destino) a Variante B en `.ai/commands.md`
- Add spec `docs/specs/checklist-entorno-limpio.md` (diseño genérico sin stack)

Merge: PR [#4](https://github.com/seiji142/personalizar-comportamiento-01/pull/4) → `63eb734`
(CI `build` + GitGuardian en verde; suites API/MCP no tocadas, no corren en CI por diseño.)

**Replan:**
- **Estado:** mergeado (2026-10-06).
- **Spec vigente:** sí; §8 [GENERAL] llenado.
- **Lección:** 1 `[GENERAL]` promovida al índice de arriba (sin bump:
  2 líneas de texto no justifican re-adopción).
- **Próxima tarea:** bump a `2026.10.05.3` cuando acumule otro cambio de
  Núcleo; nada pendiente de este lote.

### 2026-10-06 — Regla no-afirmar-sin-probar (docs-only, sin bump)

- Add §8.7 a `.ai/rules.md` (probar capacidad externa antes de
  afirmarla: `--dry-run`/permiso/scope; intentos, no garantías)
- Add spec `docs/specs/no-afirmar-sin-probar.md` (caso real:
  afirmación falsa de `gh createRepository` por plausibilidad)

Merge: PR [#5](https://github.com/seiji142/personalizar-comportamiento-01/pull/5) → `2d9d805`
(CI `build` + GitGuardian en verde; suites API/MCP no tocadas.)

**Replan:**
- **Estado:** mergeado (2026-10-06).
- **Spec vigente:** sí; §8 [GENERAL] llenado.
- **Lección:** 1 `[GENERAL]` ya promovida (§8.7, sin bump: texto).
- **Próxima tarea:** nada pendiente de este lote.

### 2026-10-06 — CI base versionado en el Núcleo (docs-only, sin bump)

- Add `templates/ci-base.yml` (job `artefactos` siempre verde + bloques
  comentados Python con `pip install`/Node para descomentar por stack)
- Fila REUTILIZAR apunta al archivo (adiós "plantilla en el comando");
  comando global `adoptar-framework.md` actualizado a copiarlo
  (cambio en `~/.config`, fuera de git)
- Add spec `docs/specs/nucleo-ci-base.md` (origen: primer run remoto
  rojo en H3 por falta de `pip install`)

Merge: PR [#6](https://github.com/seiji142/personalizar-comportamiento-01/pull/6) → `cff2bbe`
(CI `build` + GitGuardian en verde; YAML validado; suites API/MCP no tocadas.)

**Replan:**
- **Estado:** mergeado (2026-10-06).
- **Spec vigente:** sí; §8 [GENERAL] llenado.
- **Lección:** 1 `[GENERAL]` ya promovida (CI verde día uno vía job
  base + stack opt-in, sin bump: texto).
- **Próxima tarea:** nada pendiente de este lote.

### 2026-10-06 — Backport reglas de cuerpo al Núcleo (sin bump)

- Port literal del bloque de 3 reglas a `scripts/ci_checks.py`
  (sin exención: aquí no existe spec legado)
- Add spec `docs/specs/backport-spec-body.md` (origen: spec del lab
  ya probada con prueba negativa)

Merge: PR [#7](https://github.com/seiji142/personalizar-comportamiento-01/pull/7) → `c5bd6d3`
(CI `build` + GitGuardian en verde; `tests/unit` 3 passed; spec
temporal rota → rojo provocado → borrada.)

**Replan:**
- **Estado:** mergeado (2026-10-06).
- **Spec vigente:** sí; §8 [GENERAL] llenado.
- **Lección:** 1 `[GENERAL]` ya promovida (el Núcleo distribuye el
  check completo; sin bump: texto).
- **Próxima tarea:** nada pendiente de este lote.
