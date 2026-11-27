# Lista de issues

Registro único de lo que se rompió, cómo se reprodujo y cómo se cerró. La regla
que lo sostiene vive en [`docs/metodologia-issues.md`](../../metodologia-issues.md):
una sección `## I-<n>` por issue, cuatro estados, y **`cerrado` sólo lo pone el
humano** con la frase con la que comprobó que el síntoma desapareció.

- **Abiertos**: sigue roto, o no hay con qué probar el arreglo.
- **En verificación**: hay un arreglo con test determinista o corrida medida; le
  falta la prueba del humano.
- **Cerrados** y **Descartados**: una línea por issue, porque el cuerpo ya no hace
  falta.

El bloque de abajo lo genera `python scripts/issue_state.py --write` y el CI lo
compara con `--check`: no se edita a mano. `--inbox` lista los archivos de
`docs/issue/` que ningún registro cita todavía; `--next-id` da el próximo `I-<n>`.

Las capturas viven mientras el issue vive (`I-<n>-<N>.png`, tope 3 por issue) y al
cerrar se borran del árbol: git conserva la historia.

<!-- generado:inicio -->
### Resumen

| Estado | N |
|---|---:|
| abierto | 0 |
| arreglado | 0 |
| cerrado | 0 |
| descartado | 0 |
| **total** | 0 |

### Abiertos

| # | sev | título |
|---|---|---|

### En verificación

| # | sev | prueba |
|---|---|---|

<!-- generado:fin -->

## Abiertos

## En verificación

## Cerrados

| # | fecha | sha | test | aceptado |
|---|---|---|---|---|

## Descartados

| # | fecha | motivo |
|---|---|---|
