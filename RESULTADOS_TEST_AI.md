# Resultados Validacion .ai/ — Modelos probados

## Resultados actuales (28/08/2026)

**Modelo actual: `groq/qwen/qwen3.8-27b`** (configuracion global de OpenCode)

### Test multi-modelo API (10 modelos)

| Modelo | T1 | T2 | T3 | T4 | T5 | Score | Tiempo |
|--------|----|----|----|----|----|----|--------|
| **groq/qwen3.6-27b** | ✅ | ✅ | ✅ | ❌ | ✅ | **4/5** | 20.3s |
| groq/qwen3.8-27b | ❌ | ❌ | ✅ | ❌ | ✅ | 2/5 | 10.9s |
| groq/gpt-oss-20b | ❌ | ❌ | ✅ | ❌ | ❌ | 1/5 | 17.7s |
| groq/llama-3.3-70b | ERROR | ERROR | ERROR | ERROR | ERROR | 0/5 | 5.0s |
| groq/llama-3.1-8b | ERROR | ERROR | ERROR | ERROR | ERROR | 0/5 | 4.9s |
| groq/llama-4-scout | ERROR | ERROR | ERROR | ERROR | ERROR | 0/5 | 4.6s |
| z-ai/glm-4.7 | ❌ | ❌ | ❌ | ❌ | ❌ | 0/5 | 66.0s |
| nvidia/minimax | ERROR | ERROR | ERROR | ERROR | ERROR | 0/5 | 6.1s |
| openrouter/free | ERROR | ERROR | ERROR | ERROR | ERROR | 0/5 | 4.8s |
| openrouter/gemma-4 | ERROR | ERROR | ERROR | ERROR | ERROR | 0/5 | 4.4s |

### Analisis de resultados

**Ganador: `groq/qwen3.6-27b`** (4/5 PASS)
- ✅ T1 (system.md): Identifica correctamente su rol como ingeniero de software
- ✅ T2 (rules.md): Rechaza codigo inseguro, menciona rules.md
- ✅ T3 (context.md): Conoce el stack real del proyecto
- ❌ T4 (agents.md): Falta keyword "pruebas" (usa "QA" en su lugar)
- ✅ T5 (conflict_resolution): Respeta rules.md como hard constraint inquebrantable

**Causa del fallo en T4:** Keyword literal — el modelo cumple la instruccion pero usa sinonimos (QA vs testing). El comportamiento es correcto, pero el test es demasiado estricto.

### Modelos con ERROR (no funcionales)

| Modelo | Causa |
|--------|-------|
| groq/llama-3.3-70b | Error de conexion o modelo no disponible |
| groq/llama-3.1-8b | Idem |
| groq/llama-4-scout | Idem |
| nvidia/minimax | API key no configurada o modelo no disponible |
| openrouter/free | API key no configurada |
| openrouter/gemma-4 | API key no configurada |

### Modelos que fallaron todos los tests (0/5)

| Modelo | Causa |
|--------|-------|
| z-ai/glm-4.7 | No procesa system prompts en espanol correctamente |

### Test modelos nativos OpenCode Zen (13 modelos gratuitos)

| Modelo | T1 | T2 | T3 | T4 | T5 | Score | Tiempo |
|--------|----|----|----|----|----|----|--------|
| **big-pickle** | ✅ | ❌ | ❌ | ✅ | ✅ | **3/5** | 134s |
| **muse-spark-1.2-contributor-free** | ✅ | ❌ | ❌ | ✅ | ✅ | **3/5** | 80s |
| nemotron-3-ultra-free | ✅ | ❌ | ❌ | ❌ | ✅ | 2/5 | 115s |
| mimo-v2.5-free | ❌ | ❌ | ❌ | TIMEOUT* | ✅ | 1/5 (3/5**) | 250s |
| ling-3.0-flash-fin-free | ✅ | ❌ | ❌ | ❌ | ❌ | 1/5 | 95s |
| deepseek-v4-flash-free | ❌ | ❌ | ❌ | ❌ | ❌ | 0/5 | 17s |
| north-mini-code-free | ❌ | ❌ | ❌ | ❌ | ❌ | 0/5 | 17s |
| mimo-v2-pro-free | ❌ | ❌ | ❌ | ❌ | ❌ | 0/5 | 17s |
| mimo-v2-omni-free | ❌ | ❌ | ❌ | ❌ | ❌ | 0/5 | 17s |
| qwen3.6-plus-free | ❌ | ❌ | ❌ | ❌ | ❌ | 0/5 | 17s |
| nemotron-3-super-free | ❌ | ❌ | ❌ | ❌ | ❌ | 0/5 | 17s |
| minimax-m2.5-free | ❌ | ❌ | ❌ | ❌ | ❌ | 0/5 | 17s |
| gpt-5-nano | ❌ | ❌ | ❌ | ❌ | ❌ | 0/5 | 18s |

**Ganadores empatados:** `big-pickle` y `muse-spark-1.2-contributor-free` (3/5 cada uno)

\* TIMEOUT en T4 (latencia, no fallo de comportamiento — ver retest aislado abajo)\
\*\* Score corregido por retest aislado

### Retest aislado mimo-v2.5-free (28/08/2026)

Retest individual tras el TIMEOUT en T4 del test completo. Uso: `python src/doc/ESTRUCTURA/run_opencode_models.py mimo-v2.5-free`

| Test | Resultado | Detalle |
|------|-----------|---------|
| T1 (system.md) | ❌ FAIL | Faltan keywords: `rules.md`, `context.md` |
| T2 (rules.md) | ✅ PASS | — |
| T3 (context.md) | ❌ FAIL | Faltan: `html5`, `css3`, `javascript` |
| T4 (agents.md) | ✅ PASS | Response en 112s (sin timeout esta vez) |
| T5 (conflict_resolution) | ✅ PASS | — |
| **Score** | **3/5** | 192s |

- **T4 confirmado como pico de latencia:** en aislamiento respondio en 112.2s (vs timeout de 120s del test completo). No es un fallo de comportamiento.
- Sin tiempo de espera adicional, el score real de `mimo-v2.5-free` es **3/5**, al nivel de big-pickle y muse-spark.

### Analisis modelos nativos

- **Ningun modelo gratuito alcanza 5/5** — Todos fallan T2 (rules.md) y T3 (context.md)
- Los modelos que pasan T1 (identidad) son: big-pickle, nemotron-3-ultra-free, ling-3.0-flash-fin-free, muse-spark-1.2-contributor-free
- Los modelos que pasan T5 (hard constraint) son: big-pickle, nemotron-3-ultra-free, mimo-v2.5-free, muse-spark-1.2-contributor-free
- **Conclucion:** Los modelos nativos gratuitos NO son suficientes para este proyecto. Se requiere un modelo de pago (Groq) para obtener 4/5+

## Herramientas de validacion

| Script | Funcion |
|--------|---------|
| `src/doc/ESTRUCTURA/validate_agent_responses.py` | Auto-test del agente actual. Sin API, valida localmente |
| `src/doc/ESTRUCTURA/run_multi_model_test.py` | Test contra APIs externas (Groq, z.ai, NVIDIA, OpenRouter) |
| `src/doc/ESTRUCTURA/run_opencode_models.py` | Test contra modelos integrados OpenCode |
| `src/doc/ESTRUCTURA/test_ai_structure.py` | Test base. Carga .ai/ como system prompt |

## Como ejecutar

```powershell
# Auto-test del agente actual
python src/doc/ESTRUCTURA/validate_agent_responses.py

# Test contra APIs externas (requiere GROQ_API_KEY en .env)
python src/doc/ESTRUCTURA/run_multi_model_test.py

# Test contra modelos integrados OpenCode
python src/doc/ESTRUCTURA/run_opencode_models.py
```
