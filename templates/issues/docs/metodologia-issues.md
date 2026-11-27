# Metodología de issues: alta, estado y cierre con evidencia

El registro `docs/issue/LISTA-ISSUES.md` es la única fuente de "qué está roto y
qué se reparó". Este documento fija las reglas; `scripts/issue_state.py` las hace
legibles por máquina y `scripts/ci_checks.py` las exige.

## Estados y dueño

| Estado | Quién lo pone | Exige | Vive en |
|---|---|---|---|
| `abierto` | agente | `esperaba:` y `paso:` (qué veía vs qué esperaba) | sección `## I-<n>` en `## Abiertos` |
| `arreglado` | agente | `test:` (suite#caso) **o** `repro:` con corrida medida | sección `## I-<n>` en `## En verificación` |
| `descartado` | agente | `motivo:` | fila en `## Descartados` |
| `cerrado` | **sólo el humano** | `aceptado:` = fecha + frase literal de lo que probó | fila en `## Cerrados` |

Un test verde no prueba que el síntoma desapareció: prueba que el motor hace lo
que el test dice. El cierre lo aporta el usuario con la frase de lo que probó.
**Nunca** pidas ni escribas un `cerrado` por tu cuenta.

## Alta (dos pasos, en este orden)

1. Guardar los archivos planos: `docs/issue/AAAA-MM-DD-<slug>.md` describe el
   síntoma (el texto del usuario, literal) y `AAAA-MM-DD-<slug>-N.png` son las
   capturas, **planas** en `docs/issue/`, sin subcarpetas.
2. Escribir la sección `## I-<n> · <título>` en la zona que corresponda, con el
   número que devuelve `python scripts/issue_state.py --next-id` (máx + 1; sólo
   el agente lo asigna). Renombrar las capturas a `I-<n>-<N>.png`, tope 3.

`sev:` (`P0`..`P3`) lo decide el agente en el triage y **no ordena el trabajo**:
un `P3` pide la misma evidencia que un `P0`.

## Zonas y bloque generado

Cuatro zonas, en este orden: `## Abiertos`, `## En verificación`, `## Cerrados`,
`## Descartados`. Las dos últimas son una línea por registro.

El bloque entre `<!-- generado:inicio -->` y `<!-- generado:fin -->` **no se
edita a mano**: lo escribe `--write` y `--check` (y el CI) lo comparan.

## Capturas

Una captura pertenece a un issue (el nombre lo dice) y otros pueden citarla en
`evidencia:`. Un archivo de `docs/issue/` que nadie cita es bandeja y `--inbox`
lo delata. Al cerrar un issue se borran sus capturas del árbol: git conserva la
historia.

## Ninguna excepción por severidad

Un `P3` tiene exactamente la misma vara que un `P0`: `arreglado` sin `test:` ni
corrida medida es error, aunque la severidad sea baja.

## Aceptación por caso de uso

La misma frase literal repetida en varios registros **es** el lote que los
aceptó; no hay registro de casos ni ids `AC-<n>`. `grep` de la frase devuelve
todos los issues que ese caso probó.

## El disparador

El registro sólo sirve si alguien lo lee: la skill `fx-issue` (con el trigger en
su `description`) y una fila de ruteo en `AGENTS.md` que mande a
`docs/issue/LISTA-ISSUES.md` cuando la tarea toca "qué falta" o "qué está
abierto". El CI exige las dos.

## Cierre operativo

```bash
python scripts/issue_state.py --check    # valida y compara el bloque generado
python scripts/issue_state.py --write    # regenera el bloque
python scripts/issue_state.py --inbox    # archivos sin triagear
python scripts/issue_state.py --next-id  # próximo I-<n>
```

## Adaptación al proyecto

`RUN_ID_RE` en `scripts/issue_state.py` es el único punto atado al proyecto:
reconoce el nombre de una corrida medida (`ui-<ts>` / `real-<ts>` en el proyecto
de origen). Adaptalo al formato de tus corridas, o vacialo para exigir sólo un
`repro:` no vacío. Los tests de `tests/test-issue-state.py` cubren el validador y
tienen que seguir en verde después del cambio.
