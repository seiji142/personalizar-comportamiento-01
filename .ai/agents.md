# Roles del flujo (quién hace cada cosa)

Todo lo hace por defecto UN agente implementador + el humano. Solo se
divide en los casos de la regla de abajo.

## 1. Humano-arquitecto (tú)
Decide qué se construye, escribe o revisa el spec, acepta o rechaza el
resultado. Nunca escribe código que el agente deba adivinar ni deja
decisiones de diseño al azar del modelo.

## 2. Agente-implementador (default)
Un solo agente por tarea, con spec + guardrails. Escribe código y tests,
verifica con ejecución real. Es el modo normal de todo el flujo.

## 3. Agente-auditor antagonista
Solo audita con ejecución real, NO modifica. Se activa post-implementación
cuando el cambio toca: rutas, inputs, datos, credenciales, dependencias,
CI/workflows, crypto, serialización, filesystem, redirects, jobs,
`scripts/`, skills, permisos de `opencode.json` o el spec mismo.
Dictamina aprueba/no-aprueba. El implementador NO cierra hallazgos
de seguridad sin reabrir §8 del spec.

## 4. Subagente-investigador
Explora o revisa en profundidad sin contaminar el hilo principal (deep
review, research de opciones). Solo cuando el contexto principal es valioso
y la tarea es separable; reporta al implementador, nunca implementa directo.

## Regla de división
Por defecto, todo lo hace el rol 2. Se divide solo si:
- (a) hay auditoría requerida → rol 3;
- (b) hay trabajos independientes en paralelo → un rol 2 por trabajo;
- (c) hay colisión de archivos → rol 2 + worktree cada uno (ver
  `.ai/commands.md` si el proyecto adoptó gitflow).

## Especialidades por stack (sombreros del implementador)
Según la tarea, el implementador adopta el sombrero correspondiente; no son
agentes separados salvo que aplique la regla de división:

- Frontend (HTML, CSS, JavaScript y frameworks)
- Backend (APIs, bases de datos, lógica de negocio)
- DevOps (despliegue, infraestructura, CI/CD)
- Testing (unitarias, integración, E2E)
- Diseño UX/UI (accesibilidad, diseño visual)
