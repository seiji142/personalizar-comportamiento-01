---
titulo: RDD - auditor en proceso aparte con maquina de estados
estado: aprobado
entradas:
  - docs/research/odd-youtube.md §7 - RDD corre de 1 a 4 agentes segun la severidad, en
    un proceso separado "para que no venga infectado de contexto ajeno"
  - .ai/agents.md rol 3 - el auditor antagonista ya esta definido como rol, no como pieza
  - .ai/commands.md §Que entrega cada modo - la regla ya nombra
    `opencode run --standalone` como aislamiento minimo, pero nada lo ejecuta
  - Verificado 2026-11-03 - `opencode run --standalone --agent <nombre> --format json`
    existe en opencode v2.1.4 de esta maquina
salidas:
  - .opencode/agents/auditor.md - agente de solo lectura con las 4 dimensiones
  - scripts/rdd_review.py - clasifica severidad, lanza 1-4 procesos y agrega dictamenes
  - tests/scripts/test_rdd_review.py - tests offline de severidad, comandos y agregacion
dependencias:
  - .ai/agents.md (rol 3)
  - .ai/commands.md (validacion pre-PR y escaladores)
  - opencode CLI v2.1.4
tablas_impactadas: []
criterio_aceptacion: Con un diff que toca `scripts/`, `python scripts/rdd_review.py
  --dry-run` imprime 4 comandos `opencode run --standalone --agent auditor`; con un diff
  que toca solo `docs/`, imprime 1; y la suite offline demuestra que un dictamen no
  aprobado, un timeout o un JSON invalido nunca producen APPROVED.
---

# RDD: la revision deja de ser una promesa y pasa a ser un proceso

## 1. Problema

`.ai/agents.md` define el rol 3 (auditor antagonista) y `.ai/commands.md` agrega que el
aislamiento minimo es `opencode run --standalone`, pero **nadie ejecuta ese comando**. Hoy
la auditoria depende de que un humano abra otra sesion y le pegue el diff: un paso manual
que se saltea bajo apuro sin que nada lo detecte. El resultado es el peor de los dos
mundos: la regla existe (y da la sensacion de cobertura) y no se cumple.

Para quien escribe codigo en este framework, el costo es concreto: los cambios que tocan
`scripts/`, permisos o datos pasan el gate con la revision del mismo agente que los
escribio, que es exactamente el contexto contaminado que RDD busca evitar.

### Fallas conocidas

- `opencode run --standalone` levanta un server privado por invocacion: la latencia no es
  despreciable y **no se puede medir en CI**, porque el runner no tiene modelos ni
  credenciales. Esto ya es asi antes del cambio y no lo arregla.
- `--format json` emite eventos NDJSON, no un veredicto unico: cualquier parser tiene que
  tolerar texto alrededor. Asumir un JSON limpio seria un falso verde.
- El repo **no tiene `.opencode/`**: crear la carpeta es parte de este cambio y no hay
  precedente local que copiar.
- El repo no tiene job de CI para esta pieza, y este cambio no lo agrega (ver §2).

## 2. Alcance

### Incluye

1. Un agente `auditor` de **solo lectura** en `.opencode/agents/auditor.md`, con las cuatro
   dimensiones de RDD: reliability, robustness, legibilidad y seguridad.
2. `scripts/rdd_review.py`: clasifica severidad (1-4), arma y lanza 1-4 procesos
   `opencode run --standalone --agent auditor`, y agrega los dictamenes en un veredicto.
3. `--dry-run`: imprime los comandos exactos sin ejecutarlos. Es el gate que corre en CI y
   en local sin credenciales.
4. Tests offline en `tests/scripts/test_rdd_review.py` (unittest, stdlib).

### Excluye (explicito)

- **Correr el auditor en CI.** Sin modelos ni credenciales no hay dictamen. La evidencia de
  una corrida real va en §8 del spec, no en un workflow.
- **Severidad semantica.** La severidad sale de rutas y escaladores, no de leer el contenido
  del diff. Un cambio peligroso en un archivo "tranquilo" se clasifica por lo que el humano
  declara en el PR, no por inferencia.
- **Reemplazar `my-review`.** RDD es la capa de ejecucion aislada; la revision de calidad del
  implementador sigue siendo `my-review`. Son dos cosas y se suman.
- **Persistencia.** No hay base de datos ni historico: el JSON de salida lleva un `run_id`
  y nada mas.

## 3. Modulos / piezas

| Pieza | Que hace |
|---|---|
| `.opencode/agents/auditor.md` | Perfil del agente: prompt con las 4 dimensiones y permisos de solo lectura |
| `scripts/rdd_review.py` | CLI: clasifica severidad, arma comandos, lanza procesos, agrega dictamenes |
| `tests/scripts/test_rdd_review.py` | Tests offline: severidad, armado de comandos, parseo y agregacion |

## 4. Stack y dependencias

Python 3.10, solo stdlib (`argparse`, `json`, `subprocess`, `concurrent.futures`). Ninguna
dependencia nueva, ningun cambio en `requirements.txt`. OpenCode CLI v2.1.4
(`run --standalone --agent <nombre> --format json`). El script no hace red: quien la usa es
el modelo del auditor.

## 5. Diseno

**1. El agente es un perfil con permisos, no un prompt suelto.** El frontmatter de V2 es el
que impone el "solo lectura"; un prompt que dice "no edites" no impide nada.

```yaml
mode: all
permissions:
  - action: edit
    resource: "*"
    effect: deny
  - action: shell
    resource: "*"
    effect: deny
  - action: subagent
    resource: "*"
    effect: deny
  - action: webfetch
    resource: "*"
    effect: deny
  - action: websearch
    resource: "*"
    effect: deny
```

- Descartada: `mode: subagent` exclusivo. `--agent` selecciona el agente de la sesion;
  `all` cubre el lanzamiento por CLI y el uso como subagente.
- Descartada: permitir `shell` y confiar en el prompt. El auditor que puede ejecutar
  comandos deja de ser de solo lectura por definicion.

**2. La severidad es determinista y se puede discutir.** Sale de los archivos del diff:

| Severidad | Archivos |
|---|---|
| 4 | `.ai/**`, `.agents/skills/**`, `scripts/**`, `opencode.json`, auth, crypto, migraciones |
| 3 | `.github/workflows/**`, `requirements*.txt`, configuracion de runtime |
| 2 | `src/**`, `tests/**` sin escaladores |
| 1 | solo `docs/**` y Markdown |

Se toma la severidad **maxima** del diff. `--severity N` es un override humano que solo puede
subir; si intenta bajar, el script lo rechaza y explica por que (un cambio que toca
`scripts/` no se audita como un README porque alguien lo pida). El JSON de salida registra
severidad calculada y efectiva, para que la diferencia sea auditable.

**3. N procesos = N dimensiones, no N agentes al azar.**

| Severidad | Procesos | Reparto |
|---|---|---|
| 1 | 1 | las 4 dimensiones en un solo auditor |
| 2 | 2 | {reliability, robustness} / {legibilidad, seguridad} |
| 3 | 3 | {reliability, robustness} / {legibilidad} / {seguridad} |
| 4 | 4 | una dimension por proceso |

Cada proceso recibe el diff por `stdin`/`-f` y devuelve un veredicto.

**4. La agregacion falla cerrada.** `APPROVED` solo si **todos** los dictamenes son
`approve`. Un `reject` produce `REJECTED`. Timeout, exit code distinto de cero, JSON
invalido o veredicto ausente producen `INCONCLUSIVE`, que **bloquea igual que reject**: no
existe el camino "no pude, entonces apruebo".

Maquina de estados: `CLASSIFIED -> LAUNCHED -> COLLECTED -> APPROVED | REJECTED |
INCONCLUSIVE`. Con `--dry-run`: `CLASSIFIED -> DRY_RUN`.

- Descartada: reintentos automaticos. Un auditor que fallo dos veces no se arregla
  reintentando; se reporta y decide el humano.
- Descartada: mayoria simple. Con dos auditores en desacuerdo, la mayoria no existe; el
  desacuerdo es un hallazgo.

**5. Sin `shell=True`.** Los comandos se arman como lista de argumentos y el script rechaza
`--base`/`--head` que empiecen con `-`, para que un nombre de rama no se convierta en una
bandera del CLI.

## 6. Plan de verificacion

**Que ejecuta `fx-test`:**

- `python scripts/rdd_review.py --dry-run --base develop` sobre un diff de solo `docs/`
  imprime **1** comando.
- El mismo comando sobre un diff que toca `scripts/` imprime **4** comandos.
- `python scripts/rdd_review.py --dry-run --severity 1` sobre el diff de `scripts/` sale con
  error y explica que el override no puede bajar la severidad.
- `python -m unittest tests/scripts/test_rdd_review.py -v` (offline, sin modelos).
- `python -m pytest tests/unit -q`, `python tests/scripts/test_validators.py`,
  `python tests/scripts/test_rate_limit_tpd.py`, `python scripts/ci_checks.py`.
- Una corrida real con `--severity 1 --timeout 300` sobre un cambio chico, con salida y
  latencia registradas en §8.

**Que revisa `my-review`:**

- Que el frontmatter del agente niegue `edit`, `shell`, `subagent`, `webfetch`, `websearch`.
- Que `INCONCLUSIVE` no se mapee nunca a aprobado (probar con timeout y JSON roto).
- Que no haya `shell=True` ni interpolacion de ramas sin validar.
- Que ninguna linea agregada supere 120 caracteres.

## 7. Criterio de aceptacion

Con un diff que toca `scripts/`, `python scripts/rdd_review.py --dry-run` imprime 4 comandos
`opencode run --standalone --agent auditor`; con un diff que toca solo `docs/`, imprime 1; y
la suite offline demuestra que un dictamen no aprobado, un timeout o un JSON invalido nunca
producen `APPROVED`.

## 8. Lecciones del fix (DESPUES de implementar, obligatorio)

- Fix aplicado [LOCAL/GENERAL]:
- Que seccion de este spec cambia por el fix:
- Test anti-regresion que lo cubre:

## 9. Log del cambio

`L1` = pedido original del usuario, literal (2026-11-02):

> "#3 - RDD: no puede ir aca, y no es excusa. gentle-ai tiene src/ y tests/
> vacios... Va al framework... Un agente auditor con permisos de solo
> lectura. Un script que lance opencode run --standalone --agent auditor -
> 1 a 4 procesos segun la severidad. La maquina de estados que decide
> severidad y consume los dictamenes."

`L2`: "ok" (2026-11-03) - aprueba el diseno de este spec y autoriza el PR a
`develop`. Desvio registrado: el worktree se creo primero en gentle-ai porque
`worktree_create` opera sobre el repo de la sesion; se cerro y se rehizo contra
el framework. `git_crear_rama` movio el `HEAD` de gentle-ai (resuelve el repo
antes del `session_move`); se devolvio a `develop` y la rama se creo con
`git switch -c` dentro del worktree.
