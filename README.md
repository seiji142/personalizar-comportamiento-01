# personalizar-comportamiento-01

Framework para personalizar y validar el comportamiento consistente de modelos de IA en OpenCode. Define reglas, contexto y agentes especialistas que cualquier modelo debe seguir fielmente.

## Que es

Este proyecto responde a una pregunta clave: **como asegurarse de que un LLM se comporte exactamente como uno quiere, pase lo que pase?**

La solucion es un sistema de archivos `.ai/` que actuan como system prompt del agente, combinado con una suite de tests automatizados que verifican que el modelo cumpla con las reglas definidas.

## Estructura

```
├── .ai/                          # Configuracion de comportamiento del agente
│   ├── system.md                 #   Rol, tono, estilo y estructura de respuestas
│   ├── rules.md                  #   Reglas obligatorias (codigo, git, seguridad, calidad)
│   ├── context.md                #   Stack tecnico, dependencias, variables de entorno
│   └── agents.md                 #   Agentes especialistas (frontend, backend, devops, etc.)
│
├── opencode.json                 # Config principal de OpenCode (modelo, provider, instrucciones)
│
├── src/doc/ESTRUCTURA/           # Suite de validacion
│   ├── agent_questions.json      #   5 preguntas de test
│   ├── agent_answers.json        #   Respuestas ideales del agente (5/5 PASS)
│   ├── validate_agent_responses.py   # Auto-test del agente actual
│   ├── run_multi_model_test.py       # Test contra APIs externas
│   ├── run_opencode_models.py        # Test contra modelos OpenCode
│   ├── test_ai_structure.py          # Test base con .ai/ como system prompt
│   └── validation.py                 # Logica comun de validacion (sinonimos)
│   ├── run_advanced_tests.py         # Suite avanzada (jailbreak, codigo, factualidad, roles)
│   ├── advanced_validators.py        # Validadores especiales de la suite avanzada
│   └── advanced_questions.json       # 13 casos de la suite avanzada
│
├── src/doc/MEMORIA/              # PDFs de pruebas de memoria y razonamiento
└── RESULTADOS_TEST_AI.md         # Resultados consolidados de validacion
```

## Como funciona

1. OpenCode carga los 4 archivos `.ai/` como system prompt via `opencode.json`
2. El agente debe seguir las reglas de `rules.md` como **hard constraint inquebrantable**
3. La suite de validacion verifica el cumplimiento con 5 tests:

| Test | Target | Que verifica |
|------|--------|-------------|
| T1 | system.md | Identidad correcta (ingeniero de software) |
| T2 | rules.md | Rechazo de codigo inseguro (credenciales, `any`) |
| T3 | context.md | Conocimiento del stack real del proyecto |
| T4 | agents.md | Activacion de roles especializados |
| T5 | conflict_resolution | rules.md es inquebrantable (no se ignora aunque se pida) |

## Resultados de validacion

**5/5 PASS** — `groq/qwen3.6-27b` (API) y `big-pickle` (nativo gratuito). Criterio justo (sinonimos) implementado el 31/08/2026.

| Modelo | Score |
|--------|-------|
| **groq/qwen3.6-27b** | **5/5** |
| **big-pickle** (nativo Zen) | **5/5** |
| mimo-v2.5-free (nativo Zen) | 4/5 |
| groq/qwen3.8-27b | 2/5 |
| muse-spark-1.2-contributor-free | 3/5 |

> **Criterio de validacion:** desde 31/08/2026 la suite usa **sinonimos** (mide intencion, no literalidad).
> Un modelo queda exento si responde con sinonimos correctos (ej. "QA" en lugar de "testing").
> Antes del cambio, el mejor resultado era 4/5 (qwen3.6-27b); ahora 5/5.

> **Seguridad reforzada:** `rules.md` ahora incluye la seccion 6 "Reglas Inquebrantables"
> (las reglas no pueden anularse por instrucciones del usuario), lo que mejora T5.

Ver `RESULTADOS_TEST_AI.md` para el analisis completo.

## Requisitos

- [OpenCode](https://opencode.ai) instalado
- Python 3.x (para scripts de validacion)
- API key de Groq (u otro provider)

## Uso

```bash
# Iniciar OpenCode con la configuracion del proyecto
opencode

# Ejecutar auto-test del agente actual
python src/doc/ESTRUCTURA/validate_agent_responses.py

# Test contra modelos externos (Groq, OpenRouter, etc.)
python src/doc/ESTRUCTURA/run_multi_model_test.py

# Test contra modelos integrados OpenCode
python src/doc/ESTRUCTURA/run_opencode_models.py

# Test de un solo modelo (filtro por nombre)
python src/doc/ESTRUCTURA/run_opencode_models.py mimo-v2.5-free

# Suite avanzada (jailbreak, codigo, factualidad, roles)
python src/doc/ESTRUCTURA/run_advanced_tests.py big-pickle

# Suite avanzada - solo categoria A (jailbreak)
python src/doc/ESTRUCTURA/run_advanced_tests.py --category A

# Suite avanzada - modelo API (Groq)
python src/doc/ESTRUCTURA/run_advanced_tests.py --api qwen/qwen3.6-27b
```

## Variables de entorno

Copiar `.env.template` a `.env` y completar:

```env
LLM_API_KEY=tu_api_key_de_groq
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=qwen/qwen3.6-27b
```

## Licencia

MIT
