# Reutilizar el Framework de Comportamiento

Guía para adoptar el framework de archivos `.ai/` + `opencode.json` + piezas de gitflow en otro proyecto.

---

## Fuentes

El framework se compone de dos orígenes:

| Fuente | Qué aporta | Ubicación |
|--------|-----------|-----------|
| **Este proyecto** (`personalizar-comportamiento-01`) | `.ai/` de comportamiento: guardrails, plantilla de rechazo, provenance, memoria | `Proyecto AI/personalizar-comportamiento-01/.ai/` |
| **gitflow-scaffold** (template, v2026.09.25) | Piezas de gitflow: ramas, CI, gh-publish, checklist pre-PR, `opencode.json` base | `Proyecto AI/templates/gitflow-scaffold/` |

**Nota:** las piezas de gitflow (`ci.yml`, `gh-publish.ps1`, sección de ramas) se copian **desde el template**, no desde este proyecto — nuestro `ci.yml` ya está adaptado a Python.

---

## Qué es lo reutilizable

| Componente | Fuente | Descripción |
|------------|--------|-------------|
| `.ai/` | Este proyecto | System prompt del agente (rol, reglas, contexto, agentes) |
| `opencode.json` | Template | Configuración de modelo, permisos e instrucciones |
| `AGENTS.md` | Este proyecto | Punto de entrada de OpenCode |
| `scripts/gh-publish.ps1` | Template | Creación/merge de PRs vía gh CLI |
| `.github/workflows/ci.yml` | Template | CI offline en PRs y push |
| `.github/workflows/deploy.yml` | Template | Deploy a GitHub Pages (opcional, solo si aplica) |
| `TEMPLATE_GITFLOW_GH_PAGES.md` | Template | Guía completa de setup de gitflow |
| `VERSION` + `CHANGELOG.md` | Template | Control de versiones del kit para upgrades |

**No incluye:** la suite de tests (`src/doc/ESTRUCTURA/`). Los tests son específicos de este proyecto.

---

## Estructura Esencial

```
nuevo-proyecto/
├── .ai/
│   ├── system.md          # Rol, tono y estilo del agente
│   ├── rules.md           # Reglas obligatorias (seguridad, git, calidad)
│   ├── context.md         # Stack, arquitectura, ramas y convenciones
│   ├── agents.md          # Agentes especialistas
│   ├── commands.md        # Checklist pre-PR + publicación
│   └── MEMORY.md          # Persistencia de contexto
├── .github/workflows/
│   ├── ci.yml             # CI offline en PRs/push
│   └── deploy.yml         # Deploy Pages (opcional)
├── scripts/
│   └── gh-publish.ps1     # Crear/mergear PRs vía gh CLI
├── src/                   # Código fuente
├── tests/                 # Pruebas
├── docs/                  # Documentación
├── opencode.json          # Configuración de OpenCode
├── AGENTS.md              # Punto de entrada
├── .env.example           # Plantilla de variables
├── .gitignore             # Exclusiones
├── requirements.txt       # Dependencias
└── README.md              # Documentación principal
```

---

## Qué copiar de cada archivo

| Archivo | Copiar tal cual | Adaptar | Solo si hay MCP brain-ai | No copiar |
|---------|-----------------|---------|--------------------------|-----------|
| `.ai/system.md` | Jerarquía de prioridad, plantilla de rechazo, ejemplos few-shot, rol, tono, estructura de respuestas, postura epistémica, sección Git (tools `git_ver_*` / `git_subir_cambios`, config global de opencode) | Nombre de proyecto en ejemplos | Memoria persistente + Herramientas de provenance | — |
| `.ai/rules.md` | Secciones 1-5 (código, git, seguridad, calidad, documentación), 6 (hard constraints), 7 (memoria), 8.1-8.3 (verificación básica) | Ejemplos con nombre propio | Sección 9 (procedencia y referencias) | 8.5 (rutas de log específicas), 8.6 (incidente brain-ai-01) |
| `.ai/context.md` | Estructura de plantilla | Todo el contenido (stack, arquitectura, variables) | — | Convenciones de tests específicas |
| `.ai/agents.md` | **Todo (100% común)** | — | — | — |
| `.ai/commands.md` | Estructura general, nota de comandos slash, sección de publicación con gh-publish | Checklist pre-PR con tests del nuevo proyecto | Tablas de tools brain-ai | Variante B específica de este proyecto |
| `.ai/MEMORY.md` | Descripción de tools, cuándo usar cada una, categorías de memoria, flujo obligatorio | Nombre de proyecto (param default) | Todo el contenido de uso de tools | Hallazgos fechados, 429 TPD, incidentes específicos |
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

### 1. Copiar archivos base desde este proyecto

```bash
cp -r .ai/ /ruta/nuevo-proyecto/
cp opencode.json AGENTS.md /ruta/nuevo-proyecto/
```

### 2. Copiar piezas de gitflow desde el template

```bash
cp Proyecto\ AI/templates/gitflow-scaffold/scripts/gh-publish.ps1 /ruta/nuevo-proyecto/scripts/
cp Proyecto\ AI/templates/gitflow-scaffold/.github/workflows/ci.yml /ruta/nuevo-proyecto/.github/workflows/
cp Proyecto\ AI/templates/gitflow-scaffold/.github/workflows/deploy.yml /ruta/nuevo-proyecto/.github/workflows/  # solo si Pages
cp Proyecto\ AI/templates/gitflow-scaffold/VERSION /ruta/nuevo-proyecto/
```

Seguir `TEMPLATE_GITFLOW_GH_PAGES.md` para ramas, protección de `main` y autenticación de `gh`.

### 3. Limpiar contenido no reutilizable

Siguiendo la tabla "Qué copiar de cada archivo", eliminar del nuevo proyecto:

- De `rules.md`: secciones 8.5 y 8.6
- De `context.md`: convenciones de tests específicas
- De `commands.md`: Variante B específica de este proyecto
- De `MEMORY.md`: hallazgos fechados y sección de 429 TPD
- De todos: secciones de brain-ai si el nuevo proyecto no usa ese MCP

### 4. Adaptar contenido específico

- `system.md` — rol, nombre de proyecto en ejemplos
- `rules.md` — reglas del dominio, convenciones del nuevo proyecto
- `context.md` — stack real, arquitectura, dependencias, variables de entorno, ramas (desde el template)
- `commands.md` — checklist de validación con tests del nuevo proyecto
- `MEMORY.md` — nombre de proyecto en params default
- `ci.yml` — `<RUTA_APP>` + comandos de test del stack del nuevo proyecto
- `gh-publish.ps1` — ajustar comentario final si el stack es distinto

### 5. Verificar guardrails

Confirmar que las 8 instrucciones de "Guardrails Recomendados" siguen presentes.

### 6. Configurar `opencode.json`

```json
{
  "model": "tu-modelo/aqui",
  "instructions": [".ai/system.md", ".ai/rules.md", ".ai/context.md", ".ai/agents.md"],
  "permission": {
    "bash": "ask",
    "write": "ask",
    "edit": "ask"
  }
}
```

### 7. Crear archivos raíz

- `.env.example` — plantilla con las variables que el proyecto necesita
- `.gitignore` — exclusiones estándar (`.env`, `node_modules/`, `__pycache__/`, `logs/`, etc.)
- `README.md` — documentación del nuevo proyecto

---

## Checklist de Adopción

- [ ] Copiar `.ai/`, `opencode.json` y `AGENTS.md` desde este proyecto
- [ ] Copiar `gh-publish.ps1`, `ci.yml` (y `deploy.yml` si aplica) desde el template gitflow-scaffold
- [ ] Copiar `VERSION` del template para control de upgrades
- [ ] Limpiar contenido no reutilizable (tabla "Qué copiar de cada archivo")
- [ ] Adaptar `system.md` con el rol correcto
- [ ] Adaptar `rules.md` con las reglas del dominio
- [ ] Adaptar `context.md` con el stack real y ramas del template
- [ ] Adaptar `commands.md` con la checklist del nuevo proyecto
- [ ] Adaptar `MEMORY.md` con el nombre del nuevo proyecto
- [ ] Adaptar `ci.yml` con `<RUTA_APP>` y tests del stack
- [ ] Verificar que los 8 guardrails siguen presentes
- [ ] Configurar `opencode.json` con el modelo deseado
- [ ] Crear `.env.example`, `.gitignore` y `README.md`

---

## Ejemplo de Prompt para el Agente del Nuevo Proyecto

```
Adopta el framework de personalizar-comportamiento-01 siguiendo su guía
docs/REUTILIZAR.md. Copia .ai/, opencode.json y AGENTS.md desde
Proyecto AI/personalizar-comportamiento-01/. Copia scripts/gh-publish.ps1,
.github/workflows/ (ci.yml, deploy.yml si hay Pages) y VERSION desde
Proyecto AI/templates/gitflow-scaffold/, siguiendo su guía
TEMPLATE_GITFLOW_GH_PAGES.md para ramas y protección de main.
Limpia contenido específico de ese proyecto (secciones 8.5 y 8.6 de
rules.md, convenciones de tests, Variante B, hallazgos fechados).
Adapta system.md para un especialista en [DOMINIO], context.md con el
stack [STACK], ci.yml con los tests del proyecto. Configura opencode.json
con el modelo [MODELO]. Verifica que los 8 guardrails sigan presentes.
```
