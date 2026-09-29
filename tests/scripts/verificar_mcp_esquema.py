#!/usr/bin/env python3
"""Diagnostico log-only del estado de los MCP servers (tarea 16N).

Lee `~/.local/share/opencode/log/opencode.log` y responde en una linea
por server: cuando se vio por ultima vez, cuando murio su conexion,
y cual fue su ultimo uso. Convierte en comando el criterio
"MCP ausente del esquema != servicio caido" (`.ai/rules.md` 8.5):
si la ultima conexion murio sin uso posterior, el proceso de larga
duracion no reconecta -> hay que reiniciar OpenCode.

Senia MCP real: las tools se registran como `<server>_<tool>`
(`brain-ai_memory_search`, `git_publisher_git_ver_estado`). Los permisos
evaluados (`message=evaluated permission=<tool>`) son el proxy de uso:
si el server murio (linea `MCP connection closed`) despues de su ultimo
uso, esta MUERTO.

Solo lee el log (sin dependencias vivas). Uso:
  python verificar_mcp_esquema.py [--log RUTA] [--server NOMBRE]
"""

import argparse
import os
import re
import sys

DEFAULT_LOG = os.path.join(os.path.expanduser("~"), ".local", "share",
                           "opencode", "log", "opencode.log")

TS_RE = re.compile(r"timestamp=(\S+)")
RUN_RE = re.compile(r"\brun=([0-9a-f]+)")
MSG_RE = re.compile(r'message=(?:"([^"]*)"|(\S+))')
SERVER_RE = re.compile(r"\bserver=([A-Za-z0-9_.\-]+)")
UNAVAIL_RE = re.compile(r"server unavailable key=([A-Za-z0-9_.\-]+)")
PERM_RE = re.compile(r"evaluated permission=([A-Za-z0-9_.\-]+)")


def parse_line(line):
    """Extrae (timestamp, run, message, server, unavailable, permission).

    Retorna None si la linea no trae timestamp (no es evento util).
    """
    ts = TS_RE.search(line)
    if not ts:
        return None
    msg_m = MSG_RE.search(line)
    if msg_m:
        msg = msg_m.group(1) if msg_m.group(1) is not None else msg_m.group(2)
    else:
        msg = ""
    run_m = RUN_RE.search(line)
    srv_m = SERVER_RE.search(line)
    un_m = UNAVAIL_RE.search(line)
    perm_m = PERM_RE.search(line)
    return {
        "ts": ts.group(1),
        "run": run_m.group(1) if run_m else "",
        "message": msg or "",
        "server": srv_m.group(1) if srv_m else "",
        "unavailable": un_m.group(1) if un_m else "",
        "permission": perm_m.group(1) if perm_m else "",
    }


def _blank(ts):
    return {"first_seen": ts, "last_closed": "", "last_unavailable": "",
            "last_use": "", "last_use_ts": "", "last_ts": ts, "verdict": ""}


def analyze(lines):
    """Agrega eventos por server. Retorna {server: info}.

    Dos pasadas: primero servers conocidos (lineas `server=` /
    `unavailable`), luego se atribuye cada `evaluated permission=<tool>`
    al server cuyo nombre es prefijo de la tool (`<server>_<resto>`).
    Veredicto: cierre posterior al ultimo uso -> MUERTO.
    """
    events = [parse_line(li) for li in lines]
    events = [ev for ev in events if ev]
    servers = {}
    for ev in events:
        for name in (ev["server"], ev["unavailable"]):
            if name and name not in servers:
                servers[name] = _blank(ev["ts"])
    for ev in events:
        touched = set()
        for name in (ev["server"], ev["unavailable"]):
            if name:
                touched.add(name)
        for name in servers:
            if ev["permission"] and ev["permission"].startswith(name + "_"):
                touched.add(name)
        for name in touched:
            info = servers[name]
            if not info["first_seen"]:
                info["first_seen"] = ev["ts"]
            info["last_ts"] = ev["ts"]
        if ev["message"] == "MCP connection closed" and ev["server"]:
            servers[ev["server"]]["last_closed"] = ev["ts"]
        if ev["unavailable"]:
            servers[ev["unavailable"]]["last_unavailable"] = ev["ts"]
        for name in touched:
            perm = ev["permission"]
            if perm and perm.startswith(name + "_"):
                info = servers[name]
                if ev["ts"] >= info["last_use_ts"]:
                    info["last_use"] = perm
                    info["last_use_ts"] = ev["ts"]
    for _name, info in servers.items():
        if info["last_closed"] and info["last_closed"] >= info["last_use_ts"]:
            info["verdict"] = "MUERTO: reiniciar OpenCode"
        else:
            info["verdict"] = "VIVO"
    return servers


def report(servers, only=None):
    """Una linea por server."""
    lines = []
    for name in sorted(servers):
        if only and name != only:
            continue
        i = servers[name]
        lines.append(
            f"{name}: ultimo_evento={i['last_ts']} "
            f"ultimo_cierre={i['last_closed'] or '-'} "
            f"ultimo_uso={i['last_use'] or '-'}@{i['last_use_ts'] or '-'} "
            f"-> {i['verdict']}")
    return lines


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--log", default=DEFAULT_LOG)
    ap.add_argument("--server", default="")
    args = ap.parse_args(argv)
    if not os.path.exists(args.log):
        print(f"Sin log en {args.log}")
        return 1
    with open(args.log, encoding="utf-8", errors="replace") as f:
        servers = analyze(f)
    out = report(servers, args.server or None)
    print("\n".join(out) if out else "Sin servers en el log.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
