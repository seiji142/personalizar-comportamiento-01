---
titulo: no-afirmar-sin-probar
estado: implementado
entradas:
  - .ai/rules.md §8 (verificación obligatoria)
  - Caso real: afirmación falsa de capacidad `gh createRepository` (scope no verificado)
salidas:
  - .ai/rules.md §8.7 (capacidades externas se prueban antes de afirmarse)
  - Entrada docs/CHANGELOG.md via replan
dependencias:
  - .ai/rules.md
tablas_impactadas: []
criterio_aceptacion: Regla operativa fusionada en §8 (sin bloat), ci_checks verde, confirmado por el humano en el chat.
---

# Spec: no afirmar capacidad sin probarla (§8.7)

## 1. Problema
Las reglas §8.1/§8.3 prohíben asumir sin evidencia en abstracto, pero no
nombran el caso concreto "afirmar que puedo hacer X con una herramienta
externa". Caso real: se afirmó poder crear repos con `gh` por
plausibilidad (funcionó para PRs) sin verificar el scope
`createRepository` → afirmación falsa. El principio existía; el gatillo
operativo, no.

## 2. Alcance
- Incluye:
  - Subsección §8.7 operativa (3 pasos + motivo con el caso real).
  - Entrada CHANGELOG + §8 de esta spec.
- Excluye (explicito):
  - Cambiar §8.1–§8.6, §9, tests, CI o versionado (docs-only mínimo).
  - Bump de versión (texto, no Núcleo funcional; se acumula).

## 3. Modulos / piezas
- `.ai/rules.md`: §8.7 nuevo tras §8.6.

## 4. Stack y dependencias
- Solo Markdown. Sin código ni tests nuevos.

## 5. Diseño
- Decision: subsección fusionada en §8 existente (concreta y accionable:
  probar permiso/scope/red antes de prometer), no principio nuevo.
- Alternativa descartada: confiar solo en §8.1/§8.3 (ya demostrado
  insuficiente en la práctica).

## 6. Plan de verificación
- Qué ejecuta `fx-test`: `python scripts/ci_checks.py` verde (docs-only;
  suites API/MCP no tocadas, no corren en CI por diseño).
- Qué revisa `my-review`: fusión sin bloat, sin rutas hardcodeadas.

## 7. Criterio de aceptación
Regla operativa fusionada en §8 (sin bloat), ci_checks verde, confirmado por el humano en el chat.

## 8. Lecciones del fix (DESPUÉS de implementar, obligatorio)
- Fix aplicado [GENERAL]: §8.7 operativo en `.ai/rules.md` (probar
  permiso/scope antes de afirmar capacidad).
- Qué sección de este spec cambia por el fix: ninguna (el diseño se
  cumplió tal cual; docs-only).
- Test anti-regresión que lo cubre: `scripts/ci_checks.py` verde.
