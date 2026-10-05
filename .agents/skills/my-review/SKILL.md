---
name: my-review
description: Revisión de calidad de código (sin usar, duplicado, mal optimizado). Úsalo antes de cada commit o al revisar trabajo de un agente.
---

# my-review — revisión de código

Revisa 3 cosas, en este orden. Sé puntual: reporta archivo + línea + fix
sugerido, sin reescribir archivos enteros salvo que te lo pidan.

## 1. Código sin usar
Símbolos, archivos, imports o ramas que nada referencia (exports huérfanos,
variables muertas, funciones de un solo uso abandonado). Si dudas si algo se
usa, búscalo en el repo antes de marcarlo.

## 2. Lógica duplicada
Bloques copiados en 2+ sitios que deberían ser una función compartida.
Indica los sitios y propone la firma común. No propongas abstraer 2 líneas
triviales de un solo uso.

## 3. Código mal optimizado
Patrones con costo evitable: consultas N+1, consultas que traen de más,
bucles innecesarios, trabajo repetido en cada request/render. Prioriza por
impacto, no por estilo.

## Reglas
- Genérico: vale para cualquier proyecto y stack, no menciones rutas
  concretas del repo actual.
- No cambies tests para que pasen; si un test falla por tu cambio, repórtalo.
- Si no hay nada que revisar, dilo en una línea, no inventes hallazgos.
