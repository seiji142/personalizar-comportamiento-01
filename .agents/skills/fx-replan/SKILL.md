---
name: fx-replan
description: Replan documentado entre features (estado, spec vigente, lección promovida o ninguna, próxima tarea). Úsalo tras cada merge, nunca como charla sin artefacto.
---

# fx-replan — replan con I/O obligatorio

El replan no es una conversación: produce un artefacto o no ocurrió.
Ejecútalo tras cada merge, antes de la siguiente feature.

## Pasos
1. **Estado del cambio**: mergeado / parcial / cancelado / hotfix
   pendiente de tests.
2. **Spec vigente**: ¿sigue válido el spec? ¿el roadmap? ¿el proceso?
   Lo que cambió, actualízalo ahora (no «después»).
3. **Lección**: ¿alguna etiqueta `[GENERAL]` pendiente en §8 de specs?
   Promuévela a `.ai/context.md` respetando el presupuesto de
   guardrails (fusionar o podar). Si no hay, registra «ninguna».
4. **Próxima tarea**: qué sigue y su spec (o «pendiente de spec»).

## Salida
Registra el resultado en `CHANGELOG.md` bajo el merge correspondiente
(1–4 líneas). Sin registro, el replan no cuenta.

## Reglas
- Genérico: sin rutas ni proyectos hardcodeados.
- Un replan, un merge: no acumules varios cambios sin replanear.
