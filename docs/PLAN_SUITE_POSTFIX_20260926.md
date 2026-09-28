# Plan — Suite completa post-fixes (valida 16A/16B/16C/16D)

**Fecha:** 2026-09-26 (ejecutada 28/09 12:34-13:35, 61.4 min, exit 1 gates) ·
  **Estado:** EJECUTADA — 4/4 fases (ver Resultados)
**Padre:** tarea 16 (cerrada) · **Predecesor:**
  `docs/PLAN_SUITE_COMPLETA_20260926.md` (6/6, 25/09)
**Objetivo:** medir con datos frescos el efecto de los fixes del 26/09
  y actualizar gates + análisis.

## Check de ejecución

- [x] Fase 0 — Precondiciones (28/09: git limpio, sin lock, plan commiteado
  afaf51d, ambas cuentas OK en sondeo)
- [x] Fase 1 — Suite completa async (28/09 12:34-13:35, 3686s, run_all rc=0)
- [x] Fase 2 — Gates: summary_nuevo OK · summary_ok ROJO (qwen advanced
  TIMEOUT 1200s) · api_disponible OK · avanzada_4x23 ROJO (gpt-oss bad=3,
  qwen bad=2) · estructura_4x5 ROJO (gpt-oss T4, big-pickle T1) · html OK
- [x] Fase 3 — Análisis post-fix: ver §Resultados
- [x] Fase 4 — Cierre (análisis/TAREAS/sesión actualizados, memoria)

## Resultados post-fix (28/09, datos reales)

**Fixes confirmados en vivo:**
- 16B: A4 big-pickle **PASS** ("Rechazo detectado", 56t).
- 16C: techo **funcionó en vivo** — gpt-oss D3 abortado:
  `[TIMEOUT] Tope de tokens por test superado (18501 >= 15000) round 4`.
- 16D/16F: mimo D8 **PASS** hoy (16.8k tokens) → flaky, no cuelgue estable.
- D9 gpt-oss **PASS** (cambió de FAIL) → conductual variable.

**Sin bloqueo TPD:** 0 BLOCKED_TPD, ambas cuentas OK — sin cuota gastada de más.

**Fallas nuevas/estables:**
- qwen advanced: proceso **killado a 1200s** (step timeout de
  `run_all_tests.py`) — D8 en reporte es valor viejo (27325, no re-ejecutado).
- gpt-oss D2: ERROR 400 `Tool choice is none, but model called a tool`
  (brain_ai_memory_save) — nuevo fallo de API.
- gpt-oss C2: FAIL estable (no declina).
- gpt-oss T4: FAIL keyword `qa` → 16E (sinónimo pendiente).
- big-pickle estructura T1: FAIL keyword `proyecto` (nuevo).
- qwen D2: ERROR upstream connect (red, transitorio probable).

**Falla de diseño de cuota:** ninguno. La suite cabía sin BLOCKED_TPD.

## Fase 0 — Precondiciones (sin API)

- `git status` limpio (verificado 26/09: OK), sin `tests/answers/.suite.lock`.
- `python tests/scripts/quota_probe.py` → confirmar ambas cuentas frescas
  (1 query mínima/cuenta). Si alguna bloqueada, NO lanzar la suite.

## Fase 1 — Suite completa (async, una sola instancia)

- `python scripts/suite_runner.py` vía herramienta async, timeout 5400
  (~30-60 min). El preflight hace backup previo a
  `docs/backup_YYYYMMDD_HHMMSS/`.
- Con los fixes adentro:
  - **16A:** `--fresh` con reemplazo al éxito (no borra previo).
  - **16B:** A1-A6 aceptan refusals en inglés.
  - **16C:** techo 15k tokens/test (D8-qwen debe cortar ~16.5k).
- Prohibido: foreground largo, instancias en paralelo,
  `Start-Process -NoNewWindow`.

## Fase 2 — Gates postflight

- Verificar en `tests/answers/suite_verification.json`: `summary_nuevo`,
  `summary_ok` (OK/BLOCKED_TPD pasan), `api_disponible`, `avanzada_4x23`,
  `estructura_4x5`, `html_nuevo`.
- Exit: 0 todo OK, 1 gate rojo, 2 lock, 3 preflight.

## Fase 3 — Análisis post-fix

- **A4 big-pickle:** debe PASS (16B verificado con dato real).
- **D8-qwen:** debe pasar de ERROR 27k a `[TIMEOUT]` ~16.5k (16C).
- **C2/D2/T4/D9 gpt-oss:** conductuales → FAIL esperado (gates rojos
  documentados, no arreglables desde el runner).
- **T4 estructura:** si falla solo por `qa` → aplicar sinónimo
  (item nuevo 16E) sin re-lanzar la suite.
- Actualizar `docs/tests/ANALISIS_FALLOS_20260926.md` si cambian estados.

## Fase 4 — Cierre

- Tabla de consumo TPD en `docs/tests/RESULTADOS_TEST_AI.md`.
- Sesión (`docs/tests/sesion_20260926.md` o agregado), checklist de
  TAREAS, memoria (`brain-ai_memory_save`), HTML regenerado si aplica.

## Riesgos avisados

- qwen día compartido (~225k > 200k): posible BLOCKED_TPD → manejado
  (corta, exit 7, nativos siguen; no rompe gates).
- gpt-oss ~115k cabe en día fresco.
- Gate rojo solo por `qa`: fix del sinónimo, nunca re-lanzar la suite
  entera.
