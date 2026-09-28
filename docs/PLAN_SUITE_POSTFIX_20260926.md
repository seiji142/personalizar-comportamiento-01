# Plan — Suite completa post-fixes (valida 16A/16B/16C/16D)

**Fecha:** 2026-09-26 · **Estado:** PENDIENTE (documentado, sin ejecutar)
**Padre:** tarea 16 (cerrada) · **Predecesor:**
  `docs/PLAN_SUITE_COMPLETA_20260926.md` (6/6, 25/09)
**Objetivo:** medir con datos frescos el efecto de los fixes del 26/09
  y actualizar gates + análisis.

## Check de ejecución

- [ ] Fase 0 — Precondiciones (git limpio, sin lock, sondeo de cuota)
- [ ] Fase 1 — Suite completa async (`suite_runner.py`, timeout 5400)
- [ ] Fase 2 — Gates postflight (`suite_verification.json`)
- [ ] Fase 3 — Análisis post-fix (esperado vs posible por test)
- [ ] Fase 4 — Cierre (análisis, tabla TPD, sesión, checklist, memoria)

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
