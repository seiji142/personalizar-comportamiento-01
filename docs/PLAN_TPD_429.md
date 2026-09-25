# Plan: 429 TPD diario — cuota agotada ≠ fallo del modelo

**Creado:** 23/09/2026 · **Estado:** PLAN (no ejecutado)
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
cuentan `n` entradas, no estados: gpt-oss pasó esos gates con 5 FAIL +
23 ERROR. Incluir en la tarea 15 o en fix posterior que exijan PASS /
sin `[ERROR]`.
