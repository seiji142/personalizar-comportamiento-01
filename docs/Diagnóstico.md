## Diagnóstico

Hay cinco fallos independientes apilados. Ninguna de las opciones que probaste podía funcionar sola.

| \# | Problema | Evidencia |
| ----- | ----- | ----- |
| 1 | Carpeta de plugins mal nombrada | OpenCode carga \~/.config/opencode/\*\*plugin\*\*/ (singular). Tú tienes plugins/ → nunca se ejecuta, por eso no ves \[dotenv\] loaded N var(s) |
| 2 | "plugin": \[\] en opencode.json | Un array vacío en la config local puede sobrescribir/anular la lista de plugins |
| 3 | La app de escritorio no hereda $PROFILE | OPENCODE\_DOTENV\_PATH no existe en el proceso de OpenCode.exe (se lanza desde Explorer, no desde PowerShell) |
| 4 | auth.json con key vieja | El groq built-in tiene gsk\_SZSh… → "Invalid API Key" |
| 5 | La TUI recuerda el último modelo usado | model en config es solo el default de sesiones nuevas; "mimo v2.5 free" viene del estado persistido |

La causa de {env:GROQ\_CUENTA\_1} literal es la combinación de 1+3: la sustitución {env:...} de OpenCode es nativa, pero solo resuelve variables que ya existen en el proceso al momento de leer la config.

---

## Solución recomendada (Plan A): plugin que no depende de variables de entorno

Elimina la dependencia de OPENCODE\_DOTENV\_PATH por completo. El plugin lee el .env con ruta absoluta e inyecta la key directamente en la config en memoria.

### 1\. Crear la carpeta correcta y borrar la vieja

PowerShell

Remove-Item \-Recurse \-Force "$env:USERPROFILE\\.config\\opencode\\plugins" \-ErrorAction SilentlyContinue  
New-Item \-ItemType Directory \-Force "$env:USERPROFILE\\.config\\opencode\\plugin"

### 2\. \~/.config/opencode/plugin/env-groq.ts

TypeScript

import fs from "node:fs"

const ENV\_PATH \=  
  "C:/Users/seiji/OneDrive/Documentos/Proyecto AI/Verificacion-modelos-ai/.env"

function parseEnv(file: string): Record\<string, string\> {  
  const out: Record\<string, string\> \= {}  
  if (\!fs.existsSync(file)) return out  
  for (const raw of fs.readFileSync(file, "utf8").split(/\\r?\\n/)) {  
    const line \= raw.trim()  
    if (\!line || line.startsWith("\#")) continue  
    const i \= line.indexOf("=")  
    if (i \< 0) continue  
    const k \= line.slice(0, i).trim()  
    let v \= line.slice(i \+ 1).trim()  
    if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'")))  
      v \= v.slice(1, \-1)  
    out\[k\] \= v  
  }  
  return out  
}

export const EnvGroqPlugin \= async () \=\> {  
  const vars \= parseEnv(ENV\_PATH)  
  for (const \[k, v\] of Object.entries(vars)) {  
    if (\!process.env\[k\]) process.env\[k\] \= v  
  }

  const key \= vars.GROQ\_CUENTA\_1 ?? process.env.GROQ\_CUENTA\_1  
  // El provider built-in de Groq lee GROQ\_API\_KEY  
  if (key) process.env.GROQ\_API\_KEY \= key

  return {  
    config: async (cfg: any) \=\> {  
      if (\!key) return  
      cfg.provider ??= {}  
      cfg.provider.groq ??= {}  
      cfg.provider.groq.options ??= {}  
      cfg.provider.groq.options.apiKey \= key  
    },  
  }  
}

*Clave del diseño: se setea GROQ\_API\_KEY y se escribe options.apiKey en el hook config. Así funciona tanto con el provider built-in como con uno custom, y ya no importa si {env:...} resolvió o no.*

### 3\. Limpiar auth.json

La key de auth.json gana sobre el env var. Bórrala:

PowerShell

$p \= "$env:USERPROFILE\\.local\\share\\opencode\\auth.json"  
$j \= Get-Content $p \-Raw | ConvertFrom-Json  
$j.PSObject.Properties.Remove('groq')

$j | ConvertTo-Json \-Depth 10 | Set-Content $p \-Encoding utf8

(O simplemente opencode auth logout → seleccionar groq.)

### 4\. Simplificar opencode.json (proyecto)

No declares un provider custom llamado groq: colisiona con el built-in y además pierdes el catálogo de modelos de Models.dev. openai/gpt-oss-20b ya existe en el Groq built-in.

JSON

{  
  "$schema": "https://opencode.ai/config.json",  
  "model": "groq/openai/gpt-oss-20b",  
  "small\_model": "groq/openai/gpt-oss-20b"

}

Nota que quité "plugin": \[\] — ese array vacío era sospechoso de anular la carga.

### 5\. Forzar el modelo en la TUI

La config solo aplica a sesiones nuevas. En la TUI:

text

/models  → groq → OpenAI GPT-OSS 20B

O borra el estado persistido:

PowerShell

Remove-Item "$env:USERPROFILE\\.local\\share\\opencode\\state\*" \-Recurse \-Force \-ErrorAction SilentlyContinue

### 6\. Verificar

Arranca desde PowerShell con una consola limpia (para probar que no dependes del $PROFILE):

PowerShell

$env:OPENCODE\_DOTENV\_PATH \= $null

opencode

Luego:

text

/models

Debe aparecer Groq → OpenAI GPT-OSS 20B y responder sin "Invalid API Key".

Si no carga el plugin, revisa el log:

PowerShell

Get-Content "$env:USERPROFILE\\.local\\share\\opencode\\log\\\*.log" \-Tail 80

---

## Plan B (complemento, no sustituto): variable a nivel de usuario Windows

Si además quieres que *cualquier* proceso (incluida OpenCode.exe desde Explorer) vea las keys, regístralas a nivel de usuario. Esto sí lo hereda la app de escritorio:

PowerShell

\[Environment\]::SetEnvironmentVariable(  
  "GROQ\_API\_KEY",  
  (Get-Content "C:\\Users\\seiji\\OneDrive\\Documentos\\Proyecto AI\\Verificacion-modelos-ai\\.env" |  
    Where-Object { $\_ \-match '^GROQ\_CUENTA\_1=' }) \-replace '^GROQ\_CUENTA\_1=', '',

  "User")

⚠️ Requiere cerrar sesión de Windows (o reiniciar explorer.exe) para que la app nueva la herede. Y deja de ser "centralizado en el .env": si rotas la key tienes que re-ejecutar el comando. Por eso el Plan A es la respuesta a tu pregunta principal — *sin wrappers y siempre sincronizado con el .env*.

---

## Sobre las opciones que descartaste

* @aeondave/opencode-dotenv: el shim reexportaba desde \~/.cache/...@latest/.... Aunque arreglaras la carpeta plugin/, esa ruta con @latest literal es frágil (cambia al reinstalar). Mejor tu propio plugin de 30 líneas: cero dependencias, ruta explícita, control total.  
* Provider custom "groq" con @ai-sdk/openai-compatible: solo tiene sentido si necesitas un endpoint que Models.dev no conoce. Aquí no. Si aun así lo quieres (p. ej. para hacer fallback a GROQ\_CUENTA\_2), renómbralo a groq-alt y usa el modelo como groq-alt/openai/gpt-oss-20b.

## Bonus: rotación entre las dos cuentas

Si quieres usar GROQ\_CUENTA\_2 como respaldo, añade en el mismo plugin:

TypeScript

cfg.provider\["groq-2"\] \= {  
  npm: "@ai-sdk/openai-compatible",  
  name: "Groq (cuenta 2)",  
  options: { apiKey: vars.GROQ\_CUENTA\_2, baseURL: "https://api.groq.com/openai/v1" },  
  models: { "openai/gpt-oss-20b": { name: "GPT-OSS 20B (c2)" } },

}

---

### Resumen accionable

1. plugins/ → plugin/ ✅  
2. Plugin propio con ruta absoluta al .env (nada de OPENCODE\_DOTENV\_PATH) ✅  
3. Borrar entrada groq de auth.json ✅  
4. Quitar el provider custom y el "plugin": \[\] del opencode.json ✅  
5. Cambiar el modelo con /models (la config no reescribe sesiones existentes) ✅

