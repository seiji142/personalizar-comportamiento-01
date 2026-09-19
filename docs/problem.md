Sí: eso es un bucle de compactación, no una respuesta normal a “hola”. Los bloques Objective / Work State / Next Move son resúmenes internos de OpenCode que el modelo está repitiendo. La sesión anterior probablemente quedó asociada a adjuntos/contexto grande y compaction.auto: true vuelve a activarlo.

## Haz esto para detenerlo

### 1\. Desactiva temporalmente la compactación automática

En la configuración global cambia:

jsonc

"compaction": {  
  "auto": false,  
  "prune": true

}

Quita por ahora "reserved": 20000.

### 2\. Limita la salida del modelo

En el modelo local usa temporalmente:

JSON

"limit": {  
  "context": 131072,  
  "output": 4096

}

Esto evita que una respuesta degenerada continúe decenas de miles de tokens.

### 3\. Corrige el identificador del custom provider

Mi respuesta anterior contenía un error: si el provider se llama groq-custom, el modelo no puede seguir comenzando por groq/.

Tu configuración local debería quedar así:

JSON

{  
  "$schema": "https://opencode.ai/config.json",  
  "model": "groq-custom/openai/gpt-oss-20b",  
  "compaction": {  
    "auto": false,  
    "prune": true  
  },  
  "provider": {  
    "groq-custom": {  
      "npm": "@ai-sdk/openai-compatible",  
      "name": "Groq Custom",  
      "options": {  
        "apiKey": "{env:GROQ\_CUENTA\_1}",  
        "baseURL": "https://api.groq.com/openai/v1"  
      },  
      "models": {  
        "openai/gpt-oss-20b": {  
          "name": "OpenAI GPT-OSS 20B",  
          "limit": {  
            "context": 131072,  
            "output": 4096  
          }  
        }  
      }  
    }  
  }

}

Con esto, la entrada antigua groq de auth.json no debería utilizarse porque el provider ahora es groq-custom.

### 4\. No reutilices la sesión que está en bucle

Después de guardar:

1. Detén la generación.  
2. Cierra completamente OpenCode.  
3. Si queda abierto:

PowerShell

Stop-Process \-Name OpenCode \-Force \-ErrorAction SilentlyContinue

4. Abre exactamente el proyecto personalizar-comportamiento-01.  
5. Crea una sesión nueva mediante New Session o /new.  
6. Comprueba que aparezca:

text

groq-custom/openai/gpt-oss-20b

7. Escribe:

text

Responde únicamente: Hola

No continúes la sesión problemática: el modelo seleccionado y el estado de compactación pueden quedar guardados por sesión. Eso también explica por qué seguía apareciendo mimo v2.5 free aunque hubieras cambiado la configuración.

## Correcciones importantes respecto a lo anterior

* La propiedad correcta de OpenCode es "plugin", en singular, no "plugins".  
* Si se renombra el provider, también debe cambiarse el prefijo de "model".  
* No necesitas duplicar la API key como variable permanente de Windows. Para mantenerla centralizada, solo OPENCODE\_DOTENV\_PATH debería ser permanente y el plugin debe cargar GROQ\_CUENTA\_1.  
* El bucle actual es un problema de sesión/compactación/generación; no es el comportamiento esperado de una API key inválida.

Si en una sesión completamente nueva, con auto: false y salida de 4096, vuelve a repetir esos resúmenes, entonces el problema es la compatibilidad de gpt-oss-20b con el flujo agentic/compaction de OpenCode mediante openai-compatible, no el .env.  
