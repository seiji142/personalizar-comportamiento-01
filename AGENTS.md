# Agentes

Punto de entrada para instrucciones del modelo IA.

## Archivos de configuración

Lee los siguientes archivos para entender el contexto del proyecto:

| Archivo | Propósito |
|---------|-----------|
| `.ai/system.md` | Rol, tono y postura epistémica del agente |
| `.ai/rules.md` | Reglas de seguridad y restricciones |
| `.ai/context.md` | Stack tecnológico y contexto del proyecto |
| `.ai/agents.md` | Definición de agentes especialistas |
| `.ai/commands.md` | Comandos personalizados/admin |
| `.ai/MEMORY.md` | Persistencia de contexto entre sesiones |

## Uso

Al iniciar una sesión, el modelo debe:
1. Leer este archivo (AGENTS.md)
2. Cargar los archivos `.ai/` correspondientes
3. Seguir las reglas y instrucciones definidas

## Adoptar el framework en otro proyecto

Si la tarea es aplicar este framework en otro proyecto, ANTES de copiar
nada debes leer `docs/REUTILIZAR.md` §0 (Núcleo obligatorio = comportamiento
+ estructura; MCP brain-ai y gitflow-scaffold son opcionales) y seguir su
Checklist: una adopción solo con `.ai/` está incompleta por definición.
Si la sesión corre en el proyecto destino con el comando global instalado,
invoca `/adoptar-framework` (pregunta dominio/stack/modelo y ejecuta el
Núcleo solo).
