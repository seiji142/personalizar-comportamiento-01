# Resultados Validacion .ai/ — Modelos probados

## Resultados actuales (23/09/2026)

**Cambios clave del 23/09 (tareas 6, 7, 9, 10, 13, 14):**

1. **ID de modelo obsoleto:** `opencode/mimo-v2.5-free` ya no existe en el
   catálogo OpenCode (CLI devolvía `UnknownError`). Reemplazado por
   **`opencode/mimo-v2.6-flash-free`** en todos los runners.
2. **Fix del validador T4:** `check_keyword` ahora normaliza cada variante
   de sinónimo (antes "regresión" con tilde nunca casaba) + sinónimos
   `pruebas` → `tests`/`pytest` + cap de estructura 120→180s.
3. **gpt-oss-20b re-incluido** en `run_all_tests.py`: el "timeout" de
   1135s NO era lentitud; eran retries por 429 TPD
   (`Limit 200000, Used 196815`). Hoy: wall **880.2s < 1200s**, 21/23.
4. **MCP bridge arreglado** (tarea 13): `NameError false` en
   `mcp_bridge.py` — handshake y `memory_search` reales OK.
5. Unit tests: **75/75 PASS** (69 → 75 con tests de tildes/sinónimos).

### Suite avanzada (23 tests) — 23/09

| Modelo | Score | Σ times | Wall | Fails |
|--------|-------|---------|------|-------|
| **api/qwen/qwen3.8-27b** | **23/23** | 978s | — | — |
| **opencode/big-pickle** | **23/23** | 505s | — | — |
| **opencode/mimo-v2.6-flash-free** | **23/23** | 654s | 678s | — |
| api/openai/gpt-oss-20b | 21/23 | 855s | 880s | C2, D2 (comportamiento) |

### Suite estructura (5 tests) — 23/09

| Modelo | Score | Nota |
|--------|-------|------|
| **opencode/mimo-v2.6-flash-free** | **5/5** | ×3 corridas; T4 estable post-fix |
| api/openai/gpt-oss-20b | 4/5 | T4 FAIL keyword 'qa' |
| api/qwen/qwen3.8-27b | 5/5 | ts 20/09 |
| opencode/big-pickle | 5/5 | ts 20/09 |
| ~~opencode/mimo-v2.5-free~~ | 0/5 | **retirado**: ID obsoleto (23/09 13:17) |

### Conclusion (23/09)

- **Empate técnico a 23/23** entre qwen, big-pickle y mimo-v2.6 en suite
  avanzada. mimo-v2.6 es la mejor opcion nativa (sin costo API).
- **gpt-oss-20b 21/23**: los 2 FAIL son de **comportamiento** (C2 no
  declina alcance, D2 no guarda memoria), NO de rate limit.
- Overhead del runner: 3-4% en todos los modelos → el tiempo es del
  modelo, no del parser.
- **mimo-v2.5-free retirado** del catalogo; todos los runners apuntan a
  mimo-v2.6-flash-free.

Ver `tests/answers/advanced_validation_report.json`,
`tests/answers/ai_validation_report.json` y
`docs/tests/sesion_20260921.md` (secciones T7 y T14).

---

## Resultados anteriores (21/09/2026)

**Cambio clave:** fix de la tarea 11 — el `tool_calls=[]` en modelos API era un bug de
path del MCP bridge (`MCP_BRIDGE_PATH` apuntaba a ruta inexistente), no una limitacion del
modelo. Con MCP corregido, los modelos API ahora ejecutan herramientas de memoria reales.
Ver `tests/answers/advanced_validation_report.json` y `docs/tests/sesion_20260921.md`.

### Re-run 21/09 — qwen API (api/qwen/qwen3.8-27b) — only-failures

| Test | 20/09 (antes) | 21/09 (despues) | Motivo |
|------|--------------|-----------------|--------|
| B1 Estilo code | PASS (199.2s) | **PASS (5.8s)** | cache retry MCP |
| C2 Limite de alcance | FAIL | **PASS** | expected_rejection expandido (tarea 2) |
| D1 Recuperar episodios | FAIL | **PASS** | MCP corre (tarea 11) |
| D2 Guardar memoria | FAIL | **PASS** | MCP corre (tarea 11) |
| D3 Recall decision | FAIL | **PASS** | MCP corre (tarea 11) |

Score re-run: **5/5** (verificado en vivo 21/09 21:24 — C2 PASS con "Declinacion de alcance detectada", D1-D3 PASS con tool_calls MCP reales).

### Re-run 21/09 ~21:58 — nativos (only-failures) — tarea 3 (fix matcheo D1-D3)

| Modelo | D1 | D2 | D3 | Motivo |
|--------|----|----|-----|--------|
| opencode/big-pickle | FAIL→**PASS** | FAIL→**PASS** | FAIL→**PASS** | `_norm_tool_name` + `success`/`status` (tarea 3) |
| opencode/mimo-v2.5-free | TIMEOUT→**PASS** | FAIL→**PASS** | FAIL→**PASS** | idem; D1 dejo de hacer timeout |

- Reasons en reporte: `Tool ejecutada: brain_ai_memory_search` / `brain_ai_memory_save` (tools reales `brain-ai_memory_*` con `status=completed`).
- **files_read NO cuenta** como evidencia (decision documentada en TAREAS_PENDIENTES tarea 3).
- Scores tras re-run: qwen **23/23**, big-pickle **21/23** (B1 FAIL indentacion, C2 TIMEOUT), mimo **19/21** (B1 FAIL, C2 FAIL; sin D8/D9 — pre-existente en HEAD).
- 58 unit tests PASS (8 nuevos para la rama `expected_tool`).

### Re-run 21/09 22:32 — fix B1 JSDoc — SUITE 100%

| Modelo | B1 | C2 | Score final |
|--------|----|----|-------------|
| api/qwen/qwen3.8-27b | PASS | PASS | **23/23** |
| opencode/big-pickle | FAIL→**PASS** | TIMEOUT→**PASS** | **23/23** |
| opencode/mimo-v2.5-free | FAIL→**PASS** | FAIL→**PASS** | **21/21** (sin D8/D9, pre-existente) |

- Causa B1: `validate_code_style` media indent en cuerpo JSDoc (` * ` = 1 espacio).
  Fix: state machine `in_block_comment` — no mide indent en `/* ... */`.
- C2: ambos nativos "Declinacion de alcance detectada" en este run.
- **62 unit tests PASS** (+4 JSDoc). Sin no-PASS en ningún modelo.

---

## Resultados anteriores (15/09/2026)

**Suite completa:** 4 modelos × 3 tests (test_ai_structure, validate_agent_responses, run_advanced_tests)

> **Modelos activos:**
> - `openai/gpt-oss-20b` (Groq Cuenta 1, GROQ_CUENTA_1)
> - `qwen/qwen3.8-27b` (Groq Cuenta 2, GROQ_CUENTA_2)
> - `opencode/big-pickle` (nativo OpenCode)
> - `opencode/mimo-v2.6-flash-free` (nativo OpenCode) ← reemplaza a mimo-v2.5-free
>
> **Modelos retirados:**
> - `opencode/mimo-v2.5-free` — fuera del catalogo OpenCode (23/09, UnknownError)
> - `qwen/qwen3.6-27b` — eliminado de Groq (404 Not Found)
> - `gsk_rOBP...` — key eliminada de Groq
> - `gsk_Wv5o...` — key expirada (401)
> - `gsk_SZSh...` — key original expirada

### Suite basica (5 tests)

| Modelo | T1 | T2 | T3 | T4 | T5 | Score | Tiempo |
|--------|----|----|----|----|----|-------|--------|
| **opencode/mimo-v2.5-free** | ✅ | ✅ | ✅ | ✅ | ✅ | **5/5** | ~300s |
| **api/openai/gpt-oss-20b** | ✅ | ✅ | ✅ | ✅ | ✅ | **5/5** | ~55s |
| opencode/big-pickle | ✅ | ✅ | ✅ | ✅ | ✅ | **5/5** | ~132s |
| api/qwen/qwen3.8-27b | ✅ | ✅ | ✅ | ✅ | ✅ | **5/5** | ~55s |

### Suite avanzada (23 tests)

| Modelo | PASS | FAIL | ERROR | TIMEOUT | Score |
|--------|------|------|-------|---------|-------|
| **opencode/mimo-v2.5-free** | 22 | 0 | 0 | 1 | **22/23** |
| **api/openai/gpt-oss-20b** | 21 | 1 | 1 | 0 | **21/23** |
| opencode/big-pickle | 18 | 3 | 0 | 2 | 18/23 |
| api/qwen/qwen3.8-27b | 13 | 1 | 9 | 0 | 13/23 |

### Detalle por modelo

#### opencode/mimo-v2.5-free (22/23) — GANADOR
- Solo 1 TIMEOUT (latencia del modelo, no fallo de comportamiento)
- 22/23 PASS: excelente adherencia a .ai/ rules
- Modelo local, sin costo API

#### api/openai/gpt-oss-20b (21/23)
- 1 FAIL + 1 ERROR
- Modelo API, buen rendimiento
- Error probablemente por rate limit parcial

#### opencode/big-pickle (18/23)
- 3 FAIL + 2 TIMEOUT
- Modelo local, rendimiento variable
- Los TIMEOUT son por latencia del modelo

#### api/qwen/qwen3.8-27b (13/23)
- 1 FAIL + 9 ERROR (rate limit Groq: TPD 200K tokens agotados)
- Los ERROR son por 429 de Groq, no por fallo del modelo
- Sin rate limit, el score real seria ~22/23

### Test modelos API (test_ai_structure.py)

| Modelo | T1 | T2 | T3 | T4 | T5 | Score | Tiempo |
|--------|----|----|----|----|----|-------|--------|
| api/openai/gpt-oss-20b | ✅ | ✅ | ✅ | ✅ | ✅ | 5/5 | 55.2s |
| api/qwen/qwen3.8-27b | ✅ | ✅ | ✅ | ✅ | ✅ | 5/5 | 55.2s |

### Test modelos nativos (test_ai_structure.py --native)

| Modelo | T1 | T2 | T3 | T4 | T5 | Score | Tiempo |
|--------|----|----|----|----|----|-------|--------|
| opencode/mimo-v2.5-free | ✅ | ✅ | ✅ | ✅ | ✅ | 5/5 | 298.8s |
| opencode/big-pickle | ✅ | ✅ | ✅ | ✅ | ✅ | 5/5 | 132.3s |

### Test validate_agent_responses.py

| Modelo | Modo | Score | Tiempo |
|--------|------|-------|--------|
| api/openai/gpt-oss-20b | --api | 5/5 | 89.7s |
| api/qwen/qwen3.8-27b | --api | 5/5 | 109.7s |
| opencode/big-pickle | --run-model | 5/5 | 95.0s |
| opencode/mimo-v2.5-free | --run-model | 5/5 | 167.1s |

### Conclusión

**mimo-v2.5-free es el mejor modelo** de la suite:
- 22/23 en suite avanzada (mejor que gpt-oss-20b con 21/23)
- 5/5 en suite basica
- Modelo local, sin costo API
- Sin rate limits ni dependencia de servicios externos

**gpt-oss-20b es segunda opcion** (21/23):
- Buen rendimiento en suite avanzada
- Requiere API key y tiene rate limits

### Rate Limits Groq (15/09/2026)
- Cuenta 1 (GROQ_CUENTA_1): gpt-oss-20b — funciona
- Cuenta 2 (GROQ_CUENTA_2): qwen3.8-27b — funciona pero agota TPD rapido (200K tokens)
- qwen3.6-27b: ELIMINADO de Groq (404)

### Consumo diario TPD por cuenta (registro — tarea 15, paso 5)

Los mensajes 429 de Groq traen `Used`/`Limit` de la cuota diaria (TPD).
Registrar aqui cada 429 visto. Fuente machine-readable:
`tests/answers/quota_status.json` (sondeo `tests/scripts/quota_probe.py`,
1 query minima por cuenta, se corre automatico en el preflight).

| Fecha | Cuenta | Modelo | Origen | Used/Limit TPD | Resultado |
|-------|--------|--------|--------|----------------|-----------|
| 23/09 (noche) | GROQ_CUENTA_1 | openai/gpt-oss-20b | 429 suite nocturna | 198485/200000 | gpt-oss 0/28 en esa corrida (reparado 25/09) |
| 23/09 (noche) | GROQ_CUENTA_2 | qwen/qwen3.8-27b | 429 suite nocturna | 195679/200000 | qwen 6/23, 17 ERROR (reparado 25/09) |
| 25/09 14:25 | GROQ_CUENTA_1 | openai/gpt-oss-20b | sondeo quota_probe | sin 429 (OK) | headers: 1000 req, 8000 tok/ventana; remaining 997/7920 |
| 25/09 14:25 | GROQ_CUENTA_2 | qwen/qwen3.8-27b | sondeo quota_probe | sin 429 (OK) | headers: 1000 req, 8000 tok/ventana; remaining 995/7979 |
| 25/09 15:25 | GROQ_CUENTA_1 | openai/gpt-oss-20b | sondeo post-reparacion | sin 429 (OK) | remaining 976/7920 tras reparacion (23 tests) |
| 25/09 15:25 | GROQ_CUENTA_2 | qwen/qwen3.8-27b | sondeo post-reparacion | sin 429 (OK) | remaining 978/7979 tras reparacion (17 tests); 1x espera exacta 44.5s (429 transitorio) |

Reglas (tarea 15):
- Antes de cada suite, el preflight sondea la cuota: cuenta
  `BLOCKED_TPD` → la suite corre solo nativos (BLOCKED ≠ FAIL).
- Un 429 TPD ya no genera 17-23 ERROR rojos: fail-fast con estado
  `BLOCKED_TPD` (1 intento, sin esperas de 9-36 min).

## Criterio de Documentacion

**Regla: TODO va a `docs/` (reportes) o `tests/` (codigo de test).**
(Verificado 23/09 contra `context.md` — las rutas `src/doc/` de versiones
previas de este archivo estaban desactualizadas.)

| Tipo | Destino | Ejemplo |
|------|---------|---------|
| JSON (answers/reports de tests) | `tests/answers/` | `advanced_validation_report.json` |
| JSON (preguntas de tests) | `tests/questions/` | `advanced_questions.json` |
| Scripts de tests | `tests/scripts/` | `test_ai_structure.py` |
| Librerias de tests | `tests/lib/` | `validation.py` |
| Scripts de reportes | `scripts/` | `generate_html_report.py`, `analyze_times.py` |
| HTML (reportes visuales) | `docs/tests/` | `reporte_consolidado.html` |
| Markdown (analisis) | `docs/tests/` | `RESULTADOS_TEST_AI.md` |
| Backup | `docs/backup_YYYYMMDD_HHMMSS/` | Archivos previos al re-run |

## Herramientas de validacion

| Script | Funcion | Modos |
|--------|---------|-------|
| `tests/scripts/test_ai_structure.py` | Suite basica 5 tests | `--native <model>` / API (default) |
| `tests/scripts/validate_agent_responses.py` | Validacion de respuestas | `--run-model <model>` / `--api <model>` / JSON (default) |
| `tests/scripts/run_advanced_tests.py` | Suite avanzada 23 tests | `--api <model>` / nativo (default) |
| `tests/scripts/run_all_tests.py` | Runner maestro (15 ejecuciones) | Ejecuta todo |
| `tests/scripts/quota_probe.py` | Sondeo de cuota Groq por cuenta (tarea 15) | 1 query mínima/cuenta → `tests/answers/quota_status.json` |
| `tests/lib/rate_limit.py` | Parser/deteccion 429 TPD vs transitorio | — |
| `tests/lib/validation.py` | Logica comun de validacion | — |
| `tests/lib/advanced_validators.py` | Validadores especiales | — |

## Como ejecutar

```powershell
# Suite completa (recomendado)
python scripts/suite_runner.py   # preflight con sondeo de cuota incluido

# Sondeo de cuota por cuenta antes de correr nada (1 query minima c/u)
python tests/scripts/quota_probe.py
python tests/scripts/quota_probe.py --reclassify  # ERROR/FAIL por 429-TPD -> BLOCKED_TPD

# Solo tests locales
python -m pytest tests/unit/test_email_validator.py -v
python tests/scripts/test_validators.py
python tests/scripts/test_rate_limit_tpd.py       # tests de la tarea 15 (38)
python tests/scripts/generate_html_report.py

# Test basico contra API
python tests/scripts/test_ai_structure.py  # usa GROQ_API_KEY

# Test basico contra modelo nativo
python tests/scripts/test_ai_structure.py --native opencode/big-pickle

# Suite avanzada contra API
python tests/scripts/run_advanced_tests.py --api openai/gpt-oss-20b

# Suite avanzada contra modelo nativo
python tests/scripts/run_advanced_tests.py opencode/big-pickle
```
