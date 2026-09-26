# Contexto adicional (stack, esquema de BD, etc.)

## Stack Tecnologico
- Frontend: HTML5, CSS3, JavaScript ES6+
- Backend: [Por definir]
- Base de datos: MySQL
- Otros: [Por definir]

## Esquema de Base de Datos (si aplica)
[Describir tablas, relaciones y campos principales si corresponde]

## Arquitectura del Sistema
[Describir brevemente la arquitectura: microservicios, monolitica, capas, etc.]

## Dependencias Principales
- [Lista de paquetes/librerias clave]

## Variables de Entorno Requeridas
- API_KEY=[descripcion]
- DATABASE_URL=mysql://usuario:password@host:puerto/nombre_base
- DB_HOST=[host de MySQL]
- DB_PORT=[puerto, default 3306]
- DB_USER=[usuario de MySQL]
- DB_PASSWORD=[contraseña de MySQL]
- DB_NAME=[nombre de la base de datos]

## Convenciones de Archivos

**Regla: TODO va a `docs/` (reportes) o `tests/` (codigo y datos de test).**

| Tipo | Destino | Ejemplo |
|------|---------|---------|
| JSON (answers/reports de tests) | `tests/answers/` | `advanced_validation_report.json` |
| JSON (preguntas de tests) | `tests/questions/` | `advanced_questions.json` |
| Scripts de tests | `tests/scripts/` | `test_ai_structure.py` |
| Librerias de tests | `tests/lib/` | `validation.py`, `advanced_validators.py` |
| Scripts de reportes | `scripts/` | `generate_html_report.py` |
| HTML (reportes visuales de tests) | `docs/tests/` | `reporte_consolidado.html` |
| PDF (documentacion de tests) | `docs/tests/` | `TEST DE ESTRUCTURA.pdf` |
| PDF (documentacion general) | `docs/` | `Estructura proyecto AI.pdf` |
| Markdown (analisis de tests) | `docs/tests/` | `RESULTADOS_TEST_AI.md` |
| Backup | `docs/backup_YYYYMMDD_HHMMSS/` | Archivos previos al re-run |

## Notas de Desarrollo
[Cualquier informacion adicional relevante para desarrolladores]

## Ramas del Proyecto

> Setup gitflow 26/09/2026 (fuente: `Proyecto AI/templates/gitflow-scaffold`,
> versión `2026.09.25`; plan `docs/PLAN_GITFLOW_20260926.md`).

| Rama | Proposito | Sale de | Vuelve a | Proteccion |
|------|-----------|---------|----------|------------|
| `main` | Produccion (estable) | — | — | Requiere PR, SIN "Require approvals" |
| `develop` | Desarrollo diario (rama por defecto) | `main` | `main` (PR al publicar) | No |
| `clean-main` | Rama historica (trabajo previo, se mantiene) | — | — | No |
| `feature/<desc>` | Cada tarea o experimento | `develop` | `develop` (PR) | No |

Reglas de comportamiento:
- Trabajar SIEMPRE en `develop`. Antes de modificar, verificar la rama actual con
  `git status`/`git branch`; si se esta en `main`, no trabajar ahi.
- `main` solo se toca para publicar, via PR desde `develop`.
- Tareas grandes o experimentos: crear `feature/<desc>` desde `develop` y
  mergear de vuelta a `develop`.
- La proteccion de `main` es "Requerir PR" SIN "Require approvals": en repo personal
  el autor no puede aprobar su propio PR (bloqueo permanente si se activa).
- Este repo es Python sin GitHub Pages: no hay deploy automatico; la validacion
  pre-prod es local (checklist Variante B en `.ai/commands.md`).
