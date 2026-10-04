# 🏗️ Estructura Estándar para Proyectos con Desarrollo Asistido por IA

## 📊 Resumen del Análisis

Tras evaluar ambas estructuras, diseñé una plantilla híbrida universal que toma lo mejor de cada una y corrige sus debilidades. El objetivo: una base reutilizable, segura y agnóstica al lenguaje.

---

## ✅ Estructura Final Recomendada

text

proyecto-template/  
│  
├── 📁 .ai/                        \# ⭐⭐⭐⭐⭐ Instrucciones para el modelo IA  
│   ├── system.md                  \# Rol, tono y postura epistémica del agente  
│   ├── rules.md                   \# Reglas de seguridad y restricciones  
│   ├── context.md                 \# Stack tecnológico y contexto del proyecto  
│   ├── agents.md                  \# Definición de agentes especialistas  
│   ├── commands.md                \# Comandos personalizados/admin  
│   └── MEMORY.md                  \# Persistencia de contexto entre sesiones  
│  
├── 📄 AGENTS.md                   \# ⭐⭐⭐⭐⭐ Punto de entrada (convención opencode)  
├── 📄 opencode.json               \# ⭐⭐⭐⭐⭐ Configuración del proyecto IA  
│  
├── 📁 src/                        \# ⭐⭐⭐⭐⭐ Código fuente  
│   ├── api/                       \# Endpoints / rutas  
│   ├── components/                \# Componentes UI (si aplica)  
│   ├── services/                  \# Lógica de negocio  
│   ├── utils/                     \# Funciones auxiliares  
│   ├── config/                    \# Configuración de la app  
│   └── data/                      \# Estado / modelos de datos  
│  
├── 📁 tests/                      \# ⭐⭐⭐⭐⭐ Pruebas (separadas del código)  
│   ├── unit/  
│   └── integration/  
│  
├── 📁 docs/                       \# ⭐⭐⭐⭐ Documentación técnica  
├── 📁 logs/                       \# ⭐⭐⭐⭐ Registros de ejecución  
├── 📁 scripts/                    \# ⭐⭐⭐ Scripts de automatización  
│  
├── 🔒 .env                        \# Variables sensibles (NUNCA en git)  
├── 📋 .env.example                \# Plantilla de variables  
├── 🚫 .gitignore                  \# Exclusiones de git  
├── 📦 requirements.txt / package.json  \# Dependencias  
└── 📖 README.md                   \# Documentación principal

---

## 🎯 ¿Por Qué Esta Organización?

### Principio 1: **Separación de Preocupaciones** ⭐⭐⭐⭐⭐

| Zona | Responsabilidad | Beneficio |
| ----- | ----- | ----- |
| .ai/ | Cerebro del agente IA | La IA sabe *cómo* actuar |
| opencode.json \+ AGENTS.md | Configuración técnica | La IA sabe *con qué* trabajar |
| src/ | Código de la aplicación | El *qué* se construye |
| tests/ | Validación | Garantía de calidad |
| docs/ | Conocimiento humano | Onboarding y mantenimiento |

*💡 Clave: El desarrollador humano y el agente IA tienen espacios claramente delimitados.*

### Principio 2: **Agnóstico al Lenguaje** ⭐⭐⭐⭐⭐

La estructura funciona para Python, JS/TS, Go, etc. Solo cambia el archivo de dependencias (requirements.txt vs package.json).

### Principio 3: **Seguridad por Diseño** ⭐⭐⭐⭐⭐

* .env fuera de git  
* .gitignore obligatorio  
* Permisos restrictivos en opencode.json

---

## 📚 Detalle de Cada Archivo

### 🧠 Directorio .ai/ — El Cerebro del Agente

#### system.md ⭐⭐⭐⭐⭐

Función: Define la *identidad* del agente IA.

Markdown

\- Rol: "Eres un ingeniero senior especializado en..."  
\- Tono: Formal / cercano / técnico  
\- Postura epistémica: ¿Admite incertidumbre? ¿Cita fuentes?

\- Idioma y estilo de comunicación

Por qué existe: Sin esto, la IA responde de forma genérica e inconsistente entre sesiones.

---

#### rules.md ⭐⭐⭐⭐⭐

Función: Reglas inviolables de seguridad y comportamiento.

Markdown

\- NUNCA hacer commit de secretos  
\- NUNCA ejecutar comandos destructivos sin confirmar  
\- SIEMPRE validar entradas de usuario

\- Restricciones específicas del dominio

Por qué existe: Es tu "muro de contención". Previene acciones peligrosas.

---

#### context.md ⭐⭐⭐⭐⭐

Función: El *mapa* técnico del proyecto.

Markdown

\- Stack: Node.js 20, Express, PostgreSQL  
\- Arquitectura: MVC / Clean Architecture  
\- Convenciones de código

\- Dependencias clave y sus versiones

Por qué existe: Evita que la IA sugiera tecnologías incompatibles con tu proyecto.

---

#### agents.md ⭐⭐⭐⭐

Función: Define sub-agentes especializados.

Markdown

\- @backend-expert: Especialista en APIs  
\- @security-auditor: Revisa vulnerabilidades

\- @test-writer: Genera pruebas

Por qué existe: Permite delegar tareas a "personalidades" enfocadas \= mejores resultados.

---

#### commands.md ⭐⭐⭐⭐

Función: Documenta comandos personalizados.

Markdown

\- /deploy: Proceso de despliegue  
\- /audit: Auditoría de seguridad

\- /refactor: Guía de refactorización

Por qué existe: Estandariza operaciones repetitivas.

---

#### MEMORY.md ⭐⭐⭐⭐⭐

Función: *Persistencia* de decisiones y contexto.

Markdown

\- Decisiones arquitectónicas tomadas  
\- Problemas conocidos y soluciones

\- Preferencias del equipo aprendidas

Por qué existe: La IA "recuerda" entre sesiones. Es su memoria a largo plazo.

---

### ⚙️ Archivos de Configuración

#### AGENTS.md (raíz) ⭐⭐⭐⭐⭐

Función: Punto de entrada oficial de opencode.

Markdown

**\# Redirige a la configuración detallada**  
Ver instrucciones completas en .ai/

Resumen rápido del proyecto para la IA

Por qué en la raíz: Es la convención estándar de opencode. La IA lo busca automáticamente aquí.

---

#### opencode.json ⭐⭐⭐⭐⭐

Función: Configuración técnica de la herramienta IA.

JSON

{  
  "model": "groq/llama-3.3-70b-versatile",  
  "instructions": \[".ai/system.md", ".ai/rules.md", ".ai/context.md"\],  
  "permission": {  
    "bash": "deny",      // No ejecuta comandos sin permiso  
    "write": "ask",      // Pregunta antes de crear archivos  
    "edit": "ask"        // Pregunta antes de editar  
  },  
  "mcp": {  
    "brain-ai": "scripts/mcp\_bridge.py"  
  }

}

Por qué en la raíz: Más descubrible que .opencode/ y evita anidar node\_modules.

---

### 💻 Directorio src/ — El Código

| Carpeta | Función | Calificación |
| ----- | ----- | ----- |
| api/ | Rutas y endpoints REST/GraphQL | ⭐⭐⭐⭐⭐ |
| components/ | UI reutilizable (frontend) | ⭐⭐⭐⭐ |
| services/ | Lógica de negocio pura | ⭐⭐⭐⭐⭐ |
| utils/ | Helpers sin estado | ⭐⭐⭐⭐ |
| config/ | Configuración de la app | ⭐⭐⭐⭐ |
| data/ | Modelos y estado | ⭐⭐⭐⭐ |

*💡 Regla de oro: Cada archivo tiene una sola responsabilidad.*

---

### 🧪 Directorio tests/ ⭐⭐⭐⭐⭐

Función: Pruebas separadas del código productivo.

text

tests/  
├── unit/          \# Pruebas de funciones aisladas

└── integration/   \# Pruebas de flujos completos

Por qué separado: El código de producción queda limpio; los tests no se mezclan con la lógica.

---

### 📖 Archivos Raíz

| Archivo | Función | Crítico |
| ----- | ----- | ----- |
| .env | Secretos reales | 🔴 Nunca en git |
| .env.example | Plantilla de variables | 🟢 Sí en git |
| .gitignore | Exclusiones | 🔴 Obligatorio |
| requirements.txt / package.json | Dependencias | 🟢 Sí en git |
| README.md | Documentación humana | 🟢 Sí en git |

---

## 🏆 Tabla Comparativa Final

| Criterio | Estructura A | Estructura B | Template Final |
| ----- | :---: | :---: | :---: |
| Claridad config IA | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Seguridad | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Onboarding | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| Escalabilidad | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Convención opencode | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Reusabilidad | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| Separación de tests | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| PROMEDIO | 4.0 | 2.7 | 5.0 |

---

## 🚀 .gitignore Recomendado (Plantilla)

gitignore

\# Secretos  
.env  
\*.key  
auth/

\# Dependencias  
node\_modules/  
\_\_pycache\_\_/  
venv/

\# Logs  
logs/  
\*.log

\# IA  
.ai/MEMORY.md    \# Opcional: si contiene datos sensibles

\# Sistema  
.DS\_Store

---

## ✅ Checklist de Adopción

*  Copiar estructura base  
*  Personalizar .ai/system.md con el rol del agente  
*  Definir reglas en .ai/rules.md  
*  Documentar stack en .ai/context.md  
*  Configurar opencode.json con tu modelo  
*  Crear AGENTS.md en raíz  
*  Verificar .gitignore  
*  Crear .env.example

