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
│   └── test_ai_structure.py          # Test base con .ai/ como system prompt
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

**4/5 PASS** — groq/qwen3.6-27b (mejor modelo en test multi-modelo API 28/08/2026)

| Modelo | Score | Causa de fallo |
|--------|-------|----------------|
| **groq/qwen3.6-27b** | **4/5** | T4: keyword literal (QA vs testing) |
| groq/qwen3.8-27b | 2/5 | Falta rules.md, reglas, context.md |
| groq/gpt-oss-20b | 1/5 | Solo pasa T3 (context.md) |

### Modelos nativos OpenCode Zen (gratuitos)

| Modelo | Score | Tiempo |
|--------|-------|--------|
| big-pickle | 3/5 | 134s |
| muse-spark-1.2-contributor-free | 3/5 | 80s |
| nemotron-3-ultra-free | 2/5 | 115s |
| 10 modelos mas | 0-1/5 | 17-250s |

**Conclusion:** Los modelos nativos gratuitos NO alcanzan 5/5. Se requiere Groq (qwen3.6-27b) para mejores resultados.

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
