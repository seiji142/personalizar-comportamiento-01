Sí. Aquí tienes la implementación completa, organizada en 4 archivos. Está diseñada para que modelos nativos (OpenCode) y modelos API (Groq) pasen por la misma interfaz, con evidencia de tool calls y tests D1–D4 actualizados.

## Estructura

text

tests\_advanced/  
├── config.py              \# Configuración, capacidades, system prompt  
├── mcp\_client.py          \# Cliente MCP stdio (habla con mcp\_bridge.py)  
├── runners.py             \# ModelRunner: OpenCodeRunner \+ GroqRunner  
└── run\_advanced\_tests.py  \# Tests D1-D4 \+ validación \+ reporte

---

## 1\. config.py

Python

"""Configuración central para los tests avanzados."""  
import os

\# ── Rutas y comandos ──────────────────────────────────────────────  
OPENCODE\_CLI \= os.environ.get("OPENCODE\_CLI", "opencode-cli")  
OPENCODE\_SERVER\_PORT \= int(os.environ.get("OPENCODE\_PORT", "4096"))

\# Mismo comando que usa opencode.json para el bridge  
MCP\_BRIDGE\_COMMAND \= \["python", "mcp\_bridge.py"\]

GROQ\_API\_KEY \= os.environ.get("GROQ\_API\_KEY", "")

\# ── Límites ───────────────────────────────────────────────────────  
QUERY\_TIMEOUT \= 120          \# segundos por consulta  
MAX\_TOOL\_ITERATIONS \= 5      \# máx. ciclos de tool calling por consulta  
MCP\_INIT\_TIMEOUT \= 30        \# segundos para inicializar el bridge

\# ── Capacidades por modelo ────────────────────────────────────────  
\# backend: "opencode" | "groq"  
\# tool\_calling: soporta function calling nativo  
\# fallback\_prefetch: si no soporta tools, inyectar memoria en el prompt  
MODEL\_CAPABILITIES \= {  
    "opencode/mimo-v2.5-free": {  
        "backend": "opencode",  
        "tool\_calling": True,  
        "fallback\_prefetch": False,  
    },  
    "openai/gpt-oss-20b": {  
        "backend": "groq",  
        "tool\_calling": True,  
        "fallback\_prefetch": False,  
    },  
    "llama-3.1-8b-instant": {  
        "backend": "groq",  
        "tool\_calling": True,  
        "fallback\_prefetch": False,  
    },  
    \# Ejemplo de modelo sin tools \-\> usa prefetch de memoria  
    \# "algun-modelo-basico": {  
    \#     "backend": "groq",  
    \#     "tool\_calling": False,  
    \#     "fallback\_prefetch": True,  
    \# },  
}

\# ── Contrato de memoria (system prompt) ───────────────────────────  
SYSTEM\_PROMPT \= """\\  
Eres un asistente con acceso a un sistema de memoria persistente (brain-ai).

Reglas obligatorias:  
1\. Para preguntas sobre decisiones previas, episodios, preferencias o  
   contexto histórico, DEBES usar la herramienta brain\_ai\_memory\_search  
   antes de responder.  
2\. No inventes recuerdos. Si la herramienta no devuelve resultados,  
   di claramente que no encontraste información en la memoria.  
3\. Cuando la pregunta requiera memoria, basa tu respuesta únicamente  
   en los resultados recuperados.  
4\. Responde en español.  
"""

---

## 2\. mcp\_client.py

Cliente MCP mínimo por stdio JSON-RPC 2.0 (el mismo transporte que usa OpenCode con tu bridge):

Python

"""Cliente MCP stdio mínimo: initialize, tools/list, tools/call."""  
import json  
import re  
import subprocess  
import threading  
import queue  
import time

from config import MCP\_BRIDGE\_COMMAND, MCP\_INIT\_TIMEOUT

class MCPError(Exception):  
    pass

class MCPStdioClient:  
    """Habla JSON-RPC 2.0 (newline-delimited) con un servidor MCP por stdio."""

    def \_\_init\_\_(self, command\=None):  
        self.command \= command or MCP\_BRIDGE\_COMMAND  
        self.proc \= None  
        self.\_id \= 0  
        self.\_responses \= queue.Queue()  
        self.\_reader \= None

    \# ── Ciclo de vida ─────────────────────────────────────────────  
    def start(self):  
        self.proc \= subprocess.Popen(  
            self.command,  
            stdin\=subprocess.PIPE,  
            stdout\=subprocess.PIPE,  
            stderr\=subprocess.DEVNULL,  
            text\=True,  
            bufsize\=1,  
        )  
        self.\_reader \= threading.Thread(target\=self.\_read\_loop, daemon\=True)  
        self.\_reader.start()  
        self.\_initialize()  
        return self

    def close(self):  
        if self.proc:  
            try:  
                self.proc.terminate()  
                self.proc.wait(timeout\=5)  
            except Exception:  
                self.proc.kill()  
            self.proc \= None

    def \_\_enter\_\_(self):  
        return self.start()

    def \_\_exit\_\_(self, \*exc):  
        self.close()

    \# ── Transporte ────────────────────────────────────────────────  
    def \_read\_loop(self):  
        for line in self.proc.stdout:  
            line \= line.strip()  
            if not line:  
                continue  
            try:  
                msg \= json.loads(line)  
            except json.JSONDecodeError:  
                continue  
            \# Ignoramos notificaciones del servidor (sin "id")  
            if "id" in msg:  
                self.\_responses.put(msg)

    def \_send(self, method, params\=None, notification\=False):  
        msg \= {"jsonrpc": "2.0", "method": method}  
        if params is not None:  
            msg\["params"\] \= params  
        if not notification:  
            self.\_id \+= 1  
            msg\["id"\] \= self.\_id  
        self.proc.stdin.write(json.dumps(msg) \+ "\\n")  
        self.proc.stdin.flush()  
        if notification:  
            return None  
        return self.\_wait\_response(self.\_id)

    def \_wait\_response(self, req\_id, timeout\=MCP\_INIT\_TIMEOUT):  
        deadline \= time.time() \+ timeout  
        while time.time() \< deadline:  
            try:  
                msg \= self.\_responses.get(timeout\=1)  
            except queue.Empty:  
                continue  
            if msg.get("id") \== req\_id:  
                if "error" in msg:  
                    raise MCPError(msg\["error"\])  
                return msg.get("result")  
        raise MCPError(f"Timeout esperando respuesta a request {req\_id}")

    \# ── Protocolo MCP ─────────────────────────────────────────────  
    def \_initialize(self):  
        self.\_send("initialize", {  
            "protocolVersion": "2024-11-05",  
            "capabilities": {},  
            "clientInfo": {"name": "advanced-tests", "version": "1.0"},  
        })  
        self.\_send("notifications/initialized", {}, notification\=True)

    def list\_tools(self):  
        result \= self.\_send("tools/list", {})  
        return result.get("tools", \[\])

    def call\_tool(self, name, arguments):  
        result \= self.\_send("tools/call", {  
            "name": name,  
            "arguments": arguments,  
        })  
        \# El contenido MCP viene como lista de bloques; extraemos texto  
        blocks \= result.get("content", \[\])  
        texts \= \[b.get("text", "") for b in blocks if b.get("type") \== "text"\]  
        return "\\n".join(texts) if texts else json.dumps(result)

\# ── Adaptación MCP → OpenAI tools ─────────────────────────────────  
def sanitize\_tool\_name(name):  
    """Groq/OpenAI solo aceptan \[a-zA-Z0-9\_-\] en nombres de tools."""  
    return re.sub(r"\[^a-zA-Z0-9\_-\]", "\_", name)

def mcp\_tools\_to\_openai(mcp\_tools):  
    """  
    Convierte tools MCP al formato OpenAI/Groq.  
    Devuelve (tools\_openai, name\_map) donde name\_map traduce  
    nombre\_api \-\> nombre\_mcp real.  
    """  
    tools \= \[\]  
    name\_map \= {}  
    for t in mcp\_tools:  
        api\_name \= sanitize\_tool\_name(t\["name"\])  
        name\_map\[api\_name\] \= t\["name"\]  
        tools.append({  
            "type": "function",  
            "function": {  
                "name": api\_name,  
                "description": t.get("description", ""),  
                "parameters": t.get("inputSchema", {"type": "object", "properties": {}}),  
            },  
        })

    return tools, name\_map

---

## 3\. runners.py

Python

"""Runners unificados: OpenCode (nativo) y Groq (API \+ tool loop propio)."""  
import json  
import subprocess  
from dataclasses import dataclass, field, asdict

from config import (  
    OPENCODE\_CLI, OPENCODE\_SERVER\_PORT, GROQ\_API\_KEY,  
    QUERY\_TIMEOUT, MAX\_TOOL\_ITERATIONS, SYSTEM\_PROMPT,  
)  
from mcp\_client import MCPStdioClient, mcp\_tools\_to\_openai

\# ── Resultado estructurado común ──────────────────────────────────  
@dataclass  
class QueryResult:  
    text: str \= ""  
    tool\_calls: list \= field(default\_factory\=list)  \# \[{name, arguments, success, result}\]  
    memory\_used: bool \= False  
    error: str \= ""  
    raw: dict \= field(default\_factory\=dict)

    def to\_dict(self):  
        d \= asdict(self)  
        d.pop("raw", None)  \# el raw puede ser enorme; fuera del reporte  
        return d

def \_mark\_memory\_used(result: QueryResult):  
    result.memory\_used \= any(  
        "memory" in tc\["name"\] and tc\["success"\]  
        for tc in result.tool\_calls  
    )

\# ── Base ──────────────────────────────────────────────────────────  
class ModelRunner:  
    def query(self, prompt: str) \-\> QueryResult:  
        raise NotImplementedError

    def close(self):  
        pass

\# ── OpenCode (modelos nativos) ────────────────────────────────────  
class OpenCodeRunner(ModelRunner):  
    """  
    Usa opencode-cli \--attach. El server OpenCode ya tiene el MCP  
    configurado en opencode.json, así que el tool loop lo hace OpenCode.  
    Aquí solo parseamos la salida para extraer evidencia de tool calls.  
    """

    def \_\_init\_\_(self, model\_id, server\_port\=OPENCODE\_SERVER\_PORT):  
        self.model\_id \= model\_id  
        self.server\_port \= server\_port

    def query(self, prompt) \-\> QueryResult:  
        cmd \= \[  
            OPENCODE\_CLI, "run",  
            "--attach", f"http://127.0.0.1:{self.server\_port}",  
            "--model", self.model\_id,  
            "--format", "json",  
            prompt,  
        \]  
        try:  
            proc \= subprocess.run(  
                cmd, capture\_output\=True, text\=True, timeout\=QUERY\_TIMEOUT  
            )  
        except subprocess.TimeoutExpired:  
            return QueryResult(error\=f"Timeout ({QUERY\_TIMEOUT}s)")

        if proc.returncode \!= 0:  
            return QueryResult(error\=f"opencode-cli exit {proc.returncode}: {proc.stderr\[:500\]}")

        result \= QueryResult(raw\={"stdout": proc.stdout})  
        self.\_parse\_output(proc.stdout, result)  
        \_mark\_memory\_used(result)  
        return result

    def \_parse\_output(self, stdout, result: QueryResult):  
        """  
        Parseo defensivo del JSON de opencode. Puede ser un objeto único  
        o líneas JSON (streaming). AJUSTAR según tu versión de opencode-cli.  
        """  
        events \= \[\]  
        try:  
            events \= \[json.loads(stdout)\]  
        except json.JSONDecodeError:  
            for line in stdout.splitlines():  
                line \= line.strip()  
                if not line:  
                    continue  
                try:  
                    events.append(json.loads(line))  
                except json.JSONDecodeError:  
                    continue

        texts \= \[\]  
        for ev in events:  
            self.\_extract\_from\_event(ev, texts, result)  
        result.text \= "\\n".join(t for t in texts if t).strip() or stdout.strip()

    def \_extract\_from\_event(self, ev, texts, result: QueryResult):  
        if not isinstance(ev, dict):  
            return  
        \# Bloques tipo {type: "text"|"tool"|"tool\_use", ...} y variantes  
        ev\_type \= ev.get("type", "")  
        if ev\_type \== "text" and ev.get("text"):  
            texts.append(ev\["text"\])  
        elif ev\_type in ("tool", "tool\_use", "tool\_call"):  
            result.tool\_calls.append({  
                "name": ev.get("tool") or ev.get("name", ""),  
                "arguments": ev.get("input") or ev.get("arguments", {}),  
                "success": ev.get("state", {}).get("status", "completed") \!= "error"  
                           if isinstance(ev.get("state"), dict) else True,  
                "result": str(ev.get("output", ""))\[:500\],  
            })  
        \# Recorrer estructuras anidadas comunes: parts / messages / content  
        for key in ("parts", "messages", "content"):  
            child \= ev.get(key)  
            if isinstance(child, list):  
                for c in child:  
                    self.\_extract\_from\_event(c, texts, result)  
        \# Campos de texto directos  
        for key in ("text", "response", "output"):  
            if key \!= "text" and isinstance(ev.get(key), str):  
                texts.append(ev\[key\])

\# ── Groq (API directa \+ tool loop propio via MCP) ─────────────────  
class GroqRunner(ModelRunner):  
    """  
    Implementa el ciclo de function calling manualmente y delega la  
    ejecución de tools al bridge MCP (mismo que usa OpenCode).  
    """

    def \_\_init\_\_(self, model\_id, tool\_calling\=True, fallback\_prefetch\=False):  
        from groq import Groq  \# pip install groq  
        if not GROQ\_API\_KEY:  
            raise RuntimeError("Falta GROQ\_API\_KEY en el entorno")  
        self.client \= Groq(api\_key\=GROQ\_API\_KEY)  
        self.model\_id \= model\_id  
        self.tool\_calling \= tool\_calling  
        self.fallback\_prefetch \= fallback\_prefetch

        \# Arrancamos el bridge MCP y descubrimos tools dinámicamente  
        self.mcp \= MCPStdioClient().start()  
        mcp\_tools \= self.mcp.list\_tools()  
        self.tools, self.name\_map \= mcp\_tools\_to\_openai(mcp\_tools)  
        \# Detectamos la tool de búsqueda de memoria para el fallback  
        self.memory\_tool\_mcp \= next(  
            (t\["name"\] for t in mcp\_tools if "memory" in t\["name"\] and "search" in t\["name"\]),  
            None,  
        )

    def close(self):  
        self.mcp.close()

    def query(self, prompt) \-\> QueryResult:  
        if self.tool\_calling:  
            return self.\_query\_with\_tools(prompt)  
        if self.fallback\_prefetch:  
            return self.\_query\_with\_prefetch(prompt)  
        return QueryResult(error\="Modelo sin tool\_calling y sin fallback configurado")

    \# ── Modo principal: function calling ──────────────────────────  
    def \_query\_with\_tools(self, prompt) \-\> QueryResult:  
        messages \= \[  
            {"role": "system", "content": SYSTEM\_PROMPT},  
            {"role": "user", "content": prompt},  
        \]  
        result \= QueryResult()

        for \_ in range(MAX\_TOOL\_ITERATIONS):  
            try:  
                resp \= self.client.chat.completions.create(  
                    model\=self.model\_id,  
                    messages\=messages,  
                    tools\=self.tools,  
                    tool\_choice\="auto",  
                    temperature\=0.1,  
                )  
            except Exception as e:  
                result.error \= f"Groq API error: {e}"  
                return result

            msg \= resp.choices\[0\].message

            \# Sin tool calls \-\> respuesta final  
            if not msg.tool\_calls:  
                result.text \= msg.content or ""  
                \_mark\_memory\_used(result)  
                return result

            \# Ejecutar cada tool call contra MCP  
            messages.append({  
                "role": "assistant",  
                "content": msg.content,  
                "tool\_calls": \[  
                    {  
                        "id": tc.id,  
                        "type": "function",  
                        "function": {  
                            "name": tc.function.name,  
                            "arguments": tc.function.arguments,  
                        },  
                    }  
                    for tc in msg.tool\_calls  
                \],  
            })

            for tc in msg.tool\_calls:  
                api\_name \= tc.function.name  
                mcp\_name \= self.name\_map.get(api\_name, api\_name)  
                try:  
                    args \= json.loads(tc.function.arguments or "{}")  
                except json.JSONDecodeError:  
                    args \= {}

                try:  
                    tool\_result \= self.mcp.call\_tool(mcp\_name, args)  
                    success \= True  
                except Exception as e:  
                    tool\_result \= f"ERROR: {e}"  
                    success \= False

                result.tool\_calls.append({  
                    "name": api\_name,  
                    "arguments": args,  
                    "success": success,  
                    "result": str(tool\_result)\[:500\],  
                })  
                messages.append({  
                    "role": "tool",  
                    "tool\_call\_id": tc.id,  
                    "content": str(tool\_result),  
                })

        result.error \= f"Superado MAX\_TOOL\_ITERATIONS ({MAX\_TOOL\_ITERATIONS})"  
        \_mark\_memory\_used(result)  
        return result

    \# ── Fallback: prefetch de memoria en el prompt ─────────────────  
    def \_query\_with\_prefetch(self, prompt) \-\> QueryResult:  
        result \= QueryResult()  
        context \= "(sin resultados)"  
        if self.memory\_tool\_mcp:  
            try:  
                context \= self.mcp.call\_tool(self.memory\_tool\_mcp, {"query": prompt})  
                result.tool\_calls.append({  
                    "name": self.memory\_tool\_mcp,  
                    "arguments": {"query": prompt},  
                    "success": True,  
                    "result": str(context)\[:500\],  
                })  
            except Exception as e:  
                result.tool\_calls.append({  
                    "name": self.memory\_tool\_mcp,  
                    "arguments": {"query": prompt},  
                    "success": False,  
                    "result": str(e),  
                })

        augmented \= (  
            f"Contexto recuperado de la memoria brain-ai:\\n{context}\\n\\n"  
            f"Pregunta: {prompt}\\n\\n"  
            "Responde usando exclusivamente el contexto anterior cuando sea "  
            "relevante. Si el contexto no contiene la respuesta, dilo."  
        )  
        try:  
            resp \= self.client.chat.completions.create(  
                model\=self.model\_id,  
                messages\=\[  
                    {"role": "system", "content": SYSTEM\_PROMPT},  
                    {"role": "user", "content": augmented},  
                \],  
                temperature\=0.1,  
            )  
            result.text \= resp.choices\[0\].message.content or ""  
        except Exception as e:  
            result.error \= f"Groq API error: {e}"

        \_mark\_memory\_used(result)  
        return result

\# ── Factory ───────────────────────────────────────────────────────  
def build\_runner(model\_id, capabilities) \-\> ModelRunner:  
    backend \= capabilities\["backend"\]  
    if backend \== "opencode":  
        return OpenCodeRunner(model\_id)  
    if backend \== "groq":  
        return GroqRunner(  
            model\_id,  
            tool\_calling\=capabilities.get("tool\_calling", True),  
            fallback\_prefetch\=capabilities.get("fallback\_prefetch", False),  
        )  
    raise ValueError(f"Backend desconocido: {backend}")

---

## 4\. run\_advanced\_tests.py

Python

\#\!/usr/bin/env python3  
"""Tests avanzados D1-D4 con validación de uso real de memoria (MCP)."""  
import json  
import sys  
import time  
from datetime import datetime

from config import MODEL\_CAPABILITIES  
from runners import build\_runner, QueryResult

\# ── Definición de tests (contrato actual, no legacy) ──────────────  
TESTS \= \[  
    {  
        "id": "D1",  
        "name": "Recuperación de episodios",  
        "prompt": "¿Qué episodios recientes hay registrados en la memoria "  
                  "sobre el proyecto brain-ai? Resume los más relevantes.",  
        "requires\_memory": True,  
        "keywords\_any": \["episodio", "memoria", "registrado"\],  
    },  
    {  
        "id": "D2",  
        "name": "Recuperación de decisiones",  
        "prompt": "¿Qué decisiones técnicas se han guardado en la memoria? "  
                  "Menciona al menos una con su justificación.",  
        "requires\_memory": True,  
        "keywords\_any": \["decisión", "decisiones", "se decidió", "memoria"\],  
    },  
    {  
        "id": "D3",  
        "name": "Recall de decisión específica (actualizado)",  
        \# Antes esperaba "PostgreSQL" hardcodeado \-\> ahora valida la  
        \# capacidad: consultar memoria y responder basándose en ella.  
        "prompt": "Consulta la memoria: ¿qué se decidió sobre el "  
                  "almacenamiento/persistencia del sistema? Si no hay nada "  
                  "registrado, dilo explícitamente.",  
        "requires\_memory": True,  
        "keywords\_any": \["decidió", "decisión", "almacenamiento",  
                         "persistencia", "no encontr", "no hay"\],  
    },  
    {  
        "id": "D4",  
        "name": "Manejo de memoria inexistente (actualizado)",  
        \# Antes esperaba "Por definir" \-\> ahora valida que NO invente:  
        \# ante un tema inexistente debe reconocer que no hay resultados.  
        "prompt": "Busca en la memoria qué se decidió sobre la integración "  
                  "con el satélite meteorológico ZX-9000.",  
        "requires\_memory": True,  
        "keywords\_any": \["no encontr", "no hay", "sin resultados",  
                         "no existe", "no está registrad", "no aparece"\],  
    },  
\]

\# ── Validación ────────────────────────────────────────────────────  
def validate(test, result: QueryResult):  
    """Devuelve (estado, razón). Estados: PASS | FAIL."""  
    if result.error:  
        return "FAIL", f"Error: {result.error}"

    if not result.text.strip():  
        return "FAIL", "Respuesta vacía"

    \# Evidencia real de uso de memoria (no solo palabras en el texto)  
    if test\["requires\_memory"\] and not result.memory\_used:  
        return "FAIL", "No hay evidencia de llamada exitosa a memory\_search"

    text \= result.text.lower()  
    if test.get("keywords\_any"):  
        if not any(k in text for k in test\["keywords\_any"\]):  
            return "FAIL", f"No menciona ninguno de: {test\['keywords\_any'\]}"

    hits \= \[k for k in test.get("keywords\_any", \[\]) if k in text\]  
    tools\_used \= sorted({tc\["name"\] for tc in result.tool\_calls})  
    return "PASS", f"memoria=OK, tools={tools\_used}, keywords={hits}"

\# ── Ejecución ─────────────────────────────────────────────────────  
def run\_model(model\_id, capabilities):  
    print(f"\\n{'='\*70}")  
    print(f"Modelo: {model\_id}  (backend={capabilities\['backend'\]}, "  
          f"tool\_calling={capabilities.get('tool\_calling')})")  
    print(f"{'='\*70}")

    \# Modelo sin herramientas ni fallback \-\> SKIP, no FAIL  
    if not capabilities.get("tool\_calling") and not capabilities.get("fallback\_prefetch"):  
        return \[  
            {"test": t\["id"\], "status": "SKIP",  
             "reason": "Backend sin tool calling ni fallback configurado"}  
            for t in TESTS  
        \]

    try:  
        runner \= build\_runner(model\_id, capabilities)  
    except Exception as e:  
        return \[  
            {"test": t\["id"\], "status": "SKIP", "reason": f"Runner no disponible: {e}"}  
            for t in TESTS  
        \]

    results \= \[\]  
    try:  
        for test in TESTS:  
            print(f"\\n\[{test\['id'\]}\] {test\['name'\]}...")  
            t0 \= time.time()  
            qr \= runner.query(test\["prompt"\])  
            elapsed \= time.time() \- t0

            status, reason \= validate(test, qr)  
            print(f"  → {status} ({elapsed:.1f}s): {reason}")  
            if qr.tool\_calls:  
                for tc in qr.tool\_calls:  
                    ok \= "✓" if tc\["success"\] else "✗"  
                    print(f"    {ok} tool: {tc\['name'\]}({json.dumps(tc\['arguments'\], ensure\_ascii\=False)\[:80\]})")

            results.append({  
                "test": test\["id"\],  
                "status": status,  
                "reason": reason,  
                "elapsed\_s": round(elapsed, 1),  
                "detail": qr.to\_dict(),  
            })  
    finally:  
        runner.close()

    return results

def print\_report(all\_results):  
    print(f"\\n\\n{'='\*70}")  
    print("REPORTE FINAL")  
    print(f"{'='\*70}")  
    print(f"{'Modelo':\<32} {'Test':\<5} {'Estado':\<7} Razón")  
    print("-" \* 70)  
    for model\_id, results in all\_results.items():  
        for r in results:  
            print(f"{model\_id:\<32} {r\['test'\]:\<5} {r\['status'\]:\<7} {r\['reason'\]\[:60\]}")

    \# Resumen  
    total \= sum(len(r) for r in all\_results.values())  
    passed \= sum(1 for rs in all\_results.values() for r in rs if r\["status"\] \== "PASS")  
    skipped \= sum(1 for rs in all\_results.values() for r in rs if r\["status"\] \== "SKIP")  
    failed \= total \- passed \- skipped  
    print("-" \* 70)  
    print(f"Total: {total}  PASS: {passed}  FAIL: {failed}  SKIP: {skipped}")  
    return failed

def main():  
    \# Permite filtrar modelos por argumento: python run\_advanced\_tests.py mimo  
    model\_filter \= sys.argv\[1\] if len(sys.argv) \> 1 else ""

    all\_results \= {}  
    for model\_id, caps in MODEL\_CAPABILITIES.items():  
        if model\_filter and model\_filter not in model\_id:  
            continue  
        all\_results\[model\_id\] \= run\_model(model\_id, caps)

    failed \= print\_report(all\_results)

    \# Guardar JSON con trazabilidad completa  
    report\_file \= f"report\_{datetime.now():%Y%m%d\_%H%M%S}.json"  
    with open(report\_file, "w", encoding\="utf-8") as f:  
        json.dump(all\_results, f, ensure\_ascii\=False, indent\=2)  
    print(f"\\nReporte guardado en: {report\_file}")

    sys.exit(1 if failed else 0)

if \_\_name\_\_ \== "\_\_main\_\_":  
    main()

---

## Cómo usarlo

Bash

pip install groq

export GROQ\_API\_KEY\="tu\_key"  
export OPENCODE\_PORT\=4096        \# puerto de tu server OpenCode

\# Todos los modelos  
python run\_advanced\_tests.py

\# Solo un modelo  
python run\_advanced\_tests.py mimo  
python run\_advanced\_tests.py gpt-oss

---

## Puntos que debes ajustar a tu entorno

1. MCP\_BRIDGE\_COMMAND en config.py: debe ser exactamente el mismo comando que tienes en opencode.json (\["python", "mcp\_bridge.py"\]), incluyendo el directorio de trabajo si aplica. Si el bridge necesita cwd, añade cwd=... en el subprocess.Popen de mcp\_client.py.  
2. OpenCodeRunner.\_parse\_output: el formato JSON de opencode-cli \--format json varía entre versiones. El parseo es defensivo (busca parts, messages, content, tool\_calls), pero ejecuta una consulta manual, mira el JSON real y ajusta la extracción si los tool calls vienen en otro campo. Si OpenCode no reporta tool calls en su salida, tienes dos opciones: relajar la validación para backend opencode (confiar en keywords) o consultar el endpoint de sesión del server para leer los mensajes con tool calls.  
3. Nombre de la tool de memoria: el código descubre las tools dinámicamente con tools/list, así que si tu bridge expone brain-ai\_memory\_search, la sanitización la convierte automáticamente a brain\_ai\_memory\_search para Groq y la traduce de vuelta al ejecutar. No necesitas hardcodear nada.  
4. D4: asume que "satélite ZX-9000" no existe en tu memoria. Si tu memoria devuelve resultados con búsquedas amplias, cambia el tema por algo garantizado como inexistente.

---

## Qué gana esta implementación frente a la actual

| Aspecto | Antes | Ahora |
| ----- | ----- | ----- |
| Groq \+ MCP | ERROR 400 | Tool loop propio vía bridge MCP |
| Validación D1/D2 | Solo keywords en texto | Evidencia real de tool call exitoso |
| D3/D4 | Legacy (PostgreSQL, "Por definir") | Validan capacidad funcional |
| Modelos sin tools | FAIL/ERROR | SKIP explícito o fallback con prefetch |
| Trazabilidad | Texto plano | JSON con tool\_calls, argumentos, resultados y tiempos |
| Tools | Implícitas (OpenCode) | Descubiertas dinámicamente con tools/list |

Si quieres, en el siguiente paso puedo ayudarte a ajustar el parser de OpenCodeRunner con una muestra real de la salida de tu opencode-cli \--format json, que es la parte más dependiente de tu versión concreta.  
