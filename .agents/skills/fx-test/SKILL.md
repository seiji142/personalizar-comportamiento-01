---
name: fx-test
description: Genera y ejecuta tests del cambio actual (unitarios + verificación funcional), limpia artefactos y re-verifica. Úsalo después de implementar y antes del review.
---

# fx-test — testear el cambio actual

## Pasos
1. **Mira qué cambió**: revisa el diff/últimos cambios del proyecto.
   Solo testea eso, no todo el repo.
2. **Genera o actualiza tests** con el framework que ya use el proyecto
   (si no hay, dilo y propón uno antes de crear nada).
3. **Ejecuta** la suite afectada. Si falla, corrige el código (nunca el test
   para que pase) y repite hasta verde.
4. **Verificación funcional**: si el cambio tiene UI o endpoint, ejercítalo
   (navegador automatizado o request real) y confirma el comportamiento
   esperado.
5. **Limpia**: elimina SOLO artefactos temporales (capturas, cachés,
   archivos generados por la herramienta). Los tests quedan versionados
   en `tests/` con referencia al spec que cubren: un fix sin test
   permanente anti-regresión no está terminado.

## Reglas
- Genérico: sin rutas ni comandos hardcodeados de un proyecto concreto.
- Un cambio, una corrida: no mezcles features en la misma verificación.
- Reporta qué se probó, qué pasó y qué quedó sin cubrir.
