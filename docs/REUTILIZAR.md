# Reutilizar el Framework de Comportamiento

Guía para adoptar el framework en otro proyecto.

> **FRAMEWORK_VERSION: 2026.10.05.2** — el comando `/adoptar-framework`
> instala esta versión y el proyecto destino la anota en su README.
> Capas: Núcleo (siempre) ≠ dominios de ejemplo (MCP YouTube, corpus de
> videos — solo si se piden) ≠ gitflow (solo si se pide).

> **§0 — Lee esto primero.** Toda adopción del framework incluye SIEMPRE el
> **Núcleo** (comportamiento + estructura). El MCP `brain-ai` y la plantilla
> `gitflow-scaffold` son **opcionales** y solo se agregan si se piden
> explícitamente. Una adopción que solo copie `.ai/` está incompleta por
> definición (ver Checklist).
>
> **Forma preferida de adoptar:** abre OpenCode en el proyecto destino
> (vacío) e invoca `/adoptar-framework` (comando global en
> `~/.config/opencode/commands/adoptar-framework.md`; reinicia OpenCode tras
> instalarlo). El comando pregunta dominio/stack/modelo y ejecuta el Núcleo
> solo. El prompt manual de abajo es el fallback si el comando no está
> instalado.

---

## Fuentes

| Fuente | Qué aporta | Ubicación | Obligatoria |
|--------|-----------|-----------|-------------|
| **Este proyecto** (`personalizar-comportamiento-01`) | Núcleo: `.ai/` de comportamiento (guardrails, plantilla de rechazo, memoria conceptual) + estructura base (`src/`, `tests/`, `docs/`, `scripts/`, raíz) | `Proyecto AI/personalizar-comportamiento-01/` | **Sí, siempre** |
| **MCP brain-ai** (proyecto `brain-ai-01`) | Memoria persistente + provenance/handles (`brain-ai_*`) | Proyecto `brain-ai-01`, bloque `mcp` en `opencode.json` | Solo si se pide MCP |
| **gitflow-scaffold** (template, v2026.09.25) | Piezas de gitflow: ramas, CI, gh-publish, `VERSION` | `Proyecto AI/templates/gitflow-scaffold/` | Solo si se pide gitflow |

**Nota:** las piezas de gitflow (`ci.yml`, `gh-publish.ps1`, `VERSION`, sección de ramas) se copian **desde el template**, no desde este proyecto — nuestro `ci.yml` ya está adaptado a Python.

---

## Qué es lo reutilizable

### Núcleo (siempre)

| Componente | Fuente | Descripción |
|------------|--------|-------------|
| `.ai/` (limpio, sin `brain-ai_*`) | Este proyecto | System prompt del agente (rol, reglas, contexto, agentes) |
| `opencode.json` (sin bloque `mcp`, con `skills.paths`) | Este proyecto | Configuración de modelo, permisos e instrucciones |
| `AGENTS.md` | Este proyecto | Punto de entrada de OpenCode |
| `.agents/skills/` (my-review, my-review-security, fx-test, fx-changelog, fx-replan, fx-git) | Este proyecto | Skills genéricos invocables por nombre |
| `docs/specs/PLANTILLA.md` | Este proyecto | Plantilla de spec con frontmatter validable |
| `scripts/ci_checks.py` | Este proyecto | CI de artefactos stdlib (checks docs/specs se auto-omiten) |
| `.github/workflows/ci.yml` | Copiar `templates/ci-base.yml` y descomentar el bloque del stack | Job `artefactos`: Python 3.12 + `ci_checks.py` (verde día uno); tests por stack opt-in |
| `docs/CHANGELOG.md` | Este proyecto (`docs/PLANTILLA-CHANGELOG.md`) | Registro de merges + índice de lecciones |
| `src/`, `tests/`, `docs/`, `scripts/` (con `.gitkeep` + `README.md` breve) | Crear nuevos | Estructura base de código, pruebas, documentación y tooling |
| `.env.example` | Crear nuevo | Plantilla con las variables que el proyecto necesita |
| `.gitignore` | Este proyecto (adaptar) | Exclusiones estándar (`.env`, `node_modules/`, `__pycache__/`, `logs/`, etc.) |
| `README.md` | Crear nuevo | Documentación principal del nuevo proyecto |
| `requirements.txt` | Crear nuevo | Solo cuando el stack lo exija |

### Opcional MCP brain-ai (solo si se pide)

Secciones `brain-ai_*` en `system.md`, §9 de `rules.md` (procedencia/handles),
tools de memoria en `commands.md`/`MEMORY.md` y bloque `mcp.brain-ai` en
`opencode.json`.

### Opcional gitflow (solo si se pide)

| Componente | Fuente | Descripción |
|------------|--------|-------------|
| `scripts/gh-publish.ps1` | Template | Creación/merge de PRs vía gh CLI |
| `.github/workflows/ci.yml` | Template | CI offline en PRs y push |
| `.github/workflows/deploy.yml` | Template | Deploy a GitHub Pages (solo si aplica) |
| `TEMPLATE_GITFLOW_GH_PAGES.md` | Template | Guía completa de setup de gitflow |
| `VERSION` + `CHANGELOG.md` | Template | Control de versiones del kit para upgrades |

**No incluye nunca:** la suite de tests (`src/doc/ESTRUCTURA/`). Los tests son específicos de este proyecto.

---

## Estructura del Núcleo (obligatoria)

```
nuevo-proyecto/
├── .ai/
│   ├── system.md          # Rol, tono y estilo del agente
│   ├── rules.md           # Reglas obligatorias (seguridad, git, calidad)
│   ├── context.md         # Stack, arquitectura y convenciones
│   ├── agents.md          # 4 roles + regla de división
│   ├── commands.md        # Checklist pre-PR (genérica, sin gh-publish)
│   └── MEMORY.md          # Principios de memoria (sin MCP salvo opcional)
├── .agents/skills/        # my-review, my-review-security, fx-test, fx-changelog, fx-replan, fx-git
├── src/                   # Código fuente (.gitkeep + README breve)
├── tests/                 # Pruebas (.gitkeep + README breve)
├── docs/                  # Documentación (.gitkeep + README breve)
│   ├── specs/PLANTILLA.md # Plantilla de spec con frontmatter
│   └── CHANGELOG.md       # Registro + índice de lecciones
├── scripts/               # Scripts utilitarios (.gitkeep + README breve)
│   └── ci_checks.py       # CI de artefactos (stdlib)
├── .github/workflows/ci.yml  # Job build: Python + ci_checks.py
├── opencode.json          # Configuración de OpenCode (sin mcp salvo opcional)
├── AGENTS.md              # Punto de entrada
├── .env.example           # Plantilla de variables
├── .gitignore             # Exclusiones
└── README.md              # Documentación principal (+ FRAMEWORK_VERSION)
```

### Bloques opcionales (solo si se piden)

```
# Solo si MCP:  bloque "mcp": {"brain-ai": ...} en opencode.json
#               + secciones brain-ai_* en .ai/
# Solo si gitflow: .github/workflows/ci.yml (+ deploy.yml si Pages)
#                  scripts/gh-publish.ps1, VERSION, ramas main/develop
```

---

## Qué copiar de cada archivo

| Archivo | Copiar tal cual | Adaptar | Solo si hay MCP brain-ai | No copiar |
|---------|-----------------|---------|--------------------------|-----------|
| `.ai/system.md` | Jerarquía de prioridad, plantilla de rechazo, ejemplos few-shot, rol, tono, estructura de respuestas, postura epistémica, sección Git (tools `git_ver_*` / `git_subir_cambios`, config global de opencode) | Nombre de proyecto en ejemplos | Memoria persistente + Herramientas de provenance | — |
| `.ai/rules.md` | Secciones 1-5 (código, git, seguridad, calidad, documentación), 6 (hard constraints), 7 (memoria conceptual), 8.1-8.4 (verificación básica) | Ejemplos con nombre propio | Sección 9 (procedencia y referencias) | 8.5 (rutas de log específicas), 8.6 (incidente brain-ai-01) |
| `.ai/context.md` | Estructura de plantilla | Todo el contenido (stack, arquitectura, variables) | — | Convenciones de tests específicas |
| `.ai/agents.md` | **Todo (100% común)** | — | — | — |
| `.ai/commands.md` | Estructura general, nota de comandos slash | Checklist pre-PR con tests del nuevo proyecto | Tablas de tools brain-ai, sección de publicación con gh-publish | Variante B específica de este proyecto |
| `.ai/MEMORY.md` | Categorías de memoria, qué (no) guardar, flujo conceptual | Nombre de proyecto | Descripción de tools, params (`project`/`top_k`/`collection`), hallazgos fechados | 429 TPD, incidentes específicos |
| `scripts/gh-publish.ps1` | **Casi todo** (es del template) | Comentario "Python sin GitHub Pages" | — | — |
| `.github/workflows/ci.yml` | Estructura y triggers | `<RUTA_APP>`, pasos de test al stack del nuevo proyecto | — | Comandos de test de este proyecto |
| `.github/workflows/deploy.yml` | Solo si el nuevo proyecto usa GitHub Pages | `<SUB_PROYECTO>` | — | — |

**Nota sobre brain-ai:** las secciones marcadas "Solo si hay MCP brain-ai" solo aplican si el nuevo proyecto configura el servidor MCP `brain-ai` en `opencode.json`. Si no lo usa, eliminar esas secciones.

---

## Guardrails Recomendados

Estas instrucciones deben quedarse siempre en cualquier proyecto, sin importar el dominio:

1. **Jerarquía de prioridad** — seguridad/idioma > estilo > instrucciones del usuario
2. **Plantilla de rechazo fija** + prohibición de eco de secretos (no repetir credenciales)
3. **Regla de idioma inviolable** — responder siempre en el idioma configurado
4. **No leer `.env`** ni archivos de credenciales
5. **Leer antes de afirmar** — diagnosticar con evidencia, nunca asumir contenido de archivos
6. **No asumir servicios caídos** sin re-verificar con una herramienta real
7. **Memoria: no guardar credenciales** ni datos personales
8. **Postura epistémica** — distinguir SÉ / NO SÉ / NO APLICA

---

## Paso a Paso

### 1. Copiar el Núcleo desde este proyecto (obligatorio, siempre)

```bash
cp -r .ai/ /ruta/nuevo-proyecto/
cp opencode.json AGENTS.md .gitignore /ruta/nuevo-proyecto/
```

Quitar el bloque `mcp` de `opencode.json` salvo que se haya pedido el opcional MCP.
Permisos recomendados para proyecto nuevo: todo en `ask`.

### 2. Crear la estructura base (obligatorio, siempre)

```bash
mkdir /ruta/nuevo-proyecto/src /ruta/nuevo-proyecto/tests /ruta/nuevo-proyecto/docs /ruta/nuevo-proyecto/scripts
```

En cada carpeta: `.gitkeep` + `README.md` breve (propósito + convención de `.ai/context.md` + ejemplo de ruta).

### 3. Crear archivos raíz (obligatorio, siempre)

- `.env.example` — plantilla con las variables que el proyecto necesita
- `README.md` — documentación del nuevo proyecto
- `requirements.txt` — solo cuando el stack lo exija

### 4. Limpiar contenido no reutilizable (obligatorio, siempre)

Siguiendo la tabla "Qué copiar de cada archivo", eliminar del nuevo proyecto:

- De `rules.md`: secciones 8.5 y 8.6, y §9 completa salvo opcional MCP
- De `context.md`: convenciones de tests específicas; stack/architectura a lo real del nuevo proyecto
- De `commands.md`: Variante B específica de este proyecto; tablas `brain-ai_*` salvo opcional MCP; `gh-publish` salvo opcional gitflow
- De `MEMORY.md`: hallazgos fechados y sección de 429 TPD; tools salvo opcional MCP
- De `system.md`: secciones de `brain-ai_*` salvo opcional MCP

### 5. Adaptar contenido específico (obligatorio, siempre)

- `system.md` — rol, nombre de proyecto en ejemplos
- `rules.md` — reglas del dominio, convenciones del nuevo proyecto
- `context.md` — stack real, arquitectura, dependencias, variables de entorno
- `commands.md` — checklist de validación con tests del nuevo proyecto
- `MEMORY.md` — nombre del nuevo proyecto
- `opencode.json` — modelo deseado

### 6. Opcional MCP (solo si se pide explícitamente)

Agregar bloque `mcp.brain-ai` en `opencode.json` y restaurar las secciones
`brain-ai_*` según la columna "Solo si hay MCP brain-ai" de la tabla.

### 7. Opcional gitflow (solo si se pide explícitamente)

Forma preferida: invocar `/adoptar-gitflow` en el proyecto destino.
Fusiona el job `build` en el mismo `.github/workflows/ci.yml` sin borrar
`artefactos` (prohibido `cp` directo de `ci.yml`) y registra el flujo en
`.ai/` (Ramas en `context.md`, Publicación en `commands.md`). `deploy.yml`
solo si Pages. Fallback manual: copiar `gh-publish.ps1` y `VERSION` desde el
scaffold, para `ci.yml` insertar el job `build` a mano con `<RUTA_APP>`
adaptado (no reemplazar el archivo) y registrar Ramas/Publicación en `.ai/`
(ver `TEMPLATE_GITFLOW_GH_PAGES.md` Fase 2).

```bash
cp Proyecto\ AI/templates/gitflow-scaffold/scripts/gh-publish.ps1 /ruta/nuevo-proyecto/scripts/
# NO hacer cp directo de ci.yml (pisa artefactos). Usar /adoptar-gitflow.
cp Proyecto\ AI/templates/gitflow-scaffold/.github/workflows/deploy.yml /ruta/nuevo-proyecto/.github/workflows/  # solo si Pages
cp Proyecto\ AI/templates/gitflow-scaffold/VERSION /ruta/nuevo-proyecto/
```

Seguir `TEMPLATE_GITFLOW_GH_PAGES.md` para ramas, protección de `main` y autenticación de `gh`.
Adaptar `ci.yml` (`<RUTA_APP>` + tests del stack) y `commands.md` (checklist con CI + publicación vía script).

### 8. Verificar guardrails (obligatorio, siempre)

Confirmar que las 8 instrucciones de "Guardrails Recomendados" siguen presentes.

---

## Checklist de Adopción

### Núcleo (bloqueante, siempre)
- [ ] Copiar `.ai/`, `opencode.json` (sin `mcp`, con `skills.paths`), `AGENTS.md` y `.gitignore` desde este proyecto
- [ ] Copiar `.agents/skills/`, `docs/specs/PLANTILLA.md`, `scripts/ci_checks.py` y crear `.github/workflows/ci.yml` + `docs/CHANGELOG.md` (plantilla)
- [ ] Crear `src/`, `tests/`, `docs/`, `scripts/` con `.gitkeep` + `README.md` breve
- [ ] Limpiar contenido no reutilizable (tabla "Qué copiar de cada archivo")
- [ ] Adaptar `system.md` con el rol correcto
- [ ] Adaptar `rules.md` con las reglas del dominio
- [ ] Adaptar `context.md` con el stack real
- [ ] Adaptar `commands.md` con la checklist del nuevo proyecto
- [ ] Adaptar `MEMORY.md` con el nombre del nuevo proyecto
- [ ] Verificar que los 8 guardrails siguen presentes
- [ ] Configurar `opencode.json` con el modelo deseado
- [ ] Crear `.env.example` y `README.md` (`requirements.txt` si el stack lo exige)

### Opcional MCP (solo si se pidió)
- [ ] Bloque `mcp.brain-ai` en `opencode.json` + secciones `brain-ai_*` restauradas

### Opcional gitflow (solo si se pidió)
- [ ] Copiar `gh-publish.ps1`, `ci.yml` (y `deploy.yml` si aplica) y `VERSION` desde el template gitflow-scaffold
- [ ] Adaptar `ci.yml` con `<RUTA_APP>` y tests del stack
- [ ] Ramas y protección de `main` según `TEMPLATE_GITFLOW_GH_PAGES.md`

---

## Ejemplo de Prompt para el Agente del Nuevo Proyecto

Forma preferida (comando global, lo habitual):

```
/adoptar-framework
```

(Desde el proyecto destino. El comando pregunta dominio/stack/modelo y
ejecuta el Núcleo. Requiere el archivo en
`~/.config/opencode/commands/adoptar-framework.md` + reinicio de OpenCode.)

Fallback manual (si el comando no está instalado):

Mínimo (Núcleo):

```
Adopta el framework de personalizar-comportamiento-01 siguiendo su guía
docs/REUTILIZAR.md (§0: Núcleo obligatorio = comportamiento + estructura).
Copia .ai/, opencode.json (sin mcp), AGENTS.md y .gitignore desde
Proyecto AI/personalizar-comportamiento-01/. Crea src/, tests/, docs/,
scripts/ con .gitkeep + README breve. Crea .env.example y README.md.
Limpia contenido específico de ese proyecto (secciones 8.5 y 8.6 de
rules.md, §9 salvo MCP, convenciones de tests, Variante B, hallazgos
fechados, secciones brain-ai_*). Adapta system.md para un especialista
en [DOMINIO] y context.md con el stack [STACK]. Configura opencode.json
con el modelo [MODELO]. Verifica que los 8 guardrails sigan presentes.
```

Con opcionales (agregar solo lo pedido):

```
# + MCP: ...agrega el bloque mcp.brain-ai y restaura las secciones
# brain-ai_* según la tabla de REUTILIZAR.md.
# + Gitflow: ...copia scripts/gh-publish.ps1, .github/workflows/
# (ci.yml, deploy.yml si hay Pages) y VERSION desde
# Proyecto AI/templates/gitflow-scaffold/, siguiendo su guía
# TEMPLATE_GITFLOW_GH_PAGES.md para ramas y protección de main.
```
