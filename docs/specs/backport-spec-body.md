---
titulo: backport-spec-body
estado: implementado
entradas:
  - Lab hermano: spec `ci-checks-spec-body.md` implementada y probada (incluye prueba negativa)
  - scripts/ci_checks.py de la base (solo valida frontmatter)
salidas:
  - scripts/ci_checks.py con las 3 reglas de cuerpo (sin exención: aquí no existe spec legado)
  - Entrada docs/CHANGELOG.md via replan
dependencias:
  - scripts/ci_checks.py
  - docs/specs/*.md (3 specs implementado que deben seguir verdes)
tablas_impactadas: []
criterio_aceptacion: CI verde con las 3 specs actuales + rojo provocado efímero, confirmado por el humano en el chat.
---

# Spec: backport reglas de cuerpo (desde el lab)

## 1. Problema
El `ci_checks.py` del Núcleo (el que se copia a cada adopción) valida
frontmatter pero no cuerpo; el lab ya probó las 3 reglas mínimas con
prueba negativa. Sin backport, el Núcleo distribuye la versión que
deja pasar specs incompletas.

## 2. Alcance
- Incluye:
  - Portar el bloque de 3 reglas (secciones 1-8, estado válido, §8
    sin placeholders si implementado).
  - Prueba negativa efímera + `tests/unit` + `ci_checks`.
- Excluye (explicito):
  - La exención nominal de `auditoria-fixes.md` (archivo solo del
    lab; aquí no aplica).
  - Bump de versión (se acumula, criterio de #4/#5/#6).

## 3. Modulos / piezas
- `scripts/ci_checks.py::check_specs`: +1 bloque tras frontmatter.

## 4. Stack y dependencias
- Python stdlib. Sin tests nuevos permanentes.

## 5. Diseño
- Decision: port literal del bloque probado en el lab (misma regex,
  mismo formato de error). Nada que re-diseñar; la evidencia ya existe.

## 6. Plan de verificación
- Positiva: `ci_checks.py` verde (las 3 specs implementado tienen §8
  lleno) + `tests/unit` verde.
- Negativa: spec temporal rota → rojo → se borra.

## 7. Criterio de aceptación
CI verde con las 3 specs actuales + rojo provocado efímero, confirmado por el humano en el chat.

## 8. Lecciones del fix (DESPUÉS de implementar, obligatorio)
- Fix aplicado [GENERAL]: port literal del bloque (sin exención, no
  aplica aquí); verde día uno con las 3 specs actuales.
- Qué sección de este spec cambia por el fix: ninguna.
- Test anti-regresión que lo cubre: spec temporal rota → rojo
  provocado → borrada; `tests/unit` 3 passed.
