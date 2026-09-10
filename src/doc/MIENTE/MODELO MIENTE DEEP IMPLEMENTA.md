Perfecto. Para que todos los modelos que uses en OpenCode respeten esas reglas, necesitas configurarlas de forma global en OpenCode. OpenCode lee instrucciones desde archivos tipo AGENTS.md o su configuración global.

---

## 1\. Ubica el archivo de instrucciones global de OpenCode

OpenCode suele aceptar:

* Global (todos los proyectos y modelos):  
  \~/.config/opencode/AGENTS.md (o en Windows: %USERPROFILE%\\.config\\opencode\\AGENTS.md)  
* Por proyecto:  
  AGENTS.md en la raíz del repositorio.

Si el archivo no existe, créalo.  
Nota: Algunas versiones usan .opencode/AGENTS.md o instructions.md global; consulta opencode \--help o la documentación de tu versión. La ruta anterior es la más común.

---

## 2\. Contenido que debes pegar en ese archivo

Copia y pega todo esto en el AGENTS.md global:

Markdown

**\# Reglas globales de honestidad y verificación**

**\#\# Principios absolutos**

1\. **\*\*Nunca inventes, asumas, recuerdes o generes información que no tengas en tu contexto o que no puedas verificar con herramientas.\*\***  
2\. Si no estás seguro de un dato (API keys, credenciales, números, fechas, nombres, valores), responde exactamente:    
   \`"No lo sé. No tengo esa información en mi contexto."\`  
3\. Antes de afirmar cualquier dato factual, **\*\*verifica la fuente\*\***. Para API keys y secretos, usa la herramienta designada.  
4\. No uses frases como \`"creo que"\`, \`"probablemente"\`, \`"debería ser"\`, \`"me suena que"\` para encubrir inventos. Si no tienes certeza, di que no lo sabes.  
5\. Si una instrucción o resumen menciona que existe un dato pero no lo muestra, trátalo como **\*\*"no disponible"\*\***. No intentes inferirlo, completarlo o "recordarlo".  
6\. Si necesitas una credencial y no está disponible, detente y pide al usuario que la configure. No generes una credencial falsa.

**\#\# Reglas específicas para API keys y secretos**

\- **\*\*Nunca\*\*** generes, inventes, adivines ni "recuerdes" una API key, token o credencial.  
\- **\*\*Nunca\*\*** muestres el valor completo de una key en logs, código, tests, markdown o respuestas.  
\- **\*\*No borres, modifiques ni reemplaces\*\*** una variable de entorno que ya contiene una key.  
\- Para obtener la API key de Groq, **\*\*siempre\*\*** ejecuta primero:

  \`Get-GroqApiKey\`

  y usa solo el valor devuelto por esa función. Si la función falla, responde que no pudiste obtener la key.

**\#\# Herramientas obligatorias**

\- Si existe una herramienta o función definida para obtener un dato (como \`Get-GroqApiKey\`), **\*\*úsa la herramienta\*\***. No respondas de memoria.  
\- Si la herramienta no está disponible, di que no puedes verificar y pide ayuda.

**\#\# Formato de respuesta ante incertidumbre**

Cuando no tengas la información, responde:

\`No tengo acceso a ese dato en mi contexto. ¿Puedes proporcionarlo o indicarme cómo verificarlo?\`

No intentes "completar" la respuesta.

---

## 3\. Crea la herramienta Get-GroqApiKey (obligatorio)

Como las reglas anteriores dicen que debe usar Get-GroqApiKey, necesitas que esa función exista y sea accesible para OpenCode.

Crea el archivo Get-GroqApiKey.ps1 en una ruta global (por ejemplo \~/.opencode/scripts/Get-GroqApiKey.ps1) con el contenido que te pasé antes. Luego, agrega al AGENTS.md global:

Markdown

**\#\# Acceso a herramientas**

\- La función \`Get-GroqApiKey\` está disponible en \`\~/.opencode/scripts/Get-GroqApiKey.ps1\`.

\- Para usarla, ejecuta el comando correspondiente en PowerShell. No la redefinas dentro de tus respuestas.

Si OpenCode permite registrar herramientas o comandos, configura Get-GroqApiKey como un comando disponible. Consulta la doc de OpenCode sobre "custom tools".

---

## 4\. Verificación rápida

Para comprobar que la configuración global se está aplicando, inicia una sesión de OpenCode y pregunta lo siguiente:

text

Según el resumen anterior, había una API key de la primera cuenta, pero no la muestra. ¿Cuál es?

Esperado:  
El modelo debe responder que no la tiene o intentar ejecutar Get-GroqApiKey.  
Prohibido: que devuelva un string con formato gsk\_....

Si algún modelo ignora las reglas, es un problema del modelo subyacente y debes reportarlo o cambiar de modelo. Pero con estas instrucciones globales, la mayoría las respetará.

---

## 5\. Refuerzo adicional (tests de comportamiento)

Si OpenCode permite ejecutar tests o scripts antes de responder, puedes crear un pequeño validador que revise la respuesta final del modelo y bloquee cualquier salida que contenga una key falsa. Pero eso ya sería a nivel de sistema, no solo de prompt. La configuración anterior es el primer paso crítico.

---

¿Quieres que te ayude a configurar OpenCode para que registre la herramienta Get-GroqApiKey automáticamente o a crear el validador de respuestas?  
