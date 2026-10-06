---
titulo: nucleo-ci-base
estado: implementado
entradas:
  - .ai/commands.md (CI exigido en verde, sin workflow que lo ejecute)
  - templates/gitflow-scaffold (ci.yml Node que falla por diseño hasta adaptarse)
  - Evidencia H3 (E8): ci.yml escrito desde cero, primer run rojo por falta de pip install
salidas:
  - templates/ci-base.yml versionado (job artefactos + bloques por stack)
  - 1 línea en docs/REUTILIZAR.md (apuntar la fila al archivo versionado)
  - Comando global actualizado a copiar el archivo (fuente única = repo)
  - Entrada docs/CHANGELOG.md via replan
dependencias:
  - scripts/ci_checks.py (lo que el job base ejecuta)
tablas_impactadas: []
criterio_aceptacion: Toda adopción obtiene CI verde día uno para artefactos tras descomentar su bloque, confirmado por el humano en el chat.
---

# Spec: ci.yml base en el Núcleo

## 1. Problema
El Núcleo exige CI verde pero no trae ningún workflow que lo ejecute;
el único `ci.yml` vive en el scaffold opcional, es Node y falla por
diseño hasta adaptarse. Resultado medido (H3/E8): el adoptante escribe
el workflow desde cero y el primer run remoto sale rojo (faltó
instalar dependencias de test). Hueco estructural, no descuido.

## 2. Alcance
- Incluye:
  - `.github/workflows/ci.yml` base: job `artefactos` (`checkout` +
    `ci_checks.py`, sin dependencias) + bloques comentados Python
    (`pip install` + `pytest`) y Node (`npm ci/build`) para
    descomentar según stack.
  - 1 línea en `docs/REUTILIZAR.md`: copiar el workflow y descomentar
    el bloque del stack.
- Excluye (explicito):
  - Tocar el `ci.yml` del scaffold, gates, versionado o suites
    (se acumula al próximo bump; sin bump propio).
  - Bloques para otros stacks (el adoptante los añade; el patrón
    queda mostrado).

## 3. Modulos / piezas
- `templates/ci-base.yml` (nuevo, versionado): job `artefactos`
  (`checkout` + Python 3.12 + `ci_checks.py`) + bloques comentados
  Python (`pip install` + `pytest`) y Node (`npm ci/build`).
- `docs/REUTILIZAR.md`: la fila pasa de "plantilla mínima en el
  comando" a copiar este archivo y descomentar el bloque del stack.
- Comando global `adoptar-framework.md`: copiar el archivo en vez de
  describir contenido inline (fuente única sigue siendo el repo).

## 4. Stack y dependencias
- Solo YAML/Markdown. GitHub Actions `ubuntu-latest`.

## 5. Diseño
- Decision: job base sin dependencias (siempre verde día uno) +
  bloques opt-in por stack. La parte común se ejecuta; el stack se
  elige. Alternativa descartada: workflow completo por stack en el
  Núcleo (bloat; el Núcleo no conoce stacks).

## 6. Plan de verificación
- Qué ejecuta `fx-test`: `python scripts/ci_checks.py` verde
  (docs-only; suites API/MCP no tocadas).
- Qué revisa `my-review`: YAML válido, sin secretos, sin rutas
  hardcodeadas.

## 7. Criterio de aceptación
Toda adopción obtiene CI verde día uno para artefactos tras descomentar su bloque, confirmado por el humano en el chat.

## 8. Lecciones del fix (DESPUÉS de implementar, obligatorio)
- Fix aplicado [GENERAL]: `templates/ci-base.yml` versionado + fila
  REUTILIZAR apuntando al archivo + comando global copiando el
  archivo (fuente única = repo). Hallazgo durante el trabajo: el
  repo ya traía su propio `ci.yml` de suite y el comando describía
  la plantilla inline sin versionar; la spec se corrigió a eso (§3).
- Qué sección de este spec cambia por el fix: §3 (de "ci.yml base
  en el Núcleo" a archivo versionado + comando).
- Test anti-regresión que lo cubre: `scripts/ci_checks.py` verde +
  parse YAML válido del template.
