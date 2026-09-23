# Subplan: Run instrumentado unificado

**Padre:** `docs/TAREAS_PENDIENTES.md` → tareas 6, 9, 10 (y opcional 7)
**Creado:** 23/09/2026 · **Estado:** PLAN (no ejecutado)

> Este documento NO es una tarea nueva: es el plan de ejecución COMPARTIDO
> de las tareas 6, 9 y 10 (y opcionalmente 7) de la lista principal.
> Al terminar, las sub-tareas correspondientes se marcan [x] en
> TAREAS_PENDIENTES.md; este archivo queda como registro del cómo.

## Tareas padre que cubre

| ID en TAREAS_PENDIENTES | Título | Cubierta por fases |
|---|---|---|
| 6 | mimo — Timeout en C2 y D8 | Fase 1 (run C2/D8) + 2 + 3 |
| 9 | mimo T3 flaky — keywords intermitentes | Fase 1 (×3 estructura) + 2 + 3 |
| 10 | mimo timeout advanced >1200s | Fase 0 (medición) + 2 + 3 |
| 7 (opcional) | gpt-oss-20b — excluido por timeout | Fase 1 extendida + 2 (429) |

## Contexto verificado (23/09)

- La suite avanzada YA guarda `time_seconds` por test (`run_advanced_tests.py:115`).
- Falta instrumentación en `test_ai_structure.py` (sin `time_seconds`).
- Evidencia previa: mimo advanced murió a los 1200s (`test_run_summary.json`);
  faltan D8/D9 en el reporte actual. C2 de mimo PASS 54s (timeout histórico
  puede estar vencido → re-medir, no asumir).
- T3 = id 3 de `ai_structure_questions.json` (expected_contains: stack, react,
  typescript, fastapi, postgresql) → flakiness por keywords faltantes.
- gpt-oss excluido en `run_all_tests.py:115`; evidencia histórica 429 TPD=200000.

## Fase 0 — Instrumentación mínima (~10 min)

1. Agregar `time_seconds` en `test_ai_structure.py` (wrapper en `run_test`).
2. Script `scripts/analyze_times.py`: lee `advanced_validation_report.json` +
   `ai_validation_report.json` + `test_run_summary.json` y produce:
   - total por modelo, top-N tests más lentos, tests TIMEOUT
   - overhead = wall_del_suite − Σ(time_seconds)
     (separa "lento el modelo" de "lento el runner/parser/CLI")
3. Backup del reporte actual a `docs/backup_YYYYMMDD_HHMMSS/`.
   NO usar `--fresh` (borraría datos de otros modelos).

## Fase 1 — Un solo run instrumentado (~20 min)

```bash
# Estructura (T1-T5, incluye T3) — 3 repeticiones para medir flakiness
python tests/scripts/test_ai_structure.py --native opencode/mimo-v2.5-free  # ×3

# Avanzada completa (23 tests, incluye C2/D8) — merge por ID, sin --fresh
python tests/scripts/run_advanced_tests.py opencode/mimo-v2.5-free
```

Registrar wall-clock de cada suite (Measure-Command o timestamps).

## Fase 2 — Análisis → decisiones con números

| Dato | Decisión (tarea padre) |
|------|------------------------|
| Tests >150s cerca del cap de 180 | T6: `QUERY_TIMEOUT`/`GROQ` 180→300 (`model_runner.py:33-34`) |
| Σ times ≈ wall → suite >1200s | T10: suite timeout 1200→1800 (`run_all_tests.py:187`) |
| Σ times ≪ wall → overhead grande | T10 alt.: atacar overhead (sleep(1), CLI/query); NO subir timeout |
| C2 o D8 TIMEOUT/>180s | T6: simplificar esos prompts |
| T3: variación en 3 corridas | T9: falla >1/3 → sinónimos en id 3; 0-1/3 → aceptar y documentar |
| (Opcional) gpt-oss 429 | T7: confirmar TPD → re-incluir solo si hay headroom |

## Fase 3 — Solo los fixes que los datos justifiquen

Candidatos: `model_runner.py:33-34` · `run_all_tests.py:187` ·
`ai_structure_questions.json` id 3 · `run_all_tests.py:115`.

## Fase 4 — Verificación y cierre

1. Re-run de tests afectados
2. Suite unitaria (69 actual)
3. Marcar sub-tareas completadas en `docs/TAREAS_PENDIENTES.md` (6/9/10, +7)
4. Sección en sesión de tests (nueva fecha o `sesion_20260921.md`)
5. `memory_save` con decisión + evidencia
6. commit/push (ramas clean-main / main-clean)

## Alcance pendiente de confirmar

- [x] **Solo mimo (T6/9/10, ~20-25 min)** — confirmado 23/09. gpt-oss (T7) queda
      fuera de este run; se abordará en una pasada posterior si hay headroom TPD.
