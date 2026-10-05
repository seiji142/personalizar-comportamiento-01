---
name: fx-changelog
description: Registra cada cambio mergeado (qué, por qué, qué fix enseñó) en CHANGELOG.md. Úsalo después del review y antes del commit.
---

# fx-changelog — registrar el cambio para el futuro

El changelog es cómo le hablas a tu yo futuro y a otros agentes: cada
entrada debe permitir que el próximo spec nazca con la lección de este fix.

## Pasos
1. **Mira qué se mergea**: diff de la feature/fix actual.
2. **Agrega entrada** en `CHANGELOG.md` (créalo si no existe) con formato:
   `fecha — qué cambió — por qué — fix aplicado y qué sección del spec
   actualizó (§8 Lecciones)`.
3. **Si la lección es general** (vale para futuros specs), anótalo en la
   entrada con etiqueta `REPLAN:` para subirla a `.ai/context.md`.

## Reglas
- Una entrada por cambio; 3–5 líneas, sin muros de texto.
- Genérico: sin rutas ni proyectos hardcodeados.
- Nunca inventes motivos: si el porqué no está claro, pregunta antes de
  registrar.
