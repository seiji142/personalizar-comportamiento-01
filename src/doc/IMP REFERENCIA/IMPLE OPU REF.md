# Plan de implementación incremental

La regla de oro del orden: primero el mecanismo, después el prompt. Si cambias rules.md antes de tener el gateway, el modelo aprende a hablar de procedencia sin que exista. Con llama-3.3-70b en Groq esto es especialmente cierto: es un modelo que sigue protocolos de forma inconsistente, así que todo lo que dependa de su disciplina fallará bajo presión.

## Resumen de fases

| Fase | Objetivo | Rompe algo | Duración típica |
| ----- | ----- | ----- | ----- |
| 0 | Observabilidad: medir el problema real | No | 2-3 días |
| 1 | Tipos \+ resolver read-only (aditivo) | No | 1 día |
| 2 | Store de handles server-side | No | 1-2 días |
| 3 | Gateway \+ políticas en modo warn | No | 2-3 días |
| 3.5 | Cerrar superficie de efectos (bash, write) | Sí, controlado | 1 día |
| 4 | enforce gradual por acción | Sí, intencional | 1-2 semanas |
| 5 | Capa de prompt alineada al mecanismo real | No | 1 día |
| 6 | Suite de red team | No | 2 días |
| 7 | Métricas y mantenimiento | No | Continuo |

## Estructura final de archivos

text

brain-ai-01/  
├── server.py                     \# FastAPI (modificado)  
├── mcp\_bridge.py                 \# Bridge MCP (modificado)  
├── clients/  
│   └── memoria.py                \# sin cambios  
├── provenance/  
│   ├── \_\_init\_\_.py  
│   ├── audit.py                  \# Fase 0  
│   ├── detectors.py              \# Fase 0  
│   ├── types.py                  \# Fase 1  
│   ├── sources.py                \# Fase 1  
│   ├── resolver.py               \# Fase 1 y 2  
│   ├── store.py                  \# Fase 2  
│   ├── policies.py               \# Fase 3  
│   ├── gateway.py                \# Fase 3  
│   └── errors.py  
├── scripts/  
│   └── audit\_report.py           \# Fase 0 y 7  
├── tests/  
│   └── test\_provenance.py        \# Fase 6  
└── logs/  
    └── audit.jsonl

---

# Fase 0 — Observabilidad

Objetivo: saber con qué frecuencia y en qué campos ocurre el problema, antes de bloquear nada. Sin esto vas a calibrar las políticas a ciegas.

## provenance/audit.py

Python

from \_\_future\_\_ import annotations

import hashlib  
import json  
import os  
import threading  
from datetime import datetime, timezone  
from pathlib import Path  
from typing import Any

\_LOCK \= threading.Lock()  
AUDIT\_PATH \= Path(os.getenv("BRAIN\_AUDIT\_PATH", "logs/audit.jsonl"))  
AUDIT\_PATH.parent.mkdir(parents\=True, exist\_ok\=True)

SENSITIVE\_HINTS \= ("key", "token", "secret", "password", "passwd", "credential", "auth")

def fingerprint(value: str) \-\> str:  
    return "sha256:" \+ hashlib.sha256(value.encode("utf-8")).hexdigest()\[:16\]

def redact(obj: Any, key\_name: str \= "") \-\> Any:  
    """Nunca escribas valores sensibles al log. Solo huellas."""  
    if isinstance(obj, dict):  
        return {k: redact(v, k) for k, v in obj.items()}  
    if isinstance(obj, list):  
        return \[redact(v, key\_name) for v in obj\]  
    if isinstance(obj, str):  
        lowered \= key\_name.lower()  
        if any(h in lowered for h in SENSITIVE\_HINTS) or len(obj) \> 200:  
            return {"\_\_redacted\_\_": True, "fp": fingerprint(obj), "len": len(obj)}  
        return obj  
    return obj

def log(event: str, \*\*fields: Any) \-\> None:  
    record \= {  
        "ts": datetime.now(timezone.utc).isoformat(),  
        "event": event,  
        \*\*fields,  
    }  
    line \= json.dumps(record, ensure\_ascii\=False, default\=str)  
    with \_LOCK:  
        with AUDIT\_PATH.open("a", encoding\="utf-8") as f:  
            f.write(line \+ "\\n")

## provenance/detectors.py

Python

from \_\_future\_\_ import annotations

import re  
from typing import Any

\# Campos que jamás deberían aceptar un literal generado por el modelo.  
REFERENTIAL\_FIELDS \= {  
    "api\_key", "apikey", "api-key", "token", "access\_token", "refresh\_token",  
    "secret", "client\_secret", "password", "passwd", "credential", "credentials",  
    "authorization", "auth", "dsn", "connection\_string", "database\_url",  
    "account\_id", "tenant\_id", "user\_id", "project\_id", "record\_id",  
    "endpoint", "base\_url", "webhook\_url", "host", "bucket",  
}

SECRET\_PATTERNS \= \[  
    re.compile(r"\\bsk-\[A-Za-z0-9\_**\\-**\]{16,}\\b"),  
    re.compile(r"\\bgsk\_\[A-Za-z0-9\_**\\-**\]{16,}\\b"),  
    re.compile(r"\\bAKIA\[0-9A-Z\]{16}\\b"),  
    re.compile(r"\\bghp\_\[A-Za-z0-9\]{20,}\\b"),  
    re.compile(r"\\beyJ\[A-Za-z0-9\_**\\-**\]{10,}**\\.**\[A-Za-z0-9\_**\\-**\]{10,}**\\.**"),  \# JWT  
    re.compile(r"\\b\[A-Za-z0-9+/\]{40,}\={0,2}\\b"),                     \# base64 largo  
\]

PLACEHOLDER\_PATTERNS \= \[  
    re.compile(r"(?i)\\b(your|tu|my|mi)\[\_**\\-** \]?(api\[\_**\\-** \]?key|token|secret)\\b"),  
    re.compile(r"(?i)\\b(xxx\+|abc123|changeme|placeholder|example|foobar|dummy)\\b"),  
    re.compile(r"^**\\\<**.\***\\\>**$"),  
\]

def scan(tool: str, params: dict\[str, Any\]) \-\> list\[dict\]:  
    findings: list\[dict\] \= \[\]  
    for name, value in \_flatten(params):  
        lowered \= name.lower()

        if lowered in REFERENTIAL\_FIELDS:  
            findings.append({"type": "referential\_field", "field": name, "tool": tool})

        if not isinstance(value, str):  
            continue

        for pat in SECRET\_PATTERNS:  
            if pat.search(value):  
                findings.append({"type": "secret\_shape", "field": name, "pattern": pat.pattern})  
                break

        for pat in PLACEHOLDER\_PATTERNS:  
            if pat.search(value):  
                findings.append({"type": "placeholder\_shape", "field": name})  
                break

    return findings

def \_flatten(obj: Any, prefix: str \= ""):  
    if isinstance(obj, dict):  
        for k, v in obj.items():  
            yield from \_flatten(v, f"{prefix}.{k}" if prefix else str(k))  
    elif isinstance(obj, list):  
        for i, v in enumerate(obj):  
            yield from \_flatten(v, f"{prefix}\[{i}\]")  
    else:  
        yield prefix, obj

## Enganche en mcp\_bridge.py

Envuelve todas las tools que ya expones, sin cambiar su comportamiento:

Python

from provenance import audit, detectors

def observed(tool\_name: str, fn):  
    """Decorador de observación. Fase 0: no bloquea nada."""  
    def wrapper(\*\*params):  
        session\_id \= params.get("\_session\_id", "unknown")  
        findings \= detectors.scan(tool\_name, params)  
        audit.log(  
            "tool\_call",  
            tool\=tool\_name,  
            session\=session\_id,  
            params\=audit.redact(params),  
            findings\=findings,  
        )  
        result \= fn(\*\*params)  
        audit.log("tool\_result", tool\=tool\_name, session\=session\_id, ok\=True)  
        return result  
    return wrapper

\# Uso:  
\# TOOLS\["buscar"\] \= observed("buscar", memoria.buscar)

\# TOOLS\["guardar"\] \= observed("guardar", memoria.guardar)

## scripts/audit\_report.py

Python

import json  
from collections import Counter  
from pathlib import Path

path \= Path("logs/audit.jsonl")  
by\_type \= Counter()  
by\_field \= Counter()  
by\_tool \= Counter()  
total\_calls \= 0

for line in path.read\_text(encoding\="utf-8").splitlines():  
    rec \= json.loads(line)  
    if rec\["event"\] \!= "tool\_call":  
        continue  
    total\_calls \+= 1  
    for f in rec.get("findings", \[\]):  
        by\_type\[f\["type"\]\] \+= 1  
        by\_field\[f.get("field", "?")\] \+= 1  
        by\_tool\[rec\["tool"\]\] \+= 1

print(f"Llamadas totales: {total\_calls}\\n")  
print("Hallazgos por tipo:")  
for k, v in by\_type.most\_common():  
    print(f"  {k:24} {v}")  
print("\\nCampos más problemáticos:")  
for k, v in by\_field.most\_common(15):  
    print(f"  {k:32} {v}")  
print("\\nTools más problemáticas:")  
for k, v in by\_tool.most\_common(10):  
    print(f"  {k:24} {v}")

Definición de hecho (Fase 0): tienes una lista concreta de tools y campos donde aparecen valores sin procedencia. Esa lista define el orden de las fases 3 y 4\.

Rollback: eliminar el decorador observed.

---

# Fase 1 — Tipos y resolver read-only

Objetivo: que exista una forma de decir "no resuelto" y un único camino legítimo de obtener valores. Todavía nada se bloquea.

## provenance/errors.py

Python

class ProvenanceError(Exception):  
    code \= "provenance\_error"

class UnresolvedReferenceError(ProvenanceError):  
    code \= "unresolved\_reference"

class MissingProvenanceError(ProvenanceError):  
    code \= "missing\_provenance"

class HandleError(ProvenanceError):  
    code \= "handle\_error"

class PolicyViolation(ProvenanceError):  
    code \= "policy\_violation"

class ActionDenied(ProvenanceError):  
    code \= "action\_denied"

## provenance/types.py

Python

from \_\_future\_\_ import annotations

from dataclasses import dataclass, field  
from enum import Enum

class ValueKind(str, Enum):  
    SECRET \= "secret"  
    ENV\_VAR \= "env\_var"  
    PATH \= "path"  
    ENDPOINT \= "endpoint"  
    RECORD\_ID \= "record\_id"  
    CONFIG \= "config"  
    FREE\_TEXT \= "free\_text"

SENSITIVE\_KINDS \= {ValueKind.SECRET, ValueKind.ENDPOINT, ValueKind.RECORD\_ID}

class MatchType(str, Enum):  
    EXACT \= "exact"      \# el nombre coincide con una clave existente  
    ALIAS \= "alias"      \# coincide vía alias declarado explícitamente  
    FUZZY \= "fuzzy"      \# coincidencia aproximada: nunca auto-resuelve nada sensible

@dataclass  
class Candidate:  
    key: str                     \# nombre canónico real, p.ej. "GROQ\_API\_KEY"  
    kind: ValueKind  
    source: str                  \# "env" | "memoria" | "user\_message" | "workspace"  
    source\_record\_id: str        \# prueba de que existe en algún lado  
    match\_type: MatchType  
    preview: str | None \= None   \# metadato NO sensible  
    value: str \= field(repr\=False, default\="")

def public\_metadata(c: Candidate) \-\> dict:  
    """Lo único que puede ver el LLM sobre un candidato."""  
    return {  
        "key": c.key,  
        "kind": c.kind.value,  
        "source": c.source,  
        "source\_record\_id": c.source\_record\_id,  
        "match": c.match\_type.value,  
        "preview": c.preview,  
    }

## provenance/sources.py

Python

from \_\_future\_\_ import annotations

import difflib  
import os  
from pathlib import Path  
from typing import Protocol

from .types import Candidate, MatchType, ValueKind

WORKSPACE\_ROOT \= Path(os.getenv("WORKSPACE\_ROOT", ".")).resolve()

def \_preview(value: str, kind: ValueKind) \-\> str:  
    if kind in (ValueKind.SECRET,):  
        return f"len={len(value)} ···{value\[\-4:\]}" if len(value) \> 8 else "len\<=8"  
    return value\[:60\]

class Source(Protocol):  
    name: str  
    def lookup(self, expression: str, expected\_kind: ValueKind | None) \-\> list\[Candidate\]: ...  
    def enumerate\_keys(self, expected\_kind: ValueKind | None) \-\> list\[str\]: ...

class EnvSource:  
    name \= "env"

    \# Alias explícitos y auditables. NO se generan automáticamente.  
    ALIASES \= {  
        "api key de groq": "GROQ\_API\_KEY",  
        "clave de groq": "GROQ\_API\_KEY",  
    }

    def \_kind\_of(self, key: str) \-\> ValueKind:  
        lowered \= key.lower()  
        if any(h in lowered for h in ("key", "token", "secret", "password")):  
            return ValueKind.SECRET  
        if lowered.endswith(("\_url", "\_endpoint", "\_host")):  
            return ValueKind.ENDPOINT  
        return ValueKind.ENV\_VAR

    def lookup(self, expression, expected\_kind):  
        expr \= expression.strip()  
        out: list\[Candidate\] \= \[\]

        if expr in os.environ:  
            out.append(self.\_mk(expr, MatchType.EXACT))  
        elif expr.lower() in self.ALIASES and self.ALIASES\[expr.lower()\] in os.environ:  
            out.append(self.\_mk(self.ALIASES\[expr.lower()\], MatchType.ALIAS))  
        else:  
            near \= difflib.get\_close\_matches(expr.upper(), list(os.environ), n\=3, cutoff\=0.82)  
            out.extend(self.\_mk(k, MatchType.FUZZY) for k in near)

        if expected\_kind:  
            out \= \[c for c in out if c.kind \== expected\_kind\]  
        return out

    def \_mk(self, key: str, match: MatchType) \-\> Candidate:  
        value \= os.environ\[key\]  
        kind \= self.\_kind\_of(key)  
        return Candidate(  
            key\=key, kind\=kind, source\=self.name,  
            source\_record\_id\=f"env:{key}", match\_type\=match,  
            preview\=\_preview(value, kind), value\=value,  
        )

    def enumerate\_keys(self, expected\_kind):  
        keys \= list(os.environ)  
        if expected\_kind:  
            keys \= \[k for k in keys if self.\_kind\_of(k) \== expected\_kind\]  
        return sorted(keys)

class MemoriaSource:  
    """Adaptador sobre clients/memoria.py. Normaliza lo que devuelva tu cliente."""  
    name \= "memoria"

    def \_\_init\_\_(self, memoria\_client):  
        self.client \= memoria\_client

    def lookup(self, expression, expected\_kind):  
        raw \= self.client.buscar(expression) or \[\]  
        if isinstance(raw, dict):  
            raw \= \[raw\]

        out \= \[\]  
        for r in raw:  
            key \= r.get("key") or r.get("nombre") or expression  
            value \= r.get("value") or r.get("contenido") or ""  
            rid \= r.get("id") or r.get("record\_id")  
            if not rid or not value:  
                continue  \# sin id verificable no es procedencia  
            kind \= ValueKind(r.get("kind", ValueKind.CONFIG.value))  
            if expected\_kind and kind \!= expected\_kind:  
                continue  
            out.append(Candidate(  
                key\=key, kind\=kind, source\=self.name,  
                source\_record\_id\=f"memoria:{rid}",  
                match\_type\=MatchType.EXACT if key \== expression else MatchType.FUZZY,  
                preview\=\_preview(str(value), kind), value\=str(value),  
            ))  
        return out

    def enumerate\_keys(self, expected\_kind):  
        return \[\]

class UserMessageSource:  
    """  
    Valores declarados por el usuario, extraídos del transcript CRUDO por el bridge.  
    Nunca se pueblan por una tool que el LLM pueda llamar.  
    """  
    name \= "user\_message"

    def \_\_init\_\_(self):  
        self.\_store: dict\[str, Candidate\] \= {}

    def ingest(self, message\_id: str, text: str) \-\> int:  
        """Llamar desde el bridge con el mensaje literal del usuario."""  
        import re  
        count \= 0  
        for m in re.finditer(r"\\b(\[A-Z\]\[A-Z0-9\_\]{2,})\\s\*\=\\s\*(\[^\\s**\\"**'\]\+)", text):  
            key, value \= m.group(1), m.group(2)  
            kind \= ValueKind.SECRET if any(  
                h in key.lower() for h in ("key", "token", "secret", "password")  
            ) else ValueKind.CONFIG  
            self.\_store\[key\] \= Candidate(  
                key\=key, kind\=kind, source\=self.name,  
                source\_record\_id\=f"user\_message:{message\_id}:{m.start()}\-{m.end()}",  
                match\_type\=MatchType.EXACT,  
                preview\=\_preview(value, kind), value\=value,  
            )  
            count \+= 1  
        return count

    def lookup(self, expression, expected\_kind):  
        c \= self.\_store.get(expression.strip())  
        if not c:  
            return \[\]  
        if expected\_kind and c.kind \!= expected\_kind:  
            return \[\]  
        return \[c\]

    def enumerate\_keys(self, expected\_kind):  
        return sorted(self.\_store)

class WorkspaceSource:  
    name \= "workspace"

    def lookup(self, expression, expected\_kind):  
        if expected\_kind not in (None, ValueKind.PATH):  
            return \[\]  
        candidate \= (WORKSPACE\_ROOT / expression).resolve()  
        if not str(candidate).startswith(str(WORKSPACE\_ROOT)):  
            return \[\]  
        if not candidate.exists():  
            return \[\]  
        return \[Candidate(  
            key\=expression, kind\=ValueKind.PATH, source\=self.name,  
            source\_record\_id\=f"workspace:{candidate}",  
            match\_type\=MatchType.EXACT, preview\=str(candidate),  
            value\=str(candidate),  
        )\]

    def enumerate\_keys(self, expected\_kind):  
        return \[\]

## provenance/resolver.py (versión Fase 1, devuelve metadatos)

Python

from \_\_future\_\_ import annotations

from . import audit  
from .types import SENSITIVE\_KINDS, Candidate, MatchType, ValueKind, public\_metadata

class Resolver:  
    def \_\_init\_\_(self, sources: list, store\=None):  
        self.sources \= sources  
        self.store \= store  \# se conecta en Fase 2

    def resolve(  
        self,  
        expression: str,  
        expected\_kind: str | None,  
        session\_id: str,  
        context: dict | None \= None,  
        allowed\_sources: set\[str\] | None \= None,  
    ) \-\> dict:  
        kind \= ValueKind(expected\_kind) if expected\_kind else None  
        audit.log("resolve\_request", expr\=expression, kind\=expected\_kind,  
                  session\=session\_id, context\=context)

        candidates: list\[Candidate\] \= \[\]  
        for src in self.sources:  
            if allowed\_sources and src.name not in allowed\_sources:  
                continue  
            try:  
                candidates.extend(src.lookup(expression, kind))  
            except Exception as e:  
                audit.log("source\_error", source\=src.name, error\=str(e))

        if not candidates:  
            result \= {  
                "status": "unresolved",  
                "expression": expression,  
                "available\_keys": self.\_hint(kind, allowed\_sources),  
                "next\_step": "Pregunta al usuario o usa una de las claves disponibles. "  
                             "No inventes un valor ni un nombre de clave.",  
            }  
            audit.log("resolve\_result", status\="unresolved", expr\=expression, session\=session\_id)  
            return result

        if len(candidates) \> 1:  
            result \= {  
                "status": "ambiguous",  
                "expression": expression,  
                "candidates": \[public\_metadata(c) for c in candidates\[:10\]\],  
                "next\_step": "Muestra estos candidatos al usuario y pídele que elija. "  
                             "No selecciones por plausibilidad.",  
            }  
            audit.log("resolve\_result", status\="ambiguous", expr\=expression,  
                      n\=len(candidates), session\=session\_id)  
            return result

        c \= candidates\[0\]

        if c.match\_type \== MatchType.FUZZY and c.kind in SENSITIVE\_KINDS:  
            audit.log("resolve\_result", status\="needs\_confirmation", expr\=expression,  
                      key\=c.key, session\=session\_id)  
            return {  
                "status": "needs\_confirmation",  
                "expression": expression,  
                "candidate": public\_metadata(c),  
                "next\_step": f"Coincidencia aproximada con '{c.key}'. Pide confirmación explícita "  
                             f"al usuario antes de usarla.",  
            }

        return self.\_issue(c, session\_id, expression)

    def \_issue(self, c: Candidate, session\_id: str, expression: str) \-\> dict:  
        \# Fase 1: sin store todavía, solo metadatos.  
        audit.log("resolve\_result", status\="resolved", key\=c.key,  
                  source\=c.source, session\=session\_id,  
                  value\_fp\=audit.fingerprint(c.value))  
        return {"status": "resolved", \*\*public\_metadata(c)}

    def \_hint(self, kind, allowed\_sources) \-\> list\[str\]:  
        keys: list\[str\] \= \[\]  
        for src in self.sources:  
            if allowed\_sources and src.name not in allowed\_sources:  
                continue  
            keys.extend(src.enumerate\_keys(kind))  
        return sorted(set(keys))\[:40\]

## Endpoint en server.py

Python

from fastapi import FastAPI  
from pydantic import BaseModel

from clients import memoria  
from provenance.resolver import Resolver  
from provenance.sources import EnvSource, MemoriaSource, UserMessageSource, WorkspaceSource

app \= FastAPI()

user\_source \= UserMessageSource()  
resolver \= Resolver(sources\=\[  
    EnvSource(),  
    user\_source,  
    MemoriaSource(memoria),  
    WorkspaceSource(),  
\])

class ResolveRequest(BaseModel):  
    expression: str  
    expected\_kind: str | None \= None  
    session\_id: str  
    context: dict | None \= None

@app.post("/resolve\_reference")  
def resolve\_reference(req: ResolveRequest):  
    return resolver.resolve(  
        expression\=req.expression,  
        expected\_kind\=req.expected\_kind,  
        session\_id\=req.session\_id,  
        context\=req.context,  
    )

class IngestRequest(BaseModel):  
    message\_id: str  
    text: str

@app.post("/internal/ingest\_user\_message")  
def ingest\_user\_message(req: IngestRequest):  
    """Solo lo llama el bridge con el texto crudo. NO se expone como tool MCP."""  
    n \= user\_source.ingest(req.message\_id, req.text)  
    return {"ingested": n}

Definición de hecho (Fase 1): puedes llamar resolve\_reference("la variable") y recibir unresolved con la lista de claves reales disponibles.

---

# Fase 2 — Store de handles server-side

Objetivo: que el valor sensible deje de viajar al modelo. Aquí es donde la procedencia pasa de declarada a autenticada.

## provenance/store.py

Python

from \_\_future\_\_ import annotations

import secrets  
import sqlite3  
import time  
from dataclasses import dataclass  
from pathlib import Path

from . import audit  
from .errors import HandleError

@dataclass  
class HandleRecord:  
    handle: str  
    key: str  
    value: str  
    kind: str  
    source: str  
    source\_record\_id: str  
    session\_id: str

SCHEMA \= """  
CREATE TABLE IF NOT EXISTS handles (  
    handle TEXT PRIMARY KEY,  
    key TEXT NOT NULL,  
    value TEXT NOT NULL,  
    value\_fp TEXT NOT NULL,  
    kind TEXT NOT NULL,  
    source TEXT NOT NULL,  
    source\_record\_id TEXT NOT NULL,  
    session\_id TEXT NOT NULL,  
    created\_at REAL NOT NULL,  
    expires\_at REAL NOT NULL,  
    max\_uses INTEGER NOT NULL,  
    used INTEGER NOT NULL DEFAULT 0,  
    revoked INTEGER NOT NULL DEFAULT 0  
);  
CREATE INDEX IF NOT EXISTS idx\_session ON handles(session\_id);  
CREATE INDEX IF NOT EXISTS idx\_fp ON handles(value\_fp);  
"""

class ResolvedStore:  
    def \_\_init\_\_(self, db\_path: str \= "logs/handles.db"):  
        Path(db\_path).parent.mkdir(parents\=True, exist\_ok\=True)  
        self.conn \= sqlite3.connect(db\_path, check\_same\_thread\=False)  
        self.conn.executescript(SCHEMA)  
        self.conn.commit()

    def issue(self, \*, key, value, kind, source, source\_record\_id,  
              session\_id, ttl\_seconds\=600, max\_uses\=3) \-\> str:  
        handle \= "vh\_" \+ secrets.token\_urlsafe(18)  
        now \= time.time()  
        self.conn.execute(  
            "INSERT INTO handles VALUES (?,?,?,?,?,?,?,?,?,?,?,0,0)",  
            (handle, key, value, audit.fingerprint(value), kind, source,  
             source\_record\_id, session\_id, now, now \+ ttl\_seconds, max\_uses),  
        )  
        self.conn.commit()  
        audit.log("handle\_issued", handle\=handle, key\=key, kind\=kind,  
                  source\=source, session\=session\_id, ttl\=ttl\_seconds)  
        return handle

    def validate(self, \*, handle, session\_id, expected\_kind\=None,  
                 allowed\_sources\=None, consume\=True) \-\> HandleRecord:  
        row \= self.conn.execute(  
            "SELECT handle,key,value,kind,source,source\_record\_id,session\_id,"  
            "expires\_at,max\_uses,used,revoked FROM handles WHERE handle=?",  
            (handle,),  
        ).fetchone()

        if row is None:  
            self.\_fail(handle, session\_id, "handle\_not\_found")  
        (h, key, value, kind, source, srid, sess, expires\_at, max\_uses, used, revoked) \= row

        if revoked:  
            self.\_fail(handle, session\_id, "handle\_revoked")  
        if time.time() \> expires\_at:  
            self.\_fail(handle, session\_id, "handle\_expired")  
        if sess \!= session\_id:  
            self.\_fail(handle, session\_id, "session\_mismatch")  
        if used \>= max\_uses:  
            self.\_fail(handle, session\_id, "handle\_exhausted")  
        if expected\_kind and kind \!= expected\_kind:  
            self.\_fail(handle, session\_id, f"kind\_mismatch:{kind}\!={expected\_kind}")  
        if allowed\_sources and source not in allowed\_sources:  
            self.\_fail(handle, session\_id, f"source\_not\_allowed:{source}")

        if consume:  
            self.conn.execute("UPDATE handles SET used=used+1 WHERE handle=?", (handle,))  
            self.conn.commit()

        audit.log("handle\_validated", handle\=handle, key\=key, source\=source,  
                  session\=session\_id)  
        return HandleRecord(h, key, value, kind, source, srid, sess)

    def describe(self, handle: str, session\_id: str) \-\> dict | None:  
        row \= self.conn.execute(  
            "SELECT key,kind,source,source\_record\_id,expires\_at FROM handles "  
            "WHERE handle=? AND session\_id=?", (handle, session\_id),  
        ).fetchone()  
        if not row:  
            return None  
        return {"handle": handle, "key": row\[0\], "kind": row\[1\],  
                "source": row\[2\], "source\_record\_id": row\[3\], "expires\_at": row\[4\]}

    def known\_fingerprints(self, session\_id: str) \-\> set\[str\]:  
        rows \= self.conn.execute(  
            "SELECT value\_fp FROM handles WHERE session\_id=?", (session\_id,)  
        ).fetchall()  
        return {r\[0\] for r in rows}

    def \_fail(self, handle, session\_id, reason):  
        audit.log("handle\_rejected", handle\=handle, session\=session\_id, reason\=reason)  
        raise HandleError(reason)

## Cambio en resolver.py

Reemplaza \_issue:

Python

   def \_issue(self, c: Candidate, session\_id: str, expression: str) \-\> dict:  
        if self.store is None:  
            audit.log("resolve\_result", status\="resolved\_no\_store", key\=c.key)  
            return {"status": "resolved", \*\*public\_metadata(c)}

        handle \= self.store.issue(  
            key\=c.key, value\=c.value, kind\=c.kind.value, source\=c.source,  
            source\_record\_id\=c.source\_record\_id, session\_id\=session\_id,  
        )  
        audit.log("resolve\_result", status\="resolved", key\=c.key,  
                  source\=c.source, handle\=handle, session\=session\_id)

        payload \= {"status": "resolved", "handle": handle, \*\*public\_metadata(c)}  
        if c.kind in SENSITIVE\_KINDS:  
            payload\["value"\] \= None  
            payload\["note"\] \= "Valor no expuesto. Usa el handle en la acción."  
        else:  
            payload\["value"\] \= c.value

        return payload

Nota importante: para SECRET el valor nunca sale hacia el modelo. Para PATH o CONFIG sí puede salir, porque el agente necesita razonar con ellos, pero el handle sigue siendo lo que valida el gateway.

Definición de hecho (Fase 2): resolve\_reference("GROQ\_API\_KEY") devuelve un handle y value: null.

---

# Fase 3 — Gateway y políticas en modo warn

Objetivo: tener el punto único de control, todavía sin bloquear.

## provenance/policies.py

Python

from \_\_future\_\_ import annotations

import re  
from dataclasses import dataclass, field  
from pathlib import Path

from .types import ValueKind

@dataclass  
class HandlePolicy:  
    expected\_kind: ValueKind  
    allowed\_sources: set\[str\]  
    mode: str \= "verified\_handle"

@dataclass  
class LiteralPolicy:  
    type: type  
    min: float | None \= None  
    max: float | None \= None  
    max\_len: int \= 200  
    pattern: str | None \= None  
    mode: str \= "literal"

@dataclass  
class EnumPolicy:  
    values: set\[str\]  
    mode: str \= "enum"

@dataclass  
class PathPolicy:  
    root: str  
    must\_exist: bool \= True  
    mode: str \= "path"

\# Modo por acción: "off" | "shadow" | "warn" | "enforce"  
ENFORCEMENT: dict\[str, str\] \= {  
    "http\_request": "warn",  
    "run\_shell": "warn",  
    "write\_file": "warn",  
    "deploy": "warn",  
}

ACTION\_POLICIES: dict\[str, dict\] \= {  
    "http\_request": {  
        "url": HandlePolicy(ValueKind.ENDPOINT, {"env", "memoria", "user\_message"}),  
        "method": EnumPolicy({"GET", "POST", "PUT", "DELETE", "PATCH"}),  
        "api\_key": HandlePolicy(ValueKind.SECRET, {"env", "user\_message"}),  
        "timeout": LiteralPolicy(int, min\=1, max\=120),  
        "body": LiteralPolicy(str, max\_len\=20000),  
    },  
    "write\_file": {  
        "path": PathPolicy(root\="."),  
        "content": LiteralPolicy(str, max\_len\=200000),  
    },  
    "run\_shell": {  
        "command": EnumPolicy({"npm test", "pytest", "git status", "git diff"}),  
    },  
    "deploy": {  
        "environment": EnumPolicy({"staging", "production"}),  
        "api\_key": HandlePolicy(ValueKind.SECRET, {"env"}),  
        "region": EnumPolicy({"us-east-1", "eu-west-1"}),  
    },  
}

def validate\_literal(name: str, value, policy: LiteralPolicy):  
    from .errors import PolicyViolation  
    if not isinstance(value, policy.type):  
        raise PolicyViolation(f"{name}: se esperaba {policy.type.\_\_name\_\_}")  
    if isinstance(value, str):  
        if len(value) \> policy.max\_len:  
            raise PolicyViolation(f"{name}: excede max\_len")  
        if policy.pattern and not re.fullmatch(policy.pattern, value):  
            raise PolicyViolation(f"{name}: no coincide con el patrón permitido")  
    if isinstance(value, (int, float)):  
        if policy.min is not None and value \< policy.min:  
            raise PolicyViolation(f"{name}: menor que {policy.min}")  
        if policy.max is not None and value \> policy.max:  
            raise PolicyViolation(f"{name}: mayor que {policy.max}")  
    return value

def validate\_enum(name: str, value, policy: EnumPolicy):  
    from .errors import PolicyViolation  
    if value not in policy.values:  
        raise PolicyViolation(f"{name}: valor no permitido. Permitidos: {sorted(policy.values)}")  
    return value

def validate\_path(name: str, value, policy: PathPolicy):  
    from .errors import PolicyViolation  
    root \= Path(policy.root).resolve()  
    target \= (root / str(value)).resolve()  
    if not str(target).startswith(str(root)):  
        raise PolicyViolation(f"{name}: ruta fuera del workspace")  
    if policy.must\_exist and not target.exists():  
        raise PolicyViolation(f"{name}: la ruta no existe")  
    return str(target)

## provenance/gateway.py

Python

from \_\_future\_\_ import annotations

from typing import Callable

from . import audit  
from .errors import ActionDenied, HandleError, PolicyViolation  
from .policies import (  
    ACTION\_POLICIES, ENFORCEMENT, EnumPolicy, HandlePolicy, LiteralPolicy,  
    PathPolicy, validate\_enum, validate\_literal, validate\_path,  
)

class ActionGateway:  
    def \_\_init\_\_(self, store, executors: dict\[str, Callable\]):  
        self.store \= store  
        self.executors \= executors

    def execute(self, action: str, params: dict, session\_id: str):  
        mode \= ENFORCEMENT.get(action, "enforce")  \# deny by default para acciones nuevas  
        policy \= ACTION\_POLICIES.get(action)

        if policy is None:  
            audit.log("action\_denied", action\=action, session\=session\_id,  
                      reason\="no\_policy", mode\=mode)  
            raise ActionDenied(  
                f"La acción '{action}' no tiene política declarada. "  
                f"Debe registrarse en ACTION\_POLICIES antes de ejecutarse."  
            )

        resolved: dict \= {}  
        violations: list\[str\] \= \[\]

        extra \= set(params) \- set(policy) \- {"\_session\_id"}  
        if extra:  
            violations.append(f"campos no declarados: {sorted(extra)}")

        for field\_name, field\_policy in policy.items():  
            if field\_name not in params:  
                continue  
            supplied \= params\[field\_name\]  
            try:  
                resolved\[field\_name\] \= self.\_validate\_field(  
                    action, field\_name, supplied, field\_policy, session\_id  
                )  
            except (PolicyViolation, HandleError) as e:  
                violations.append(f"{field\_name}: {e}")  
                resolved\[field\_name\] \= self.\_raw(supplied)

        leaks \= self.\_detect\_leaks(resolved, session\_id)  
        violations.extend(leaks)

        if violations:  
            audit.log("policy\_violation", action\=action, session\=session\_id,  
                      mode\=mode, violations\=violations)

        if violations and mode \== "enforce":  
            raise ActionDenied(  
                "Acción bloqueada por falta de procedencia.\\n\- " \+ "\\n\- ".join(violations)  
                \+ "\\n\\nUsa resolver\_referencia() para obtener un handle verificado."  
            )

        if mode \== "shadow":  
            audit.log("action\_shadow", action\=action, session\=session\_id)  
            return {"status": "shadow", "would\_execute": action}

        audit.log("action\_allowed", action\=action, session\=session\_id,  
                  mode\=mode, had\_violations\=bool(violations))  
        return self.executors\[action\](\*\*resolved)

    def \_validate\_field(self, action, name, supplied, policy, session\_id):  
        if isinstance(policy, HandlePolicy):  
            handle \= supplied.get("handle") if isinstance(supplied, dict) else None  
            if not handle:  
                raise PolicyViolation(  
                    "requiere un handle verificado, se recibió un literal"  
                )  
            record \= self.store.validate(  
                handle\=handle,  
                session\_id\=session\_id,  
                expected\_kind\=policy.expected\_kind.value,  
                allowed\_sources\=policy.allowed\_sources,  
            )  
            return record.value

        if isinstance(policy, EnumPolicy):  
            return validate\_enum(name, self.\_raw(supplied), policy)  
        if isinstance(policy, LiteralPolicy):  
            return validate\_literal(name, self.\_raw(supplied), policy)  
        if isinstance(policy, PathPolicy):  
            return validate\_path(name, self.\_raw(supplied), policy)

        raise PolicyViolation(f"{name}: tipo de política desconocido")

    @staticmethod  
    def \_raw(supplied):  
        if isinstance(supplied, dict) and "value" in supplied:  
            return supplied\["value"\]  
        return supplied

    def \_detect\_leaks(self, resolved: dict, session\_id: str) \-\> list\[str\]:  
        """Si un literal coincide con un secreto conocido, el modelo lo copió."""  
        known \= self.store.known\_fingerprints(session\_id)  
        out \= \[\]  
        for name, value in resolved.items():  
            if isinstance(value, str) and len(value) \>= 12:  
                if audit.fingerprint(value) in known:  
                    out.append(f"{name}: valor secreto copiado como literal")  
                    audit.log("leak\_detected", field\=name, session\=session\_id)  
        return out

## Registro de ejecutores y ruteo

En server.py:

Python

from provenance.gateway import ActionGateway  
from provenance.store import ResolvedStore

store \= ResolvedStore()  
resolver.store \= store

def \_http\_request(url, method\="GET", api\_key\=None, timeout\=30, body\=None):  
    import httpx  
    headers \= {"Authorization": f"Bearer {api\_key}"} if api\_key else {}  
    r \= httpx.request(method, url, headers\=headers, content\=body, timeout\=timeout)  
    return {"status\_code": r.status\_code, "body": r.text\[:5000\]}

def \_write\_file(path, content):  
    from pathlib import Path  
    Path(path).write\_text(content, encoding\="utf-8")  
    return {"written": path, "bytes": len(content)}

gateway \= ActionGateway(store, executors\={  
    "http\_request": \_http\_request,  
    "write\_file": \_write\_file,  
})

class ExecuteRequest(BaseModel):  
    action: str  
    params: dict  
    session\_id: str

@app.post("/actions/execute")  
def execute\_action(req: ExecuteRequest):  
    from provenance.errors import ProvenanceError  
    try:  
        return {"ok": True, "result": gateway.execute(req.action, req.params, req.session\_id)}  
    except ProvenanceError as e:

        return {"ok": False, "error\_code": e.code, "message": str(e)}

Definición de hecho (Fase 3): en logs/audit.jsonl aparecen eventos policy\_violation con nombres de campo concretos, pero nada se rompe todavía.

---

# Fase 3.5 — Cerrar la superficie de efectos

Este es el paso que la mayoría se salta y que invalida todo lo anterior.

Tu gateway solo controla lo que pasa por él. Si OpenCode le da al agente bash, write y edit nativos, el modelo puede escribir la API key inventada directamente en un archivo o ejecutar curl con ella, sin tocar tu MCP.

Acciones concretas:

1. Inventario: lista todas las tools que el agente puede invocar hoy (nativas de OpenCode \+ tus tools MCP).  
2. Clasifica cada una: read-only o efectiva.  
3. Toda tool efectiva debe pasar por el gateway o quedar deshabilitada.  
4. Restringe permisos en opencode.json. La forma exacta de las claves depende de tu versión, verifícala en la documentación de tu build; el patrón general es:

JSON

{  
  "model": "groq/llama-3.3-70b-versatile",  
  "instructions": \[".ai/system.md", ".ai/rules.md", ".ai/context.md"\],  
  "permission": {  
    "bash": "deny",  
    "webfetch": "deny",  
    "write": "ask",  
    "edit": "ask"  
  },  
  "mcp": {  
    "brain-ai": {  
      "type": "remote",  
      "url": "http://localhost:8000"  
    }  
  }

}

Si necesitas shell, expónelo solo como la acción run\_shell de tu gateway con EnumPolicy de comandos permitidos, y ve ampliando esa lista deliberadamente.

Definición de hecho (Fase 3.5): no existe ningún camino a un efecto externo que no pase por gateway.execute.

---

# Fase 4 — enforce gradual

No cambies todo a la vez. Promueve una acción cada vez, en este orden:

| Orden | Acción | Criterio para promover |
| ----- | ----- | ----- |
| 1 | Acciones con secretos (deploy, http\_request con api\_key) | 0 violaciones legítimas en 3 días de warn |
| 2 | run\_shell | Lista de comandos permitidos estable |
| 3 | Escrituras (write\_file, edit) | Rutas del workspace cubiertas |
| 4 | Resto | — |

El cambio es una sola línea:

Python

ENFORCEMENT\["deploy"\] \= "enforce"

Antes de cada promoción, corre:

Bash

python scripts/audit\_report.py | grep policy\_violation

Si aparecen violaciones que son flujos legítimos, la política está mal, no el flujo. Corrige la política. Si es que sí es una alucinación de procedencia, tienes evidencia de que el mecanismo funciona.

Regla operativa: un enforce que genera fricción diaria acaba siendo desactivado. Es mejor promover despacio que tener que revertir.

---

# Fase 5 — Capa de prompt alineada al mecanismo

Recién ahora. El prompt ya no promete nada: describe herramientas que existen.

## Añadir a .ai/rules.md

Markdown

**\#\# 6.5 Referencias no resueltas**

Una expresión es una REFERENCIA NO RESUELTA si no viene de:  
(a) el mensaje literal del usuario en esta conversación, o  
(b) un resultado de \`resolver\_referencia\`.

Para una referencia no resuelta:  
\- NO la sustituyas por un valor.  
\- NO infieras el nombre de la clave por plausibilidad.  
\- Llama a \`resolver\_referencia(expression, expected\_kind)\`.

Emitir "no resuelto" es una respuesta CORRECTA y COMPLETA, no un fallo.

**\#\# 6.6 Uso de handles**

\`resolver\_referencia\` devuelve uno de estos estados:

| status | Qué hacer |  
|---|---|  
| \`resolved\` | Usa \`{"handle": "vh\_..."}\` en el campo de la acción |  
| \`ambiguous\` | Muestra \`candidates\` al usuario y pide que elija |  
| \`needs\_confirmation\` | Pide confirmación explícita del candidato |  
| \`unresolved\` | Reporta NO DISPONIBLE y muestra \`available\_keys\` |

Para valores de tipo \`secret\`, \`value\` siempre es \`null\`. Esto es correcto.  
No necesitas ver el valor: pasa el handle.

**\#\# 6.7 Prohibición de literales referenciales**

Nunca escribas literalmente: api\_key, token, secret, password, credential,  
connection\_string, dsn, account\_id, record\_id, endpoint, base\_url.

Estos campos solo aceptan handles. El gateway rechaza literales y la acción falla.

**\#\# 6.8 Formato de reporte cuando no puedes proceder**

​\`\`\`  
NO DISPONIBLE  
Referencia: "\<expresión textual del usuario\>"  
Tipo esperado: \<kind\>  
Buscado en: env, memoria, mensajes del usuario  
Claves disponibles: \<lista de available\_keys\>  
Necesito: que confirmes cuál usar, o el valor.  
​\`\`\`

**\#\# 6.9 Prohibición de fabricar procedencia**

No construyas objetos con campos \`provenance\`, \`source\`, \`record\_id\`, \`verified\`  
ni \`origin\`. Esos campos los emite el sistema. Un objeto de procedencia escrito  
por ti será rechazado y la acción quedará registrada como violación.

## Añadir a .ai/system.md

Markdown

**\#\# Postura epistémica**

Distingue siempre tres estados y nómbralos explícitamente:

\- SÉ el valor: lo obtuve de una tool con handle en esta sesión.  
\- NO SÉ el valor: existe la referencia, no tengo el dato.  
\- NO APLICA: la referencia no corresponde a nada real.

Decir "no sé" con precisión es más valioso que producir un valor plausible.  
Si el usuario dice "la variable", "el endpoint", "la key" sin más contexto,  
eso es una referencia sin resolver. Trátala como tal.

## Herramientas en mcp\_bridge.py

Python

TOOLS \= {  
    "resolver\_referencia": {  
        "description": (  
            "Resuelve una referencia (nombre de variable, ruta, endpoint, credencial) "  
            "contra fuentes autorizadas. ÚNICA forma legítima de obtener un valor. "  
            "Devuelve resolved | ambiguous | needs\_confirmation | unresolved."  
        ),  
        "parameters": {  
            "expression": "str: la expresión tal como la escribió el usuario",  
            "expected\_kind": "str: secret|env\_var|path|endpoint|record\_id|config",  
        },  
    },  
    "describir\_handle": {  
        "description": "Metadatos de un handle. No devuelve el valor.",  
        "parameters": {"handle": "str"},  
    },  
    "ejecutar\_accion": {  
        "description": (  
            "Ejecuta una acción con efectos. Los campos referenciales requieren "  
            "{'handle': 'vh\_...'} obtenido de resolver\_referencia."  
        ),  
        "parameters": {"action": "str", "params": "object"},  
    },  
}

El bridge debe inyectar session\_id desde su propio estado, nunca desde un parámetro que el modelo controle.

---

# Fase 6 — Suite de red team

## tests/test\_provenance.py

Python

import pytest

from provenance.errors import ActionDenied, HandleError  
from provenance.gateway import ActionGateway  
from provenance.policies import ENFORCEMENT  
from provenance.store import ResolvedStore

SESSION \= "sess\_test"

@pytest.fixture  
def setup(tmp\_path):  
    store \= ResolvedStore(str(tmp\_path / "h.db"))  
    calls \= \[\]  
    gw \= ActionGateway(store, executors\={  
        "deploy": lambda \*\*kw: calls.append(kw) or {"ok": True},  
    })  
    ENFORCEMENT\["deploy"\] \= "enforce"  
    return store, gw, calls

def test\_literal\_en\_campo\_secreto\_es\_rechazado(setup):  
    store, gw, calls \= setup  
    with pytest.raises(ActionDenied):  
        gw.execute("deploy", {  
            "environment": "staging",  
            "api\_key": "sk-abc123inventada",  
            "region": "us-east-1",  
        }, SESSION)  
    assert calls \== \[\]

def test\_procedencia\_fabricada\_por\_el\_modelo\_es\_rechazada(setup):  
    store, gw, calls \= setup  
    with pytest.raises(ActionDenied):  
        gw.execute("deploy", {  
            "environment": "staging",  
            "api\_key": {  
                "type": "verified\_value",  
                "value": "sk-abc123",  
                "provenance": {"source": "brain-ai", "record\_id": "mem\_1234",  
                               "verified": True},  
            },  
            "region": "us-east-1",  
        }, SESSION)  
    assert calls \== \[\]

def test\_bypass\_origin\_literal\_es\_rechazado(setup):  
    store, gw, calls \= setup  
    with pytest.raises(ActionDenied):  
        gw.execute("deploy", {  
            "environment": "staging",  
            "api\_key": {"origin": "literal", "value": "sk-abc123"},  
            "region": "us-east-1",  
        }, SESSION)  
    assert calls \== \[\]

def test\_handle\_valido\_ejecuta(setup):  
    store, gw, calls \= setup  
    h \= store.issue(key\="GROQ\_API\_KEY", value\="gsk\_real", kind\="secret",  
                    source\="env", source\_record\_id\="env:GROQ\_API\_KEY",  
                    session\_id\=SESSION)  
    gw.execute("deploy", {"environment": "staging",  
                          "api\_key": {"handle": h},  
                          "region": "us-east-1"}, SESSION)  
    assert calls\[0\]\["api\_key"\] \== "gsk\_real"

def test\_handle\_de\_otra\_sesion\_es\_rechazado(setup):  
    store, gw, calls \= setup  
    h \= store.issue(key\="K", value\="v", kind\="secret", source\="env",  
                    source\_record\_id\="env:K", session\_id\="otra\_sesion")  
    with pytest.raises(ActionDenied):  
        gw.execute("deploy", {"environment": "staging",  
                              "api\_key": {"handle": h},  
                              "region": "us-east-1"}, SESSION)

def test\_handle\_expirado\_es\_rechazado(setup):  
    store, gw, \_ \= setup  
    h \= store.issue(key\="K", value\="v", kind\="secret", source\="env",  
                    source\_record\_id\="env:K", session\_id\=SESSION, ttl\_seconds\=-1)  
    with pytest.raises(HandleError):  
        store.validate(handle\=h, session\_id\=SESSION)

def test\_handle\_inventado\_es\_rechazado(setup):  
    store, gw, \_ \= setup  
    with pytest.raises(ActionDenied):  
        gw.execute("deploy", {"environment": "staging",  
                              "api\_key": {"handle": "vh\_inventado\_por\_el\_llm"},  
                              "region": "us-east-1"}, SESSION)

def test\_handle\_de\_fuente\_no\_permitida(setup):  
    store, gw, \_ \= setup  
    h \= store.issue(key\="K", value\="v", kind\="secret", source\="memoria",  
                    source\_record\_id\="memoria:1", session\_id\=SESSION)  
    \# deploy.api\_key solo permite source="env"  
    with pytest.raises(ActionDenied):  
        gw.execute("deploy", {"environment": "staging",  
                              "api\_key": {"handle": h},  
                              "region": "us-east-1"}, SESSION)

def test\_accion\_sin\_politica\_se\_deniega(setup):  
    store, gw, \_ \= setup  
    with pytest.raises(ActionDenied):  
        gw.execute("accion\_nueva\_no\_declarada", {}, SESSION)

Añade también un test end-to-end conversacional: pídele al agente "usa la variable para conectarte" sin haber definido nada, y verifica que en audit.jsonl aparezca resolve\_result status=unresolved y ningún action\_allowed.

---

# Fase 7 — Métricas y mantenimiento

Métricas que valen la pena seguir semanalmente:

| Métrica | Señal |
| ----- | ----- |
| unresolved / resolve\_request | Si baja mucho, el agente aprendió a usar claves reales |
| policy\_violation por acción | Dónde falta política o dónde el modelo insiste en inventar |
| leak\_detected | El modelo está copiando valores de handles: revisa qué expones |
| action\_denied por no\_policy | Tools nuevas sin política registrada |
| Tiempo medio hasta resolved | Fricción del flujo para el usuario |

Rituales:

* Al agregar una tool efectiva: primero política, después ejecutor. El deny-by-default hace que olvidarlo falle ruidosamente, que es lo correcto.  
* Revisión mensual de ALIASES: cada alias es una superficie de resolución implícita. Que sean pocos y explícitos.  
* Revisión de EnumPolicy de run\_shell: tiende a crecer sin control.

---

# Orden de trabajo sugerido

text

Semana 1  ── Fase 0: audit \+ detectors \+ report        (medir)  
          └─ Fase 1: types \+ sources \+ resolver        (aditivo)

Semana 2  ── Fase 2: store de handles                  (aditivo)  
          └─ Fase 3: policies \+ gateway en warn        (aditivo)

Semana 3  ── Fase 3.5: cerrar bash/write/webfetch      (primer corte real)  
          └─ Fase 6: tests de red team                 (antes de enforce)

Semana 4+ ── Fase 4: enforce por acción, una a la vez  
          └─ Fase 5: rules.md alineado

          └─ Fase 7: métricas

---

# Errores comunes al implementar esto

1. Empezar por rules.md. Es lo más rápido y lo menos efectivo. El modelo empieza a producir objetos de procedencia falsos que se ven bien y son peores que el problema original, porque generan confianza injustificada.  
2. Dejar bash habilitado. Todo el gateway se vuelve decorativo. Es el fallo más común y el más silencioso.  
3. Permitir que el modelo pase session\_id. Si el modelo controla la sesión, puede reutilizar handles de otros contextos. El bridge inyecta ese valor, siempre.  
4. Exponer el valor junto al handle. Si devuelves ambos, el modelo copiará el valor en algún literal. Por eso está \_detect\_leaks, pero la prevención es no exponerlo.  
5. Poner enforce global de golpe. Genera fricción, se desactiva y el proyecto vuelve a cero. La promoción por acción con evidencia de warn es lo que sostiene el cambio.  
6. Confundir "no encontrado" con "no existe". El resolver debe decir "no encontrado en env, memoria, mensajes del usuario", no "no existe". Esa precisión evita que el agente concluya que puede inventar.  
7. Políticas demasiado laxas al principio. Un LiteralPolicy(str) sin pattern ni max\_len en un campo referencial es equivalente a no tener política.

Si tuviera que priorizar con tiempo limitado: Fase 0 \+ Fase 3.5 \+ un HandlePolicy en los campos de secretos. Eso ya cubre el escenario que originó el problema. El resto es profundidad.  
