---
name: fx-issue
description: Alta y estado de issues en docs/issue/LISTA-ISSUES.md (cuatro estados, cierre sólo por el humano con evidencia). Úsalo al reportar un bug con capturas, al arreglarlo, o cuando la tarea pregunte "qué falta" o "qué está abierto".
---

# fx-issue — el registro de issues no se escribe a mano

`docs/issue/LISTA-ISSUES.md` es la única fuente de "qué está roto y qué se reparó".
La regla vive en `odd/tasks/issue-metodologia.md` (S1-S11); esta skill es el disparador
para que se aplique en el momento, no cuando alguien se acuerda.

## Cuándo se activa

- El usuario reporta un bug con capturas → **alta**.
- Se arregla algo que ya está en el registro → **cambio de estado**.
- El usuario pregunta qué falta, qué está abierto o qué se arregló → **leer el registro**,
  no responder de memoria.

## Alta (dos pasos, en este orden)

1. **Guardar los archivos planos**: `docs/issue/AAAA-MM-DD-<slug>.md` describe el síntoma
   (el texto del usuario, literal) y `docs/issue/AAAA-MM-DD-<slug>-N.png` son las capturas,
   **planas** en `docs/issue/`, sin subcarpetas.
2. **Escribir la sección** `## I-<n> · <título>` en la zona que corresponda, con el número
   que devuelve `python scripts/issue_state.py --next-id` (máx + 1, sólo el agente lo
   asigna). Renombrar las capturas a `I-<n>-<N>.png`, tope 3.

`sev:` lo decide el agente en el triage (`P0`..`P3`) y **no ordena el trabajo**: un P3
pide la misma evidencia que un P0.

## Estados y quién los pone

| Estado | Quién | Exige |
|---|---|---|
| `abierto` | agente | `esperaba:` y `paso:` (qué veía vs qué esperaba) |
| `arreglado` | agente | `test:` (suite#caso) **o** una corrida medida `ui-<ts>` en `repro:` |
| `descartado` | agente | fila en `## Descartados` con el `motivo:` |
| `cerrado` | **sólo el humano** | fila en `## Cerrados` con `aceptado:` = fecha + frase literal |

Un test verde no prueba que el síntoma desapareció: prueba que el motor hace lo que el test
dice. El cierre lo aporta el usuario con la frase de lo que probó. **Nunca** pidas ni
escribas un `cerrado` por tu cuenta.

## Cierre operativo

```bash
python scripts/issue_state.py --check    # valida y compara el bloque generado
python scripts/issue_state.py --write    # regenera el bloque (después de mover un estado)
python scripts/issue_state.py --inbox    # archivos sin triagear
python scripts/issue_state.py --next-id  # próximo I-<n>
```

El bloque entre `<!-- generado:inicio -->` y `<!-- generado:fin -->` **no se edita a mano**:
lo escribe `--write` y `--check` (y el CI) lo comparan.

## Reglas

- Una captura pertenece a un issue (el nombre lo dice) y otros pueden citarla en
  `evidencia:`; un archivo que nadie cita es bandeja y `--inbox` lo delata.
- Al cerrar un issue se borran sus capturas del árbol: git conserva la historia.
- No se inventa el estado de un issue viejo: si no hay test ni corrida medida, queda
  `abierto` con la nota de qué falta.
- Un issue nuevo no se agrega a la tabla resumen: la tabla la genera el script.
