# Diagnóstico: MCP desconectado, guardado sin proyecto y episodio invisible

**Creado:** 2026-09-28 23:20 (local, UTC-3)
**Actualizado:** 2026-09-28 23:55 (decisiones aplicadas, §6)
**Estado:** INVESTIGACIÓN CERRADA. **Decisiones tomadas 28/09:** 16L implementada en
`brain-ai-01` (`4eca553`, local); 16M = C3 aplicado / C1 pendiente. 16N, 16O siguen sin decisión.
**Alcance:** `../brain-ai-01` (bridge + cliente) y este repo (documentación).
**Relacionado:** `docs/PLAN_CONVENCION_TOOLS_MCP.md` (16J, cerrado), ítems 16I y 16K de
`docs/TAREAS_PENDIENTES.md`.

> Este documento es para leer y decidir. Cada hallazgo tiene: qué se investigó, con qué
> evidencia, **qué NO se sabe**, y la propuesta con sus alternativas y consecuencias.
> Las 3 decisiones de §6 fueron tomadas el 28/09 23:40 y ya están aplicadas (ver §5).

---

## 0. Resumen ejecutivo

| # | Hallazgo | Dónde | Veredicto | Propuesta |
|---|---|---|---|---|
| **A** | El MCP `brain-ai` no estaba en el esquema de la sesión interactiva | `opencode.log` | **Causa raíz encontrada**: la conexión murió en el proceso de larga duración 1,9 s después de lanzar la suite completa y nunca volvió. Resuelto reiniciando OpenCode | 16N: documentar el criterio + script de diagnóstico |
| **B** | No se debe guardar un episodio sin `project` | `mcp_bridge.py:456` | **El servidor ya valida**; el puente no, y sus dos modos de fallo dan mensajes inútiles al modelo | 16L: validar en el bridge + desenvolver `detail` |
| **C** | `memory_search` solo busca en `semantic` por defecto | `mcp_bridge.py:433` | **Contradicción con la documentación**: `.ai/MEMORY.md` dice que combina episódica + semántica; el schema y el código buscan solo una, con default `semantic` | 16M: decidir si se cambia el default o la documentación |

**Los tres son independientes entre sí.** B no tiene relación con A ni con C. C explica por qué
un episodio recién guardado puede ser invisible, pero **no explica** el caso concreto que
disparó la investigación (ver §4.5: hay un segundo factor sin confirmar).

---

## 1. Cronología

Hora local = **UTC-3** (Montevideo). El log de OpenCode escribe en UTC (`Z`); la conversión
importa porque una conclusión anterior quedó mal convertida y se corrigió (ver §2.6).

| Local | UTC | Qué pasó | Fuente |
|---|---|---|---|
| 26/09 10:55:02 | 13:55:02Z | Arranca el proceso OpenCode de larga duración `run=d5c3b641` (el que sirvió la sesión anterior y la mía) | log:203102 |
| 26/09 11:47:36 | 14:47:36Z | `WARN server unavailable key=brain-ai type=local status=failed` (y lo mismo para `git_publisher`) | log:205153-205154 |
| 28/09 12:33:08 | 15:33:08Z | La tool **funciona** en ese mismo proceso: `evaluated permission=brain-ai_memory_search ... allow` | log:206713 |
| 28/09 **12:34:17** | 15:34:17Z | Alguien lanza `python scripts/suite_runner.py` | log:206778 |
| 28/09 **12:34:19** | 15:34:19Z | **3 × `WARN MCP connection closed server=brain-ai`** — 1,9 s después | log:206779-206781 |
| 28/09 12:34-13:35 | — | Suite completa (coincide con `docs/tests/sesion_20260928.md`: "12:34-13:35") | sesión doc |
| 28/09 21:00-21:50 | — | Sesión de 16J Fase 0/1/3. **Sin MCP conectado**; se usó el cliente Python como fallback | sesión doc |
| 28/09 22:30-22:36 | 01:30-01:36Z | Trabajo de la Fase 2. Los procesos **hijos** `opencode run --dir test-ai-config` (runs `e9503ec7`, `cd293f69`, `4b512d89`) **sí** usan `brain-ai_memory_search/save` | log:217651-217751 |
| 28/09 22:50:11 | 01:50:11Z | Arranca mi sesión: `booting location services` para `personalizar-comportamiento-01`, **sin ninguna tool `brain-ai_*` en el esquema** | log:218202 |
| 28/09 22:54:10 | 01:54:10Z | Guardo el episodio `ep_0c550738…` vía `memoria.guardar` (cliente Python) porque el MCP no estaba | `logs/traces/ingest.jsonl` |
| 28/09 23:05:14 | 02:05:14Z | **Reinicio de OpenCode** por parte del usuario → proceso nuevo `run=376417c8` | log:218583-588 |
| 28/09 23:06-23:15 | — | Verificación: las **10** tools `brain-ai_*` presentes y una llamada real a `brain-ai_memory_search` devuelve resultados | esta sesión |

---

## 2. Hallazgo A — el MCP `brain-ai` no estaba en el esquema

### 2.1 Síntoma exacto

En la sesión del 28/09 22:50 el modelo (yo) tenía en su esquema 4 tools `git_publisher_*` y
**cero** tools `brain-ai_*`, aunque el proyecto declara el server en `opencode.json` con
`"enabled": true` y el servicio REST responde. `list_mcp_resources` devolvía `[]` (pero eso no
prueba nada: ver §2.3).

### 2.2 Descartes: qué NO era (con evidencia)

| Hipótesis | Veredicto | Cómo se descartó |
|---|---|---|
| El servicio está caído | **Falso** | `GET localhost:8000/health` → `{"ok":true}` en 5 s, dos veces |
| El `opencode.json` está mal | **Falso** | El server `brain-ai` está declarado con `enabled: true`; además el **mismo** config funcionó 12:33:08 en el mismo proceso (log:206713) |
| La ruta del bridge está mal | **Falso** | `Test-Path` del path absoluto de `mcp_bridge.py` (de `opencode.json`) → `True` |
| `python` no resuelve | **Falso** | `Get-Command python` → `C:\Users\seiji\AppData\Local\Programs\Python\Python310\python.exe` |
| El bridge está roto | **Falso** | Los procesos hijos de los tests D1-D3 de las 22:35 lo usaron y las tools se ejecutaron `success: true` |
| Es el problema de nombres de 16J | **Falso** | El log registra `brain-ai_memory_search` con guion; el nombre es correcto |
| El server falta en el config global | **Esperado** | `~/.config/opencode/opencode.jsonc` solo declara `git_publisher`; `brain-ai` viene del config del proyecto. Correcto |

### 2.3 El mecanismo: dos cosas distintas que se confunden

| | Qué es | Cómo se verifica |
|---|---|---|
| **Backend REST** | Un servicio que escucha en `localhost:8000` (FastAPI). Siempre vivo, independiente de OpenCode | `GET /health` |
| **MCP `brain-ai`** | Un **subproceso stdio** que OpenCode lanza por proceso y que habla JSON-RPC por stdin/stdout. Traduce tool calls a HTTP contra el backend | `command` en `opencode.json`; aparece en el esquema del modelo |

`/health` verde dice que el backend está bien. **No dice nada** sobre si el bridge llegó a ser
lanzado por OpenCode. Por eso el health check no era evidencia de nada.

Corolario: `list_mcp_resources` tampoco sirve como señal. Un server MCP que solo declara
**tools** (como `brain-ai` y `git_publisher`) devuelve `[]` aunque esté conectado. La única
señal válida es **que las tools aparezcan en el esquema** o que una llamada real funcione.

### 2.4 La evidencia que cierra el caso

Tres cosas en el log, en orden:

1. **28/09 12:33:08** — la tool se evaluó y se permitió en el proceso `d5c3b641`:
   `evaluated permission=brain-ai_memory_search pattern=* ... action.action=allow`
2. **28/09 12:34:17** — se lanza `python scripts/suite_runner.py`
3. **28/09 12:34:19** — `MCP connection closed server=brain-ai` **×3**, y **no vuelve a
   aparecer una sola línea** de `brain-ai` en ese proceso desde entonces (salvo mis propias
   llamadas a `memoria.py` por bash, que no son tools)

Y el contraste decisivo: **procesos nuevos** de OpenCode (`opencode run --dir test-ai-config`,
los que lanza el propio harness) **sí** conectan y **sí** usan las tools. Mismo config, mismo
bridge, mismo backend. Lo único que cambia es el proceso.

**Causa raíz:** el proceso OpenCode de larga duración perdió la conexión del bridge y no la
relevanta. Como el esquema de tools de una sesión se arma con lo que el proceso tiene
registrado, todas las sesiones de ese proceso quedaron sin `brain-ai_*` — la del 28/09 de la
noche y la mía.

### 2.5 Qué NO se sabe (importante)

- **Por qué murió el bridge.** No hay error ni excepción asociada a esas 3 líneas, solo el
  cierre. Correlación temporal fuerte con el arranque de la suite, pero **correlación no es
  causalidad**: no puedo afirmar que la suite lo mató. Descartadas las explicaciones fáciles
  (config, path, python, servicio, proceso muerto), queda sin explicar.
- **Por qué 3 cierres a la vez.** Hay 3 conexiones abiertas (una por location con el server
  cargado: este repo, `test-ai-config`, `youtube-transcripts` — se ven los boots en
  log:218122-218156). No verifiqué si las 3 cerraron porque las 3 estaban vivas o porque el
  proceso bridged era uno solo compartido.
- **Por qué `git_publisher` sobrevivió** si también se había marcado `unavailable` el 26/09.
  Se recuperó; `brain-ai` no. No verifiqué el mecanismo de reconexión.
- Si el 26/09 11:47:36 (`server unavailable ... status=failed`) y la muerte del 28/09 son el
  mismo problema o dos distintos. **Sin verificar.**

### 2.6 Corrección de una conclusión anterior

Informé en su momento que la conexión había muerto a las **18:34**. Era una conversión
UTC→local mal hecha. **La hora correcta es 12:34:19 local**, que es además la que coincide con
el inicio de la suite completa en `sesion_20260928.md`. La conclusión no cambia (la conexión
murió al arrancar la suite), pero la hora sí, y ahora es coherente con el resto de la evidencia.

### 2.7 Verificación tras el reinicio (hecho)

| Verificación | Resultado |
|---|---|
| Tools `brain-ai_*` en el esquema | **10 presentes** (antes 0) |
| `brain-ai_memory_search` (llamada real) | Devuelve resultados con score y proyecto |
| Proceso | Nuevo: `run=376417c8` (distinto de `d5c3b641`) |
| `server unavailable` / `MCP connection closed` nuevos | **Ninguno** |

**Conclusión: el MCP funciona.** El remedio fue reiniciar OpenCode, sin tocar código.

### 2.8 Propuesta A (tarea 16N)

**A1 — Documentar el criterio de diagnóstico.** Hoy cada sesión que encuentra el MCP ausente
reinventa su propio diagnóstico, y el `.ai/` no dice qué hacer. Falta en el criterio de uso que
propone `PLAN_CONVENCION_TOOLS_MCP.md` §7.4 el caso 3 (hoy solo cubre `unavailable tool` y
`not in request.tools`). Propuesta de texto para `.ai/rules.md` y §7.4:

> Si una tool MCP no está en el esquema: (1) no asumas caída del servicio — verificá
> `GET /health`; (2) buscá en `~/.local/share/opencode/log/opencode.log` las líneas
> `MCP connection closed server=<nombre>` y `server unavailable key=<nombre>`; (3) si la última
> conexión murió y no hay reintento posterior, **reiniciá OpenCode**: el proceso de larga
> duración no reconecta. La señal de que volvió es que la tool aparezca en el esquema.

**A2 — Script de diagnóstico.** `tests/scripts/verificar_mcp_esquema.py`, siguiendo la
convención de los `verificar_*.py` que ya existen. Leería el log y respondería en una línea:
qué servers están declarados, cuál se conectó y cuándo, cuál murió y cuándo, y cuál fue el
último tool call de cada uno. Convierte el hallazgo de hoy en un comando. Requiere decidir si
lee solo el log o además consulta el esquema.

**A3 — Deuda menor ya identificada.** `~/.config/opencode/PLANTILLA_MCP.md:44` dice
`toolCount=8`; el bridge expone **10** tools (deuda de `PLAN_CONVENCION_TOOLS_MCP.md` §7.5).
Es config global, fuera de este repo: por eso lo señalo y no lo toco.

**A4 — Descartado, con motivo.** Poner el path absoluto de `python` en el `opencode.json` del
proyecto (como hace `git_publisher` en el global). **No lo recomiendo:** contradice el "no
tocar los `opencode.json`" de `PLAN_CONVENCION_TOOLS_MCP.md` §9.1 y **la evidencia no lo
sostiene** — los procesos hijos arrancan el bridge perfectamente con `python` a secas.

**No propuesto a propósito:** nada más. Reiniciar el proceso es lo que funciona; no hay nada que
"arreglar" en código para la causa raíz mientras no se sepa por qué murió el bridge.

---

## 3. Hallazgo B — no se debe guardar un episodio sin `project`

### 3.1 Lo que pediste

Que el guardado no pueda ocurrir sin proyecto, señalando `mcp_bridge.py`:
`"project": args["project"],`.

### 3.2 Lo que YA existe: el servidor valida

`../brain-ai-01/ai_architect/pipelines/ingest.py:9`

```python
REQUIRED = ["project", "source_type", "author", "title", "summary", "timestamp"]
```

`validate_episode` (línea 11-14) rechaza `None` o `""` con `"Missing required field: project"`,
y `mcp_server.py:270-275` lo convierte en **HTTP 400**.

**Consecuencia: hoy no se está guardando nada sin proyecto.** El riesgo no es corrupción de
datos, es que el fallo sea invisible o confuso.

### 3.3 Los dos defectos del puente

`handle_memory_save` (`mcp_bridge.py:456-476`) no valida nada y confunde la forma de la
respuesta de error:

| Qué manda el modelo | Qué pasa realmente | Qué ve el modelo |
|---|---|---|
| Call **sin** la key `project` | `args["project"]` → `KeyError` en la línea 460; lo atrapa el dispatcher (línea 643) | `Error ejecutando memory_save: 'project'` — un `KeyError` crudo, sin decir qué hacer |
| `project: ""` o `null` | POST a `/ingest` → 400; `_api_request` hace `r.json()` y devuelve `{"detail": {"ok": false, "error": "Missing required field: project", ...}}`; la línea 474 mira `result.get("error")`, que no existe en ese nivel | **`Error al guardar: Unknown error`** — el motivo real queda enterrado en `detail` |

El segundo caso es el peor: el sistema **sí** tiene la respuesta correcta en la mano y la
descarta. Un modelo que se equivoca al mandar el proyecto recibe "Unknown error" y no tiene
forma de corregirse.

### 3.4 Propuesta B (tarea 16L) — el cuerpo propuesto

```python
def handle_memory_save(args):
    """Guarda un episodio en memoria."""
    project = (args.get("project") or "").strip()
    decision = (args.get("decision") or "").strip()
    if not project:
        return ("Error al guardar: falta 'project'. Es obligatorio: cada episodio se guarda "
                "bajo un proyecto y sin el no se puede recuperar. "
                "Ej.: project='personalizar-comportamiento-01'")
    if not decision:
        return "Error al guardar: falta 'decision' (texto de la decisión o lección aprendida)."
    result = _api_request("/ingest", {
        "episode": {
            "project": project,
            "source_type": "chat",
            "author": "modelo",
            "title": decision[:50],
            "summary": decision,
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "decisions": [{"text": decision}],
            "evidence": [{"type": "doc", "url_or_path": "",
                          "excerpt": args.get("evidence", "")}] if args.get("evidence") else [],
            "tags": args.get("tags", [])
        }
    })

    if result.get("ok"):
        episode_id = result.get("episode_id", "unknown")
        return f"Episodio guardado exitosamente. ID: {episode_id}"

    # El servidor envuelve el error en "detail" cuando responde 400; sin esto
    # el modelo ve "Unknown error" y no puede corregir la llamada.
    detail = result.get("error") or (result.get("detail") or {}).get("error") or result.get("detail")
    return f"Error al guardar: {detail or 'respuesta sin detalle del servidor'}"
```

Qué cambia, en una línea: se validan `project` y `decision` **antes** de gastar un request
(sin HTTP en el caso de error), y el error real del servidor llega al modelo.

**Por qué en el puente y no solo en el servidor:** el servidor ya es la última línea (y está
bien). La validación en el bridge existe para (a) no gastar un round-trip en un error previsible
y (b) devolver un mensaje que el modelo pueda corregir. Es defensa en profundidad, no
sustitución.

### 3.5 El cliente Python tiene el mismo hueco

`clients/memoria.py:99` — `def guardar(proyecto, decision, ...)`: `proyecto` es posicional
obligatorio, pero `guardar(None, ...)` o `guardar("", ...)` pasa el chequeo y se va al 400 sin
explicar. Propuesta: `ValueError` temprano con el mismo mensaje. Es una línea y hace que el
fallback en Python sea tan honesto como el MCP.

### 3.6 Tests a agregar

`../brain-ai-01/tests/test_mcp_bridge_validacion.py`, con fakes (sin HTTP, sin servidor),
siguiendo el estilo de `test_memory.py`. Casos:

1. `project` ausente → mensaje accionable, **0 requests** hechos
2. `project: ""` → ídem
3. `project: "   "` (solo espacios) → ídem
4. `decision` ausente o vacía → mensaje accionable, 0 requests
5. `project` + `decision` válidos → 1 request, devuelve `Episodio guardado...`
6. El servidor responde `{"detail": {"error": "Missing required field: project"}}` → el texto
   que vuelve al modelo **contiene** el motivo, no `Unknown error`

Al escribirlos hay que confirmar que **importar `mcp_bridge` no tiene efectos secundarios**
(el `if __name__ == "__main__"` y la ausencia de I/O a nivel de módulo lo sugieren, pero no lo
verifiqué).

### 3.7 Decisiones que necesito para B

1. **¿Se toca la `description` de `memory_save`?** El `inputSchema` ya declara
   `"required": ["project", "decision"]` (línea 207), así que la validación no la necesita.
   Pero esa descripción viaja en el schema que el harness publica a Groq en D1-D3: cambiarla
   cambia la request y obliga a re-correr la suite — el mismo argumento que §8.4 del plan 16J
   con `test-ai-config`. **Recomiendo no tocarla.**
2. **¿Dónde se commitea?** `brain-ai-01` está en la rama **`main-clean`**, no en `develop`, y
   es otro repo con sus propias convenciones. ¿Aplico el cambio solo en disco, o commiteo en
   `main-clean` también?

---

## 4. Hallazgo C — `memory_search` solo busca en `semantic`

### 4.1 Lo que dice la documentación vs lo que hace el código

| Fuente | Qué dice |
|---|---|
| `.ai/MEMORY.md` (este repo, y los otros 5) | "Combina búsqueda episódica + semántica"; el tool "Busca episodios **y** conocimiento" |
| `mcp_bridge.py:433` | `"collection": args.get("collection", "semantic")` |
| `mcp_bridge.py:168-173` (schema) | `collection`: enum `["semantic","episodic"]`, `default: "semantic"` |
| `clients/memoria.py:114-143` | `buscar()` con `collection=None` busca en **`["episodic","semantic"]`** (las dos) |
| `mcp_server.py:244` | `collection: str = "semantic"` |

**Tres de cinco fuentes dicen "las dos"; el camino MCP busca una sola.** Consecuencia
operativa: un episodio recién guardado vive en la colección **episodic** hasta que la
consolidación lo promueve, así que **durante esa ventana es invisible por la vía MCP** salvo que
el modelo pida `collection="episodic"` explícitamente.

### 4.2 El episodio que disparó la investigación: **sí está guardado**

No hay pérdida de datos. Evidencia:

| Verificación | Resultado |
|---|---|
| `logs/traces/ingest.jsonl`, última línea | `{"ts": "2026-09-29T01:54:10Z", "operation": "ingest", "episode_id": "ep_0c550738ea5d461e8cc058d898b32356", "project": "personalizar-comportamiento-01"}` |
| `memory/episodic/ep_0c550738ea5d461e8cc058d898b32356.json` | Existe, 4951 bytes, 28/09 22:54 |
| `logs/traces/failures.jsonl` | Última modificación **25/09 15:53**: ningún fallo de `ingest` ni de `ingest_index` desde entonces |

Es decir: pasó la validación (incluido `project`), se guardó y **no se registró ningún error de
indexado**.

### 4.3 Búsquedas que no lo encontraron (4)

| # | Query | Colección | Resultado |
|---|---|---|---|
| 1 | `16J convencion de nombres de tools MCP brain-ai` | default (semantic) | 3 resultados, ninguno mío (top: 0.92, un item de `.ai/` de `test-ai-config`) |
| 2 | `discover_server_name publicar cada tool MCP con el nombre real de OpenCode` | episodic | El **handoff** de 16J (0.91), el mío ausente |
| 3 | `16K finish_reason GroqRunner tool call truncada 800 tokens` | default | 3 resultados, el mío ausente |
| 4 | su título literal-ish | episodic | 3 resultados no relacionados (0.90/0.43/0.38) |

Como contraste, la query 2 **sí** devolvió el episodio handoff (`ep_d92dc638…`), que también es
episódico. O sea que la búsqueda sí funciona en general; mi episodio es el que no aparece.

### 4.4 Un dato de ruido que hay que tener en cuenta

En la query 4, cuyo texto es casi el título exacto del episodio, el resultado número 1 (0.90) fue
un item sobre `ESTADO_PROVENANCE.md`, sin relación alguna. Y en la query 3 aparecieron dos
episodios sobre validación de email con score 0.22 frente a un 0.92 de provenance. **El ranking
por similitud es ruidoso**: texto largo y muy específico rinde mal.

### 4.5 Qué NO se sabe (y por qué no lo averigué)

- **Si mi episodio está indexado en la colección `episodic` de Chroma.** No lo verifiqué. Es la
  causa más probable del caso concreto, y es distinta del default `semantic`.
- **Por qué el ranking es tan ruidoso** para queries largas/específicas.
- Si el filtro estricto por proyecto (`retrieval.py:8-16`, `where["project"] = project`) juega
 bien con un episodio de 4951 bytes con `evidence` larga.

Paré la investigación acá a propósito: es un agujero de recuperación, no un problema de nombres,
y el usuario pidió no complicar la sesión.

### 4.6 Propuesta C (tarea 16M) — dos caminos distintos, hay que elegir

**Opción C1 — arreglar el default (cambia código).** Que `memory_search` busque en las dos
colecciones y las combine, como hace `memoria.buscar()`. Implica: el `enum` del schema pasa a
admitir un valor `"both"` (o se quita el enum y se documenta que `None` = ambas). **Riesgo:** el
schema de tools es lo que ve el modelo, y `memory_search` participa en D1 y D3. Cambiarlo cambia
la request de esos tests y, si además cambia el default, **obliga a re-correr la suite** para que
los resultados sean comparables.

**Opción C2 — arreglar la documentación (cambia `.ai/`).** Decidir que el default `semantic` es
el correcto y corregir `.ai/MEMORY.md` en los 6 repos, para que la documentación deje de prometer
una búsqueda combinada. **Costo:** bajo, sin riesgo de suite, pero deja la limitación real (un
episodio recién guardado no se encuentra) como una trampa documentada en vez de resuelta.

**Opción C3 — solo documentar el criterio de uso.** Sin tocar código ni `.ai/`: anotar que
para encontrar algo recién guardado hay que pasar `collection="episodic"`. Es el mínimo
honesto, y sirve aunque después se haga C1 o C2.

**Recomiendo C3 ahora y C1 después de la suite completa**, para no mezclar un cambio de
comportamiento en la búsqueda con el re-run que ya hay pendiente. **No recomiendo C2 sola**:
deja la trampa instalada en 6 repos.

---

## 5. Tareas que se deben hacer

| # | Tarea | Repo | Prioridad | Estado | Depende de |
|---|---|---|---|---|---|
| **16L** | Bridge: no guardar sin `project` (validar `project` y `decision` + desenvolver `detail`) | `brain-ai-01` | **Alta** — pedido explícito | **HECHA 28/09**, commit `4eca553` en `main-clean` (local) (§3) | — |
| **16L.b** | Cliente `memoria.guardar`: `ValueError` si `proyecto` vacío | `brain-ai-01` | Media | **HECHA** (mismo commit) | — |
| **16L.c** | `tests/test_mcp_bridge_validacion.py` (6 casos) | `brain-ai-01` | Media | **HECHA — 6/6 pass** (mismo commit) | — |
| **16M** | `memory_search`: default `semantic` vs documentado "combina ambas" | `brain-ai-01` + 6 `.ai/` | Media | **C3 aplicado** (`.ai/MEMORY.md` de este repo); **C1 pendiente** (§4.6) | C1: después de la suite |
| **16N** | Documentar el criterio "MCP ausente del esquema ≠ servicio caído" + script de diagnóstico | este repo | Media | Propuesta (§2.8), **sin decisión** | — |
| **16O** | `PLANTILLA_MCP.md:44` dice `toolCount=8`, son 10 | config global | Baja | Señalado, sin tocar | Tu OK (fuera del repo) |
| **16K** | `finish_reason` en `GroqRunner` (de `PLAN_CONVENCION_TOOLS_MCP.md` §8.5.2) | este repo | Media | Propuesta, sin implementar | — |
| **16I** | `test_ai_structure.py --only-failures` destruye el bloque del modelo | este repo | Media | Abierta, independiente | — |
| **D3** | Re-correr la suite completa con día dedicado de cuota | este repo | Alta | Pendiente | Ninguna de las 3 decisiones exige re-run; **C1 (16M) sí**, hacerla antes del re-run o incluirla |

**Nota sobre el orden (actualizada 28/09):** 16L se aplicó **sin** tocar el schema, así que no
sumó nada al re-run pendiente. La única que obligará a re-correr la suite es **C1 (16M)**, que
queda para después del re-run actual — o para incluirse en él si querés aprovechar la misma
corrida. Si se hace, C1 + cualquier otro cambio de schema van juntos, **una sola corrida**.

---

## 6. Las 3 decisiones que necesito → **DECIDIDAS 28/09 23:40**

1. **16L:** ¿aplico la validación en el bridge? ¿Toco la `description` de `memory_save`
   (implica re-correr la suite) o la dejo intacta?
   → **Se aplica** (§3.4 + §3.5 + §3.6). **La `description` NO se toca**: el `inputSchema` ya
   declara `required`, y cambiarla cambiaría la request de D1-D3 y obligaría a re-correr la suite.
2. **16L en `brain-ai-01`:** ¿solo en disco, o commiteo en `main-clean`?
   → **Commiteo en `main-clean`, solo local (sin push).**
3. **16M:** ¿C1 (cambiar el default a buscar ambas), C2 (corregir la documentación en 6 repos),
   C3 (solo documentar el criterio), o postergarlo?
   → **C3 ahora + C1 después de la suite completa.** C2 queda descartada (dejaría la trampa
   instalada en 6 repos).

**Consecuencia para la suite:** ninguna de las 3 decisiones cambia el schema de tools que ve el
modelo, así que **no obligan a re-correr la suite por sí solas**. C1 (postergado) sí obligará.

---

## 7. Verificación reproducible

```powershell
# A) ¿Cuándo se conectó y murió cada server MCP?
& "$env:USERPROFILE\.local\share\opencode\bin\rg.exe" -a -n `
  "MCP connection closed server=|server unavailable key=" `
  "$env:USERPROFILE\.local\share\opencode\log\opencode.log" | Select-Object -Last 10

# ¿Hubo un uso de la tool cerca del cierre? (28/09 12:33:08 = 15:33:08Z)
& "$env:USERPROFILE\.local\share\opencode\bin\rg.exe" -a -n `
  "permission=brain-ai_memory" "$env:USERPROFILE\.local\share\opencode\log\opencode.log" |
  Select-Object -Last 10

# Procesos hijos que sí conecta (01:30-01:36Z = 22:30-22:36 local)
& "$env:USERPROFILE\.local\share\opencode\bin\rg.exe" -a -n `
  "^timestamp=2026-09-29T01:3[5-6].*permission=brain-ai" `
  "$env:USERPROFILE\.local\share\opencode\log\opencode.log"

# B) ¿El servidor valida project?
Select-String "..\brain-ai-01\ai_architect\pipelines\ingest.py" -Pattern "REQUIRED|def validate_episode" -Context 0,3

# ¿El bridge valida? (no)
Select-String "..\brain-ai-01\mcp_bridge.py" -Pattern 'def handle_memory_save' -Context 0,20

# C) El episodio invisible: existe y no tiene fallos
Select-String "..\brain-ai-01\logs\traces\ingest.jsonl" -Pattern "ep_0c550738"
Test-Path "..\brain-ai-01\memory\episodic\ep_0c550738ea5d461e8cc058d898b32356.json"
Get-Item "..\brain-ai-01\logs\traces\failures.jsonl" | Select-Object LastWriteTime

# El default de collection
Select-String "..\brain-ai-01\mcp_bridge.py" -Pattern 'collection.*args.get' -Context 1,1
# Y lo que promete la documentación
Select-String ".ai\MEMORY.md" -Pattern "Combina búsqueda|episodic"
```

---

## 8. Lo que no se toca en este trabajo

- **`mcp_bridge.py`**: no se renombra ninguna tool. El patrón `<server_name>_<tool_name>` de
  16J sigue intacto y correcto.
- **Ningún `opencode.json`**: el server `brain-ai` ya produce el prefijo correcto.
- **La implementación de los 3 hallazgos**: 16L aplicada en `brain-ai-01`; 16M solo a nivel de
  documentación (C3); 16N sigue sin decidir.
- **`ai_architect/`**: la validación del servidor ya está; no se toca.
- **Los repos hermanos** (`.ai/` de `portfolio`, `portfolio-02`, `youtube-transcripts`,
  `test-ai-config`, `templates/gitflow-scaffold`): solo se tocarían si elegís C2 en 16M.
- **El harness de tests** de este repo: sin cambios en este trabajo.

---

## 9. Prompt para retomar (handoff 28/09 23:25)

> Copiado del handoff de cierre de la sesión del 28/09. Sirve para arrancar una sesión nueva
> sin depender de la memoria del chat. Las 3 decisiones de §6 ya están tomadas arriba; lo que
> sigue **sin decisión** sigue abierto.

### 9.1 Estado de la sesión

1. **16J completo** (Fases 0-5, la 5 parcial): los nombres de tool MCP son `brain-ai_*` con
   guion. El harness publica **10** tools (antes 16 con alias), leídas de `opencode.json`. El
   prompt de **D2** (`advanced_questions.json:147`) es crítico: sin él vuelve el 400.
   Verificado: 18/18 unit, 0 errores 400, D1/D2 API PASS, 3/3 nativo.
2. **MCP desconectado: causa raíz encontrada y resuelta.** La conexión del proceso OpenCode de
   larga duración murió 1,9 s después de lanzar la suite y **nunca reconectó**; se resolvió
   reiniciando OpenCode. **No hay fix de código pendiente** por esa causa (ver 16N para el
   criterio de diagnóstico).

### 9.2 Pendientes y sus decisiones

| # | Qué | Estado |
|---|---|---|
| **16L** | No guardar sin `project` en el bridge | **Decidido: implementar**, sin tocar la `description`, commiteado en `brain-ai-01/main-clean` (local) |
| **16M** | `memory_search` solo busca en `semantic` | **Decidido: C3 ahora** (documentar el criterio) **+ C1 tras la suite completa** |
| **16N** | Documentar "MCP ausente del esquema ≠ servicio caído" + script | **Sin decisión** (§2.8) |
| **16O** | `toolCount=8` vs 10 en `~/.config/opencode/PLANTILLA_MCP.md` | **Sin decisión** (config global, fuera del repo) |
| **16K** | `finish_reason` en `GroqRunner` | **Sin decisión** |
| **16I** | `--only-failures` destruye el bloque del modelo | **Sin decisión** |

### 9.3 La suite completa: NO lanzarla sin día dedicado

Cierra **D3** y **16G**. El TPD es 200k/cuenta y la corrida completa son 122k (gpt-oss) +
191k (qwen). El 25/09 ambas cuentas llegaron a 199k. **Revisar cuota antes de lanzar.**

### 9.4 Trampas que costaron tiempo

1. `/health` verde **no** prueba que el MCP esté registrado: el bridge es un subproceso stdio
   que OpenCode lanza por proceso. `list_mcp_resources` devuelve `[]` **siempre** (solo declara
   tools) — no sirve como señal. La única señal válida es que las tools estén en el esquema.
2. Si faltan las `brain-ai_*`: grep en `~/.local/share/opencode/log/opencode.log` de
   `MCP connection closed server=` y `server unavailable key=`, y **reiniciar OpenCode**.
3. `tests/scripts/quota_probe.py` solo mide el rate limit por minuto; los campos TPD salen
   `null`. **No sirve para saber si hay presupuesto diario.**
4. Cambiar un schema de tools o el `.ai/` de `test-ai-config` ⇒ re-correr la suite entera
   (regla §8.4 del plan 16J).
5. `mcp_tools_to_openai` solo lo usa `GroqRunner`; `test_ai_structure.py` no manda tools.
6. `brain-ai-01` es repo hermano: está en **`main-clean`**, y no se le renombra ninguna tool
   (16J lo cerró).

### 9.5 Abierto, sin investigación exhaustiva

- **Por qué murió el bridge** (el log solo registra el cierre, sin error). Correlación fuerte
  con la suite, causalidad no probada.
- **Por qué el episodio `ep_0c550738…` sí está guardado** (trace con el `project` correcto,
  JSON en `memory/episodic/`, `failures.jsonl` sin fallos) **pero 4 búsquedas no lo devuelven**.
  Segundo factor sin confirmar (indexado o ranking) — ver §4.5.

### 9.6 Memoria de la sesión

- `ep_23692b21…` — análisis de las 4 tareas (vía tool MCP).
- `ep_0c550738…` — cierre de 16J (vía cliente Python, porque el MCP no estaba).

Recuperables con `brain-ai_memory_search(project="personalizar-comportamiento-01")`. Para lo
recién guardado, además `collection="episodic"` (16M/C3).
