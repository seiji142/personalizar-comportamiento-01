Hay varios problemas independientes. El más importante es que OpenCode no lee archivos .env de forma nativa: {env:GROQ\_CUENTA\_1} solamente consulta el entorno del proceso. Además, la ruta configurada actualmente parece incorrecta.

## 1\. Corregir la ruta del .env

La ruta configurada en $PROFILE es:

text

C:\\Users\\seiji\\OneDrive\\Documentos\\Proyecto AI\\Verificacion-modelos-ai.env

Pero, según la descripción, la ruta real es:

text

C:\\Users\\seiji\\OneDrive\\Documentos\\Proyecto AI\\Verificacion-modelos-ai\\.env

Falta \\ antes de .env.

Verifícalo:

PowerShell

$dotenv \= 'C:\\Users\\seiji\\OneDrive\\Documentos\\Proyecto AI\\Verificacion-modelos-ai\\.env'

Test-Path \-LiteralPath $dotenv

Debe devolver True.

---

## 2\. Crear OPENCODE\_DOTENV\_PATH como variable de usuario de Windows

El $PROFILE de PowerShell no se ejecuta cuando abres OpenCode.exe desde el menú Inicio, acceso directo o Explorer. Por eso la aplicación de escritorio no recibe esa variable.

Créala como variable persistente de usuario:

PowerShell

\[Environment\]::SetEnvironmentVariable(  
    'OPENCODE\_DOTENV\_PATH',  
    'C:\\Users\\seiji\\OneDrive\\Documentos\\Proyecto AI\\Verificacion-modelos-ai\\.env',  
    'User'

)

También puedes establecerla en la sesión actual para hacer pruebas:

PowerShell

$env:OPENCODE\_DOTENV\_PATH \=

    'C:\\Users\\seiji\\OneDrive\\Documentos\\Proyecto AI\\Verificacion-modelos-ai\\.env'

Comprueba el valor persistente:

PowerShell

\[Environment\]::GetEnvironmentVariable(  
    'OPENCODE\_DOTENV\_PATH',  
    'User'

)

### Importante

Los procesos existentes no reciben variables nuevas. Después de establecerla:

1. Cierra completamente OpenCode.  
2. Comprueba que no quede ningún proceso:

PowerShell

Get-Process OpenCode \-ErrorAction SilentlyContinue |

    Stop-Process \-Force

3. Cierra sesión de Windows y vuelve a entrar. Esto es más fiable que reiniciar solamente Explorer.  
4. Abre de nuevo OpenCode.

---

## 3\. Declarar el plugin explícitamente

Tener el paquete instalado en la caché no garantiza que OpenCode lo cargue. Decláralo en la configuración global.

En:

text

C:\\Users\\seiji\\.config\\opencode\\opencode.jsonc

añade:

jsonc

{  
  "$schema": "https://opencode.ai/config.json",

  "plugin": \[  
    "@aeondave/opencode-dotenv@latest"  
  \],

  "compaction": {  
    "auto": true,  
    "prune": true,  
    "reserved": 20000  
  }

}

Conserva también tu bloque mcp.

Elimina este campo de la configuración local:

JSON

"plugin": \[\]

Aunque dependiendo de la versión las listas pueden combinarse, es mejor no dejar una lista local vacía que pueda reemplazar o interferir con la configuración global.

Si prefieres usar el shim local, no declares a la vez el paquete npm y el shim. Usa solamente uno de los dos mecanismos.

---

## 4\. Evitar la colisión con el provider integrado groq

Es recomendable no llamar groq al provider personalizado, porque OpenCode también tiene un provider integrado con ese identificador y una credencial en auth.json.

Usa, por ejemplo, groq-central.

Además, como la aplicación de escritorio puede abrirse sin tomar el directorio del proyecto como directorio activo, conviene colocar el modelo y el provider en la configuración global si quieres que estén disponibles siempre.

Configuración global recomendada:

jsonc

{  
  "$schema": "https://opencode.ai/config.json",

  "plugin": \[  
    "@aeondave/opencode-dotenv@latest"  
  \],

  "model": "groq-central/openai/gpt-oss-20b",

  "provider": {  
    "groq-central": {  
      "npm": "@ai-sdk/openai-compatible",  
      "name": "Groq central",  
      "options": {  
        "apiKey": "{env:GROQ\_CUENTA\_1}",  
        "baseURL": "https://api.groq.com/openai/v1"  
      },  
      "models": {  
        "openai/gpt-oss-20b": {  
          "name": "OpenAI GPT-OSS 20B",  
          "limit": {  
            "context": 131072,  
            "output": 65536  
          }  
        }  
      }  
    }  
  },

  "compaction": {  
    "auto": true,  
    "prune": true,  
    "reserved": 20000  
  },

  "mcp": {  
    "git\_publisher": {  
      "type": "local",  
      "command": \[  
        "C:/Users/seiji/.config/opencode/herramientas/.venv/Scripts/python.exe",  
        "C:/Users/seiji/.config/opencode/herramientas/git\_tool.py"  
      \],  
      "enabled": true  
    }  
  }

}

He usado / en las rutas de JSON para evitar problemas con escapes como \\U, \\S, etc.

Después puedes eliminar el bloque provider y model del opencode.json local para evitar configuraciones duplicadas.

### Ventaja del alias

Al usar:

text

groq-central/openai/gpt-oss-20b

la entrada antigua:

JSON

"groq": {  
  "type": "api",  
  "key": "..."

}

de auth.json ya no debería aplicarse al provider personalizado.

No es necesario borrar auth.json para esta solución. Si quieres limpiar la credencial antigua, hazlo mediante el comando de autenticación de OpenCode, pero no debería influir sobre groq-central.

---

## 5\. No reutilizar una sesión antigua

El modelo mostrado por una conversación o sesión existente puede permanecer guardado. Después del cambio:

1. Abre el proyecto correcto.  
2. Crea una sesión/conversación nueva.  
3. Comprueba que aparezca:

text

OpenAI GPT-OSS 20B

o:

text

groq-central/openai/gpt-oss-20b

Que siga apareciendo mimo v2.5 free no implica necesariamente que falle la API key; también puede significar que:

* la aplicación no cargó el opencode.json local;  
* se reabrió una sesión antigua;  
* la configuración global no contiene el modelo;  
* el plugin no fue registrado.

Por eso mover el provider a la configuración global simplifica el diagnóstico.

---

## 6\. Si el plugin sigue sin funcionar

Existe una limitación importante: OpenCode resuelve {env:VARIABLE} usando el entorno del proceso. Dependiendo del orden de inicialización de la versión 1.18.31, un plugin dotenv puede cargarse demasiado tarde para intervenir en la sustitución de variables de configuración.

La alternativa más fiable es copiar la key desde el .env a una variable de usuario de Windows. OpenCode la recibirá directamente al iniciarse y ya no dependerá del plugin.

Puedes hacerlo sin escribir la key manualmente:

PowerShell

$dotenv \= 'C:\\Users\\seiji\\OneDrive\\Documentos\\Proyecto AI\\Verificacion-modelos-ai\\.env'

$line \= Get-Content \-LiteralPath $dotenv |  
    Where-Object { $\_ \-match '^\\s\*GROQ\_CUENTA\_1\\s\*=' } |  
    Select-Object \-First 1

if (-not $line) {  
    throw 'No se encontró GROQ\_CUENTA\_1 en el archivo .env'  
}

$key \= ($line \-split '=', 2)\[1\].Trim().Trim('"').Trim("'")

\[Environment\]::SetEnvironmentVariable(  
    'GROQ\_CUENTA\_1',  
    $key,  
    'User'

)

Después cierra sesión de Windows y vuelve a entrar.

En ese caso puedes incluso prescindir del plugin dotenv, porque esta configuración funcionará directamente:

JSON

"apiKey": "{env:GROQ\_CUENTA\_1}"

La desventaja es que la key queda copiada en las variables de usuario de Windows y tendrás que volver a sincronizarla cuando cambie. Esa sincronización podría ejecutarse mediante una tarea programada al iniciar sesión, sin usar wrappers para abrir OpenCode.

---

## Recomendación final

Prueba en este orden:

1. Corregir la ruta a Verificacion-modelos-ai\\.env.  
2. Crear OPENCODE\_DOTENV\_PATH como variable de usuario.  
3. Declarar explícitamente @aeondave/opencode-dotenv@latest en la configuración global.  
4. Renombrar el provider a groq-central.  
5. Mover model y provider a la configuración global.  
6. Cerrar sesión de Windows y abrir una sesión nueva de OpenCode.  
7. Si todavía falla, establecer GROQ\_CUENTA\_1 directamente como variable de usuario usando el script anterior.

La opción 7 es la más robusta para la aplicación de escritorio. Windows no carga archivos .env automáticamente; para leer realmente el archivo en cada inicio hace falta necesariamente algún cargador: plugin, tarea programada o wrapper.

Si cualquiera de las keys mostradas fue publicada completa en algún sitio, conviene revocarla y generar una nueva.  
