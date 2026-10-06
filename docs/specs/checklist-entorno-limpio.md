---
titulo: checklist-entorno-limpio
estado: borrador
entradas:
  - .ai/commands.md (Variante B pre-PR)
  - Evidencia pilotos H1/H2 del lab hermano (E6/E7): falso verde de entorno
salidas:
  - .ai/commands.md con 2 refuerzos (dependencias + entorno destino)
  - Entrada docs/CHANGELOG.md via replan
dependencias:
  - .ai/commands.md
tablas_impactadas: []
criterio_aceptacion: Checklist exige entorno limpio ante cambio de dependencias y pruebas en entorno/SO destino, confirmado por el humano en el chat.
---

# Spec: checklist entorno limpio (refuerzo Variante B)

## 1. Problema
La checklist pre-PR no pide probar en entorno limpio ni en el entorno
destino. Dos pilotos lo pagaron: H1 verde en UTF-8 pero rojo en
Windows cp1252; H2 verde local pero rojo en instalación fresca
(`mcp 2.x` vs `fastapi-mcp 0.4.0`). Ambos son la misma clase de falso
verde de entorno (hermana del E5 del banco).

## 2. Alcance
- Incluye:
  - Regla "si tocas dependencias: instalación limpia + suite".
  - Regla "si el producto corre en otro SO/entorno: pruebas allí".
- Excluye (explicito):
  - Cambiar suites, gates o CI (solo texto de checklist).
  - Versionado aparte: entra en el próximo bump si lo hay; si no,
    se registra sin bump (cambio de 2 líneas, sin código).

## 3. Modulos / piezas
- `.ai/commands.md` Variante B: 2 ítems nuevos (1b y 1c).

## 4. Stack y dependencias
- Solo Markdown. Sin código, sin tests nuevos (la evidencia ya existe
  en E6/E7 del lab hermano).

## 5. Diseño
- Decision: genérico ("entorno limpio", "entorno/SO destino"), sin
  mencionar pip/venv/cp1252: el Núcleo no conoce stacks.
- Alternativa descartada: guía larga con ejemplos por stack (bloat;
  los ejemplos viven en el banco E6/E7, no en el Núcleo).

## 6. Plan de verificación
- Qué ejecuta `fx-test`: `python scripts/ci_checks.py` verde (el
  cambio es docs-only; suites con API/MCP no corren en CI por diseño
  y el cambio no las toca).
- Qué revisa `my-review`: texto fusionado, sin duplicar reglas
  existentes; sin rutas hardcodeadas.

## 7. Criterio de aceptación
Checklist exige entorno limpio ante cambio de dependencias y pruebas en entorno/SO destino, confirmado por el humano en el chat.

## 8. Lecciones del fix (DESPUÉS de implementar, obligatorio)
- Fix aplicado [GENERAL]: ítems 1b (entorno limpio) y 1c (entorno
  destino) en Variante B, genéricos sin stack, desde E6/E7.
- Qué sección de este spec cambia por el fix: ninguna (el diseño se
  cumplió tal cual; docs-only, sin código).
- Test anti-regresión que lo cubre: `scripts/ci_checks.py` verde
  (la evidencia de fondo vive en E6/E7 del lab hermano).
