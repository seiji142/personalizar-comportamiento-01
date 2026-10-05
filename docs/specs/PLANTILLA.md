---
titulo: <tema del spec>
estado: borrador  # borrador | aprobado | implementado
entradas:
  - <qué necesita para empezar>
salidas:
  - <qué entrega al terminar>
dependencias:
  - <módulos, archivos o servicios afectados>
tablas_impactadas: []
criterio_aceptacion: <frase verificable que el usuario confirma en el chat>
---

# PLANTILLA de spec (flujo spec-70%)

Copia este archivo a `docs/specs/<tema>.md` y complétalo ANTES de
implementar. El frontmatter es validable por script (ver
`scripts/ci_checks.py`); el cuerpo se revisa con el humano. El spec
principal debe cubrir ~70-80% del trabajo.

## 1. Problema
¿Qué problema resuelve? ¿Para quién?

## 2. Alcance
- Incluye:
- Excluye (explícito):

## 3. Módulos / piezas
Lista de módulos o archivos implicados y qué hace cada uno.

## 4. Stack y dependencias
Lenguajes, herramientas, MCPs o servicios usados.

## 5. Diseño
Decision(es) clave y por qué (alternativas descartadas en 1 línea).

## 6. Plan de verificación
- Qué ejecuta `fx-test`:
- Qué revisa `my-review`:

## 7. Criterio de aceptación
Frase verificable que el usuario debe confirmar en el chat antes del PR.

## 8. Lecciones del fix (DESPUÉS de implementar, obligatorio)

Orden correcto ante un fallo (nunca reescribir el spec para justificar la
solución):

1. **Clasificar**: ¿el spec era correcto? → solo código + test de
   regresión, sin tocar el spec. ¿el spec estaba mal/incompleto? →
   corregir spec + revalidar criterio (§7) ANTES de tocar código.
2. **Re-disparar**: cada fix re-ejecuta tests afectados + auditoría si
   toca sus disparadores (ver `.ai/agents.md` rol 3).
3. **Registrar** abajo con etiqueta `[LOCAL]` (vale para este spec) o
   `[GENERAL]` (candidata a `context.md` en el replan).

- Fix aplicado [LOCAL/GENERAL]:
- Qué sección de este spec cambia por el fix:
- Test anti-regresión que lo cubre:

**Hotfix (excepción explícita)**: si la urgencia impide el spec previo, se
aplica directo PERO deja trazabilidad (qué, por qué, riesgo) y tests
después, en el mismo día. Sin excepción silenciosa.
