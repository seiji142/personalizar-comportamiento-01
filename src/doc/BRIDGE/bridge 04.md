## Diagnóstico corto

No es un problema de los modelos, es del harness: tienes dos caminos que miden cosas distintas.

* Nativos → OpenCode server → tienen brain-ai\_memory\_search → pueden usar memoria.  
* API → Groq directo → *no tienen ninguna tool* → el modelo intenta llamar una tool que no existe → 400\.

Mientras eso siga así, la comparación entre modelos no vale nada (el ERROR de Groq es un fallo de infraestructura, no del modelo). Así que lo primero es igualar el camino.

## Recomendación principal: una sola ruta, todo por OpenCode server

Es la opción con menos código y menos deriva: el MCP ya funciona, MEMORY.md se inyecta igual para todos, y no tienes que reimplementar tool-calling.

1. Dar credenciales de Groq al *server*, no al CLI. Con \--attach el CLI solo reenvía la petición; quien llama al proveedor es opencode serve, así que GROQ\_API\_KEY tiene que estar en el entorno de ese proceso (o vía opencode auth login → Groq). Opcionalmente explícito en opencode.json:  
2. JSON

"provider": {  
  "groq": { "options": { "apiKey": "{env:GROQ\_API\_KEY}" } }

3. }  
4. Reinicia el server después.  
5. Cambiar los ids de modelo al formato proveedor/modelo: openai/gpt-oss-20b → groq/openai/gpt-oss-20b (Groq usa ids con slash; OpenCode corta en el primero).  
6. En run\_advanced\_tests.py, la tabla de modelos deja de tener tipo api: todos pasan por query\_native. Deja query\_api detrás de un flag (\--raw-api) o bórrala.  
7. Verifica con opencode models | grep groq y una corrida de D1 antes de lanzar la suite completa.

Ojo: si un modelo de Groq no soporta tool calling (los hay), D1/D2 fallarán legítimamente. Eso sí es un resultado ("este modelo no sabe usar la memoria"), no un error del harness. Repórtalo como FAIL, no ERROR.

## Si realmente necesitas la ruta API directa

(Por ejemplo, para medir sin OpenCode o para proveedores que OpenCode no cubre.) Entonces query\_api tiene que implementar el loop de tool calling que hoy hace OpenCode por ti:

Python

def query\_api(model\_id, prompt, system, tools, max\_steps\=6):  
    client \= Groq()  
    messages \= \[{"role": "system", "content": system},  
                {"role": "user", "content": prompt}\]  
    calls \= \[\]  
    for \_ in range(max\_steps):  
        resp \= client.chat.completions.create(  
            model\=model\_id, messages\=messages, tools\=tools, tool\_choice\="auto")  
        msg \= resp.choices\[0\].message  
        if not msg.tool\_calls:  
            return {"text": msg.content, "tool\_calls": calls}  
        messages.append(msg)  
        for tc in msg.tool\_calls:  
            args \= json.loads(tc.function.arguments or "{}")  
            result \= call\_brain(tc.function.name, args)   \# HTTP a brain-ai-01  
            calls.append({"name": tc.function.name, "args": args})  
            messages.append({"role": "tool", "tool\_call\_id": tc.id,  
                             "content": json.dumps(result, ensure\_ascii\=False)})

    return {"text": None, "tool\_calls": calls, "error": "max\_steps"}

Para no duplicar esquemas a mano, saca tools del propio mcp\_bridge.py con el SDK de MCP (list\_tools() → convertir a formato OpenAI function, call\_tool() para ejecutar). Así la ruta API usa exactamente las mismas definiciones que OpenCode y no se desincronizan.

Una tercera opción sería inyectar la memoria por RAG (buscar tú antes y meter los resultados en el prompt), pero eso mide otra cosa —recall con contexto dado, no capacidad agéntica—. Si la usas, etiquétala como métrica distinta, no la mezcles en la misma tabla.

## Lo que sí es de los tests (arréglalo aunque no toques lo anterior)

* D3/D4: la memoria cambió y los tests no. Mejor que actualizar strings a mano: siembra un fixture conocido en brain-ai antes de correr (seed\_memory.json) y genera las expectativas desde ese fixture. Así los tests no se pudren cada vez que cambie la memoria real y la corrida es determinista.  
* Validación débil: "menciona memoria" pasa si el modelo dice *"no tengo memoria de eso"*. Como \--format json te devuelve los eventos, valida que realmente se invocó brain-ai\_memory\_search (busca las parts de tipo tool con el nombre de la herramienta; confirma el campo exacto con la salida de una corrida de D1) y, opcionalmente, que la respuesta contiene el dato concreto del fixture. Eso convierte D1/D2 en tests de verdad.  
* Separa ERROR de FAIL en el reporte: ERROR \= el harness no pudo ejecutar; FAIL \= el modelo ejecutó y lo hizo mal. Hoy ya lo distingues en la tabla, mantenlo así para no leer mal los resultados.

Orden que seguiría: (1) unificar ruta por OpenCode, (2) validar por tool call real, (3) fixture \+ reescribir D3/D4.  
