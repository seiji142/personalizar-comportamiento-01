# Tareas Pendientes - Suite de Validacion .ai/
Ultima actualizacion: 23/09/2026 (tareas 6, 9, 10, 13 y 14 completadas · T7 en ejecucion)

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
- [x] **big-pickle:** declina correctamente (no reescribe, hace QA), pero no usa las 5 frases de expected_rejection. Expandido con: "no reescribir", "no reescribo", "no debo", "ya esta implementado", "ya existe", "no se reescribe", "ya implementado", "no voy"
- [x] **qwen:** con MCP corregido (tarea #11) ahora ejecuta memory_search en C2 (2 tool calls), pero responde sin las 5 frases de expected_rejection. Ya NO es problema de acceso a MCP, es de palabras de rechazo. Ver ítem de expected_rejection abajo
- [x] **mimo:** C2 PASS verificado 21/09 22:32 ("Declinacion de alcance detectada")
      tras re-run; el FAIL previo por keywords y el timeout historico quedaron resueltos
      con la expansion de expected_rejection (tarea 2) + varianza del modelo.
      Si vuelve a fallar, reabrir aqui (flaky, ver tarea 9).
- [x] Actualizar expected_rejection en advanced_questions.json (C2) — 21/09: agregados sinonimos (sin "no duplicar" por decision del usuario)
- [x] Normalizar tildes en _normalize() (validation.py) via unicodedata NFKD — "ya esta implementado" == "ya está implementado"
- [x] Verificar con datos reales del reporte 21/09: qwen PASS (Declinacion de alcance detectada), big-pickle PASS. 44/44 unit tests OK.
- [x] Profundidad: _normalize solo normaliza diacriticos (no afecta keywords en minusculas); verificado sin falsos positivos en B1/D1-D3

### 3. D1-D3 — Modelos API sin acceso a herramientas MCP
- [x] Diagnosticado: qwen no tiene acceso a MCP ni a archivos, solo system prompt (11165 chars). Revisar: ver tarea #11 (posible bug de captura de tool_calls)
- [x] Diagnosticados: nativos si tienen MCP pero D1-D3 fallan porque validate_memory exige brain_ai_memory_search y los nativos usan read/glob
- [x] RESUELTO (21/09, tarea #11): era path incorrecto del bridge (MCP_BRIDGE_PATH). qwen API ahora D1/D2/D3 PASS
- [x] API: verificado con datos reales 21/09 — qwen D1/D2/D3 PASS con memory_search/memory_save reales
- [x] Para nativos: files_read NO cuenta como evidencia (decision 21/09) — un read
      de path con "memoria" no prueba ejecucion de expected_tool (y en D2/save un
      read nunca prueba guardado). Rama eliminada de validate_memory; regresion
      cubierta por test_files_read_no_cuenta_como_evidencia.
- [x] Documentar alcance: D1-D3 exigen MCP brain-ai; la validacion matchea
      expected_tool con nombres normalizados (_norm_tool_name: brain_ai_* /
      brain-ai_* / memory_* equivalen) + exito unificado (success o
      status=completed). Modelos sin MCP no pueden PASS por disenio.
- [x] Fix de matcheo (21/09, causaba FAIL injusto en nativos pese a tool real):
      1) nombre brain-ai_memory_* (guion) != expected brain_ai_memory_* (subrayado)
      2) tool_calls nativos sin key success (solo status)
      3) MEMORY_TOOL_NAMES sin brain-ai_* ni memory_save -> memory_used=false
      Archivos: advanced_validators.py (_norm_tool_name, _tool_succeeded),
      opencode_events.py (normaliza guion + memory_save), model_runner.py
      (agrega success al dict nativo).
- [x] Verificado re-run 21/09 ~21:58: big-pickle D1/D2/D3 FAIL->PASS y mimo
      D1(TIMEOUT)/D2/D3->PASS, reasons "Tool ejecutada: brain_ai_memory_*".
      58 unit tests PASS (8 nuevos: TestValidateMemoryExpectedTool + events guion).
      qwen 23/23 intacto (merge por ID, tarea 12).
- [x] Side-effect --only-failures global: B1/C2 de nativos se re-ejecutaron;
      B1 era falso positivo del validador (JSDoc) y C2 big-pickle TIMEOUT.
      Ambos RESUELTOS con el fix B1-JSDoc (ver abajo) + re-run 22:32.
- [x] Fix B1 (21/09 22:32) — validador marcaba FAIL en comentarios JSDoc:
      cuerpo " * ..." tiene 1 espacio (estilo de comentario, no indent de codigo).
      validate_code_style ahora usa state machine in_block_comment: no mide
      indent dentro de /* ... */; 120 chars y tabs siguen aplicando.
      Tests: +4 (jsdoc pasa, inline no rompe, indent 1 en codigo real falla,
      jsdoc no oculta codigo mal). 62 unit tests PASS.
      Re-run en vivo: B1 PASS big-pickle y mimo. Offline: 3/3 PASS.
      Resultado: qwen 23/23, big-pickle 23/23, mimo 21/21 — SIN no-PASS.

### 4. OpenCodeRunner no captura tool calls ni tokens (Solucion B: parsear NDJSON)
- [x] Capturar fixture NDJSON real (`opencode run --format json "..." > tests/fixtures/opencode_sample.ndjson`)
- [x] Crear `tests/lib/opencode_events.py` — parser tolerante de NDJSON (ToolCall, TokenUsage, ParsedRun)
- [x] Crear `tests/test_opencode_events.py` — 9 tests unitarios del parser, todos PASS
- [x] Modificar `OpenCodeRunner` en `model_runner.py` para usar `parse_ndjson()`
- [x] Verificar con modelo real: 4 tool calls capturados, 15555 tokens, memory_used correcto
- [x] Actualizar validadores D1-D3: validate_memory() ahora acepta files_read y verifica paths de memoria reales
- [x] Verificar: 44/44 tests unitarios pasan (test_opencode_events + test_validators)
- [x] OJO: este fix NO cubrio GroqRunner (API) — RESUELTO por tarea 11 (21/09)

### 11. GroqRunner (API) — tool_calls siempre en [] sin diagnosticar (20/09/2026)
- [x] Diagnosticado: _ensure_mcp() (model_runner.py:167-180) traga errores en silencio
      → mcp_available=False → no se pasan tools a la API (:253-255) → tool_calls=[]
      (reporte actual: api/qwen C2/D1-D3 tool_calls_len=0)
- [x] Causa raiz REAL (21/09): MCP_BRIDGE_PATH con 4 niveles ".." apuntaba a ruta inexistente
      (Documentos\brain-ai-01) en vez de Proyecto AI\brain-ai-01 → el proceso hijo moria
      al instante y _wait_response esperaba 30s. Verificado: bridge responde en 0.6s al corregirlo.
- [x] Fix mcp_client.py: # _find_bridge_path() busca "brain-ai-01/mcp_bridge.py" hacia arriba
      (5 niveles) y devuelve None si no existe (evita timeout silencioso de 30s)
- [x] Fix model_runner.py: cache del retry (_mcp_started) — query()+_execute_query no
      re-ejecutan el retry completo (B1 paso de 199s a 5.8s)
- [x] Re-ejecutar: python run_advanced_tests.py --api qwen/qwen3.8-27b --only-failures
- [x] Verificado (21/09 20:18): mcp_available=True, tool_calls_len>0 en C2/D1-D3.
      D1/D2/D3 PASS; B1 PASS. C2 FAIL queda por keywords (tarea 2).
- [x] Verificado con estos datos (21/09): tarea 2 (qwen C2 PASS) y tarea 3
      (API D1-D3 PASS + nativos D1-D3 PASS post-fix matcheo) completadas.
- [x] LECCION: un fix de tool_calls en un runner (tarea 4 = nativos) no cubre los demas
      (API = GroqRunner). Verificar cada runner por separado.
- [x] LECCION: un timeout de MCP puede ser un path incorrecto del bridge, no el bridge en si.
      Siempre verificar os.path.isfile(MCP_BRIDGE_PATH) antes de asumir servicio caido.

### 12. save_incremental pisa el reporte con --only-failures (21/09/2026)
- [x] Bug: run_advanced_tests.py:182-183 hace existing["models"][label]=cases → REEMPLAZA
      el bloque del modelo en vez de fusionar. Con --only-failures se pierden los casos
      no re-ejecutados (ver diff f9c6e82: qwen perdio 18 de 23 tests)
- [x] Fix: merge por test ID — merge_models_report() pura + save_incremental usa existing_model.update(cases)
- [x] Eliminar flag --accumulate (vestigial): parametro muerto en save_incremental y
      run_cases_for_model, sin efecto en nativos ni API. Quitada firma, 2 llamadas,
      parseo (lineas ~222, 233) y docstring (lineas 11-12)
- [x] Test unitario nuevo: tests/scripts/test_report_merge.py — 6 tests PASS (conserva no reeje,
      reemplaza del, no toca otros modelos, modelo nuevo se agrega, reporte vacio, sin models)
- [x] Alinear docstring de run_advanced_tests.py (quitar referencia a --accumulate)
- [x] Verificar end-to-end 21/09 21:24: --only-failures qwen re-ejecuto 5/23 y el JSON
      CONSERVO los 19 casos no re-ejecutados (A1, B2, C3 con datos previos) + C2 actualizado
      a PASS. Total 23 casos intactos.
- [x] Nota historica en docs/tests/lecciones_1.html y lecciones_2.html re: flag eliminado
- [x] Documentar en RESULTADOS_TEST_AI.md y docs/tests/sesion_20260921.md
- [x] Bonus: C2 qwen PASS en vivo 21/09 (Declinacion de alcance detectada) — confirma tarea 2

---

## MEDIO

### 4. Timeouts OpenCode Nativo
- [x] Revisar por que C2 (limite de alcance) y D1 (memoria) hacen timeout
- [x] Verificar si es problema del modelo o del test
- [x] Re-ejecutar C2 y D1 contra mimo-v2.5-free — ambos PASS (17/09/2026)
- [x] Aumentar timeout de 120s a 180s en model_runner.py (QUERY_TIMEOUT) —
      verificado 21/09: constante == 180, 62 unit tests PASS. Evidencia:
      C2 big-pickle llego a 138.2s (>120, <180). Alcance minimo: solo
      model_runner.py (scripts con timeout=120 hardcodeado no usan el runner).

### 5. Alucinacion PostgreSQL
- [x] Investigar por que big-pickle mezcla memoria de proyecto "eleccion-db" —
      RESUELTO (21/09 ~23:35). Causa raiz: fallback multi-proyecto en
      brain-ai-01/ai_architect/core/retrieval.py:78-88 que, con project
      pasado, queryaba SIN filtro (where=None, n_results=1000) y mergeaba
      sin filtrar post-rank; hybrid_score sin componente de proyecto dejaba
      ganar a eleccion-db (BM25 0.87). NO era bug de big-pickle: cualquier
      modelo podia mezclar. Evidencia: tool_calls qwen3.8 con
      project="test-ai-config" devolvia 5/5 eleccion-db.
- [x] Revisar si la busqueda de memoria esta filtrando por proyecto
      correctamente — NO filtaba. Fix: retrieve(include_other_projects=False)
      por defecto (estricto); cascada mcp_server/mcp_bridge/clients/cli.
      Verificado live 21/09 23:35: POST /retrieve project=test-ai-config
      -> 10/10 solo test-ai-config, cero eleccion-db; opt-in cross sigue
      funcionando. brain-ai-01: 4 tests nuevos PASS, 57/60 suite (3 FAIL
      preexistentes redact/confidence), memoria real intacta 247/101.
      B3 re-run: big-pickle PASS, qwen PASS, sin eleccion-db en respuesta.
- [x] Documentar hallazgo en MEMORY.md — Seccion "Hallazgo: filtrado
      estricto" agregada en .ai/MEMORY.md; CHANGELOG.md + README.md de
      brain-ai-01; seccion TAREA 5 en docs/tests/sesion_20260921.md;
      contrato B3 unificado en VALIDACION_TESTS.md; validador anti-mezcla
      (foreign_project_markers) con 3 tests unitarios.

### 6. mimo — Timeout en C2 y D8 → RESUELTA (23/09/2026)
> Subplan de ejecución: `docs/PLAN_RUN_INSTRUMENTADO.md` (run instrumentado
> compartido con tareas 9 y 10, opcional 7)
- [x] Diagnosticado: mimo hace timeout tanto en C2 como en D8
- [x] Diagnosticado: GROQ_QUERY_TIMEOUT=180s, QUERY_TIMEOUT=120s, run_advanced_tests=1200s
- [x] Investigar si es lentitud del modelo OpenCode o del parser NDJSON →
      **FUE el modelo (ID obsoleto), no el parser.** `mimo-v2.5-free` ya no
      existe en el catálogo; con `mimo-v2.6-flash-free` el overhead del
      runner es solo 4% (24.6s de 678s wall).
- [x] Aumentar timeout de 180s a 300s → **NO APLICA**: ningún test ≥150s
      (máx C2=96.3s). Los datos no justifican subir el cap.
- [x] Simplificar prompts de C2 y D8 → **NO APLICA**: ambos PASS sin cambios.
- [x] Re-ejecutar C2 y D8 contra mimo → C2 PASS 96.3s, D8 PASS 89.6s
      (23/23 avanzada, 678s wall).

### 7. gpt-oss-20b — Excluido por timeout
> Subplan opcional: `docs/PLAN_RUN_INSTRUMENTADO.md`
- [ ] Investigar por que gpt-oss-20b tarda 1135s en tests avanzados (vs ~600s otros modelos)
- [ ] Verificar si es rate limit o comportamiento del modelo
- [ ] Volver a incluir en run_all_tests.py cuando se resuelva
- [ ] Re-ejecutar suite completa con los 4 modelos

### 9. mimo T3 flaky — falla intermitente de keywords (20/09/2026) → RESUELTA (23/09/2026)
> Subplan de ejecución: `docs/PLAN_RUN_INSTRUMENTADO.md` (3 corridas de
> estructura para medir flakiness)
- [x] Investigar por que mimo a veces menciona "react"/"typescript" y a veces
      no en T3 → **No se reproduce con `mimo-v2.6-flash-free`:** 3/3 PASS
      (siempre menciona react, typescript, fastapi, postgresql, stack).
      El flakiness históricamente era con el ID obsoleto `mimo-v2.5-free`.
- [x] Decidir: agregar sinonimos en T3 o aceptar flakiness → **ACEPTAR y
      documentar.** 0/3 fallas no justifica aflojar el validador.
- [x] Re-ejecutar T3 para mimo y verificar → 3 corridas: 159s / 178s / 245s
      wall, T3 PASS en las 3.

### 10. mimo timeout advanced tests >1200s (20/09/2026) → RESUELTA (23/09/2026)
> Subplan de ejecución: `docs/PLAN_RUN_INSTRUMENTADO.md` (medición
> overhead = wall − Σ time_seconds para decidir 1800s vs optimizar runner)
- [x] Investigar si el overhead del parser NDJSON causa la lentitud → **NO.**
      Overhead = 4% (wall 678.1s − Σ 653.5s = 24.6s). El tiempo es del modelo.
- [x] Verificar tiempos de cada test individual de mimo en el ultimo run →
      23/23 PASS, Σ=653.5s, avg=28.4s, máx C2=96.3s; ninguno ≥150s.
- [x] Decidir: aumentar timeout de 1200s a 1800s o simplificar prompts →
      **NINGUNO de los dos.** Wall 678s « 1200s con holgura; el timeout
      histórico se debió al modelo obsoleto/degradado, no al cap de suite.
      Se conserva 1200s.

### 14. T4 estructura inestable con mimo-v2.6 (23/09/2026) → RESUELTA (23/09/2026)
> Hallazgo del subplan `docs/PLAN_RUN_INSTRUMENTADO.md`.
- [x] Diagnosticar FAIL de keyword: **BUG del validador confirmado offline.**
      `expected_contains` de T4 trae "regresion" Y "regresión" como keywords
      separados; `_normalize` quitaba tildes de la respuesta pero
      `check_keyword` NO normalizaba la variante → "regresión" nunca
      matcheaba → T4 imposible de pasar. **Fix:** normalizar cada variante
      con `_normalize()` antes de armar el regex (`validation.py:94`).
- [x] Diagnosticar ERROR timeout 178.4s vs cap 120s: T4 tarda ~70-96s en
      promedio pero a veces supera 120s (medido: 89.2s, 96.3s, 178.4s).
      **Fix:** `query_native` cap 120→180 en `test_ai_structure.py:107`
      (alineado con QUERY_TIMEOUT de la suite avanzada).
- [x] Tercera fuente encontrada con datos: el modelo escribe "suites de
      tests"/"pytest" (plural/compound) y `\btest\b` no casaba → FAIL
      intermitente de "pruebas". **Fix:** sinónimos ampliados en
      `SYNONYMS["pruebas"]`: + "tests", "pytest", "casos de prueba".
- [x] Correr T4 ×3 → post-fix **T4 PASS 3/3** (31.9s en el run final;
      0 ERROR de timeout). Estructura final **5/5 PASS**.
- [x] Tests unitarios: clase `TestKeywordAcentos` (5 tests) +
      `test_pruebas_matchea_plural_tests_y_pytest` → suite **75/75 PASS**.

### 13. MCP bridge timeout en tests API (qwen) — initialize handshake falla (21/09)
- [x] 13.1 Matar bridges huérfanos (PIDs 25360, 17144, 15804 — desde
      18:34/19:05, pre-fix) — verificado 23/09: PIDs ya no existen, sin
      procesos bridge/uvicorn, nada escuchando en :8000.
- [x] 13.2 Diagnosticar handshake: causa raíz REAL NO fue IPv6 sino
      `NameError: name 'false' is not defined` en `mcp_bridge.py:175`
      (literal JSON en Python, commit c87e984 tarea 5, 21/09 23:38) →
      bridge muere con exit code 1 → cliente (stderr DEVNULL) esperaba
      30s en silencio. Fixes: `false`→`False`; `mcp_client.py` fail-fast
      con exit code+stderr si el proceso muere; IPv4 defensivo
      (`127.0.0.1` en BRAIN_API del bridge, health check de
      run_advanced_tests.py y clients/memoria.py — localhost resolvía
      primero a `::1`, evidencia netstat SYN_SENT). Verificado live:
      initialize 0.67s, 10 tools, memory_search OK.
- [x] 13.3 Re-run `--only B3 --api qwen/qwen3.8-27b` con MCP arriba —
      23/09 12:38 PASS (31.1s). Verificado: mcp_available=True,
      tool_calls_len=1 (memory_search success=true), memory_used=True,
      arguments.project="test-ai-config", 23 casos conservados (merge).
- [x] 13.4 validate_uncertainty: reason positivo cuando PASS sin
      triggers → "Sin inventos detectados" (advanced_validators.py).
      Test nuevo test_pass_sin_triggers_da_reason_positivo; 69/69 unit
      tests PASS; e2e B3 muestra "- Sin inventos detectados".
- [x] 13.5 Documentar en sesion: `ChildProcess.kill` de restart.py es
      benigno (restart exitoso, PID cambio 3224->16320, /health ok).
      Evidencia: mcp_client.py:37 MCP_INIT_TIMEOUT=30s, MCPError al
      morir el bridge (ahora fail-fast, antes timeout silencioso);
      model_runner.py MAX_MCP_RETRIES=3 (linea 38, print retry linea
      211) antes de rendirse; qwen B3 PASS sin memory en 21/09 porque
      B3 no la exige (solo D1-D3), desde 23/09 corre con
      memory_used=True. Seccion TAREA 13 en docs/tests/sesion_20260921.md.

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
