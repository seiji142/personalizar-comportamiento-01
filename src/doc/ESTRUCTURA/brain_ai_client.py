#!/usr/bin/env python3
"""
Cliente HTTP reutilizable para brain-ai-01.

Extrae la logica de memoria.py y mcp_bridge.py en un modulo compartido.
Usado por model_runner.py para ejecutar tool calls de memoria.
"""

import json
import os
import requests
from datetime import datetime


BRAIN_API = os.getenv("BRAIN_AI_URL", "http://localhost:8000")


def search(query, project=None, top_k=5, collection="semantic"):
    """Busca episodios en memoria via HTTP."""
    try:
        r = requests.post(f"{BRAIN_API}/retrieve", json={
            "query": query,
            "top_k": top_k,
            "project": project,
            "collection": collection
        }, timeout=30)
        result = r.json()

        if "results" in result:
            items = result["results"]
            if not items:
                return {"ok": True, "results": [], "text": "No se encontraron resultados."}

            lines = [f"Encontrados {len(items)} resultados:"]
            for i, item in enumerate(items, 1):
                text = item.get("text", "")[:200]
                score = item.get("score", 0)
                proj = item.get("project", "desconocido")
                lines.append(f"{i}. [{score:.2f}] (Proyecto: {proj}) {text}")

            return {"ok": True, "results": items, "text": "\n".join(lines)}

        return {"ok": False, "error": result.get("error", "Unknown error")}

    except requests.ConnectionError:
        return {"ok": False, "error": f"No se puede conectar a brain-ai-01 en {BRAIN_API}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def save(project, decision, evidence="", tags=None):
    """Guarda un episodio en memoria via HTTP."""
    try:
        r = requests.post(f"{BRAIN_API}/ingest", json={"episode": {
            "project": project,
            "source_type": "chat",
            "author": "modelo",
            "title": decision[:50],
            "summary": decision,
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "decisions": [{"text": decision}],
            "evidence": [{"type": "doc", "url_or_path": "", "excerpt": evidence}] if evidence else [],
            "tags": tags or []
        }}, timeout=30)
        result = r.json()

        if result.get("ok"):
            episode_id = result.get("episode_id", "unknown")
            return {"ok": True, "episode_id": episode_id, "text": f"Episodio guardado. ID: {episode_id}"}

        return {"ok": False, "error": result.get("error", "Unknown error")}

    except requests.ConnectionError:
        return {"ok": False, "error": f"No se puede conectar a brain-ai-01 en {BRAIN_API}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def consolidate(project=None):
    """Consolida memoria episodica a semantica."""
    try:
        r = requests.post(f"{BRAIN_API}/consolidate", json={"project": project}, timeout=30)
        result = r.json()

        promotions = result.get("promotions", 0)
        contradictions = result.get("contradictions", 0)
        text = f"Consolidacion: {promotions} episodios promovidos, {contradictions} contradicciones."

        return {"ok": True, "promotions": promotions, "contradictions": contradictions, "text": text}

    except requests.ConnectionError:
        return {"ok": False, "error": f"No se puede conectar a brain-ai-01 en {BRAIN_API}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def execute_tool(tool_name, arguments):
    """Ejecuta un tool por nombre. Usado por el tool loop de Groq."""
    handlers = {
        "brain_ai_memory_search": lambda args: search(
            query=args.get("query", ""),
            project=args.get("project"),
            top_k=args.get("top_k", 5),
            collection=args.get("collection", "semantic")
        ),
        "brain_ai_memory_save": lambda args: save(
            project=args.get("project", ""),
            decision=args.get("decision", ""),
            evidence=args.get("evidence", ""),
            tags=args.get("tags")
        ),
        "brain_ai_memory_consolidate": lambda args: consolidate(
            project=args.get("project")
        ),
        # Aliases sin guion bajo (para compatibilidad con MCP names)
        "memory_search": lambda args: search(
            query=args.get("query", ""),
            project=args.get("project"),
            top_k=args.get("top_k", 5),
            collection=args.get("collection", "semantic")
        ),
        "memory_save": lambda args: save(
            project=args.get("project", ""),
            decision=args.get("decision", ""),
            evidence=args.get("evidence", ""),
            tags=args.get("tags")
        ),
        "memory_consolidate": lambda args: consolidate(
            project=args.get("project")
        ),
    }

    handler = handlers.get(tool_name)
    if handler:
        return handler(arguments)
    return {"ok": False, "error": f"Tool desconocida: {tool_name}"}


# Schema de tools para Groq/OpenAI API (formato function calling)
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "brain_ai_memory_search",
            "description": "Busca episodios, decisiones y conocimiento en la memoria persistente. Usar ANTES de responder preguntas sobre decisiones pasadas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Texto a buscar (ej: 'configuracion de base de datos')"
                    },
                    "project": {
                        "type": "string",
                        "description": "Proyecto a filtrar"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Numero maximo de resultados",
                        "default": 5
                    },
                    "collection": {
                        "type": "string",
                        "enum": ["semantic", "episodic"],
                        "default": "semantic"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "brain_ai_memory_save",
            "description": "Guarda un episodio en memoria. Usar DESPUES de tomar una decision importante.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project": {
                        "type": "string",
                        "description": "Nombre del proyecto"
                    },
                    "decision": {
                        "type": "string",
                        "description": "Decision tomada o leccion aprendida"
                    },
                    "evidence": {
                        "type": "string",
                        "description": "Evidencia que respalda la decision"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags descriptivos"
                    }
                },
                "required": ["project", "decision"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "brain_ai_memory_consolidate",
            "description": "Consolida episodios en conocimiento semantico.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project": {
                        "type": "string",
                        "description": "Proyecto a consolidar"
                    }
                }
            }
        }
    }
]
