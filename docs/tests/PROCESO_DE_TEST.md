# Proceso de Test - Suite de Validación .ai/

## Descripción general

La suite de tests valida que el agente de IA lee y respeta los archivos `.ai/` del proyecto, ejecutando preguntas contra múltiples modelos (API Groq y OpenCode nativo) y verificando las respuestas.

---

## Punto de entrada

**Entrada única de la suite completa** (con lock, backup y verificación):

```bash
python scripts/suite_runner.py
```

Lanzarlo **solo** con la herramienta async de tests (una sola llamada,
esperar la notificación):

```text
run_tests(command="python scripts/suite_runner.py",
          cwd="<raiz del proyecto>",
          timeout=5400)
```

No lanzar `run_all_tests.py` a mano para la suite completa: el runner
hace lock anti-duplicados, backup de reportes, preflight (huérfanos +
keys) y gates de verificación al finalizar.

**Prohibido (incidente 23/09/2026):** foreground con timeout de 90 min,
`Start-Process` desde la herramienta shell, lanzar el mismo comando N
veces en paralelo, ni polls con `Start-Sleep` encadenados.

### Qué hace suite_runner.py

```
suite_runner.py
  ├── [Lock]   tests/answers/.suite.lock (exclusivo; exit 2 si ya corre otro)
  ├── [Preflight] exit 3 si falla
  │     ├── mata mcp_bridge.py huerfanos
  │     ├── backup reportes+summary → docs/backup_YYYYMMDD_HHMMSS/
  │     └── verifica GROQ_CUENTA_1/2 presentes (sin imprimir valores)
  ├── [Run]    subprocess → run_all_tests.py
  │     └── stdout+stderr → tests/answers/suite_runner.log (con timestamps)
  └── [Postflight] → tests/answers/suite_verification.json
        gates: summary_nuevo · summary_ok ·
               avanzada (4 modelos × 23) · estructura (4 modelos × 5) · html_nuevo
        exit: 0 todo OK · 1 gate falló · 2 lock · 3 preflight
```

Si un solo gate falla: arreglar **ESA** pieza y re-run selectivo del
sub-script correspondiente (`--api` / `--native` / `--only`); **nunca**
relanzar la suite entera por un eslabón roto.

---

## Flujo completo

### 0. suite_runner (lock + preflight)

```
scripts/suite_runner.py
  ├── adquiere lock .suite.lock (si ocupado → exit 2)
  ├── mata mcp_bridge huerfanos
  ├── backup de reportes → docs/backup_*/
  └── verifica keys en ../Verificacion-modelos-ai/.env
```

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
  ├── subprocess → tests/scripts/test_validators.py       (unit tests de validators)
  └── (el HTML se genera al FINAL, paso 5)
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
run_all_tests.py (por cada modelo: big-pickle, mimo-v2.6-flash-free)
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

### 5. Resumen, HTML y verificación

```
run_all_tests.py
  ├── subprocess → scripts/generate_html_report.py   (reporte HTML consolidado)
  └── Guarda results{} en tests/answers/test_run_summary.json

scripts/suite_runner.py (postflight)
  └── Gates → tests/answers/suite_verification.json
```

---

## Archivos involucrados

### Orquestador

| Archivo | Rol |
|---------|-----|
| `scripts/suite_runner.py` | **Punto de entrada único** (lock + backup + preflight + gates) |
| `run_all_tests.py` | Interno: ejecuta las 4 suites (no lanzar a mano para la suite completa) |

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
| `tests/answers/suite_verification.json` | Gates del postflight (leer esto tras el run) |
| `tests/answers/suite_runner.log` | Log con timestamps del run completo |
| `tests/answers/.suite.lock` | Lock exclusivo (vive mientras corre la suite) |
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
| `opencode/mimo-v2.6-flash-free` | Nativo (OpenCode) | — |

> `opencode/mimo-v2.5-free` quedó **retirado** el 23/09/2026 (fuera del
> catálogo OpenCode; CLI devolvía `UnknownError`).

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
# Suite completa (UNICO entrypoint — con lock, backup y gates)
python scripts/suite_runner.py
# Lanzar via run_tests async con timeout 5400; NO en foreground

# Diagnóstico tras un run
python -c "import json; print(json.load(open('tests/answers/suite_verification.json'))['gates'])"
python scripts/analyze_times.py --top 8

# Solo un modelo nativo (sub-runs cortos; sin lock)
python tests/scripts/test_ai_structure.py --native opencode/mimo-v2.6-flash-free
python tests/scripts/run_advanced_tests.py opencode/mimo-v2.6-flash-free

# Solo un modelo API
python tests/scripts/test_ai_structure.py --api openai/gpt-oss-20b
python tests/scripts/run_advanced_tests.py --api openai/gpt-oss-20b
python tests/scripts/run_advanced_tests.py --api qwen/qwen3.8-27b

# Unit tests (sin modelo)
python -m pytest tests -q
python tests/scripts/test_validators.py
```
