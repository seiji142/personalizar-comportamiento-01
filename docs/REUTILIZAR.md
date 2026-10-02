# Reutilizar el Framework de Comportamiento

Guía para adoptar el framework de archivos `.ai/` + `opencode.json` en otro proyecto.

---

## Qué es lo reutilizable

| Componente | Descripción |
|------------|-------------|
| `.ai/` | System prompt del agente (rol, reglas, contexto, agentes) |
| `opencode.json` | Configuración de modelo, permisos e instrucciones |
| `AGENTS.md` | Punto de entrada de OpenCode |

**No incluye:** la suite de tests (`src/doc/ESTRUCTURA/`). Los tests son específicos de este proyecto.

---

## Estructura Esencial

```
nuevo-proyecto/
├── .ai/
│   ├── system.md          # Rol, tono y estilo del agente
│   ├── rules.md           # Reglas obligatorias (seguridad, git, calidad)
│   ├── context.md         # Stack, arquitectura y convenciones
│   ├── agents.md          # Agentes especialistas
│   ├── commands.md        # Comandos personalizados
│   └── MEMORY.md          # Persistencia de contexto
├── src/                   # Código fuente
├── tests/                 # Pruebas
├── docs/                  # Documentación
├── scripts/               # Scripts de automatización
├── opencode.json          # Configuración de OpenCode
├── AGENTS.md              # Punto de entrada
├── .env.example           # Plantilla de variables
├── .gitignore             # Exclusiones
├── requirements.txt       # Dependencias
└── README.md              # Documentación principal
```

---

## Qué copiar de cada archivo `.ai/`

| Archivo | Copiar tal cual | Adaptar | Solo si hay MCP brain-ai | No copiar |
|---------|-----------------|---------|--------------------------|-----------|
| `system.md` | Jerarquía de prioridad, plantilla de rechazo, ejemplos few-shot, rol, tono, estructura de respuestas, postura epistémica, sección Git (tools `git_ver_*` / `git_subir_cambios`, config global de opencode) | Nombre de proyecto en ejemplos | Memoria persistente + Herramientas de provenance | — |
| `rules.md` | Secciones 1-5 (código, git, seguridad, calidad, documentación), 6 (hard constraints), 7 (memoria), 8.1-8.3 (verificación básica) | Ejemplos con nombre propio | Sección 9 (procedencia y referencias) | 8.5 (rutas de log específicas), 8.6 (incidente brain-ai-01) |
| `context.md` | Estructura de plantilla | Todo el contenido (stack, arquitectura, variables) | — | Ramas del proyecto, convenciones de tests específicas |
| `agents.md` | **Todo (100% común)** | — | — | — |
| `commands.md` | Estructura general, nota de comandos slash | Checklist pre-PR del nuevo proyecto | Tablas de tools brain-ai | gh-publish.ps1, Variante B específica |
| `MEMORY.md` | Descripción de tools, cuándo usar cada una, categorías de memoria, flujo obligatorio | Nombre de proyecto (param default) | Todo el contenido de uso de tools | Hallazgos fechados, 429 TPD, incidentes específicos |

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

### 1. Copiar archivos base

```bash
cp -r .ai/ /ruta/nuevo-proyecto/
cp opencode.json /ruta/nuevo-proyecto/
cp AGENTS.md /ruta/nuevo-proyecto/
```

### 2. Limpiar contenido no reutilizable

Siguiendo la tabla "Qué copiar de cada archivo", eliminar del nuevo proyecto:

- De `rules.md`: secciones 8.5 y 8.6
- De `context.md`: secciones de ramas y convenciones de tests
- De `commands.md`: checklist Variante B y gh-publish.ps1
- De `MEMORY.md`: hallazgos fechados y sección de 429 TPD
- De todos: secciones de brain-ai si el nuevo proyecto no usa ese MCP

### 3. Adaptar contenido específico

- `system.md` — rol, nombre de proyecto en ejemplos
- `rules.md` — reglas del dominio, convenciones del nuevo proyecto
- `context.md` — stack real, arquitectura, dependencias, variables de entorno
- `commands.md` — checklist de validación del nuevo proyecto
- `MEMORY.md` — nombre de proyecto en params default

### 4. Verificar guardrails

Confirmar que las 8 instrucciones de "Guardrails Recomendados" siguen presentes.

### 5. Configurar `opencode.json`

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

### 6. Crear archivos raíz

- `.env.example` — plantilla con las variables que el proyecto necesita
- `.gitignore` — exclusiones estándar (`.env`, `node_modules/`, `__pycache__/`, `logs/`, etc.)
- `README.md` — documentación del nuevo proyecto

---

## Checklist de Adopción

- [ ] Copiar `.ai/`, `opencode.json` y `AGENTS.md` al nuevo proyecto
- [ ] Limpiar contenido no reutilizable (tabla "Qué copiar de cada archivo")
- [ ] Adaptar `system.md` con el rol correcto
- [ ] Adaptar `rules.md` con las reglas del dominio
- [ ] Adaptar `context.md` con el stack real
- [ ] Adaptar `commands.md` con la checklist del nuevo proyecto
- [ ] Adaptar `MEMORY.md` con el nombre del nuevo proyecto
- [ ] Verificar que los 8 guardrails siguen presentes
- [ ] Configurar `opencode.json` con el modelo deseado
- [ ] Crear `.env.example`, `.gitignore` y `README.md`

---

## Ejemplo de Prompt para el Agente del Nuevo Proyecto

```
Copia la carpeta .ai/ y el archivo opencode.json desde el proyecto
personalizar-comportamiento-01. Sigue la guía docs/REUTILIZAR.md para
limpiar contenido específico de ese proyecto (secciones 8.5 y 8.6 de
rules.md, convenciones de tests, checklist de gitflow, hallazgos fechados).
Adapta system.md para que el agente sea un especialista en [DOMINIO].
Actualiza context.md con el stack: [STACK]. Configura opencode.json con
el modelo [MODELO]. Verifica que los 8 guardrails sigan presentes.
```
