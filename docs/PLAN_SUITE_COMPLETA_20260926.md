# Plan — Suite completa vía suite_runner + residuales tarea 15

**Fecha:** 2026-09-25 (archivo creado como 20260926 por error, ejecución 25/09
  16:08-16:43) · **Estado:** EJECUTADA — 6/6 fases (tarea 16 abierta)
**Padre:** `docs/TAREAS_PENDIENTES.md` → residuales tarea 15
**Referencias:** `docs/PLAN_TPD_429.md` §Historial y §Ejecución ·
  `docs/tests/sesion_20260925.md` §Pendientes residuales
**Sondeo previo 16:08:** ambas cuentas `OK`
  (`tests/answers/quota_status.json`) — ventana fresca, `Used` diario
  no visible; cuenta 1 con ~28 tests ya gastados hoy (riesgo TPD alto,
  gestionado por diseño con `BLOCKED_TPD`).

## Check de ejecución

- [x] Fase 0 — Revisión obligatoria (sin API) — 25/09: historial OK,
  retry `MAX_RETRIES=3` existe en `tests/lib/model_runner.py:43`,
  protocolo `suite_runner.py:17-33` confirmado, sin lock
  (`tests/answers/.suite.lock` ausente), reportes previos 25/09 intactos.
- [x] Fase 1 — Preflight + sondeo — 25/09 16:08: ambas cuentas `OK`
  (`quota_status.json` 16:08:39), backup en `docs/backup_20260925_161304/`.
- [x] Fase 2 — Suite completa — 25/09 16:13:04-16:43:41, 1832.7s (~30.5 min,
  más rápido que lo estimado porque los cortes TPD acortan los runs API).
- [x] Fase 3 — Gates postflight — verificados contra
  `suite_verification.json` 16:43:41 (ver §Resultados abajo).
- [x] Fase 4 — Análisis residuales — ver §Resultados abajo.
- [x] Fase 5 — Cierre (sesión, consumo TPD, checklist, memoria) — 25/09:
  `sesion_20260925.md` §Alcance 16:08-16:43, tabla de consumo en
  `RESULTADOS_TEST_AI.md`, tarea 16 abierta en `TAREAS_PENDIENTES.md`,
  restore verificado en §Restauración.

## Resultados 25/09 16:43 (verificados contra archivos reales)

Gates: `summary_nuevo` OK · `summary_ok` OK · `api_disponible` OK ·
  `avanzada_4x23` ROJO · `estructura_4x5` ROJO · `html_nuevo` OK ·
  `all_ok=false`.
Summary: locales OK (pytest, validators 35, rate_limit 38) · estructura
  4/4 modelos OK · avanzada API 2/2 `BLOCKED_TPD` (exit 7) · avanzada
  nativos OK · HTML OK.

TPD medido (calibración): gpt-oss `Used 199181/200000` en D3 (reintento
  en 1709s) · qwen `Used 199320/200000` en A1 (1924s). Ver
  `docs/tests/RESULTADOS_TEST_AI.md` §Consumo para el modelo de costo
  por query derivado (~4k gpt-oss, ~8k qwen).

Residuales: C2 gpt-oss FAIL con reply VACÍA (evidencia débil, re-run con
  cuota pendiente) · D9 no ejecutado (corte en D3) · T4 gpt-oss FAIL con
  reply VACÍA (mismo caveat) · D8 qwen no ejecutado (corte en A1, backup
  conserva D8 ERROR max-tool-rounds).
Nuevos (candidatos tarea 16+): A4 big-pickle FAIL por refusal EN INGLÉS
  vs validador solo-español (flaky, ayer PASS) · D8 mimo TIMEOUT (ayer
  PASS 89.6s, flaky) · BUG `--fresh` + corte `BLOCKED_TPD` = pérdida
  silenciosa de casos previos (avanzada 23→17 gpt-oss, 23→1 qwen;
  recuperable desde `docs/backup_20260925_161304/`; el comentario
  `run_advanced_tests.py:141-142` es falso en ese camino).
- [ ] Fase 2 — Suite completa async (`python scripts/suite_runner.py`, timeout 5400)
- [ ] Fase 3 — Gates postflight (`suite_verification.json`)
- [ ] Fase 4 — Análisis residuales (C2/D9 gpt-oss, T4 `qa`, D8 qwen)
- [ ] Fase 5 — Cierre (sesión, consumo TPD, checklist, memoria)

## Estado de partida (verificado 2026-09-26, solo lectura)

- Tarea 15 cerrada 25/09: pasos 0-5 + fix de gates OK.
  Detalle en `docs/PLAN_TPD_429.md:98-160` y
  `docs/tests/sesion_20260925.md:1-100`.
- Residuales pendientes (comportamiento, no 429) en
  `docs/tests/sesion_20260925.md:94-100` y `docs/TAREAS_PENDIENTES.md:1-7`:
  - gpt-oss C2 (no declina fuera de alcance) y D9 (no menciona `context.md`)
  - gpt-oss estructura T4 keyword `qa`
  - qwen D8 ERROR max tool rounds (2 intentos, `MAX_TOOL_ITERATIONS=5`)
  - Falta correr suite completa vía `suite_runner.py` end-to-end
    (preflight verificado aislado 25/09 15:27, gates nuevos no
    verificados end-to-end).
- `tests/answers/quota_status.json:1-37` de 25/09 15:27 (ambas OK) —
  caducado para hoy, hay que re-sondear.
- `tests/answers/suite_verification.json:1-41` y `test_run_summary.json:1-59`
  del 23/09 con formato viejo de gates (sin `api_disponible`, sin
  `PASS/BLOCKED_TPD`) — quedarán obsoletos tras el run.

## Fase 0 — Revisión obligatoria (5 min, sin API)

- Leer `docs/PLAN_TPD_429.md:13-26` §Historial (retry 16/09 en
  `model_runner.py:288-319` existe — no reimplementar).
- Confirmar `scripts/suite_runner.py:17-33` protocolo: entrypoint único,
  lock `.suite.lock`, preflight, postflight gates.
- Verificar que no hay lock rancio en `tests/answers/.suite.lock` ni
  bridges huérfanos (lo hace el preflight solo).

## Fase 1 — Preflight + sondeo (automático en `suite_runner.py:152-238`)

- Mata `mcp_bridge.py` huérfanos, backup a `docs/backup_YYYYMMDD_HHMMSS/`,
  verifica `GROQ_CUENTA_1/2` presentes sin imprimir valores, corre
  `tests/scripts/quota_probe.py` → `tests/answers/quota_status.json`.
- Si sondeo falla → exit 3, no correr a ciegas. Si cuenta `BLOCKED_TPD` →
  `run_all_tests.py:155-179` la salta (summary `BLOCKED_TPD`, exit 7),
  corre solo disponibles. Esto es correcto, no es fallo.

## Fase 2 — Suite completa (50-65 min estimados, datos 23/09)

- Orden en `run_all_tests.py:129-258`: locales pytest +
  `test_validators.py` + `test_rate_limit_tpd.py` (38 tests) → API
  gpt-oss (~880s) + qwen (~948s) → nativos big-pickle (~463s) +
  mimo (~678s) → `generate_html_report.py`.
- Lanzar solo vía herramienta async, un comando, sin paralelo:
  `python scripts/suite_runner.py` con timeout 5400.
- Prohibido: foreground 90 min, N instancias en paralelo,
  `Start-Process -NoNewWindow` (`scripts/suite_runner.py:9-15`).

## Fase 3 — Gates postflight (`scripts/suite_runner.py:341-387`)

- Verificar `tests/answers/suite_verification.json`: `summary_nuevo`,
  `summary_ok` (OK/BLOCKED_TPD pasan), `api_disponible`, `avanzada_4x23`
  (4x23 estados `PASS/BLOCKED_TPD` vía `model_gate()` en
  `scripts/suite_runner.py:274-309`), `estructura_4x5` (4x5), `html_nuevo`.
- Exit 0 todo OK, 1 gate rojo, 2 lock, 3 preflight.

## Fase 4 — Análisis de residuales (tras gates, sin re-lanzar suite)

- Contrastar `advanced_validation_report.json` y `ai_validation_report.json`
  nuevos contra los 4 pendientes. Criterio: `BLOCKED_TPD` no rompe gate;
  `FAIL/ERROR/TIMEOUT` de comportamiento sí (decisión registrada 25/09).
- Diagnóstico dirigido por caso (runs selectivos `--only` solo si un
  residual cambió de estado):
  - C2 gpt-oss: revisar `expected_rejection` en
    `tests/questions/advanced_questions.json` vs respuesta real.
  - D9 gpt-oss: idem mención `context.md`.
  - T4 `qa`: sinónimo en `tests/lib/validation.py`
    (precedente tarea 14: `validation.py:94`).
  - D8 qwen: bucle de tools, ver `tool_calls` y `MAX_TOOL_ITERATIONS`.

## Fase 5 — Cierre

- Actualizar `docs/tests/sesion_20260925.md` (o nueva `sesion_20260926.md`),
  tabla de consumo TPD en `docs/tests/RESULTADOS_TEST_AI.md`, checklist en
  `docs/TAREAS_PENDIENTES.md`.
- Guardar episodio en memoria (decisión, evidencia, tags) y consolidar
  si aplica.

## Riesgos avisados

- Gasto de TPD de ambas cuentas en un día (200k/día c/u, ya se consumió
  reparación el 25/09); wall ~1h; si un gate falla se arregla esa pieza
  con `--only`, nunca relanzar la suite entera.

## Restauración post-suite (25/09, solo datos reales de corridas)

El bug `--fresh`+TPD dejó avanzada en 17/1. Restaurados solo los IDs ausentes
desde `docs/backup_20260925_161304/` (reparación real 15:24, mismo día):
gpt-oss D4, D5, D6, D7, D8, D9 + qwen A2-D9 (22) → conteo 23/23/23/23
verificado. Intactos de la corrida 16:43: C2/D2 FAIL y D3/A1 BLOCKED_TPD.
Restaurados (valores reales del backup, no inventos): D9 FAIL, D8-qwen ERROR,
resto PASS. Gates tras el restore: siguen rojos por fallos reales
(C2, D2, D9, D8-qwen, A4 big-pickle, D8-mimo) — sin gate-gaming.
Estado del plan: EJECUTADA, 6/6 fases. Tarea 16 abierta para el fix de código
y los re-runs de mañana con cuota fresca.
