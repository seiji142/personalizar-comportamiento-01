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
