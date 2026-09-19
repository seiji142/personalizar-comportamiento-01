# Tareas Pendientes - Suite de Validacion .ai/
Ultima actualizacion: 19/09/2026

---

## CRITICO

### 1. Fix validador T4 — sinonimo "regresion"
- [ ] Agregar `"regresion": ["regresion", "regresión"]` a SYNONYMS en `tests/lib/validation.py`
- [ ] Verificar que T4 pasa para los 3 modelos (big-pickle, mimo, qwen)
- [ ] Re-ejecutar suite completa y confirmar fix

### 2. C2 — Modelos no declinan tarea fuera de alcance
- [ ] Analizar respuestas de C2 para los 3 modelos (big-pickle, mimo, qwen)
- [ ] Decidir: ajustar `expected_rejection` o aceptar como debilidad real del modelo
- [ ] Re-ejecutar C2 si se ajusta el test

### 3. D1-D3 — Modelos API sin acceso a herramientas MCP
- [ ] Decidir: excluir D1-D3 de modelos API o cambiar validacion para aceptar "sin acceso"
- [ ] Documentar que D1-D3 solo aplican a modelos nativos con MCP

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

### 6. D8 mimo — Timeout en test de agente QA
- [ ] Aumentar timeout de Groq de 180s a 300s en `tests/lib/model_runner.py`
- [ ] O simplificar el prompt de D8

### 7. gpt-oss-20b — Excluido por timeout
- [ ] Investigar por que gpt-oss-20b tarda 1135s en tests avanzados (vs ~600s otros modelos)
- [ ] Verificar si es rate limit o comportamiento del modelo
- [ ] Volver a incluir en run_all_tests.py cuando se resuelva
- [ ] Re-ejecutar suite completa con los 4 modelos

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
5. Verificar con tests
6. Registrar decision en memoria
7. Marcar como completada en el checklist
