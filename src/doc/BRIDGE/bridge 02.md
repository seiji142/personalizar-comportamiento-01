Tu diagnóstico es correcto: no es un problema de los tests D1/D2 ni específicamente de mimo-v2.5-free; es una diferencia de runtime/camino de ejecución.

* Los modelos nativos ejecutados por opencode-cli \--attach heredan la configuración MCP del servidor OpenCode.  
* Los modelos consultados directamente vía Groq no tienen acceso a ese MCP, salvo que tú implementes y ejecutes el ciclo de herramientas desde tu código.

Mi recomendación es separar claramente dos problemas y resolverlos por capas.

---

## 1\. Corregir D3 y D4 primero: son tests obsoletos

Según tu reporte:

* D3 espera PostgreSQL.  
* D4 espera "Por definir".

Si el comportamiento o la arquitectura actual ya no exige eso, esos tests están validando una especificación antigua. No conviene “hacer que el sistema falle correctamente” sólo para satisfacerlos.

Actualiza los tests para validar el contrato actual:

Python

\# Antes: validación demasiado específica y obsoleta  
assert "PostgreSQL" in response

\# Mejor: validar la capacidad o la fuente esperada  
assert "memoria" in response.lower()  
assert any(term in response.lower() for term in \[  
    "episodio", "decisión", "contexto", "brain-ai"

\])

O, mejor todavía, haz que D3/D4 sean tests de comportamiento estructurado:

Python

expected \= {  
    "found\_memory": True,  
    "source": "brain-ai",  
    "answer\_contains": \["..."\]

}

No mezcles una expectativa histórica de infraestructura (“PostgreSQL”) con una expectativa funcional (“recupera una decisión guardada”).

---

## 2\. Unificar el acceso a MCP para modelos nativos y modelos API

Ahora tienes dos comportamientos distintos:

| Ruta | Acceso a MCP |
| ----- | ----: |
| OpenCode Server \+ modelo nativo | Sí |
| API directa a Groq | No |

Eso hace que los resultados dependan del proveedor, no de la capacidad real del sistema.

La solución más limpia es que tu runner de tests sea quien controle las herramientas, en vez de depender implícitamente de que OpenCode las inyecte.

Arquitectura recomendada:

text

run\_advanced\_tests.py  
  └─ ModelAdapter  
      ├─ OpenCodeAdapter  
      └─ GroqAdapter  
  └─ ToolExecutor / MCP Client  
      └─ brain-ai MCP bridge

          └─ brain-ai-01

De esa forma ambos tipos de modelos reciben las mismas tools disponibles.

---

## 3\. Implementar tool calling para Groq/API directa

Para modelos que se consumen por API, debes enviar la definición de la tool y manejar el ciclo:

1. Mandas prompt \+ tools.  
2. El modelo responde con una llamada a brain\_ai\_memory\_search.  
3. Tu código ejecuta esa llamada contra MCP/bridge.  
4. Añades el resultado como mensaje tool.  
5. Vuelves a consultar al modelo.  
6. El modelo genera la respuesta final.

Conceptualmente:

Python

messages \= \[  
    {"role": "system", "content": system\_prompt},  
    {"role": "user", "content": prompt},  
\]

tools \= \[{  
    "type": "function",  
    "function": {  
        "name": "brain\_ai\_memory\_search",  
        "description": "Busca recuerdos, decisiones y episodios relevantes.",  
        "parameters": {  
            "type": "object",  
            "properties": {  
                "query": {  
                    "type": "string"  
                }  
            },  
            "required": \["query"\]  
        }  
    }  
}\]

response \= groq\_client.chat.completions.create(  
    model\=model\_id,  
    messages\=messages,  
    tools\=tools,  
    tool\_choice\="auto",

)

Si el modelo pide una tool:

Python

for tool\_call in response.choices\[0\].message.tool\_calls:  
    if tool\_call.function.name \== "brain\_ai\_memory\_search":  
        args \= json.loads(tool\_call.function.arguments)

        result \= mcp\_client.call\_tool(  
            "brain-ai\_memory\_search",  
            {"query": args\["query"\]}  
        )

        messages.append(response.choices\[0\].message)  
        messages.append({  
            "role": "tool",  
            "tool\_call\_id": tool\_call.id,  
            "content": json.dumps(result),

        })

Luego haces una segunda consulta:

Python

final\_response \= groq\_client.chat.completions.create(  
    model\=model\_id,  
    messages\=messages,

)

Importante: el nombre de la tool expuesta a Groq puede ser brain\_ai\_memory\_search, aunque internamente la traduzcas al nombre MCP brain-ai\_memory\_search. Lo importante es mantener una capa de adaptación consistente.

---

## 4\. No dependas de MEMORY.md como mecanismo de integración

Que el modelo “lea MEMORY.md y decida llamar una herramienta” puede funcionar, pero es frágil.

Problemas típicos:

* Un modelo puede ignorar el archivo.  
* Puede responder inventando información en vez de consultar memoria.  
* Puede llamar la herramienta con argumentos inválidos.  
* Un proveedor puede no soportar tools o usar un formato distinto.  
* El prompt puede cambiar el comportamiento involuntariamente.

Usa MEMORY.md para instrucciones humanas o contexto, pero deja explícito el contrato de herramientas en el system prompt.

Ejemplo:

text

Tienes acceso a una herramienta de búsqueda de memoria.

Reglas:  
1\. Para preguntas sobre decisiones previas, episodios, preferencias o contexto histórico,  
   debes usar brain\_ai\_memory\_search antes de responder.  
2\. No inventes recuerdos si la herramienta no devuelve resultados.  
3\. Si no hay resultados, indícalo claramente.

4\. Basa la respuesta únicamente en los resultados recuperados cuando la pregunta requiera memoria.

Esto debe estar disponible en ambas rutas: OpenCode y API.

---

## 5\. Crear un adaptador único para las dos rutas

En vez de tener lógica separada en query\_native() y query\_api() que se comporte de forma distinta, define una interfaz común:

Python

class ModelRunner:  
    def query(self, prompt: str, tools: list | None \= None) \-\> dict:

        ...

Implementaciones:

Python

class OpenCodeRunner(ModelRunner):  
    def query(self, prompt, tools\=None):  
        \# OpenCode ya conoce MCP vía opencode.json  
        \# Pero registra si hubo tool calls.  
        ...

class GroqRunner(ModelRunner):  
    def query(self, prompt, tools\=None):  
        \# Ejecuta function calling y delega herramientas al MCP client.

        ...

Y en el test:

Python

result \= runner.query(  
    prompt\=test\_prompt,  
    tools\=\[brain\_ai\_memory\_search\_tool\],  
)

validate\_advanced(test\_id, result)

Así los tests dejan de saber si el modelo corre en OpenCode, Groq, OpenAI u otro backend.

---

## 6\. Añadir tests de integración de herramientas, no sólo tests de texto

Actualmente D1/D2 aparentemente validan que la respuesta mencione “memoria”, “episodio” o “decisión”. Eso puede dar falsos positivos: el modelo podría mencionar esas palabras sin haber consultado MCP.

Añade validación de trazabilidad.

Ejemplo de resultado estructurado:

JSON

{  
  "text": "Encontré una decisión previa sobre ...",  
  "tool\_calls": \[  
    {  
      "name": "brain\_ai\_memory\_search",  
      "arguments": {  
        "query": "decisión previa sobre ..."  
      },  
      "success": true  
    }  
  \],  
  "memory\_used": true

}

Entonces D1/D2 pueden validar:

Python

assert result\["memory\_used"\] is True  
assert any(  
    call\["name"\] \== "brain\_ai\_memory\_search"  
    and call\["success"\]  
    for call in result\["tool\_calls"\]  
)

assert "decisión" in result\["text"\].lower()

Esto es mucho más fiable que buscar palabras en el texto final.

---

## 7\. Manejar explícitamente modelos sin soporte de tools

No todos los modelos de Groq o proveedores externos soportan tool/function calling del mismo modo.

Por eso define capacidades:

Python

MODEL\_CAPABILITIES \= {  
    "opencode/mimo-v2.5-free": {  
        "mcp": True,  
        "tool\_calling": True,  
    },  
    "openai/gpt-oss-20b": {  
        "mcp": False,  
        "tool\_calling": True,  \# confirmar según endpoint/modelo  
    },

}

Si un modelo no soporta tools, tienes tres alternativas:

1. Excluirlo de D1/D2, marcándolo como SKIP, no como FAIL.  
2. Hacer recuperación de memoria antes de invocar al modelo y pasar el resultado en el prompt.  
3. Usar un modelo/endpoint que sí soporte function calling.

La opción 2 funciona como fallback:

text

Contexto recuperado de memoria:  
\- Decisión: ...  
\- Episodio: ...

Responde usando exclusivamente este contexto cuando sea relevante.

Pero es menos flexible que el tool calling, porque tu programa debe decidir cuándo buscar y qué buscar.

---

## Plan de acción recomendado

### Inmediato

1. Actualiza o elimina D3 y D4 si validan requisitos ya retirados.  
2. Cambia los errores de API directa de ERROR a algo explícito:  
   * SKIP: backend sin MCP/tool bridge  
   * o FAIL: backend debería soportar tools pero no está configurado.  
3. Registra llamadas a herramientas en el resultado de cada test.  
4. Asegura que D1/D2 no sólo busquen palabras, sino evidencia de uso de brain-ai\_memory\_search.

### Corto plazo

5. Implementa un MCPClient reutilizable que se conecte al bridge.  
6. Implementa tool/function calling para Groq.  
7. Introduce una interfaz ModelRunner común para OpenCode y APIs.

### Medio plazo

8. Haz que todos los tests dependan de capacidades declaradas, no del proveedor.  
9. Ejecuta una matriz de compatibilidad:

| Modelo | Backend | Tool calling | MCP | D1 | D2 |
| ----- | ----- | ----: | ----: | ----: | ----: |
| mimo-v2.5-free | OpenCode | Sí | Sí | PASS | PASS |
| gpt-oss-20b | Groq \+ bridge propio | Sí | Sí | PASS esperado | PASS esperado |
| modelo sin tools | API | No | No | SKIP/fallback | SKIP/fallback |

---

La idea principal es esta:

*OpenCode está resolviendo por ti el ciclo MCP para los modelos nativos. Si quieres paridad con Groq/API directa, debes mover esa responsabilidad a tu aplicación de tests o hacer que toda consulta pase por OpenCode.*

Si buscas la solución más rápida, enruta también los modelos API a través de OpenCode si ese servidor puede usar esos providers. Si buscas la solución más mantenible y portable, implementa el cliente MCP \+ tool loop dentro de run\_advanced\_tests.py o de un adaptador compartido.  
