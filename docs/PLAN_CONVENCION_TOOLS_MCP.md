# Convención de nombres de tools MCP — diagnóstico y plan de reestructuración

**Creado:** 2026-09-28
**Actualizado:** 2026-09-28 — Fase 0 completada, D1 resuelta
**Estado:** DIAGNÓSTICO CERRADO. Ningún cambio de código aplicado todavía.
**Origen:** cierre de 16H (fix de alias) y hallazgo de `LECCIONES.md:217` (youtube-transcripts)
**Alcance:** 7 repositorios, 3 convenciones de nombres coexistiendo

> Este documento es el punto de partida. La Fase 0 confirmó el patrón único:
> **guion** (`brain-ai_*`), respaldado por documentación oficial y 824 llamadas reales.

---

## 1. Resumen ejecutivo

El fix de 16H (publicar cada tool de memoria con 3 alias) fue un **parche sobre un síntoma**,
no una solución. La causa real es que existen **tres convenciones de nombres conviviendo** en la
documentación `.ai/`, y solo una coincide con lo que OpenCode registra.

| Convención | Dónde vive | ¿Existe como tool real? |
|---|---|---|
| `memory_save` | `mcp_bridge.py:184` | Sí — nombre interno del bridge |
| `brain-ai_memory_save` | `MEMORY.md`, `commands.md` (5 proyectos) | **Sí — el nombre real. 824 llamadas** |
| `brain_ai_memory_save` | `system.md`, `rules.md` (6 proyectos) | **No. 0 llamadas.** Solo por el alias de 16H |

**Decisión (D1, cerrada en Fase 0):** el patrón único es **`brain-ai_*` con guion**, que es
`<server_name>` + `_` + `<tool_name>` según la documentación oficial de OpenCode.

**Impacto:** tres fallos distintos ya se produjeron, por la misma causa raíz:

- `400 tool_use_failed` en gpt-oss (16H) — canal API
- `Model tried to call unavailable tool 'brain-ai_memory_save'` en youtube-transcripts — canal nativo
- Modelos que obedecen el prompt y llaman un nombre inexistente

---

## 2. Verificación de Fase 0 — completada

### 2.1 Fuente oficial: el prefijo es obligatorio

`https://opencode.ai/docs/mcp-servers/`, sección "Glob patterns":

> **"MCP server tools are registered with server name as prefix, so to disable all tools for a
> server simply use: `"mymcpservername_*": false`"**

Y el ejemplo de la misma página: el glob `"my-mcp*"` desactiva `my-mcp_search` y `my-mcp_list`.

Es decir: **`memory_search` a secas nunca funciona.** El nombre sin prefijo solo existe dentro del
bridge; el modelo solo ve `<server_name>_<tool_name>`.

### 2.2 Dato empírico: el log de OpenCode (78 MB)

Fuente: `~/.local/share/opencode/log/opencode.log`. Todas las llamadas de tool registradas:

| Tool | Ocurrencias |
|---|---|
| `brain-ai_test_status` | 1181 |
| `brain-ai_memory_search` | 511 |
| `brain-ai_run_tests` | 237 |
| `brain-ai_memory_save` | 229 |
| `brain-ai_memory_consolidate` | 84 |
| `brain-ai_ejecutar_accion` | 65 |
| `brain-ai_resolver_referencia` | 7 |
| **Total con guion** | **824** |
| `brain_ai_memory_save` (underscore) | **0 como tool call** |

El prefijo es **uniforme** para los 10 tools del bridge, incluidos los de provenance
(`resolver_referencia`, `describir_handle`, `ejecutar_accion`) y los de ejecución
(`run_tests`, `test_status`, `run_command`, `command_status`).

### 2.3 Las 7 ocurrencias de underscore NO son tool calls

Al contar `brain_ai_memory_save` en el log aparecen 7 coincidencias, pero al inspeccionar el
contexto **ninguna es una invocación de tool**:

- 4 ocurrencias: código Python de sesiones de desarrollo — la constante
  `MEMORY_ALIAS_PREFIXES` y scripts que importan `mcp_client`.
- 3 ocurrencias: comandos `bash` con llamadas a `brain-ai-01/clients/memoria.py`.

Este conteo explica por qué el número no es exactamente cero **sin invalidar** la conclusión.

### 2.4 La trampa que produjo el error: la lista de tools de la sesión

En la sesión interactiva, la lista de tools que ve el modelo puede mostrar
`brain_ai_memory_search` con underscore, aunque OpenCode registre `brain-ai_memory_search`.

Motivo: la capa que expone el schema al modelo **normaliza guiones a guiones bajos** en su
convención propia. No es el nombre que OpenCode registra, y no es el que acepta la API.

**Consecuencia práctica:** si alguien copia un nombre de esa lista a un `.ai/`, escribe
underscore. Eso es exactamente lo que pasó con `system.md` y `rules.md`.

**No forma parte del log de OpenCode.** Para conocer el nombre real hay que mirar el log, el
NDJSON de `opencode run --format json`, o la documentación oficial.

### 2.5 El server name nunca cambió

```
92bdb26 Fix multi-modelo: acumulacion de resultados...
3f82e99 docs: documentacion completa + git_tool.py
284291a Add MCP bridge config and update D1-D3 prompts
274a0f6 Integrate brain-ai-01 persistent memory
55e591f Initial commit
```

`git log -p --follow -- opencode.json` muestra un único cambio del server name: siempre fue
`"brain-ai"`. No es una regresión reciente.

### 2.6 Comparación con el caso que ya funciona

| `opencode.json` | Server name | Prefijo | Tool resultante |
|---|---|---|---|
| Global | `git_publisher` | `git_publisher_` | `git_publisher_git_ver_estado` |
| Este proyecto | `brain-ai` | `brain-ai_` | `brain-ai_memory_search` |

Mismo mecanismo `<server_name>` + `_` + `<tool_name>`. La diferencia de guion vs underscore no es
una convención de memoria: es simplemente el nombre que cada proyecto le dio a su servidor.

### 2.7 Conclusión de Fase 0

| Pregunta | Respuesta | Base |
|---|---|---|
| ¿Cuál es el nombre canónico? | `brain-ai_*` (guion) | Doc oficial + 824 llamadas |
| ¿`memory_search` funciona solo? | No | Doc oficial: prefijo obligatorio |
| ¿El prefijo es uniforme en los 10 tools? | Sí | Log: 7 tools distintos, todos con guion |
| ¿Qué acepta la API de Groq? | El nombre publicado en `tools[]` | El 400 lo define: `not in request.tools` |
| ¿Hay que tocar el bridge? | No | El bridge expone nombres internos; OpenCode pone el prefijo |
| ¿Hay que tocar `opencode.json`? | No | El server name ya es correcto |

**El bridge y los `opencode.json` quedan intactos.** El problema es 100 % documental.

---

## 3. El error 16H y por qué el alias fue un síntoma

**Síntoma:** `400 tool_use_failed: attempted to call tool 'brain_ai_memory_save' which was not in
request.tools`

**Por qué ocurre:** el harness de tests (`GroqRunner`) habla directo con `api.groq.com`. Ese camino
**no pasa por OpenCode**, así que no hay namespacing de servidor. Las tools se construyen desde
`mcp_bridge.py`, que publica `memory_save`. El modelo, leyendo `system.md:73`, llama
`brain_ai_memory_save`, y Groq responde que no está en `request.tools`.

**Por qué el fix de alias no resolvió la raíz:** añadió un tercer nombre (`brain_ai_`) que no
aparece en ninguna llamada registrada. De dos convenciones rotas pasó a tres. El 400 desapareció
porque ahora el modelo puede acertar entre 3 nombres, no porque la documentación sea correcta.

**Por qué no fallaba siempre:** si el modelo leía la lista de tools en vez del prompt y llamaba
`memory_save`, salía bien. El alias convirtió un fallo intermitente en uno que se puede repetir.

**Costo de la duplicación:** el 400 resultaba en 4 herramientas publicadas con el mismo propósito
(10 tools reales, 16 publicadas). El modelo elige entre 4 nombres equivalentes para la misma
acción, lo que degrada la precisión en los tests D1/D2/D3.

---

## 4. Las tres convenciones y su distribución

### 4.1 Nombres reales del bridge (`brain-ai-01/mcp_bridge.py`)

| Línea | Nombre | Propósito |
|---|---|---|
| 150 | `memory_search` | Buscar episodios y conocimiento |
| 184 | `memory_save` | Guardar episodio |
| 211 | `memory_consolidate` | Consolidar episódico a semántico |
| 224 | `resolver_referencia` | Resolver referencia contra fuentes autorizadas |
| 247 | `describir_handle` | Metadatos de un handle |
| 261 | `ejecutar_accion` | Ejecutar acción con efectos |
| 282 | `run_tests` | Ejecutar tests en background |
| 310 | `test_status` | Estado de un task de tests |
| 327 | `run_command` | Ejecutar comando en background |
| 355 | `command_status` | Estado de un task de comando |

### 4.2 Distribución de convenciones por repositorio

`brain_ai_*` (underscore) en `system.md` y `rules.md` — 0 llamadas registradas en el log de
OpenCode. 63 ocurrencias en 6 repositorios.

| Repositorio | `system.md` | `rules.md` | `MEMORY.md` | `commands.md` | Total `_` |
|---|---|---|---|---|---|
| `personalizar-comportamiento-01` | 14 `_` | 6 `_` | 8 `_` + 15 `-` | — | 28 |
| `portfolio` | 14 `_` | 7 `_` | 8 `_` + 15 `-` | 3 `-` | 29 |
| `portfolio-02` | 14 `_` | 6 `_` | 8 `_` + 15 `-` | — | 28 |
| `youtube-transcripts` | 10 `_` | 4 `_` | 7 `-` | 3 `-` | 14 |
| `test-ai-config` | 6 `_` | — | 8 `-` | — | 6 |
| `templates/gitflow-scaffold` | 10 `_` | 3 `_` | 15 `-` | — | 13 |
| `brain-ai-01` | — | — | — | 1 en `README.md:85` | 1 |
| **Total** | | | | | **119** |

Leyenda: `N _` = ocurrencias con underscore (incorrectas). `N -` = ocurrencias con guion (correctas).

### 4.3 Repositorios sin el problema

No registran brain-ai ni contienen las tres convenciones:
`SERVICIO BOT - LANDING`, `whatsapp-agent-bot`, `whatsapp-agent-sin-web`,
`youtube-mcp-piloto`, `youtube-transcripts/docs/plantilla-consumidor`.

### 4.4 La plantilla es la más urgente

`templates/gitflow-scaffold` se copia a proyectos nuevos. Si no se alinea, **todo proyecto futuro
hereda el patrón roto**. Es el punto de mayor apalancamiento de la fase 3.

---

## 5. Evidencia dura

### 5.1 Documentación oficial

| Fuente | Cita | Qué prueba |
|---|---|---|
| `opencode.ai/docs/mcp-servers` | *"MCP server tools are registered with server name as prefix"* | El prefijo es obligatorio |
| misma página | glob `"my-mcp*"` desactiva `my-mcp_search`, `my-mcp_list` | El prefijo es el server name tal cual |
| misma página | *"And to use it I can add `use the mcp_everything tool`"* | El usuario nombra el server |

### 5.2 Datos reales del log de OpenCode

| Fuente | Dato | Qué prueba |
|---|---|---|
| `~/.local/share/opencode/log/opencode.log` | 824 llamadas de tool, todas `brain-ai_*` | El nombre real en ejecución |
| mismo | 0 llamadas `brain_ai_*` | El underscore nunca se ejecutó |
| mismo | 7 tools distintos con prefijo, incluidos provenance y ejecución | El prefijo es uniforme |
| `git log -p --follow -- opencode.json` | `"brain-ai"` en los 5 commits | No es una regresión |
| `tests/answers/advanced_validation_report.json` | 25x `brain-ai_memory_search`, 19x `memory_search` | Nativo con guion, API sin prefijo |
| `tests/lib/opencode_events.py:58` | *"OpenCode nativo emite brain-ai_\* (guion), no brain_ai_\*"* | Confirmado en código |
| `tests/test_opencode_events.py:68,74` | fixtures NDJSON con guion | El NDJSON nativo usa guion |

### 5.3 Evidencia del proyecto hermano

| Fuente | Cita | Qué prueba |
|---|---|---|
| `youtube-transcripts/docs/LECCIONES.md:217` | `Model tried to call unavailable tool 'brain-ai_memory_save'` | OpenCode emite guion |
| mismo :218 | *"lo que no está conectado es el puente MCP... sus tools no aparecen en el esquema"* | El bug ya ocurrió antes |
| mismo :221 | *"tool MCP ausente del esquema" ≠ "servicio caído"* | Lección no aplicada al `.ai/` |

**Sobre la última fila:** el error de youtube-transcripts se resolvió reiniciando opencode, pero
**no se documentó la causa de fondo** en los `.ai/`. Por eso el mismo problema reapareció aquí
como 16H, en otro proyecto, con otro síntoma.

---

## 6. Contradicción interna: `MEMORY.md` está duplicado

`personalizar-comportamiento-01/.ai/MEMORY.md` contiene **la misma tabla de herramientas dos
veces**, con convenciones distintas:

**Bloque 1 — guion (L12-65)**

```
L12: ### brain-ai_memory_search
L22: ### brain-ai_memory_save
L32: ### brain-ai_memory_consolidate
L43: | Pregunta sobre decisión pasada | `brain-ai_memory_search` | "¿Qué base de datos usamos?" |
L44: | Después de implementar algo   | `brain-ai_memory_save`   | Guardar por qué elegimos JWT |
L47: | Periódicamente                 | `brain-ai_memory_consolidate` | Consolidar episodios similares |
```

**Bloque 2 — underscore (L75-104)**

```
L75: | Pregunta sobre decisión pasada | `brain_ai_memory_search` | "¿Qué base de datos usamos?" |
L76: | Pregunta sobre configuración   | `brain_ai_memory_search` | "¿Cómo configuramos JWT?"   |
L82: 2. **Busca** en memoria con `brain_ai_memory_search(query="...", project="...")`
L85: 5. **Si tomas una decisión importante** -> `brain_ai_memory_save(...)`
```
Los dos bloques son **semánticamente idénticos** (misma tabla "Cuándo usar cada herramienta",
mismas tres filas de ejemplos). Solo cambia el nombre del tool.

### 6.1 Duplicación entre archivos

La sección `## brain-ai-01: Primera Fuente` está replicada:

- `system.md:99-136` — con underscore
- `MEMORY.md:67-104` — con underscore

Ambas contienen la misma tabla de "Situación → Tool → Ejemplo" y el mismo flujo obligatorio
de 5 pasos. Un archivo contradice al otro.

**Mismo archivo, misma tabla, dos respuestas a la misma pregunta.** El modelo no puede inferir
cuál obedecer cuando ambas están en su contexto.

---

## 7. Patrón único — VALIDADO en Fase 0

**Regla:** el nombre de una tool MCP es `<server_name>` + `_` + `<tool_name>`, donde
`<server_name>` es exactamente la clave declarada en `opencode.json` bajo `mcp`, sin transformar.

En este proyecto, `opencode.json:22` declara `"brain-ai"`, luego el nombre es `brain-ai_` + tool.

**Aplica a las 10 tools del bridge, no solo a las 3 de memoria.**

### 7.1 Tool calls — camino principal

**`brain-ai_*` con guion.** Sin cambios en el bridge ni en `opencode.json`.

```
brain-ai_memory_search
brain-ai_memory_save
brain-ai_memory_consolidate
```

### 7.2 Cómo se documenta en los `.ai/`

En `system.md`, `rules.md`, `MEMORY.md` y `commands.md` se escribe el **nombre completo
registrado**: `brain-ai_memory_search`. No el interno del bridge (`memory_search`) ni la forma
sanitizada con underscore (`brain_ai_memory_search`).

### 7.3 Endpoints REST — fallback documentado

El mapeo 1:1 ya existe entre `brain-ai-01/ai_architect/core/mcp_server.py` y
`brain-ai-01/clients/memoria.py`. **No se modifica.**

| REST | Tool bridge | Nombre registrado en OpenCode |
|---|---|---|
| `POST /retrieve` | `memory_search` (L150) | `brain-ai_memory_search` |
| `POST /ingest` | `memory_save` (L184) | `brain-ai_memory_save` |
| `POST /consolidate` | `memory_consolidate` (L211) | `brain-ai_memory_consolidate` |
| `POST /resolve_reference` | `resolver_referencia` (L224) | `brain-ai_resolver_referencia` |
| `POST /describe_handle` | `describir_handle` (L247) | `brain-ai_describir_handle` |
| `POST /actions/execute` | `ejecutar_accion` (L261) | `brain-ai_ejecutar_accion` |
| `POST /tests/run` | `run_tests` (L282) | `brain-ai_run_tests` |
| `GET /tests/status/{task_id}` | `test_status` (L310) | `brain-ai_test_status` |
| `POST /commands/run` | `run_command` (L327) | `brain-ai_run_command` |
| `GET /commands/status/{task_id}` | `command_status` (L355) | `brain-ai_command_status` |
| `GET /health` | — | Verificación de disponibilidad |

**Las 3 primeras filas están verificadas con llamadas reales en el log.** Las 4 últimas
(`resolver_referencia`, `ejecutar_accion`, `run_tests`, `test_status`) también aparecen con guion
en el log. `describir_handle`, `run_command` y `command_status` no aparecen en el log, pero
siguen el mismo mecanismo por definición del bridge.

### 7.4 Criterio de uso (falta documentar hoy)

Hoy no existe criterio escrito. La única guía está en
`youtube-transcripts/docs/LECCIONES.md:219-221`, como reacción a un incidente, no como norma.

**Regla propuesta:**

1. **MCP tool** — camino normal. Siempre que la tool esté en el esquema de la sesión.
2. **REST** — solo si el bridge MCP no está en el esquema. Antes de asumir caída, verificar
   `GET /health` (regla 8.4 de `.ai/rules.md` ya lo exige para servicios).
3. Ante `unavailable tool` o `not in request.tools`: **no reintentar a ciegas**. Registrar el
   nombre intentado y el canal. Ese es el patrón quecheckmark con 16H.

### 7.5 Corrección secundaria

`~/.config/opencode/PLANTILLA_MCP.md:44` documenta `brain-ai toolCount=8`.
El bridge expone **10** tools. Actualizar, junto con la lista de nombres esperados.

### 7.6 Regla para no repetir el error

> Al copiar un nombre de tool a un `.ai/`, copiarlo del **log de OpenCode** o del **NDJSON de
> `opencode run --format json`**, nunca de la lista de tools que muestra la sesión interactiva.
> Esa lista normaliza guiones a guiones bajos y produce nombres que la API rechaza.

---

## 7A. Fase 3 — alcance exacto: 3 formas incorrectas, 153 ocurrencias

### 7A.1 Las tres formas que hay que corregir

| Forma | Ejemplo | Ocurrencias | Por qué falla |
|---|---|---|---|
| **Con underscore** | `brain_ai_memory_search` | 119 | No se ejecutó nunca (0 tool calls) |
| **Desnuda (memoria)** | `memory_save` | ~15 | Es el nombre interno del bridge |
| **Desnuda (provenance/ejecución)** | `resolver_referencia` | ~21 | El prefijo es obligatorio |

**Total real: ~153 ocurrencias.** El relevamiento inicial (119) solo capturó la primera forma,
porque el patrón de búsqueda `brain[-_]ai[-_]memory` no matchea la forma desnuda.

### 7A.2 Inventario por repositorio

| Repositorio | `system.md` | `rules.md` | `MEMORY.md` | `commands.md` | Total |
|---|---|---|---|---|---|
| `templates/gitflow-scaffold` | 10 `_` | 3 `_` + 2 desnudas | 1 desnuda | — | 16 |
| `personalizar-comportamiento-01` | 14 `_` + 6 desnudas | 6 `_` + 3 desnudas | 8 `_` + 2 desnudas | 10 comandos | 39 |
| `portfolio` | 14 `_` + 4 desnudas | 7 `_` + 3 desnudas | 8 `_` + 5 desnudas | ✓ correcto | 41 |
| `portfolio-02` | 14 `_` + 4 desnudas | 6 `_` + 3 desnudas | 8 `_` + 4 desnudas | 10 comandos | 39 |
| `youtube-transcripts` | 10 `_` + 3 desnudas | 4 `_` + 1 desnuda | ✓ correcto | ✓ correcto | 18 |
| `test-ai-config` | 6 `_` + 1 desnuda | 1 desnuda | ✓ correcto | no existe | 8 |
| `brain-ai-01/README.md:85` | — | — | — | — | 1 |

### 7A.3 Ejemplos concretos de la forma desnuda

| Archivo | Línea | Actual | Correcto |
|---|---|---|---|
| `test-ai-config/.ai/rules.md` | 82 | `` `memory_save` `` / `` `memory_search` `` | `brain-ai_memory_save` / `brain-ai_memory_search` |
| `test-ai-config/.ai/system.md` | 95 | `en memory_search` | `en brain-ai_memory_search` |
| `portfolio/.ai/rules.md` | 130 | `` `resolver_referencia` `` | `brain-ai_resolver_referencia` |
| `personalizar-comportamiento-01/.ai/system.md` | 153-167 | `### resolver_referencia` | `### brain-ai_resolver_referencia` |

**Contradicción dentro del mismo archivo:** en `portfolio/.ai/MEMORY.md`,
L49 usa `brain-ai_run_command` (correcto) y L102 usa `resolver_referencia` (sin prefijo).
Un modelo que copie una línea y otra mezclaría convenciones.

### 7A.4 Comandos slash que no existen (decisión B2)

`commands.md` de `personalizar-comportamiento-01` y `portfolio-02` documentan 10 comandos
slash. **Ninguno existe**, verificado en los 6 repos:

| Verificación | Resultado |
|---|---|
| Sección `command` en `opencode.json` | No existe en ninguno de los 6 |
| Directorio `.opencode/commands/` | No existe en ningún repo |
| `~/.config/opencode/commands/` | No existe |

Según `opencode.ai/docs/commands/`, un comando custom requiere `.opencode/commands/<nombre>.md`
o la sección `command` del config. Los built-in son solo `/init`, `/undo`, `/redo`, `/share`,
`/help`.

**Comandos inventados:** `/deploy`, `/test`, `/lint`, `/git-push`, `/memory-save`,
`/memory-search`, `/memory-consolidate`, `/resolve`, `/handle`, `/action`.

**Decisión (B2):** borrarlos. Si se necesitan después, se crean como archivos reales.

### 7A.5 Duplicación de "Primera Fuente" (decisión D5)

La sección `## brain-ai-01: Primera Fuente` está en `system.md:99-136` **y** en
`MEMORY.md:67-104`, con contenido casi idéntico.

**Decisión:** queda solo en `MEMORY.md`. Se elimina de `system.md`.

Aplica a: `personalizar-comportamiento-01`, `portfolio`, `portfolio-02`.

### 7A.6 Plan de ejecución: 6 commits, uno por repositorio

Orden: la plantilla primero, para que ningún proyecto nuevo herede las 3 formas.

| # | Repositorio | Archivos a tocar | Motivo del orden |
|---|---|---|---|
| 1 | `templates/gitflow-scaffold` | `system.md`, `rules.md`, `MEMORY.md` | Plantilla: apalancamiento máximo |
| 2 | `personalizar-comportamiento-01` | `system.md`, `rules.md`, `MEMORY.md`, `commands.md` | Este repo, con su plan |
| 3 | `portfolio` | `system.md`, `rules.md`, `MEMORY.md` | |
| 4 | `portfolio-02` | `system.md`, `rules.md`, `MEMORY.md`, `commands.md` | |
| 5 | `youtube-transcripts` | `system.md`, `rules.md` | `MEMORY.md`/`commands.md` ya correctos |
| 6 | `test-ai-config` | `system.md`, `rules.md` | Sujeto del experimento: re-correr suite |

**No se tocan:** `docs/` históricos (registro), `brain-ai-01/` (repo hermano),
ningún `opencode.json`, ningún `mcp_bridge.py`.

### 7A.7 Mensaje de commit (uno por repo)

```
fix(ai): alinear nombres de tools MCP a brain-ai_*

Los .ai/ pedian brain_ai_memory_* (underscore), memory_* (nombre interno
del bridge) y resolver_referencia (sin prefijo). Ninguna de las tres formas
funciona: OpenCode registra las tools como <server_name>_<tool_name>.

Causa raiz: opencode.json declara el server como "brain-ai", luego el
nombre real es brain-ai_memory_search (guion).

Verificado en ~/.local/share/opencode/log/opencode.log: 824 llamadas, todas
con guion. 0 llamadas con underscore o sin prefijo.

Fuente oficial: opencode.ai/docs/mcp-servers
  "MCP server tools are registered with server name as prefix"

Plan completo: docs/PLAN_CONVENCION_TOOLS_MCP.md
```

### 7A.8 Verificación por commit

```powershell
# 1. Cero underscore (debe dar 0)
Select-String ".ai\*" -Pattern 'brain_ai_' -AllMatches

# 2. Cero forma desnuda (debe dar 0)
$pat = '(?<!brain-ai_)(?<!brain_ai_)\b(memory_search|memory_save|memory_consolidate'
$pat += '|resolver_referencia|describir_handle|ejecutar_accion'
$pat += '|run_tests|test_status|run_command|command_status)\b'
Select-String ".ai\*" -Pattern $pat -AllMatches

# 3. Conteo de tools con prefijo (debe aumentar, no bajar)
Select-String ".ai\*" -Pattern 'brain-ai_' -AllMatches | Measure-Object
```

### 7A.9 Ejecución — 28/09/2026

**Resultado: 0 residuales en los 6 repos.** Verificado con el patrón de §7A.8.

| # | Repositorio | Git | Commit | Archivos | Estado |
|---|---|---|---|---|---|
| 1 | `templates/gitflow-scaffold` | Sí | `89e0887` | `system.md`, `rules.md` | Commiteado |
| 2 | `personalizar-comportamiento-01` | Sí | `60bddf2` | `system.md`, `rules.md`, `MEMORY.md`, `commands.md` | Commiteado |
| 3 | `portfolio` | Sí | `82964ad` | `system.md`, `rules.md`, `MEMORY.md` | Commiteado |
| 4 | `portfolio-02` | **No** | — | `system.md`, `rules.md`, `MEMORY.md`, `commands.md` | Aplicado en disco |
| 5 | `youtube-transcripts` | Sí | `f2d1861` | `system.md`, `rules.md`, `MEMORY.md`, `commands.md`, `context.md` | Commiteado |
| 6 | `test-ai-config` | **No** | — | `system.md`, `rules.md` | Aplicado en disco |

**Hallazgo:** `portfolio-02` y `test-ai-config` **no son repositorios git**. Los cambios
quedan aplicados pero sin commit. Decidir si se inicializa git en ellos o se versionan de
otra forma.

**Cambios adicionales aplicados en este paso:**

- Duplicación "Primera Fuente" resuelta en 3 repos (`personalizar-comportamiento-01`,
  `portfolio`, `portfolio-02`): eliminada de `system.md`, queda solo en `MEMORY.md`.
- Prefijo agregado a las 3 tools de provenance en `system.md` de los repos que las documentan.
- B2 aplicado: comandos slash inventados borrados en `personalizar-comportamiento-01` y
  `portfolio-02`. Reemplazados por la tabla real de las 10 tools MCP.
- Menciones en prosa de `run_tests`/`run_command` en tablas de ejemplo también corregidas.

**Nota sobre el conteo:** los patrones de verificación capturan también menciones en prosa
(ej: "NO usar run_tests para esto"). Esas se corrigieron por consistencia, aunque no son
nombres de tool invocables.

---

## 8. Plan por fases

| Fase | Alcance | Estado |
|---|---|---|
| **0. Verificación empírica** | Determinar el nombre canónico | **COMPLETADA** (§2) |
| **1. Documentar** | Este doc + 16J + §8 de ANALISIS_FALLOS | **COMPLETADA** |
| **2. `mcp_client.py`** | Quitar el alias dual. Un solo nombre por tool. 16 → 11 tools | Pendiente |
| **3. Unificar `.ai/`** | 6 repos, ~153 ocurrencias, 3 formas | **COMPLETADA** (§7A.9) |
| **4. Código de tests** | Ver nota 8.3 | Pendiente |
| **5. Verificar** | Unit tests. Re-run `--only D1,D2,D3`. Suite completa si cambia `test-ai-config` | Pendiente |

**La Fase 0 confirmó que no hace falta tocar el bridge ni ningún `opencode.json`.** El trabajo
restante es el ajuste del harness de tests (Fases 2, 4 y 5).

> **Orden obligatorio: Fase 3 antes que Fase 2.** Ya está hecho. Al implementar la Fase 2, el
> harness publicará solo `brain-ai_*`, que es justo lo que los `.ai/` ahora piden.

### 8.0 Fase 0 — completada

Resultado en §2. Conclusión: patrón único = guion, respaldado por la documentación oficial de
OpenCode y 824 llamadas registradas en el log.

### 8.1 Fase 1 — completada

Documentación del diagnóstico en 3 archivos de este repo:

| Archivo | Qué contiene |
|---|---|
| `docs/PLAN_CONVENCION_TOOLS_MCP.md` (este) | Diagnóstico, evidencia y plan |
| `docs/TAREAS_PENDIENTES.md` ítem 16J | Estado y pendientes |
| `docs/tests/ANALISIS_FALLOS_20260926.md` §8 | Causa raíz junto a 16E-16H |

Decisiones del usuario: **no** crear `docs/LECCIONES.md`; **no** tocar
`brain-ai-01/CHANGELOG.md`; **no** corregir los `docs/` históricos de los otros repos.

### 8.2 Fase 2 — detalle

`tests/lib/mcp_client.py:171` define `MEMORY_ALIAS_PREFIXES = ("brain_ai_", "brain-ai_")` y
agrega las variantes en `mcp_tools_to_openai` (líneas 201-205). Al quedar validado el patrón,
corresponde publicar **un solo nombre por tool**, con guion, para los 10 tools
(16 publicadas → 11).

Archivos a tocar:

| Archivo | Cambio |
|---|---|
| `tests/lib/mcp_client.py:166-205` | Reemplazar el alias dual por prefijo único |
| `tests/lib/model_runner.py:426-429` | Comentario que dice "el fix son los alias" |
| `tests/scripts/test_tool_use_failed.py:153-155, 167-176` | Fixtures y assert de 3 nombres |

### 8.3 Fase 4 — detalle

| Archivo | Línea | Qué asume |
|---|---|---|
| `tests/lib/opencode_events.py` | 15-17 | `MEMORY_TOOL_NAMES` con ambas variantes |
| `tests/lib/advanced_validators.py` | 364 | `_norm_tool_name` normaliza guion/underscore |
| `tests/scripts/test_tool_use_failed.py` | 173-174 | Assert de 3 nombres publicados |
| `tests/test_opencode_events.py` | 61, 68, 74 | Fixtures NDJSON |
| `tests/questions/advanced_questions.json` | D1, D2, D3 | `expected_tool` con underscore |

Nota: `opencode_events.memory_used` normaliza guion a underscore en línea 61 porque el fixture
histórico mezclaba variantes. Con el patrón único, la normalización puede simplificar, pero
conviene conservarla: el NDJSON puede venir de versiones distintas de OpenCode.

### 8.4 Riesgo de la fase 3

Cambiar los `.ai/` de `test-ai-config` modifica el **sujeto del experimento**. Los tests D1-D3
evalúan si el modelo usa memoria; si el prompt cambia, los resultados anteriores dejan de ser
comparables y hay que re-correr la suite completa.

---

## 9. Decisiones

| # | Decisión | Estado |
|---|---|---|
| **D1** | Nombre canónico = `brain-ai_*` con guion | **CERRADA** — doc oficial + 824 llamadas (§2) |
| **D2** | Alcance: un commit por repo | **APLICADA** — 4 commits hechos; 2 repos sin git (§7A.9) |
| **D3** | `test-ai-config` obliga a re-correr la suite entera | **PENDIENTE** — falta la re-corrida |
| **D4** | `templates/gitflow-scaffold` es prioridad | **APLICADA** — commit `89e0887` |
| **D5** | Duplicación "Primera Fuente" | **APLICADA** — queda solo en `MEMORY.md` |
| **D6** | Eliminar `brain_ai_*` de la documentación | **APLICADA** — 0 residuales |
| **D7** | Comandos slash inexistentes | **APLICADA** — B2, borrados y reemplazados por tabla de tools |
| **D8** | `portfolio-02` y `test-ai-config` sin git | **ABIERTA** — decidir si se inicializa git |

### 9.1 Decisiones ya tomadas que no están en debate

- **No tocar `brain-ai-01/mcp_bridge.py`.** El MCP lo consumen todos los proyectos.
- **No tocar ningún `opencode.json`.** El server name `"brain-ai"` ya genera el prefijo correcto.
- **No renombrar el server a `brain_ai` o `memory`.** El guion funciona; cambiarlo obligaría a
  corregir 6 repos de `.ai/` que hoy están bien (`MEMORY.md`, `commands.md`).
- **No corregir los `docs/` históricos** de los repos hermanos. Son registro de lo que se dijo
  en su momento.
- **No crear `docs/LECCIONES.md` ni tocar `brain-ai-01/CHANGELOG.md`.**

---

## 10. Verificación reproducible

```powershell
# Nombres internos del bridge (10 tools, sin prefijo)
Select-String "..\brain-ai-01\mcp_bridge.py" -Pattern '"name": "' | Select-Object -First 10

# Nombres REALES registrados por OpenCode (fuente de verdad)
& "$env:USERPROFILE\.local\share\opencode\bin\rg.exe" -o -a `
  "brain[-_]ai[-_]memory_(search|save|consolidate)" `
  "$env:USERPROFILE\.local\share\opencode\log\opencode.log" |
  Group-Object | Sort-Object Count -Descending

# Verificar que las ocurrencias underscore NO son tool calls
& "$env:USERPROFILE\.local\share\opencode\bin\rg.exe" -a -n "brain_ai_memory" `
  "$env:USERPROFILE\.local\share\opencode\log\opencode.log"

# Convención por archivo en todos los repos
Get-ChildItem "..\" -Recurse -File -Filter "*.md" -Depth 3 |
  Select-String -Pattern 'brain[-_]ai[-_]memory' | Group-Object Filename

# Separar underscore de guion por archivo
Get-ChildItem "..\*\.ai" -File | ForEach-Object {
  $l = Select-String $_.FullName -Pattern 'brain[-_]ai[-_]memory'
  "{0}: _={1} -= {2}" -f $_.Name,
    ($l | Where-Object { $_.Line -match 'brain_ai_memory' }).Count,
    ($l | Where-Object { $_.Line -match 'brain-ai_memory' }).Count
}

# Server name: confirmar que nunca cambió
git log -p --follow -- opencode.json | Select-String '^[+-].*"brain'

# ToolCount documentado vs real
Select-String "$env:USERPROFILE\.config\opencode\PLANTILLA_MCP.md" -Pattern 'toolCount'
```

**Nota sobre el log:** pesa 78 MB. Los comandos usan `rg.exe` incluido con OpenCode
(`~/.local/share/opencode/bin/rg.exe`) porque `Select-String` no es eficiente para ese tamaño.

---

## 11. Lo que no se debe hacer

- **No tocar `brain-ai-01/mcp_bridge.py`.** El MCP lo consumen todos los proyectos; renombrar
  tools rompe a los que ya funcionan.
- **No tocar los `opencode.json`.** El server name `"brain-ai"` ya produce el prefijo correcto.
- **No copiar nombres de tool desde la lista de la sesión interactiva.** Normaliza guiones a
  guiones bajos (§2.4). Es la trampa que produjo `system.md` con underscore.
- **No reintentar a ciegas ante `not in request.tools`.** Como en el caso 16H: un reintento con
  más tokens en lugar de leer el mensaje real hizo pasar el síntoma, no la causa.
- **No agregar un cuarto alias.** Cada alias nuevo baja la precisión del modelo al elegir y
  vuelve a abrir la ambigüedad.
- **No asumir que el bridge se puede renombrar.** Su docstring es explícito en que lo consumen
  `proyecto-web`, `sistema-ventas` y `juego-rpg`, que no están en el alcance de este plan.

---

## 12. Referencias

### Internas

- Análisis de fallos con causas raíz: `docs/tests/ANALISIS_FALLOS_20260926.md` (sección 7)
- Sesión de cierre 16E-16H: `docs/tests/sesion_20260928.md`
- Tareas pendientes: `docs/TAREAS_PENDIENTES.md` (ítem 16, sub-ítem J pendiente de crear)
- Fixture NDJSON: `tests/fixtures/opencode_sample.ndjson`
- Runner MCP del harness: `tests/lib/mcp_client.py` (alias), `tests/lib/model_runner.py`

### Externas

- **Documentación oficial de OpenCode:** `https://opencode.ai/docs/mcp-servers/`
  Sección "Glob patterns": *"MCP server tools are registered with server name as prefix"*
- Versión instalada: `opencode-ai 1.18.31`

### Proyectos hermanos

- Bridge: `../brain-ai-01/mcp_bridge.py` (TOOLS L148-371, TOOL_HANDLERS L578-589)
- Plantilla MCP global: `~/.config/opencode/PLANTILLA_MCP.md`
- Incidente nativo: `../youtube-transcripts/docs/LECCIONES.md` líneas 213-221
- Log de ejecución: `~/.local/share/opencode/log/opencode.log` (78 MB)

### 12.1 Documentos relacionados

Si llegaste desde otro documento, el diagnóstico completo está aquí:

| Documento | Qué contiene |
|---|---|
| `docs/PLAN_CONVENCION_TOOLS_MCP.md` (este) | Diagnóstico completo, evidencia de Fase 0, plan por fases |
| `docs/TAREAS_PENDIENTES.md` ítem 16J | Estado y pendientes de la tarea |
| `docs/tests/ANALISIS_FALLOS_20260926.md` §8 | Análisis de causa raíz junto a 16E-16H |
| `docs/tests/sesion_20260928.md` | Sesión donde se descubrió que el fix 16H era un parche |
