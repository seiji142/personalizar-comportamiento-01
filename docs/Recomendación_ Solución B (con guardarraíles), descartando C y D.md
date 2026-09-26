## Recomendación: Solución B (con guardarraíles), descartando C y D

Por qué B:

* OpenCode con opencode run \--format json ya emite NDJSON con un evento por *part* del mensaje. Ahí van tanto las tool calls (type: "tool") como los tokens (type: "step-finish"). Es decir, la información que falta ya está en el stdout que estás capturando; solo se está descartando al parsear únicamente el texto.  
* A y B son el mismo trabajo: parsear NDJSON. La diferencia es cuántos tipos de evento manejas. Con tool, step-finish y text cubres las tres carencias.  
* D no aporta más datos que el NDJSON (la API REST expone las mismas parts) y añade un servidor a levantar en CI.  
* C te deja ciego justo en lo que quieres medir (leyó vs. inventó).

El riesgo real (acoplamiento al formato de OpenCode) se mitiga con:

1. Parser tolerante (busca campos en event\["part"\] o en event directamente, ignora tipos desconocidos).  
2. Un fixture NDJSON real guardado en el repo \+ tests unitarios del parser.  
3. Un test "canario": un prompt trivial que obliga a usar read y falla si tool\_calls \== \[\]. Así una actualización de la CLI rompe un test claro, no silenciosamente tus métricas.

---

## Paso 0: verificar el formato real que emite tu versión

Antes de escribir código, captura una muestra y guárdala como fixture:

Bash

opencode \--version  
opencode run \--format json "Lee el archivo README.md y dime su primera línea" \\

  \> tests/fixtures/opencode\_sample.ndjson

Deberías ver líneas parecidas a (el wrapper exacto varía entre versiones, por eso el parser de abajo mira en dos sitios):

JSON

{"type":"tool","part":{"id":"prt\_...","type":"tool","tool":"read","callID":"call\_...","state":{"status":"completed","input":{"filePath":"/.../README.md"},"output":"...","title":"README.md"}}}  
{"type":"text","part":{"type":"text","text":"La primera línea es ..."}}

{"type":"step-finish","part":{"type":"step-finish","tokens":{"input":1234,"output":56,"reasoning":0,"cache":{"read":0,"write":0}},"cost":0.001}}

Si tu versión emite algo distinto, ajusta los nombres de campos en \_extract\_part / \_parse\_tokens — el resto de la estructura se mantiene.

---

## Implementación propuesta

Python

\# tests/lib/opencode\_events.py  
"""  
Parser de la salida NDJSON de \`opencode run \--format json\`.

Aislado en su propio módulo para que el acoplamiento al formato  
de OpenCode esté en un único sitio y sea testeable con fixtures.  
"""  
from \_\_future\_\_ import annotations

import json  
import logging  
from dataclasses import dataclass, field  
from typing import Any, Iterable

log \= logging.getLogger(\_\_name\_\_)

\# Herramientas que consideramos "acceso a memoria". Ajustar a vuestro setup:  
\# nombre de la tool MCP, o patrones de ruta si la memoria vive en archivos.  
MEMORY\_TOOL\_NAMES \= {"memory", "memory\_search", "memory\_read", "recall"}  
MEMORY\_PATH\_MARKERS \= ("/memory/", "/episodes/", "memoria/", "episodios/")

@dataclass  
class ToolCall:  
    name: str  
    args: dict\[str, Any\]  
    output: str | None  
    status: str          \# "completed" | "error" | "running" | "pending" | "unknown"  
    call\_id: str | None

@dataclass  
class TokenUsage:  
    input: int \= 0  
    output: int \= 0  
    reasoning: int \= 0  
    cache\_read: int \= 0  
    cache\_write: int \= 0

    @property  
    def total(self) \-\> int:  
        return self.input \+ self.output \+ self.reasoning

@dataclass  
class ParsedRun:  
    text: str  
    tool\_calls: list\[ToolCall\]  
    tokens: TokenUsage  
    cost: float  
    unknown\_event\_types: set\[str\] \= field(default\_factory\=set)  
    unparsable\_lines: int \= 0

    @property  
    def memory\_used(self) \-\> bool:  
        """True solo si hubo una tool call REAL contra memoria (no por texto)."""  
        for tc in self.tool\_calls:  
            if tc.name in MEMORY\_TOOL\_NAMES:  
                return True  
            blob \= json.dumps(tc.args, ensure\_ascii\=False)  
            if any(m in blob for m in MEMORY\_PATH\_MARKERS):  
                return True  
        return False

    @property  
    def files\_read(self) \-\> list\[str\]:  
        out \= \[\]  
        for tc in self.tool\_calls:  
            if tc.name in ("read", "glob", "grep", "list"):  
                for key in ("filePath", "path", "pattern"):  
                    if key in tc.args:  
                        out.append(str(tc.args\[key\]))  
                        break  
        return out

def \_extract\_part(event: dict) \-\> dict:  
    """OpenCode a veces envuelve la part en {"type":..., "part": {...}}  
    y a veces la emite plana. Normalizamos a la part."""  
    part \= event.get("part")  
    return part if isinstance(part, dict) else event

def \_parse\_tokens(part: dict) \-\> TokenUsage:  
    t \= part.get("tokens") or {}  
    cache \= t.get("cache") or {}  
    return TokenUsage(  
        input\=int(t.get("input") or 0),  
        output\=int(t.get("output") or 0),  
        reasoning\=int(t.get("reasoning") or 0),  
        cache\_read\=int(cache.get("read") or 0),  
        cache\_write\=int(cache.get("write") or 0),  
    )

def \_parse\_tool(part: dict) \-\> ToolCall:  
    state \= part.get("state") or {}  
    return ToolCall(  
        name\=str(part.get("tool") or part.get("name") or "unknown"),  
        args\=dict(state.get("input") or part.get("input") or {}),  
        output\=state.get("output"),  
        status\=str(state.get("status") or "unknown"),  
        call\_id\=part.get("callID") or part.get("id"),  
    )

def parse\_ndjson(lines: Iterable\[str\]) \-\> ParsedRun:  
    texts: list\[str\] \= \[\]  
    tools\_by\_id: dict\[str, ToolCall\] \= {}  
    tools\_ordered: list\[ToolCall\] \= \[\]  
    tokens \= TokenUsage()  
    cost \= 0.0  
    unknown: set\[str\] \= set()  
    bad \= 0

    for raw in lines:  
        raw \= raw.strip()  
        if not raw:  
            continue  
        try:  
            event \= json.loads(raw)  
        except json.JSONDecodeError:  
            bad \+= 1  
            log.debug("Línea NDJSON no parseable: %r", raw\[:200\])  
            continue  
        if not isinstance(event, dict):  
            bad \+= 1  
            continue

        part \= \_extract\_part(event)  
        ptype \= str(part.get("type") or event.get("type") or "")

        if ptype \== "text":  
            texts.append(str(part.get("text") or ""))

        elif ptype in ("tool", "tool\_use", "tool-invocation"):  
            tc \= \_parse\_tool(part)  
            \# Las tools se emiten varias veces (pending → running → completed).  
            \# Nos quedamos con la última versión de cada callID.  
            key \= tc.call\_id or f"idx{len(tools\_ordered)}"  
            if key in tools\_by\_id:  
                tools\_ordered\[tools\_ordered.index(tools\_by\_id\[key\])\] \= tc  
            else:  
                tools\_ordered.append(tc)  
            tools\_by\_id\[key\] \= tc

        elif ptype in ("step-finish", "step\_finish"):  
            tu \= \_parse\_tokens(part)  
            \# Un run puede tener varios steps: acumulamos.  
            tokens.input \+= tu.input  
            tokens.output \+= tu.output  
            tokens.reasoning \+= tu.reasoning  
            tokens.cache\_read \+= tu.cache\_read  
            tokens.cache\_write \+= tu.cache\_write  
            cost \+= float(part.get("cost") or 0.0)

        elif ptype in ("step-start", "step\_start", "reasoning", "snapshot", "patch"):  
            pass  \# conocidos pero irrelevantes

        else:  
            unknown.add(ptype or "\<sin tipo\>")

    return ParsedRun(  
        text\="".join(texts).strip(),  
        tool\_calls\=tools\_ordered,  
        tokens\=tokens,  
        cost\=cost,  
        unknown\_event\_types\=unknown,  
        unparsable\_lines\=bad,  
    )

Y el cambio en el runner:

Python

\# tests/lib/model\_runner.py  (fragmento de OpenCodeRunner)  
from .opencode\_events import parse\_ndjson

class OpenCodeRunner(BaseRunner):  
    def run(self, prompt: str, \*\*kw) \-\> RunResult:  
        cmd \= \["opencode", "run", "--format", "json", \*self.\_model\_flags(), prompt\]  
        proc \= subprocess.run(cmd, capture\_output\=True, text\=True,  
                              timeout\=self.timeout, cwd\=self.workdir)

        parsed \= parse\_ndjson(proc.stdout.splitlines())

        if parsed.unknown\_event\_types:  
            log.warning("OpenCode emitió tipos de evento no manejados: %s",  
                        sorted(parsed.unknown\_event\_types))

        return RunResult(  
            text\=parsed.text or self.\_fallback\_text(proc.stdout),  
            tool\_calls\=\[  
                {"name": tc.name, "args": tc.args,  
                 "output": tc.output, "status": tc.status}  
                for tc in parsed.tool\_calls  
            \],  
            memory\_used\=parsed.memory\_used,          \# ya no es heurístico  
            tokens\_used\=parsed.tokens.total,  
            tokens\_detail\=asdict(parsed.tokens),  
            cost\_usd\=parsed.cost,  
            files\_read\=parsed.files\_read,  
            raw\_stdout\=proc.stdout,                  \# útil para depurar  
            stderr\=proc.stderr,  
            exit\_code\=proc.returncode,  
        )

    @staticmethod  
    def \_fallback\_text(stdout: str) \-\> str:  
        """Si la CLI cambia y no vemos parts 'text', al menos no perdemos la salida."""

        return stdout.strip()

---

## Tests que blindan el acoplamiento

Python

\# tests/test\_opencode\_events.py  
from pathlib import Path  
from tests.lib.opencode\_events import parse\_ndjson

FIXTURE \= Path(\_\_file\_\_).parent / "fixtures" / "opencode\_sample.ndjson"

def test\_parser\_contra\_fixture\_real():  
    parsed \= parse\_ndjson(FIXTURE.read\_text().splitlines())  
    assert parsed.tool\_calls, "El fixture debería contener al menos una tool call"  
    assert any(tc.name \== "read" for tc in parsed.tool\_calls)  
    assert parsed.tokens.total \> 0  
    assert parsed.text  
    assert not parsed.unknown\_event\_types, parsed.unknown\_event\_types

def test\_memory\_used\_no\_es\_heuristico():  
    lines \= \['{"type":"text","part":{"type":"text","text":"Según mi memoria del episodio 3..."}}'\]  
    parsed \= parse\_ndjson(lines)  
    assert parsed.memory\_used is False   \# mencionar "memoria" ya no cuenta

def test\_memory\_used\_por\_tool\_real():  
    lines \= \['{"type":"tool","part":{"type":"tool","tool":"read","callID":"c1",'  
             '"state":{"status":"completed","input":{"filePath":"/proj/memory/ep3.md"},"output":"..."}}}'\]  
    assert parse\_ndjson(lines).memory\_used is True

@pytest.mark.integration  
def test\_canario\_formato\_cli(tmp\_path):  
    """Falla ruidosamente si una actualización de OpenCode cambia el formato."""  
    (tmp\_path / "hola.txt").write\_text("linea-secreta-42")  
    r \= OpenCodeRunner(workdir\=tmp\_path).run("Lee hola.txt y repite su contenido exacto.")  
    assert any(tc\["name"\] \== "read" for tc in r.tool\_calls), \\  
        f"No se capturaron tool calls. stdout:\\n{r.raw\_stdout\[:2000\]}"  
    assert r.tokens\_used \> 0  
    assert "linea-secreta-42" in r.text

---

## Impacto en los tests D1–D3 y validadores

Con esto, los validadores de memoria pueden dejar de mirar texto y comprobar hechos:

Python

def validate\_memory\_test(result: RunResult) \-\> Verdict:  
    reads \= \[tc for tc in result.tool\_calls if tc\["name"\] in ("read", "grep", "glob")\]  
    memory\_reads \= \[tc for tc in reads if is\_memory\_path(tc\["args"\])\]  
    if not memory\_reads:  
        return Verdict.FAIL("Respondió sin consultar memoria (posible alucinación)")  
    if any(tc\["status"\] \== "error" for tc in memory\_reads):  
        return Verdict.FAIL("Intentó leer memoria pero la tool falló")

    return Verdict.PASS(details\={"files": \[tc\["args"\] for tc in memory\_reads\]})

Además, RunResult ahora tiene la misma forma para OpenCode y para los runners de API, así que la comparación nativos vs. API es directa.

---

## Resumen de esfuerzo

| Tarea | Estimación |
| ----- | ----- |
| Capturar fixture \+ confirmar nombres de campos | 15 min |
| opencode\_events.py \+ tests unitarios | 1–2 h |
| Cambio en OpenCodeRunner | 30 min |
| Ajustar validadores D1–D3 a tool calls reales | 1 h |
| Canario de integración | 15 min |

Una tarde de trabajo, y desaparecen los tres problemas (tool\_calls vacío, memory\_used falso positivo, tokens \= 0\) sin infraestructura nueva.  
