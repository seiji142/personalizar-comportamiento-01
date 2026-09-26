Tienes dos problemas distintos mezclados en el reporte. Te recomiendo atacarlos por separado:

## Problema 1: D3 y D4 (tests viejos)

No son fallos del sistema, son expectativas desactualizadas. Opciones:

Opción A (recomendada): actualizarlos. Si la arquitectura cambió (PostgreSQL → otra cosa, "Por definir" → valor real), corrige las expectativas al estado actual. Revisa el git history para ver qué cambió y cuándo.

Opción B: jubilarlos formalmente. Márkalos como skip con razón y fecha:

Python

@pytest.mark.skip(reason\="Deprecated: esperaba PostgreSQL, migrado en v2.3. Eliminar en v3")  
def test\_d3\_storage():

    ...

Mejora estructural: si las expectativas cambian seguido, centralízalas en un test\_expectations.json que los tests lean, en vez de hardcodearlas. Así el test no "pudre" cuando actualizas el config.

## Problema 2: modelos API sin MCP

Dos caminos:

### Opción A: Unificar todo por OpenCode (menos código)

Si OpenCode soporta el proveedor Groq (lo hace vía models.dev), configura el proveedor en opencode.json y elimina query\_api(). Todos los modelos pasan por el server y heredan el MCP bridge gratis:

text

query\_native() → opencode run \--model groq/openai/gpt-oss-20b → MCP ✅

### Opción B: Implementar tool-calling loop en query\_api()

Si necesitas mantener la vía directa a Groq, tienes que implementar el loop de function calling tú mismo. Groq es OpenAI-compatible, así que funciona con el cliente estándar:

Python

TOOLS \= \[{  
    "type": "function",  
    "function": {  
        "name": "brain-ai\_memory\_search",  
        "description": "Busca en la memoria del agente",  
        "parameters": {  
            "type": "object",  
            "properties": {"query": {"type": "string"}},  
            "required": \["query"\]  
        }  
    }  
}\]

def query\_api\_with\_tools(model\_id, prompt, max\_turns\=3):  
    messages \= \[{"role": "user", "content": prompt}\]  
    for \_ in range(max\_turns):  
        resp \= client.chat.completions.create(  
            model\=model\_id, messages\=messages, tools\=TOOLS  
        )  
        msg \= resp.choices\[0\].message  
        if not msg.tool\_calls:  
            return msg.content  
        messages.append(msg)  
        for tc in msg.tool\_calls:  
            args \= json.loads(tc.function.arguments)  
            result \= call\_brain\_ai\_http(args)  \# HTTP directo a brain-ai-01  
            messages.append({  
                "role": "tool",  
                "tool\_call\_id": tc.id,  
                "content": json.dumps(result)  
            })

    raise RuntimeError("max\_turns alcanzado sin respuesta final")

Nota: en esta vía ni siquiera necesitas el MCP bridge — ejecutas la tool directamente contra brain-ai-01 por HTTP.

## ⚠️ Advertencia importante: posible falso positivo en D1/D2

Tu criterio de PASS es *keyword matching* ("menciona memoria"). Un modelo puede decir "revisé mi memoria" sin haber llamado la tool nunca y el test da PASS. Verifica en los logs del MCP bridge que brain-ai\_memory\_search realmente se invocó durante la ventana del test:

Python

def test\_d1\_memory\_search():  
    bridge\_log\_before \= get\_bridge\_call\_count()  
    response \= query\_native(...)  
    bridge\_log\_after \= get\_bridge\_call\_count()  
      
    assert bridge\_log\_after \> bridge\_log\_before, "El modelo NO llamó la tool"

    assert "memoria" in response.lower()

## Orden de trabajo sugerido

1. Primero: verifica con logs si D1/D2 son reales o falsos positivos (5 min)  
2. Segundo: decide entre Opción A o B para los modelos API. Si OpenCode soporta Groq, la A te ahorra mantener el tool loop  
3. Tercero: actualiza o jubila D3/D4  
4. Después: endurece los criterios de validación (tool llamada \+ contenido, no solo keywords)

¿Qué reemplazó a PostgreSQL en tu stack actual? Con ese dato te puedo ayudar a reescribir D3/D4.  
