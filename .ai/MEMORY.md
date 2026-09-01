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

## Consolidación
- Ejecutar `brain-ai_memory_consolidate()` periódicamente
- Promueve episodios a semántico si confidence >= 0.6
- Detecta contradicciones automáticamente
