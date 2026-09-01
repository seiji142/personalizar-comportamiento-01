# Memoria Persistente - Instrucciones de Uso

## Servidor
- **Endpoint:** http://localhost:8000
- **Proyecto:** personalizar-comportamiento-01
- **Cliente:** brain-ai-01/clients/memoria.py
- **Estado:** Activo (verificar con GET /health)

## Cuándo guardar en memoria (AUTO)
Después de CADA sesión exitosa, guardar automáticamente:
1. **Decisiones de código:** por qué se eligió X sobre Y
2. **Patrones de error:** qué falló y cómo se resolvió
3. **Preferencias del usuario:** qué le gusta, qué rechaza
4. **Configuraciones efectivas:** qué configuración funcionó
5. **Lecciones aprendidas:** qué haría diferente

## Cuándo buscar en memoria (ANTES de responder)
ANTES de generar código o tomar decisiones:
1. Buscar si hay episodios similares en memoria
2. Verificar si hay decisiones pasadas relacionadas
3. Consultar si hay patrones de error conocidos

## Formato de episodios
```json
{
  "project": "personalizar-comportamiento-01",
  "source_type": "chat|decision|error|config",
  "author": "yo",
  "title": "resumen corto",
  "summary": "descripción detallada",
  "decisions": [{"text": "decisión tomada"}],
  "evidence": [{"type": "doc", "url_or_path": "", "excerpt": "evidencia"}],
  "tags": ["tag1", "tag2"]
}
```

## Categorías de memoria
- **decisión:** por qué se eligió una tecnología, patrón o aproximación
- **error:** qué falló, por qué falló, cómo se resolvió
- **configuración:** qué configuración funcionó (tests, modelos, reglas)
- **preferencia:** qué le gusta al usuario (idioma, estilo, formato)
- **lección:** qué haría diferente la próxima vez

## Uso del cliente
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
- Usar `buscar(query, proyecto="personalizar-comportamiento-01")`
- Combina búsqueda episódica + semántica
- Score híbrido: BM25 + vectorial + recencia + evidencia + confianza

## Consolidación
- Ejecutar `consolidar()` periódicamente
- Promueve episodios a semántico si confidence >= 0.6
- Detecta contradicciones automáticamente
