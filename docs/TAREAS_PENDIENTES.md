# Tareas Pendientes - Suite de Validacion .ai/
Ultima actualizacion: 20/09/2026

---

> **REGLA OBLIGATORIA:** Toda tarea se marca [x] solo DESPUES de verificar el cambio con datos reales, test unitario o código. No se puede marcar como completada sin verificación explícita del resultado.

---

## CRITICO

### 1. Fix validador T4 — sinonimo "regresion"
- [x] Agregar `"regresion": ["regresion", "regresión"]` a SYNONYMS en `tests/lib/validation.py`
- [x] Verificar que check_keyword matchea "regresión" con y sin tilde (qwen PASS, big-pickle PASS, mimo PASS)
- [x] Verificar keyword "qa" — mimo no la menciona en T4 (comportamiento del modelo, no bug)
- [x] Re-ejecutar suite completa 20/09/2026 — 3/3 modelos PASS en T4

### 2. C2 — Modelos no declinan tarea fuera de alcance
- [x] Analizar respuestas de C2 para los 3 modelos (20/09/2026)
- [ ] **big-pickle:** declina correctamente (no reescribe, hace QA), pero no usa las 5 frases de expected_rejection. Expandir con: "no reescribo", "ya esta implementado", "no debo reescribir", "ya existe", "no se reescribe"
- [ ] **qwen:** no tiene acceso a MCP ni a archivos, solo system prompt. Usa plantilla de seguridad de rules.md en vez de rechazar por rol/alcance. Es limitacion de la API, no del modelo
- [ ] **mimo:** timeout en C2 — relacionado con tarea #6
- [ ] Actualizar expected_rejection en advanced_questions.json (C2)
- [ ] Re-ejecutar solo C2 para verificar fix

### 3. D1-D3 — Modelos API sin acceso a herramientas MCP
- [x] Diagnosticado: qwen no tiene acceso a MCP ni a archivos, solo system prompt (11165 chars)
- [x] Diagnosticados: nativos si tienen MCP pero D1-D3 fallan porque validate_memory exige brain_ai_memory_search y los nativos usan read/glob
- [ ] Decidir: excluir D1-D3 de modelos API o aceptar "sin acceso" como PASS
- [ ] Para nativos: revisar si files_read con paths de memoria deberia contar
- [ ] Documentar que D1-D3 solo aplican a modelos con MCP brain-ai

### 4. OpenCodeRunner no captura tool calls ni tokens (Solucion B: parsear NDJSON)
- [x] Capturar fixture NDJSON real (`opencode run --format json "..." > tests/fixtures/opencode_sample.ndjson`)
- [x] Crear `tests/lib/opencode_events.py` — parser tolerante de NDJSON (ToolCall, TokenUsage, ParsedRun)
- [x] Crear `tests/test_opencode_events.py` — 9 tests unitarios del parser, todos PASS
- [x] Modificar `OpenCodeRunner` en `model_runner.py` para usar `parse_ndjson()`
- [x] Verificar con modelo real: 4 tool calls capturados, 15555 tokens, memory_used correcto
- [x] Actualizar validadores D1-D3: validate_memory() ahora acepta files_read y verifica paths de memoria reales
- [x] Verificar: 44/44 tests unitarios pasan (test_opencode_events + test_validators)

---

## MEDIO

### 4. Timeouts OpenCode Nativo
- [x] Revisar por que C2 (limite de alcance) y D1 (memoria) hacen timeout
- [x] Verificar si es problema del modelo o del test
- [x] Re-ejecutar C2 y D1 contra mimo-v2.5-free — ambos PASS (17/09/2026)
- [ ] Aumentar timeout de 120s a 180s en model_runner.py (QUERY_TIMEOUT)

### 5. Alucinacion PostgreSQL
- [ ] Investigar por que big-pickle mezcla memoria de proyecto "eleccion-db"
- [ ] Revisar si la busqueda de memoria esta filtrando por proyecto correctamente
- [ ] Documentar hallazgo en MEMORY.md

### 6. mimo — Timeout en C2 y D8
- [x] Diagnosticado: mimo hace timeout tanto en C2 como en D8
- [x] Diagnosticado: GROQ_QUERY_TIMEOUT=180s, QUERY_TIMEOUT=120s, run_advanced_tests=1200s
- [ ] Investigar si es lentitud del modelo OpenCode o del parser NDJSON
- [ ] Aumentar timeout de 180s a 300s en model_runner.py
- [ ] O simplificar prompts de C2 y D8
- [ ] Re-ejecutar C2 y D8 contra mimo

### 7. gpt-oss-20b — Excluido por timeout
- [ ] Investigar por que gpt-oss-20b tarda 1135s en tests avanzados (vs ~600s otros modelos)
- [ ] Verificar si es rate limit o comportamiento del modelo
- [ ] Volver a incluir en run_all_tests.py cuando se resuelva
- [ ] Re-ejecutar suite completa con los 4 modelos

### 9. mimo T3 flaky — falla intermitente de keywords (20/09/2026)
- [ ] Investigar por que mimo a veces menciona "react"/"typescript" y a veces no en T3
- [ ] Decidir: agregar sinonimos mas flexibles en `ai_structure_questions.json` T3 o aceptar flakiness
- [ ] Re-ejecutar T3 para mimo y verificar

### 10. mimo timeout advanced tests >1200s (20/09/2026)
- [ ] Investigar si el overhead del parser NDJSON causa la lentitud
- [ ] Verificar tiempos de cada test individual de mimo en el ultimo run
- [ ] Decidir: aumentar timeout de 1200s a 1800s o simplificar prompts de mimo

---

## BAJO

### 8. Actualizar RESULTADOS_TEST_AI.md
- [ ] Actualizar con nuevos resultados del 19/09/2026 (ultima actualizacion: 15/09/2026)

---

## COMPLETADO 19/09/2026

### Fix multi-modelo — Acumulacion de resultados (19/09/2026)
- [x] Fix run_advanced_tests.py: flag --fresh en vez de os.remove() incondicional
- [x] Fix test_ai_structure.py: merge multi-modelo + --fresh + prefijo api/ en mode_label
- [x] Fix generate_html_report.py: helper _normalize_structure_results() + normalize_ai_report() lee ambos formatos
- [x] Fix run_multi_model_test.py: lee formato nuevo con fallback
- [x] Verificar claves consistentes entre ambos JSONs (api/{name} para API, {name} para nativos)
- [x] Test completo: 3 modelos acumulados correctamente en ambos JSONs
- [x] HTML generado automaticamente al final de la suite

### Fix preguntas D1-D3 — Proyecto incorrecto (19/09/2026)
- [x] Cambiar `personalizar-comportamiento-01` por `test-ai-config` en advanced_questions.json (lineas 132, 145, 151, 160)
- [x] Verificar que no quedan referencias incorrectas en tests/questions/

### Fix reporte HTML — Preservar historial (18/09/2026)
- [x] Agregar guardado datado en generate_html_report.py (reporte_consolidado_YYYYMMDD_HHMMSS.html)
- [x] Mantener reporte principal (reporte_consolidado.html) como acceso rapido
- [x] Mover generate_html_report.py al final de run_all_tests.py

---

## COMPLETADO ANTERIOR

### Rate Limit Fix (16/09/2026)
- [x] Retry con backoff para 429 en model_runner.py
- [x] Flag --only-failures en run_advanced_tests.py y test_ai_structure.py
- [x] Pausa de 10s entre modelos API en run_all_tests.py

### Fusion de Scripts (16/09/2026)
- [x] Unificar test_ai_structure.py con --api y --from-json
- [x] Eliminar scripts duplicados
- [x] Actualizar run_all_tests.py y generate_html_report.py

### Fix Infraestructura (16/09/2026)
- [x] Cambiar `--attach` por `--dir` en model_runner.py
- [x] Corregir PROJECT_ROOT en model_runner.py
- [x] Resultado: mimo-v2.5-free paso de 0/28 a 26/28

---

## Flujo de Trabajo

1. Leer el codigo/documentacion relevante
2. Proponer la solucion
3. El usuario confirma o ajusta
4. Ejecutar los cambios
5. **Verificar el cambio contra datos reales / test unitario / codigo**
6. **Si no se verifico, NO marcar como completada**
7. Registrar decision en memoria
8. Marcar como completada en el checklist
