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
