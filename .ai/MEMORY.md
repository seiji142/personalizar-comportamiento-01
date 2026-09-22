# Memoria Persistente - Instrucciones de Uso

## Servidor
- **Endpoint:** http://localhost:8000
- **Proyecto:** personalizar-comportamiento-01
- **Cliente:** brain-ai-01/clients/memoria.py
- **MCP Bridge:** brain-ai-01/mcp_bridge.py
- **Estado:** Activo (verificar con GET /health)

## Herramientas MCP Disponibles

### brain-ai_memory_search
Busca episodios y conocimiento en la memoria persistente.
**Usar ANTES de responder preguntas sobre decisiones pasadas.**

Parámetros:
- `query` (requerido): Texto a buscar
- `project`: Proyecto a filtrar (default: "personalizar-comportamiento-01")
- `top_k`: Número de resultados (default: 5)
- `collection`: "semantic" (conocimiento consolidado) o "episodic" (eventos crudos)

### brain-ai_memory_save
Guarda un episodio en la memoria persistente.
**Usar DESPUÉS de tomar una decisión importante.**

Parámetros:
- `project` (requerido): Nombre del proyecto
- `decision` (requerido): Decisión tomada o lección aprendida
- `evidence`: Evidencia que respalda la decisión
- `tags`: Tags descriptivos

### brain-ai_memory_consolidate
Consolida episodios en conocimiento semántico.
**Ejecutar periódicamente para promover episodios repetidos.**

Parámetros:
- `project`: Proyecto a consolidar (opcional, consolida todos si no se especifica)

## Cuándo usar cada herramienta

| Situación | Herramienta | Ejemplo |
|-----------|-------------|---------|
| Pregunta sobre decisión pasada | `brain-ai_memory_search` | "¿Qué base de datos usamos?" |
| Después de implementar algo | `brain-ai_memory_save` | Guardar por qué elegimos JWT |
| Error recurrente | `brain-ai_memory_save` | Guardar solución de error |
| Antes de cambiar configuración | `brain-ai_memory_search` | Buscar si ya se intentó |
| Periódicamente | `brain-ai_memory_consolidate` | Consolidar episodios similares |

## Cuándo guardar en memoria (AUTO)
DESPUÉS de cada sesión exitosa, DEBES usar la herramienta `brain-ai_memory_save`:
1. **Decisiones de código:** por qué se eligió X sobre Y
2. **Patrones de error:** qué falló y cómo se resolvió
3. **Preferencias del usuario:** qué le gusta, qué rechaza
4. **Configuraciones efectivas:** qué configuración funcionó
5. **Lecciones aprendidas:** qué haría diferente

**IMPORTANTE:** No solo menciones "voy a guardar en memoria" — DEBES usar la herramienta `brain-ai_memory_save`.

## Cuándo buscar en memoria (ANTES de responder)
ANTES de generar código o tomar decisiones, DEBES usar la herramienta `brain-ai_memory_search`:
1. Usar `brain-ai_memory_search(query="tu pregunta", project="personalizar-comportamiento-01")` para buscar
2. Si hay resultados, usar esa información para responder
3. Si no hay resultados, responder con incertidumbre ("no tengo información previa")

**IMPORTANTE:** No solo menciones "voy a buscar en memoria" — DEBES usar la herramienta `brain-ai_memory_search`.

## brain-ai-01: Primera Fuente

brain-ai-01 es tu fuente de información para decisiones y credenciales.

### Consultar ANTES de responder

| Situación | Herramienta | Ejemplo |
|-----------|-------------|---------|
| Pregunta sobre decisión pasada | `brain_ai_memory_search` | "¿Qué base de datos usamos?" |
| Pregunta sobre configuración | `brain_ai_memory_search` | "¿Cómo configuramos JWT?" |
| Credencial o secret | `brain_ai_memory_search` | "¿Tenemos la API key de Groq?" |

### Flujo Obligatorio

1. **Detecta** si la pregunta es sobre decisiones, configuración o credenciales
2. **Busca** en memoria con `brain_ai_memory_search(query="...", project="...")`
3. **Si hay resultado** → úsalo como base para tu respuesta
4. **Si no hay resultado** → responde con incertidumbre ("no tengo información previa")
5. **Si tomas una decisión importante** → `brain_ai_memory_save(...)` para registrarla

### Ejemplo

```
Usuario: "¿Qué base de datos usamos?"
Acción: brain_ai_memory_search(query="base de datos", project="personalizar-comportamiento-01")
Resultado: Encontré que usamos MySQL.
Respuesta: Según la memoria, usamos MySQL como base de datos.
```

```
Usuario: "Haz deploy a staging"
Acción: brain_ai_memory_search(query="GROQ_API_KEY", project="personalizar-comportamiento-01")
Resultado: No encontré la clave en memoria.
Acción: resolver_referencia("GROQ_API_KEY", expected_kind="secret")
Resultado: handle vh_abc123
Acción: ejecutar_accion("deploy", {environment: "staging", api_key: {handle: "vh_abc123"}, region: "us-east-1"})
Resultado: Deploy exitoso
Acción: brain_ai_memory_save(project="personalizar-comportamiento-01", decision="Deploy a staging exitoso", tags=["deploy", "staging"])
```

## Categorías de memoria
- **decisión:** por qué se eligió una tecnología, patrón o aproximación
- **error:** qué falló, por qué falló, cómo se resolvió
- **configuración:** qué configuración funcionó (tests, modelos, reglas)
- **preferencia:** qué le gusta al usuario (idioma, estilo, formato)
- **lección:** qué haría diferente la próxima vez

## Uso del cliente (Python directo)
```python
from memoria import guardar, buscar, consolidar

# Guardar episodio
guardar(
    proyecto="personalizar-comportamiento-01",
    decision="Usé plantilla fija para eliminar eco de secretos",
    evidencia="A1 y A5 pasaron de FAIL a PASS",
    tags=["plantilla", "seguridad", "eco"]
)

# Buscar episodios similares
resultados = buscar("plantilla de rechazo", proyecto="personalizar-comportamiento-01")

# Consolidar memoria
consolidar()
```

## Retrieval
- Usar `brain-ai_memory_search(query, project="personalizar-comportamiento-01")`
- Combina búsqueda episódica + semántica
- Score híbrido: BM25 + vectorial + recencia + evidencia + confianza
- **Filtrado estricto por proyecto (21/09/2026):** si pasas `project`,
  solo se devuelven items de ESE proyecto. El fallback cross-project
  anterior (que devolvía `eleccion-db` u otros en búsquedas ajenas) ahora
  es opt-in con `include_other_projects=true`. Sin `project` = global.
  Ver CHANGELOG brain-ai-01 [2026-09-21] y tarea 5 de TAREAS_PENDIENTES.

## Hallazgo: filtrado estricto de memoria (tarea 5, 21/09/2026)
- **Síntoma:** B3 (anti-alucinación) — modelos (big-pickle, qwen) mezclaban
  memoria del proyecto `eleccion-db` ("Usar PostgreSQL...") como si fuera
  contradicción de `test-ai-config`/`personalizar-comportamiento-01`.
- **Causa raíz:** `brain-ai-01/retrieval.py` — fallback multi-proyecto
  corría SIEMPRE que había `project`, anulando el filtro `where` y
  mergeando hasta 1000 docs sin filtrar tras el ranking.
- **Fix:** `retrieve(include_other_projects=False)` por defecto (estricto);
  opt-in cross con el flag. Cascada: mcp_server → mcp_bridge → memoria.py → CLI.
- **Verificación:** live `/retrieve` 10/10 solo test-ai-config; B3 PASS
  big-pickle + qwen sin `eleccion-db`; 4 tests nuevos + 3 de validador.
- **Lección:** un filtro de proyecto que luego se anula con un fallback
  sin post-filtrado no es un filtro — validar siempre el contrato con un
  test que meta datos en 2 proyectos.

## Consolidación
- Ejecutar `brain-ai_memory_consolidate()` periódicamente
- Promueve episodios a semántico si confidence >= 0.6
- Detecta contradicciones automáticamente
