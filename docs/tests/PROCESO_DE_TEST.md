# Proceso de Test - Suite de Validación .ai/

## Descripción general

La suite de tests valida que el agente de IA lee y respeta los archivos `.ai/` del proyecto, ejecutando preguntas contra múltiples modelos (API Groq y OpenCode nativo) y verificando las respuestas.

---

## Punto de entrada

```bash
python run_all_tests.py
```

---

## Flujo completo

### 1. Inicio

```
run_all_tests.py
  ├── Carga API keys de ../Verificacion-modelos-ai/.env
  ├── Configura TEST_PROJECT = ../test-ai-config
  └── Inicia results = {}
```

### 2. Tests locales (sin API)

```
run_all_tests.py
  ├── subprocess → tests/unit/test_email_validator.py    (pytest)
  ├── subprocess → tests/scripts/test_validators.py       (35 unit tests)
  └── subprocess → scripts/generate_html_report.py        (genera HTML)
```

### 3. Tests API (cada modelo)

```
run_all_tests.py (por cada modelo: gpt-oss-20b, qwen3.8-27b)
  │
  ├── subprocess → tests/scripts/test_ai_structure.py --api <modelo>
  │     └── importa tests/lib/model_runner.py → GroqRunner
  │           └── llama a Groq API vía openai SDK
  │
  └── subprocess → tests/scripts/run_advanced_tests.py --api <modelo>
        ├── Lee tests/questions/advanced_questions.json
        ├── importa tests/lib/model_runner.py → GroqRunner
        │     └── llama a Groq API + MCP tools (memoria)
        ├── importa tests/lib/advanced_validators.py → valida cada respuesta
        └── Guarda en tests/answers/advanced_validation_report.json
```

### 4. Tests nativos (cada modelo)

```
run_all_tests.py (por cada modelo: big-pickle, mimo-v2.5-free)
  │
  ├── subprocess → tests/scripts/test_ai_structure.py --native <modelo>
  │     └── importa tests/lib/model_runner.py → OpenCodeRunner
  │           └── ejecuta: opencode run --dir ../test-ai-config
  │
  └── subprocess → tests/scripts/run_advanced_tests.py <modelo>
        ├── Lee tests/questions/advanced_questions.json
        ├── importa tests/lib/model_runner.py → OpenCodeRunner
        │     └── ejecuta: opencode run --dir ../test-ai-config
        ├── importa tests/lib/advanced_validators.py → valida cada respuesta
        └── Guarda en tests/answers/advanced_validation_report.json
```

### 5. Resumen final

```
run_all_tests.py
  └── Guarda results{} en tests/answers/test_run_summary.json
```

---

## Archivos involucrados

### Orquestador

| Archivo | Rol |
|---------|-----|
| `run_all_tests.py` | Punto de entrada único |

### Scripts de test (se ejecutan como subprocess)

| Archivo | Qué hace |
|---------|----------|
| `tests/unit/test_email_validator.py` | Unit tests de validación de email |
| `tests/scripts/test_validators.py` | Unit tests de los validators (35 tests) |
| `tests/scripts/test_ai_structure.py` | Suite de 5 tests de estructura .ai/ |
| `tests/scripts/run_advanced_tests.py` | Suite de 23 tests avanzados |
| `scripts/generate_html_report.py` | Genera reporte HTML |

### Librerías (importadas por los scripts)

| Archivo | Qué hace |
|---------|----------|
| `tests/lib/model_runner.py` | Interfaz para ejecutar modelos (OpenCodeRunner + GroqRunner) |
| `tests/lib/advanced_validators.py` | Valida respuestas del modelo (jailbreak, factuality, roles, etc.) |
| `tests/lib/validation.py` | Funciones base de validación (_normalize, check_keyword) |
| `tests/lib/opencode_cli.py` | Encuentra el binario de OpenCode |
| `tests/lib/mcp_client.py` | Cliente MCP para tools de memoria (brain-ai) |

### Datos de entrada

| Archivo | Qué contiene |
|---------|--------------|
| `tests/questions/advanced_questions.json` | Las 23 preguntas y criterios de validación |
| `test-ai-config/.ai/system.md` | System prompt del agente (fingerprint) |
| `test-ai-config/.ai/rules.md` | Reglas de seguridad |
| `test-ai-config/.ai/context.md` | Stack tecnológico (React/FastAPI/PostgreSQL) |
| `test-ai-config/.ai/agents.md` | Agentes (QA, Security) |
| `../Verificacion-modelos-ai/.env` | API keys de Groq |

### Datos de salida

| Archivo | Qué contiene |
|---------|--------------|
| `tests/answers/test_run_summary.json` | Resumen: qué tests pasaron/fallaron |
| `tests/answers/ai_validation_report.json` | Resultados de test_ai_structure.py |
| `tests/answers/advanced_validation_report.json` | Resultados de run_advanced_tests.py |

---

## Modelos probados

| Modelo | Tipo | Cuenta |
|--------|------|--------|
| `openai/gpt-oss-20b` | API (Groq) | GROQ_CUENTA_1 |
| `qwen/qwen3.8-27b` | API (Groq) | GROQ_CUENTA_2 |
| `opencode/big-pickle` | Nativo (OpenCode) | — |
| `opencode/mimo-v2.5-free` | Nativo (OpenCode) | — |

---

## Tiempos estimados

| Fase | Duración |
|------|----------|
| Tests locales | ~5s |
| API (por modelo) | ~12-15 min |
| Nativo (por modelo) | ~15-20 min |
| **Total (4 modelos)** | **~45-60 min** |

---

## Comandos útiles para el día a día

```bash
# Suite completa
python run_all_tests.py

# Solo un modelo nativo
python tests/scripts/test_ai_structure.py --native opencode/mimo-v2.5-free
python tests/scripts/run_advanced_tests.py opencode/mimo-v2.5-free

# Solo un modelo API
python tests/scripts/test_ai_structure.py --api openai/gpt-oss-20b
python tests/scripts/run_advanced_tests.py --api openai/gpt-oss-20b

# Unit tests (sin modelo)
python -m pytest tests/unit/test_email_validator.py -v
python tests/scripts/test_validators.py
```
