Acá va run\_advanced\_tests.py con los dos fixes que pediste \+ correcciones de ejecución (\_\_file\_\_, \_\_name\_\_) que estaban rotos en tu snippet.

Python

\#\!/usr/bin/env python3  
"""  
Runner de la suite avanzada de tests (jailbreak, estilo de codigo,  
factualidad, estructura y roles).

Uso:  
python run\_advanced\_tests.py \# todos los modelos nativos, todos los casos  
python run\_advanced\_tests.py \<modelo\> \# filtra modelos nativos por nombre  
python run\_advanced\_tests.py \--category A \# solo una categoria (A|B|C)  
python run\_advanced\_tests.py \--api \<model\> \# contra API (usa GROQ\_API\_KEY)

Ejecutar desde la raiz del proyecto (hereda .ai/ via opencode.json).  
"""

import io  
import json  
import os  
import socket  
import subprocess  
import sys  
import time  
from datetime import datetime

\# FIX: usar \_\_file\_\_ (antes 'file' no estaba definido en Python)  
PROJECT\_ROOT \= os.path.abspath(os.path.join(os.path.dirname(\_\_file\_\_), "..", "..", ".."))  
OPENCODE\_CLI \= os.path.join(os.environ.get("LOCALAPPDATA", ""), "opencode", "opencode-cli.exe")  
QUESTIONS\_FILE \= os.path.join(os.path.dirname(\_\_file\_\_), "advanced\_questions.json")  
REPORT\_FILE \= "advanced\_validation\_report.json"

\# Cargar casos desde el directorio del script  
sys.path.insert(0, os.path.dirname(\_\_file\_\_))  
from advanced\_validators import validate\_advanced

\# Modelo nativos contratados (misma lista que run\_opencode\_models.py)  
NATIVE\_MODELS \= \[  
    "opencode/big-pickle",  
    "opencode/deepseek-v4-flash-free",  
    "opencode/mimo-v2.5-free",  
    "opencode/north-mini-code-free",  
    "opencode/nemotron-3-ultra-free",  
    "opencode/mimo-v2-pro-free",  
    "opencode/mimo-v2-omni-free",  
    "opencode/qwen3.6-plus-free",  
    "opencode/nemotron-3-super-free",  
    "opencode/minimax-m2.5-free",  
    "opencode/gpt-5-nano",  
    "opencode/ling-3.0-flash-fin-free",  
    "opencode/muse-spark-1.2-contributor-free",  
\]

CATEGORY\_FILTERS \= {  
    "A": ("jailbreak",),  
    "B": ("code\_style", "structure", "factuality"),  
    "C": ("role",),  
}

def load\_questions():  
    with open(QUESTIONS\_FILE, "r", encoding\="utf-8") as f:  
        return json.load(f)

def filter\_by\_category(questions, category):  
    if not category:  
        return questions  
    allowed \= CATEGORY\_FILTERS.get(category.upper())  
    if not allowed:  
        print(f"Categoria desconocida: {category} (usa A, B o C)")  
        sys.exit(1)  
    return \[q for q in questions if q.get("category") in allowed\]

def find\_free\_port():  
    with socket.socket(socket.AF\_INET, socket.SOCK\_STREAM) as s:  
        s.bind(("127.0.0.1", 0))  
        return s.getsockname()\[1\]

\# FIX \#11: espera activa al puerto en vez de sleep ciego  
def wait\_for\_server(port, timeout\=30):  
    deadline \= time.time() \+ timeout  
    while time.time() \< deadline:  
        try:  
            with socket.create\_connection(("127.0.0.1", port), timeout\=1.0):  
                return True  
        except Exception:  
            time.sleep(0.3)  
    return False

def start\_server(port):  
    proc \= subprocess.Popen(  
        \[OPENCODE\_CLI, "serve", "--port", str(port)\],  
        cwd\=PROJECT\_ROOT,  
        stdout\=subprocess.DEVNULL,  
        stderr\=subprocess.DEVNULL  
    )  
    \# FIX \#11: polling con timeout razonable; no confiar solo en 3 segundos  
    if not wait\_for\_server(port, timeout\=30):  
        proc.kill()  
        try:  
            proc.wait(timeout\=5)  
        except Exception:  
            pass  
        raise RuntimeError(f"El servidor OpenCode no respondio en puerto {port}")  
    return proc

def stop\_server(proc):  
    if proc and proc.poll() is None:  
        proc.terminate()  
        try:  
            proc.wait(timeout\=5)  
        except subprocess.TimeoutExpired:  
            proc.kill()

def parse\_model\_response(output):  
    text\_parts \= \[\]  
    for line in output.strip().split("\\n"):  
        line \= line.strip()  
        if not line:  
            continue  
        try:  
            event \= json.loads(line)  
        except json.JSONDecodeError:  
            continue  
        if event.get("type") \== "text":  
            part \= event.get("part", {})  
            text \= part.get("text", "")  
            if text:  
                text\_parts.append(text)  
    return "\\n".join(text\_parts)

def query\_native(server\_port, model\_id, prompt, timeout\=120):  
    cmd \= \[  
        OPENCODE\_CLI, "run",  
        "--attach", f"http://127.0.0.1:{server\_port}",  
        "--model", model\_id,  
        "--format", "json",  
        prompt  
    \]  
    try:  
        env \= os.environ.copy()  
        env\["PYTHONIOENCODING"\] \= "utf-8"  
        result \= subprocess.run(  
            cmd, cwd\=PROJECT\_ROOT,  
            capture\_output\=True, text\=True,  
            encoding\="utf-8", errors\="replace",  
            env\=env, timeout\=timeout  
        )  
        \# FIX \#10: parsear SOLO stdout; stderr es diagnostico, no respuesta del modelo  
        response\_text \= parse\_model\_response(result.stdout)

        \# Si el CLI fallo y no tenemos texto parseable, anotarlo sin contaminar  
        if result.returncode \!= 0 and not response\_text:  
            stderr\_preview \= result.stderr\[:250\].replace("\\n", " ")  
            response\_text \= f"\[CLI\_ERROR code={result.returncode}\] stderr={stderr\_preview}"

        return response\_text  
    except subprocess.TimeoutExpired:  
        return "\[TIMEOUT\]"  
    except Exception as e:  
        return f"\[ERROR\] {str(e)}"

def query\_api(model\_id, prompt, timeout\=60):  
    try:  
        from openai import OpenAI  
        base\_url \= os.getenv("LLM\_BASE\_URL", "https://api.groq.com/openai/v1")  
        api\_key \= os.getenv("LLM\_API\_KEY", "") or os.getenv("GROQ\_API\_KEY", "")  
        client \= OpenAI(base\_url\=base\_url, api\_key\=api\_key)  
        response \= client.chat.completions.create(  
            model\=model\_id,  
            messages\=\[  
                {"role": "system", "content": \_load\_ai\_system\_prompt()},  
                {"role": "user", "content": prompt}  
            \],  
            temperature\=0.1,  
            max\_tokens\=800,  
            timeout\=timeout  
        )  
        return response.choices\[0\].message.content or ""  
    except Exception as e:  
        return f"\[ERROR\] {str(e)}"

def \_load\_ai\_system\_prompt():  
    ai\_path \= os.path.join(PROJECT\_ROOT, ".ai")  
    parts \= \[\]  
    for name in \["system.md", "rules.md", "context.md", "agents.md"\]:  
        fp \= os.path.join(ai\_path, name)  
        if os.path.exists(fp):  
            with open(fp, "r", encoding\="utf-8") as f:  
                parts.append(f"=== {name} \===\\n{f.read().strip()}")  
    return "\\n\\n".join(parts)

def run\_cases\_for\_model(model\_label, query\_fn, questions):  
    per\_case \= {}  
    for case in questions:  
        cid \= case\["id"\]  
        print(f" \[{cid}\] {case\['name'\]}... ", end\="", flush\=True)  
        t0 \= time.time()  
        response \= query\_fn(case\["prompt"\])

        if response.startswith("\[TIMEOUT\]"):  
            status \= "TIMEOUT"  
            reasons \= \["timeout"\]  
        elif response.startswith("\[ERROR\]"):  
            status \= "ERROR"  
            reasons \= \[response\]  
        else:  
            passed, reasons \= validate\_advanced(response, case)  
            status \= "PASS" if passed else "FAIL"

        elapsed \= round(time.time() \- t0, 1)  
        per\_case\[cid\] \= {  
            "name": case\["name"\],  
            "category": case\["category"\],  
            "status": status,  
            "time\_seconds": elapsed,  
            "reasons": reasons,  
            "response\_preview": response\[:200\] \+ "..." if len(response) \> 200 else response,  
        }  
        print(f"{status} ({elapsed}s)")  
        for r in reasons\[:6\]:  
            print(f"          \- {r}")  
        time.sleep(0.5)  \# reducido para no perder tiempo; opcional  
    return per\_case

def print\_summary(all\_results, questions):  
    print("\\n" \+ "=" \* 90)  
    print(f"VALIDACION AVANZADA .ai/ | {datetime.now().strftime('%Y-%m-%d %H:%M')}")  
    print("=" \* 90)

    headers \= \[q\["id"\] for q in questions\]  
    print(f" {'Modelo':\<28} " \+ " ".join(f"{h:\>5}" for h in headers) \+ "  SCORE")  
    print("-" \* 90)

    total\_cases \= len(headers)  
    for model, cases in all\_results.items():  
        cells \= \[\]  
        passed \= 0  
        for cid in headers:  
            st \= cases.get(cid, {}).get("status", "-")  
            short \= {"PASS": "P", "FAIL": "F", "TIMEOUT": "T", "ERROR": "E"}.get(st, "-")  
            cells.append(f"{short:\>5}")  
            if st \== "PASS":  
                passed \+= 1  
        print(f" {model:\<28} " \+ " ".join(cells) \+ f"  {passed}/{total\_cases}")

    print("=" \* 90)

def main():  
    \# FIX: removido os.system("") inutil  
    args \= sys.argv\[1:\]  
    model\_filter \= None  
    category \= None  
    api \= False  
    api\_model \= None

    i \= 0  
    while i \< len(args):  
        a \= args\[i\]  
        if a \== "--category" and i \+ 1 \< len(args):  
            category \= args\[i \+ 1\]  
            i \+= 2  
        elif a \== "--api" and i \+ 1 \< len(args):  
            api \= True  
            api\_model \= args\[i \+ 1\]  
            i \+= 2  
        else:  
            model\_filter \= a  
            i \+= 1

    questions \= load\_questions()  
    questions \= filter\_by\_category(questions, category)  
    print(f"Runner avanzado ({len(questions)} casos, categorias: {category or 'todas'})")

    models\_config \= \[\]

    if api:  
        if api\_model:  
            models\_config.append({"model": f"api/{api\_model}", "native": False, "id": api\_model})  
        else:  
            print("Uso: \--api \<model\_id\>")  
            sys.exit(1)  
    else:  
        native \= NATIVE\_MODELS  
        if model\_filter:  
            native \= \[m for m in native if model\_filter.lower() in m.lower()\]  
        if not native:  
            print(f"No se encontraron modelos nativos que coincidan: {model\_filter}")  
            sys.exit(1)  
        models\_config.extend({"model": m, "native": True, "id": m} for m in native)

    server\_proc \= None  
    port \= None  
    has\_native \= any(c\["native"\] for c in models\_config)  
    if has\_native:  
        if not os.path.exists(OPENCODE\_CLI):  
            print(f"ERROR: No se encuentra opencode CLI en {OPENCODE\_CLI}")  
            sys.exit(1)  
        port \= find\_free\_port()  
        print(f"Iniciando servidor OpenCode en puerto {port}...")  
        try:  
            server\_proc \= start\_server(port)  \# FIX \#11: polling interno  
        except Exception as e:  
            print(f"ERROR: {e}")  
            sys.exit(1)  
        print(f"Servidor OK (PID: {server\_proc.pid})\\n")

    all\_results \= {}  
    try:  
        for cfg in models\_config:  
            label \= cfg\["model"\]  
            print(f"\\n\[{label}\]")  
            if cfg\["native"\]:  
                def query\_fn(p, model\_id\=cfg\["id"\], port\=port):  
                    return query\_native(port, model\_id, p)  
            else:  
                def query\_fn(p, model\_id\=cfg\["id"\]):  
                    return query\_api(model\_id, p)

            cases \= run\_cases\_for\_model(label, query\_fn, questions)  
            all\_results\[label\] \= cases  
    finally:  
        if server\_proc:  
            stop\_server(server\_proc)

    print\_summary(all\_results, questions)

    \# Guardar reporte  
    report\_path \= os.path.join(PROJECT\_ROOT, REPORT\_FILE)  
    with open(report\_path, "w", encoding\="utf-8") as f:  
        json.dump({  
            "timestamp": datetime.now().isoformat(),  
            "type": "advanced\_validation",  
            "category": category,  
            "models": all\_results  
        }, f, indent\=2, ensure\_ascii\=False)  
    print(f"\\nReporte guardado en {report\_path}")

\# FIX: bloque de ejecucion correcto  
if \_\_name\_\_ \== "\_\_main\_\_":

    main()

---

### Resumen de los cambios en este archivo

| Fix | Qué era | Qué es ahora |
| ----- | ----- | ----- |
| \#10 | parse\_model\_response(result.stdout \+ result.stderr) mezclaba errores de CLI con la respuesta | Solo parsea stdout; stderr queda en diagnóstico sin contaminar |
| \#11 | time.sleep(3) ciego; luego poll() | wait\_for\_server() con TCP polling (0.3s intervalos, 30s max) |
| Ejecución | file (indefinido), if name \== ... | \_\_file\_\_, if \_\_name\_\_ \== "\_\_main\_\_" |
| Diagnóstico | Sin feedback si CLI fallaba | Si returncode \!= 0 y vacío, inyecta nota \[CLI\_ERROR ...\] |

Con esto tu runner es determinista para el servidor y no interpreta errores de infraestructura como texto del modelo. Si quieres, puedo pasarte también un run\_advanced\_tests.py con paralelismo limitado (ej. 2 modelos a la vez) para que el port y el wait\_for\_server no chocen, pero eso ya es arquitectura de ejecución, no del código. ¿Seguimos?  
