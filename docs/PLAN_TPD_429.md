# Plan: 429 TPD diario — cuota agotada ≠ fallo del modelo

**Creado:** 23/09/2026 · **Estado:** EJECUTADO (25/09/2026 — pasos 0-5 +
fix de gates completados; ver §Ejecución abajo)
**Padre:** `docs/TAREAS_PENDIENTES.md` → tarea 15
**Disparador:** suite nocturna 23/09 — qwen 17/23 ERROR y gpt-oss 0/28,
ambos 429 "tokens per day" (Used ~195k-199k / 200k). El usuario tuvo que
recordar que ya existían fixes previos de 429 → este documento evita
re-diagnosticar lo resuelto.

---

## HISTORIAL: qué ya está arreglado (NO repetir)

| Fecha | Fix | Dónde queda | Verificación |
|---|---|---|---|
| 16/09 | **Retry con backoff 429** en `model_runner.py:288-319` (MAX_RETRIES=3, espera 5s/10s/20s) + flag `--only-failures` + pausa entre modelos | `TAREAS_PENDIENTES.md` §Rate Limit Fix | Commit del fix |
| 21/09 | Retry verificado **funcionando** con 429 transitorio: *"1×[RATE LIMIT] en C2 resuelto con backoff 5s (intento 1/3)"* | `sesion_20260921.md:424` | — |
| 23/09 (T7) | Diagnóstico: 1135s históricos = esperas de 429 TPD, NO lentitud; gpt-oss re-incluido con wall 880s | `TAREAS_PENDIENTES.md` §T7 | Suite T7 |

**Verificar ANTES de proponer cualquier fix 429:**
1. ¿Existe ya el retry en `model_runner.py`? → NO reimplementar.
2. ¿Está documentado en `RESULTADOS_TEST_AI.md` ("ERROR son 429 de Groq,
   sin rate limit el score real sería ~22/23")? → NO duplicar diagnóstico.
3. ¿Es el MISMO tipo de 429? → distinguir abajo.

---

## Qué se arregló y qué NO (aclaración — 25/09)

> **Pregunta que originó esto: "¿se arregló el 429?"**
>
> - **SÍ se arregló el MANEJO del 429** (era lo que era bug nuestro):
>   ya no se disfraza de fallo (estado `BLOCKED_TPD` en vez de 17-23 ERROR
>   rojos), fail-fast en 1 intento (sin 3 esperas inútiles de 9-36 min),
>   sondeo previo por cuenta (`quota_probe.py`) antes de gastar, gates que
>   exigen estados (el flaw de contar solo `n`), y el bug del case
>   `"[ERROR]"`/`"[error]"` que hacía que el texto de la cuota contara como
>   FAIL de comportamiento en estructura.
> - **NO se arregla (ni es arreglable) la cuota de Groq**: 200k tokens/día
>   por cuenta es límite externo. Si se agota, la cuenta queda
>   `BLOCKED_TPD` hasta mañana y la suite corre solo con los modelos
>   disponibles (nativos + cuentas con cuota). Se **gestiona**, no se
>   elimina. `BLOCKED_TPD ≠ FAIL`.

---

## Por qué "volvió": dos clases de 429 distintas

| Clase | Mensaje API | El retry actual (5/10/20s) |
|---|---|---|
| **Transitorio** (RPM/ventana corta) | "try again in 5s" | Lo resuelve ✅ (verificado 21/09 y 23/09) |
| **TPD diario** (cuota de tokens/día) | "tokens per day: Used 195k/200k, try again in 9m-36m" | **Nunca va a alcanzar**: 35s de presupuesto vs espera de 9-36 min ❌ |

Anoche: qwen gastó 3 retry × 17 tests ≈ 10 min de esperas fútiles contra
cuota que pedía hasta 36 min. **El retry no falló: le pidieron imposible.**

Causa de fondo: el mismo día se consumió el TPD de AMBAS cuentas
(sondeo T7 + suite completa), no un bug de código.

---

## Plan (sin tocar el retry existente)

| # | Acción | Por qué cierra el ciclo |
|---|---|---|
| 0 | **Sondeo de cuota**: 1 query mínima por cuenta al inicio (estructura o 1 test) | Saber HOY si hay TPD antes de gastar |
| 1 | **Detección de TPD diario en el 429**: si mensaje contiene `tokens per day` o `try again in >2min` → **fail-fast**: 1 intento, no 3; marcar modelo **`BLOCKED_TPD`** y cortar el resto de tests | 17 ERRORs rojos → 1 estado claro "cuota agotada, reintentar mañana" |
| 2 | Si 429 dice `try again in ≤90s` → **esperar ese tiempo exacto** (parsear el número) en vez de 5/10/20 ciego | Mejora el fix existente sin reemplazarlo |
| 3 | **Preflight en `suite_runner`**: cuenta BLOCKED → correr solo modelos con cuota (nativos) + gate `api_disponible` (BLOCKED ≠ FAIL) | La suite deja de "fallar" por algo que no es fallo |
| 4 | **Reparación de anoche solo si hay cuota hoy**: qwen `--only-failures` (17) · gpt-oss estructura + `--only-failures` (28) · mimo `--only D8,D9` | Sin cuota → documentado como BLOCKED, no FAIL |
| 5 | **Presupuesto documentado**: en `RESULTADOS_TEST_AI.md` registrar consumo diario por cuenta (los 429 traen `Used`/`Limit`) | Evita repetir la corrida sin mirar cuota |

## Lo que NO se va a hacer

- Reimplementar el retry 429 ni subir `MAX_RETRIES`.
- Esperas largas (minutos) dentro del suite por TPD.
- Reescribir resultados fallidos como PASS (el summary es histórico).

## Reparaciones pendientes del run 23/09 (referencia)

- qwen avanzada: 6/23 → faltan 17 (`B1-B4, C1-C3, D1-D9, L1`)
- gpt-oss: estructura 0/5 (429) + avanzada 0/23 (429)
- mimo avanzada: 21/23 → faltan `D8, D9` (rate limit free tier, timeout 1200s)
- Estructura qwen/big-pickle/mimo: OK, no tocar.

## Flaw conocido de los gates (del run 23/09)

Los gates `estructura_4x5` y `avanzada_4x23` de `suite_runner.py` solo
contaban `n` entradas, no estados: gpt-oss pasó esos gates con 5 FAIL +
23 ERROR. **FIX (25/09):** `suite_runner.model_gate()` exige `n` exacto
y estados en `{PASS, BLOCKED_TPD}`; FAIL/TIMEOUT/ERROR rompen el gate.
Nuevo gate `api_disponible` (sondeo de cuota; BLOCKED_TPD ≠ FAIL) y
`summary_ok` ahora acepta `BLOCKED_TPD` además de `OK`.

---

## Ejecución 25/09/2026 (decisiones del usuario registradas en memoria)

Decisiones aprobadas: (1) gates exigen PASS con BLOCKED_TPD permitido;
(2) reclasificar ERROR/FAIL con evidencia de 429-TPD a BLOCKED_TPD;
(3) alcance 0-3 + gates + tests primero, paso 4 solo si hay cuota.

### Implementado (pasos 0-3)

| Paso | Qué | Dónde |
|---|---|---|
| 0 | `tests/scripts/quota_probe.py` — 1 query mínima/cuenta → `tests/answers/quota_status.json` (status, Used/Limit si hay 429, headers x-ratelimit) | Sondeo standalone + preflight |
| 0 | `tests/lib/rate_limit.py` — parser puro: `parse_rate_limit` (TPD vs transitorio), `classify_probe`, `reclassify_report_tpd/_file_tpd`, `compute_wait` | Compartido |
| 1 | Detección TPD fail-fast: `GroqRunner` marca `tpd_blocked`, 1 intento, sin sleep, error `[BLOCKED_TPD]`; `run_advanced_tests` status `BLOCKED_TPD` + corta el resto de tests; `test_ai_structure` idem | `model_runner.py`, `run_advanced_tests.py`, `test_ai_structure.py` |
| 1 | **Fix case-sensitivity**: `test_ai_structure.run_test` comparaba `"[error]"` y `query_api` devolvía `"[ERROR]"` → el texto del 429 caía al validador y contaba como FAIL de comportamiento (era el "5 FAIL" de gpt-oss). Nuevo `reply_status()` puro y testeado | `test_ai_structure.py` |
| 2 | Espera exacta si 429 indica `try again in ≤90s` (+1s), si no backoff original 5/10/20s; `query_api` de estructura ahora tiene retry (antes no tenía ninguno) | `rate_limit.compute_wait` + ambos runners |
| 3 | Preflight corre el sondeo (fallo → exit 3); `run_all_tests` salta cuentas BLOCKED_TPD (marca el summary y reclasifica), exit 7 → `BLOCKED_TPD` en summary | `suite_runner.py`, `run_all_tests.py` |
| — | `--only-failures` ahora re-ejecuta también casos `BLOCKED_TPD` (con cuota pasan a PASS; sin cuota vuelven a BLOCKED_TPD sin gastar API) | ambos scripts |

Retry de 16/09 (`model_runner.py` MAX_RETRIES=3, backoff 5/10/20s):
**intacto y no reimplementado** — solo se le añadió el parse de espera
exacta y el corte TPD antes de gastar reintentos.

### Verificación

- **Unit tests:** `tests/scripts/test_rate_limit_tpd.py` — 38 tests
  (parser con mensajes 429 reales del 23/09, espera exacta, classify,
  reclasificación, `reply_status` regression, corte de `run_cases`,
  gates con estados). Suite: pytest 113 + validators 55 + merge 6 +
  email 3 = **todos PASS**.
- **Sondeo real 25/09 14:25-14:26:** `GROQ_CUENTA_1` OK, `GROQ_CUENTA_2`
  OK (headers RPM/TPM: 1000 req, 8000 tokens/ventana).
- **Gates contra reportes previos (antes de reparar):** `avanzada_4x23`
  False (bad=23 gpt-oss, bad=17 qwen), `estructura_4x5` False (bad=1) —
  el gate ahora ve los estados que antes ignoraba.
- **Paso 4a:** gpt-oss estructura `--only-failures` → 4 PASS + 1 FAIL
  (keyword `qa`, comportamiento del modelo; ya no hay 429 disfrazado).

### Paso 4 — Reparación del run 23/09 (25/09 14:26-15:24, sondeo OK)

| Run | Resultado |
|---|---|
| gpt-oss estructura `--only-failures` (5) | 4 PASS + 1 FAIL (T4 keyword `qa`) |
| qwen avanzada `--only` 17 IDs | 16 PASS + 1 D8 TIMEOUT → retry: ERROR max-tool-rounds (2 intentos, comportamiento) |
| gpt-oss avanzada `--only-failures` (23) | 21 PASS + C2/D9 FAIL (comportamiento) + D3 ERROR → retry PASS |
| mimo `--only D8,D9` | 2/2 PASS → mimo 23/23 |

Evidencia del backoff mejorado en vivo: `[RATE LIMIT] Esperando 2.7325s
(intento 1/3)... PASS` (espera exacta de un 429 transitorio en D4 gpt-oss)
y `Esperando 44.5343s` en la corrida de qwen.

**Estado final de reportes (25/09):** avanzada gpt-oss 21/23, qwen 22/23,
big-pickle 23/23, mimo 23/23 · estructura 4/5 + 5/5 + 5/5 + 5/5.
**Cero casos con ERROR por 429.** Gates: `api_disponible` OK (ambas
cuentas); `avanzada_4x23` y `estructura_4x5` en rojo SOLO por FAIL/ERROR
de comportamiento (C2, D9, D8 tool-rounds, T4 `qa`) — exactamente lo que
el gate estricto debe mostrar.

### Paso 5 — Registro de consumo

Sección "Consumo diario TPD por cuenta" en
`docs/tests/RESULTADOS_TEST_AI.md` (tabla con Used/Limit de los 429 del
23/09 y sondeos del 25/09) + `tests/answers/quota_status.json`
machine-readable (incluye headers x-ratelimit RPM/TPM).
