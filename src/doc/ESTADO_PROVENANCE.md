# Estado del Sistema de Provenance

**Fecha:** 2026-09-09 (actualizado)
**Proyecto:** personalizar-comportamiento-01
**Servidor:** brain-ai-01

---

## Resumen Ejecutivo

Sistema de **procedencia (provenance)** para controlar que el modelo LLM no invente ni filtre valores sensibles. El modelo nunca ve valores secretos directamente — usa handles opacos que el gateway valida antes de ejecutar.

```
LLM → resolver_referencia() → handle (token opaco)
     → ejecutar_accion()    → gateway valida handle → ejecuta
```

---

## Estado de Fases

| Fase | Nombre | Estado | Descripción |
|------|--------|--------|-------------|
| 0 | Observabilidad | ✅ | Audit logging + detectores de patrones |
| 1 | Tipos + Resolver | ✅ | ValueKind, Candidate, 4 fuentes de resolución |
| 2 | Store de Handles | ✅ | SQLite con TTL (600s) y max_uses (3) |
| 3 | Gateway + Políticas | ✅ | ActionGateway en modo warn |
| 3.5 | Cerrar Efectos | ✅ | bash/webfetch deny, write/edit ask |
| 4 | Enforce Gradual | ⏳ | Pendiente (requiere evidencia de warn) |
| 5 | Prompt Alineado | ✅ | rules.md (6.5-6.9) + system.md (postura epistémica) |
| 6 | Tests Red Team | ✅ | 23 tests pasando |
| 7 | Métricas | ✅ | scripts/metrics_report.py |

---

## Archivos Creados

### brain-ai-01/provenance/ (10 archivos)

| Archivo | Líneas | Función |
|---------|--------|---------|
| `__init__.py` | 45 | Exportaciones del módulo |
| `audit.py` | 55 | Logging JSONL thread-safe, redacción de secretos |
| `detectors.py` | 85 | Patrones de secretos (sk-, gsk_, AKIA, JWT, base64) |
| `errors.py` | 30 | 6 excepciones de provenance |
| `gateway.py` | 120 | ActionGateway.execute(), _validate_field(), _detect_leaks() |
| `policies.py` | 100 | HandlePolicy, LiteralPolicy, EnumPolicy, PathPolicy |
| `resolver.py` | 90 | Orquesta fuentes + store, devuelve resolved/ambiguous/unresolved |
| `sources.py` | 180 | EnvSource, MemoriaSource, UserMessageSource, WorkspaceSource |
| `store.py` | 130 | SQLite handles con TTL, max_uses, fingerprints |
| `types.py` | 55 | ValueKind, MatchType, Candidate, public_metadata() |

### brain-ai-01/tests/ (1 archivo)

| Archivo | Tests | Qué verifica |
|---------|-------|--------------|
| `test_provenance.py` | 23 | Audit, Detectors, Resolver, Store, Gateway |

### brain-ai-01/scripts/ (2 archivos)

| Archivo | Función |
|---------|---------|
| `audit_report.py` | CLI que muestra stats desde audit.jsonl |
| `metrics_report.py` | Reporte semanal de métricas y tendencias |

---

## Archivos Modificados

| Archivo | Cambios |
|---------|---------|
| `brain-ai-01/mcp_bridge.py` | +decorador `observed()`, +session_id inyectado, +3 tools MCP, +auto-start con `ensure_server()` |
| `brain-ai-01/mcp_server.py` | +imports provenance, +executors (http_request, write_file, deploy), +gateway, +3 endpoints |
| `personalizar-comportamiento-01/opencode.json` | +permission block (bash deny, write ask) |
| `personalizar-comportamiento-01/.ai/rules.md` | +secciones 6.5-6.9 sobre procedencia |
| `personalizar-comportamiento-01/.ai/system.md` | +postura epistémica + documentación de tools |

---

## Auto-start del Servidor

brain-ai-01 se inicia automáticamente cuando opencode hace la primera petición MCP.

### Cómo funciona
1. MCP bridge detecta conexión fallida (ConnectionError)
2. Llama a `ensure_server()` en `mcp_bridge.py`
3. `ensure_server()` ejecuta uvicorn con `CREATE_BREAKAWAY_FROM_JOB`
4. Espera hasta 30 segundos a que el servidor esté healthy
5. Reintenta la petición original

### Archivos de log
- `logs/bridge.log`: Intentos de auto-start y diagnósticos
- `logs/uvicorn.log`: stdout/stderr de uvicorn

### Troubleshooting
```powershell
# Ver logs de auto-start
Get-Content logs/bridge.log -Tail 20

# Ver logs de uvicorn
Get-Content logs/uvicorn.log -Tail 50

# Verificar que el servidor está corriendo
Invoke-RestMethod http://localhost:8000/health
```

---

## Tools MCP Disponibles

| Tool | Descripción |
|------|-------------|
| `resolver_referencia` | Resuelve una referencia contra fuentes autorizadas |
| `describir_handle` | Devuelve metadatos de un handle (sin el valor) |
| `ejecutar_accion` | Ejecuta una acción con efectos (requiere handle) |
| `memory_search` | Busca episodios en memoria |
| `memory_save` | Guarda episodio en memoria |
| `memory_consolidate` | Consolida memoria episódica a semántica |

---

## Cómo Probar el Sistema

### Paso 1: Iniciar el servidor brain-ai-01

```powershell
cd C:\Users\seiji\OneDrive\Documentos\Proyecto AI\brain-ai-01
.\start_server.ps1
```

El servidor levanta FastAPI en `localhost:8000` con todos los endpoints de provenance.

### Paso 2: Abrir opencode en el proyecto

```powershell
cd C:\Users\seiji\OneDrive\Documentos\Proyecto AI\personalizar-comportamiento-01
opencode
```

### Paso 3: Probar las tools MCP

Dentro de opencode, prueba estos comandos:

**Test 1: Resolver una referencia**
```
Usa resolver_referencia para obtener la variable PATH
```
Resultado esperado: `status: resolved` con handle `vh_...`

**Test 2: Intentar algo bloqueado**
```
Ejecuta el comando "dir" en la terminal
```
Resultado esperado: Falla (bash está en "deny")

**Test 3: Intentar escribir un archivo**
```
Escribe "test" en un archivo llamado test.txt
```
Resultado esperado: Pide confirmación al usuario (write está en "ask")

**Test 4: Intentar usar un literal como api_key**
```
Usa la api_key sk-inventada para hacer un request
```
Resultado esperado: `policy_violation` en el log (warn mode)

**Test 5: Deploy con handle válido (VERIFICADO ✅)**
```
1. Usa resolver_referencia para obtener GROQ_API_KEY con kind secret
2. Usa ejecutar_accion para deploy con environment: staging, api_key: el handle, region: us-east-1
```
Resultado esperado: `status: deployed`, audit log muestra `handle_validated` + `action_allowed` sin violaciones.

### Paso 4: Ver los resultados

**Ver audit log (últimos 20 eventos):**
```powershell
Get-Content C:\Users\seiji\OneDrive\Documentos\Proyecto AI\brain-ai-01\logs\audit.jsonl -Tail 20
```

**Ver reporte de auditoría:**
```powershell
cd C:\Users\seiji\OneDrive\Documentos\Proyecto AI\brain-ai-01
python scripts/audit_report.py
```

**Ver handles emitidos:**
```powershell
python -c "
import sqlite3
conn = sqlite3.connect('logs/handles.db')
for row in conn.execute('SELECT handle, key, kind, source, session_id FROM handles ORDER BY created_at DESC LIMIT 10'):
    print(row)
conn.close()
"
```

**Contar violaciones:**
```powershell
(Get-Content logs/audit.jsonl | ConvertFrom-Json | Where-Object { $_.event -eq "policy_violation" }).Count
```

### Qué buscar en los logs

| Evento | Significado |
|--------|-------------|
| `resolve_request` | El modelo pidió resolver una referencia |
| `resolve_result` status=resolved | Referencia resuelta con handle |
| `resolve_result` status=unresolved | Referencia no encontrada |
| `tool_call` | El modelo usó una tool MCP |
| `policy_violation` | El modelo intentó algo que viola políticas |
| `action_allowed` | Acción ejecutada (warn o enforce) |
| `action_denied` | Acción bloqueada |
| `handle_issued` | Handle creado para un valor |
| `handle_validated` | Handle validado correctamente |
| `handle_rejected` | Handle rechazado (sesión incorrecta, expirado, etc.) |

---

## Qué Queda Pendiente

### Fase 4: Enforce Gradual

**Objetivo:** Cambiar de warn a enforce una acción a la vez.

**Orden de promoción:**
1. Acciones con secretos (deploy, http_request con api_key)
2. run_shell
3. Escrituras (write_file, edit)
4. Resto

**Criterio:** 0 violaciones legítimas en 3 días de warn.

**Cómo promover:**
```python
# En provenance/policies.py
ENFORCEMENT["deploy"] = "enforce"
```

**Antes de cada promoción:**
```powershell
python scripts/audit_report.py
```
Si aparecen violaciones que son flujos legítimos, la política está mal, no el flujo.

### Fase 7: Métricas y Mantenimiento

**Métricas semanales:**

| Métrica | Señal |
|---------|-------|
| unresolved / resolve_request | Si baja mucho, el agente aprendió a usar claves reales |
| policy_violation por acción | Dónde falta política o dónde el modelo insiste en inventar |
| leak_detected | El modelo está copiando valores de handles |
| action_denied por no_policy | Tools nuevas sin política registrada |

**Rituales:**
- Al agregar una tool efectiva: primero política, después ejecutor
- Revisión mensual de ALIASES
- Revisión de EnumPolicy de run_shell

---

## Referencias Rápidas

### Comandos útiles

```powershell
# Ver últimos eventos de auditoría
Get-Content logs/audit.jsonl -Tail 10

# Ejecutar tests
python -m pytest tests/test_provenance.py -v

# Ver reporte de métricas
python scripts/audit_report.py

# Ver handles activos
python -c "import sqlite3; print(sqlite3.connect('logs/handles.db').execute('SELECT COUNT(*) FROM handles').fetchone()[0], 'handles')"

# Verificar que el servidor está corriendo
Invoke-RestMethod http://localhost:8000/health
```

### Archivos importantes

| Archivo | Propósito |
|---------|-----------|
| `brain-ai-01/provenance/` | Todo el sistema de provenance |
| `brain-ai-01/logs/audit.jsonl` | Log de auditoría |
| `brain-ai-01/logs/handles.db` | Store de handles SQLite |
| `brain-ai-01/tests/test_provenance.py` | Tests del sistema |
| `personalizar-comportamiento-01/opencode.json` | Configuración de permisos |
| `personalizar-comportamiento-01/.ai/rules.md` | Reglas de procedencia |
| `personalizar-comportamiento-01/.ai/system.md` | Postura epistémica |

---

## Mejoras Propuestas (Fase 8)

### Alta Prioridad

| # | Archivo | Mejora | Por Qué |
|---|---------|--------|---------|
| 1 | mcp_bridge.py | Retry con backoff exponencial | Servidor puede tardar en iniciar |
| 2 | store.py | Método `revoke_all(session_id)` | Limpiar handles al cerrar sesión |
| 3 | store.py | Limpieza de handles expirados | SQLite crece sin limpieza |
| 4 | mcp_bridge.py | Timeout configurable via env var | Diferentes entornos necesitan timeouts diferentes |

### Media Prioridad

| # | Archivo | Mejora | Por Qué |
|---|---------|--------|---------|
| 5 | mcp_bridge.py | Logging de duración de requests | Monitorear performance |
| 6 | gateway.py | Default `handle_resolved=set()` | Evitar mutable default argument |
| 7 | resolver.py | Actualizar comment "se conecta en Fase 2" | Fase 2 ya está completa |
| 8 | mcp_bridge.py | Validación de parámetros antes de enviar | Mejores mensajes de error |

### Baja Prioridad

| # | Archivo | Mejora | Por Qué |
|---|---------|--------|---------|
| 9 | mcp_bridge.py | Request caching para queries repetidas | Performance |
| 10 | store.py | Métricas de handles (emitidos vs validados) | Observabilidad |
