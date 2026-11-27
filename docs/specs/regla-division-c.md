---
titulo: Regla de division (c) coherente con el gitflow adoptado
estado: implementado
entradas:
  - Auditoria de drift entre los 3 repos que cargan la regla
salidas:
  - .ai/agents.md con la vineta (c) sin condicional obsoleto
dependencias:
  - .ai/agents.md
tablas_impactadas: []
criterio_aceptacion: La regla (c) de personalizar-comportamiento-01 refiere a la seccion Publicacion igual que en gentle-ai, sin el condicional "si el proyecto adopto gitflow".
---

# Regla de division (c)

## 1. Problema

La vineta (c) de "Regla de division" dice: `rol 2 + worktree cada uno (ver
.ai/commands.md si el proyecto adopto gitflow)`. Este repo **si** adopto
gitflow: tiene seccion `## Publicacion`, `scripts/gh-publish.ps1` y
`.github/workflows/ci.yml`. El condicional deja escrita como abierta una duda ya
resuelta, y difiere de la redaccion de `gentle-ai`, que es el mismo hecho.

## 2. Alcance

- Incluye: la vineta (c) de `.ai/agents.md`.
- Excluye (explicito): la redaccion de `templates/gitflow-scaffold` (es la
  plantilla; ahi el condicional si aplica porque el adoptante decide) y el resto
  del archivo.

## 3. Modulos / piezas

`.ai/agents.md`, seccion "Regla de division", vineta (c).

## 4. Stack y dependencias

Markdown cargado como `instructions` por `opencode.json`. `scripts/ci_checks.py`
no valida prosa: este cambio no puede tener test automatico.

## 5. Diseno

Alternativas descartadas: (a) dejar el condicional - mantiene el drift y la duda
escrita; (b) copiar la redaccion del scaffold - genericiza de mas un repo que ya
decidio. Se elige la redaccion de `gentle-ai` porque el hecho (gitflow adoptado)
esta verificado con archivos presentes.

## 6. Plan de verificacion

- Que ejecuta `fx-test`: `python scripts/ci_checks.py` -> VERDE.
- Que revisa `my-review`: que el diff toque solo las 2 lineas de la vineta y que
  el texto quede igual al de `gentle-ai`.

## 7. Criterio de aceptacion

La regla (c) de `personalizar-comportamiento-01` refiere a la seccion
Publicacion igual que en `gentle-ai`, sin el condicional "si el proyecto adopto
gitflow".

## 8. Lecciones del fix (DESPUES de implementar, obligatorio)

Sin fixes posteriores a la implementacion inicial: la verificacion paso en la
primera corrida.

## 9. Log del cambio (opcional, solo si hubo correcciones)

`L1` = "dale" (respuesta a la propuesta de unificar la regla (c)).
