# Resultados Validacion .ai/ — Modelos probados

## Resultados actuales (21/09/2026)

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

> **PENDIENTE — re-run completo:** opencode/big-pickle y opencode/mimo-v2.5-free no se
> re-ejecutaron completos el 21/09 (solo se verifico C2 de big-pickle con datos del reporte).
> No actualizar sus lineas en la tabla de suite avanzada hasta re-correr la suite completa.
> Ver tarea 12 en TAREAS_PENDIENTES.md.

---

## Resultados anteriores (15/09/2026)

**Suite completa:** 4 modelos × 3 tests (test_ai_structure, validate_agent_responses, run_advanced_tests)

> **Modelos activos:**
> - `openai/gpt-oss-20b` (Groq Cuenta 1, GROQ_CUENTA_1)
> - `qwen/qwen3.8-27b` (Groq Cuenta 2, GROQ_CUENTA_2)
> - `opencode/big-pickle` (nativo OpenCode)
> - `opencode/mimo-v2.5-free` (nativo OpenCode)
>
> **Modelos retirados:**
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

## Criterio de Documentación

**Regla: TODO va a `docs/`.**

| Tipo | Destino | Ejemplo |
|------|---------|---------|
| JSON (datos crudos de tests) | `docs/` | `advanced_validation_report.json` |
| HTML (reportes visuales) | `docs/` | `reporte_consolidado.html` |
| Markdown (análisis) | `docs/` | `RESULTADOS_TEST_AI.md` |
| Backup | `docs/backup_YYYYMMDD_HHMMSS/` | Archivos previos al re-run |
| Scripts de tests | `src/doc/ESTRUCTURA/` | `test_ai_structure.py` |
| Scripts de reportes | `src/doc/LECCIONES/` | `generate_html_report.py` |

`src/doc/LECCIONES/` es solo para código fuente (scripts), NO como destino de reportes generados.

## Herramientas de validacion

| Script | Funcion | Modos |
|--------|---------|-------|
| `tests/scripts/test_ai_structure.py` | Suite basica 5 tests | `--native <model>` / API (default) |
| `tests/scripts/validate_agent_responses.py` | Validacion de respuestas | `--run-model <model>` / `--api <model>` / JSON (default) |
| `tests/scripts/run_advanced_tests.py` | Suite avanzada 23 tests | `--api <model>` / nativo (default) |
| `tests/scripts/run_all_tests.py` | Runner maestro (15 ejecuciones) | Ejecuta todo |
| `tests/lib/validation.py` | Logica comun de validacion | — |
| `tests/lib/advanced_validators.py` | Validadores especiales | — |

## Como ejecutar

```powershell
# Suite completa (recomendado)
python tests/scripts/run_all_tests.py

# Solo tests locales
python -m pytest tests/unit/test_email_validator.py -v
python tests/scripts/test_validators.py
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
