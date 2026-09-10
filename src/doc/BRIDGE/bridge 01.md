Tu diagnóstico es correcto, pero en realidad tienes dos problemas distintos y conviene separarlos:

1. Arquitectónico: query\_api() habla con Groq directo, sin herramientas, así que el modelo "alucina" la llamada a brain-ai\_memory\_search y Groq devuelve 400 tool\_use\_failed.  
2. De datos: D3/D4 validan contra valores fijos ("PostgreSQL", "Por definir") que ya no coinciden con la memoria real.

---

## Problema 1: modelos API sin MCP

### Opción recomendada: que *todos* los modelos pasen por el OpenCode server

En lugar de mantener dos caminos, registra Groq como provider en OpenCode y usa query\_native() para todo. Groq ya viene soportado; basta con que el server tenga la key:

Bash

export GROQ\_API\_KEY\=...

opencode serve \--port 4096     \# o como arranques el server

Si prefieres declararlo explícito (o usas un provider OpenAI-compatible no soportado):

JSON

// opencode.json  
{  
  "provider": {  
    "groq": {  
      "npm": "@ai-sdk/openai-compatible",  
      "name": "Groq",  
      "options": {  
        "baseURL": "https://api.groq.com/openai/v1",  
        "apiKey": "{env:GROQ\_API\_KEY}"  
      },  
      "models": {  
        "openai/gpt-oss-20b": { "name": "GPT-OSS 20B (Groq)" }  
      }  
    }  
  },  
  "mcp": { "brain-ai": { "command": \["python", "mcp\_bridge.py"\], "enabled": true } }

}

Y en run\_advanced\_tests.py el registro de modelos queda plano:

Python

MODELS \= \[  
    "opencode/mimo-v2.5-free",  
    "groq/openai/gpt-oss-20b",      \# antes iba por query\_api()  
\]

for model\_id in MODELS:

    out \= query\_native(SERVER\_PORT, model\_id, prompt)   \# único camino

Ventajas: un solo código, mismo system prompt, mismas tools y mismo bucle de tool-calling para todos → la comparación entre modelos es justa. query\_api() desaparece o queda como fallback.

### Alternativa: implementar tool-calling en query\_api()

Solo tiene sentido si quieres medir modelos fuera del harness de OpenCode (sin su system prompt, con control total). Groq soporta tools en formato OpenAI, así que necesitas un bucle:

Python

def query\_api(model\_id, prompt, max\_turns\=6):  
    messages \= \[{"role": "system", "content": SYSTEM\_PROMPT},  
                {"role": "user", "content": prompt}\]  
    for \_ in range(max\_turns):  
        r \= client.chat.completions.create(  
            model\=model\_id, messages\=messages,  
            tools\=TOOLS, tool\_choice\="auto")  
        msg \= r.choices\[0\].message  
        if not msg.tool\_calls:  
            return msg.content  
        messages.append(msg)  
        for tc in msg.tool\_calls:  
            result \= call\_brain\_ai(tc.function.name, json.loads(tc.function.arguments))  
            messages.append({"role": "tool", "tool\_call\_id": tc.id,  
                             "content": json.dumps(result)})

    raise RuntimeError("max\_turns alcanzado")

Para que TOOLS no se desincronice del MCP, genéralo desde el propio bridge: conéctate a mcp\_bridge.py con el SDK mcp de Python, haz list\_tools() para los schemas y call\_tool() para ejecutar. Así reutilizas exactamente lo mismo que ve OpenCode.

### Lo que NO recomiendo

* Quitar las instrucciones de MCP del prompt para modelos API: elimina el 400, pero D1/D2 dejan de medir uso de memoria; el PASS sería vacío.  
* Inyectar los resultados de memoria en el prompt (RAG previo): funciona, pero mide otra cosa (comprensión de contexto, no uso de herramientas). Útil como test separado, no como sustituto.

### Fix inmediato (5 minutos)

Mientras migras, que el reporte sea honesto: si el camino no tiene tools y el test las requiere, marca SKIP, no ERROR:

Python

if not model\_has\_tools(model\_id) and test\["needs\_tools"\]:  
    results\[test\_id\] \= ("SKIP", "camino sin acceso a MCP")

    continue

---

## Problema 2: D3/D4 con valores obsoletos

El fallo de fondo es que los tests dependen de la memoria viva, que cambia. Dos formas de arreglarlo:

a) Fixtures sembradas (recomendado): antes de correr, inserta hechos conocidos en brain-ai (idealmente con un tag o namespace de test) y valida contra ellos:

Python

FIXTURES \= \[  
    {"type": "decision", "content": "Base de datos: PostgreSQL 16", "tags": \["test-fixture"\]},  
    {"type": "decision", "content": "Proveedor de email: por definir", "tags": \["test-fixture"\]},  
\]  
TESTS\["D3"\]\["expect"\] \= "PostgreSQL"   \# derivado de FIXTURES, no hardcodeado aparte

def setup():    seed(FIXTURES)

def teardown(): delete\_by\_tag("test-fixture")

b) Expectativas dinámicas: si no puedes sembrar, al inicio consulta brain-ai por la decisión actual y úsala como expect. Menos aislado, pero no se pudre.

---

## Bonus: endurecer D1/D2

"Menciona memoria/episodio" es una validación por palabras clave: un modelo puede escribir "según mi memoria…" sin llamar a nada. Con \--format json OpenCode te devuelve las partes de la respuesta, incluidos los eventos de tool call. Valida que exista una invocación real a brain-ai\_memory\_search en vez de buscar substrings; así el PASS significa que el modelo usó la herramienta.

## Orden sugerido

1. SKIP en vez de ERROR (hoy).  
2. Configurar Groq en OpenCode y unificar en query\_native() (borra query\_api()).  
3. Fixtures para D3/D4.  
4. Validar D1/D2 por tool calls reales.

