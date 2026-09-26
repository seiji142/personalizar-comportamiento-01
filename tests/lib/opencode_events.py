"""Parser de la salida NDJSON de ``opencode run --format json``.

Aislado en su propio modulo para que el acoplamiento al formato
de OpenCode este en un unico sitio y sea testeable con fixtures.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Iterable

log = logging.getLogger(__name__)

MEMORY_TOOL_NAMES = {
    "memory", "memory_search", "memory_save", "memory_read", "recall",
    "brain_ai_memory_search", "brain_ai_memory_save",
}
MEMORY_PATH_MARKERS = ("/memory/", "/episodes/", "memoria/", "episodios/")


@dataclass
class ToolCall:
    name: str
    args: dict[str, Any]
    output: str | None
    status: str
    call_id: str | None


@dataclass
class TokenUsage:
    input: int = 0
    output: int = 0
    reasoning: int = 0
    cache_read: int = 0
    cache_write: int = 0

    @property
    def total(self) -> int:
        return self.input + self.output + self.reasoning


@dataclass
class ParsedRun:
    text: str
    tool_calls: list[ToolCall]
    tokens: TokenUsage
    cost: float
    unknown_event_types: set[str] = field(default_factory=set)
    unparsable_lines: int = 0

    @property
    def memory_used(self) -> bool:
        """True solo si hubo una tool call REAL contra memoria.

        Normaliza guiones a guiones bajos: OpenCode emite
        brain-ai_memory_search/save (guion), el set usa brain_ai_*.
        """
        for tc in self.tool_calls:
            norm_name = tc.name.lower().replace("-", "_")
            if norm_name in MEMORY_TOOL_NAMES:
                return True
            blob = json.dumps(tc.args, ensure_ascii=False)
            if any(m in blob for m in MEMORY_PATH_MARKERS):
                return True
        return False

    @property
    def files_read(self) -> list[str]:
        out = []
        for tc in self.tool_calls:
            if tc.name in ("read", "glob", "grep", "list"):
                for key in ("filePath", "path", "pattern"):
                    if key in tc.args:
                        out.append(str(tc.args[key]))
                        break
        return out


def _extract_part(event: dict) -> dict:
    """OpenCode a veces envuelve la part en {"type":..., "part": {...}}
    y a veces la emite plana. Normalizamos a la part."""
    part = event.get("part")
    return part if isinstance(part, dict) else event


def _parse_tokens(part: dict) -> TokenUsage:
    t = part.get("tokens") or {}
    cache = t.get("cache") or {}
    return TokenUsage(
        input=int(t.get("input") or 0),
        output=int(t.get("output") or 0),
        reasoning=int(t.get("reasoning") or 0),
        cache_read=int(cache.get("read") or 0),
        cache_write=int(cache.get("write") or 0),
    )


def _parse_tool(part: dict) -> ToolCall:
    state = part.get("state") or {}
    return ToolCall(
        name=str(part.get("tool") or part.get("name") or "unknown"),
        args=dict(state.get("input") or part.get("input") or {}),
        output=state.get("output"),
        status=str(state.get("status") or "unknown"),
        call_id=part.get("callID") or part.get("id"),
    )


def parse_ndjson(lines: Iterable[str]) -> ParsedRun:
    texts: list[str] = []
    tools_by_id: dict[str, ToolCall] = {}
    tools_ordered: list[ToolCall] = []
    tokens = TokenUsage()
    cost = 0.0
    unknown: set[str] = set()
    bad = 0

    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            event = json.loads(raw)
        except json.JSONDecodeError:
            bad += 1
            log.debug("Linea NDJSON no parseable: %r", raw[:200])
            continue
        if not isinstance(event, dict):
            bad += 1
            continue

        part = _extract_part(event)
        ptype = str(part.get("type") or event.get("type") or "")

        if ptype == "text":
            texts.append(str(part.get("text") or ""))

        elif ptype in ("tool", "tool_use", "tool-invocation"):
            tc = _parse_tool(part)
            key = tc.call_id or f"idx{len(tools_ordered)}"
            if key in tools_by_id:
                tools_ordered[tools_ordered.index(tools_by_id[key])] = tc
            else:
                tools_ordered.append(tc)
            tools_by_id[key] = tc

        elif ptype in ("step-finish", "step_finish"):
            tu = _parse_tokens(part)
            tokens.input += tu.input
            tokens.output += tu.output
            tokens.reasoning += tu.reasoning
            tokens.cache_read += tu.cache_read
            tokens.cache_write += tu.cache_write
            cost += float(part.get("cost") or 0.0)

        elif ptype in ("step-start", "step_start", "reasoning", "snapshot", "patch"):
            pass

        else:
            unknown.add(ptype or "<sin tipo>")

    return ParsedRun(
        text="".join(texts).strip(),
        tool_calls=tools_ordered,
        tokens=tokens,
        cost=cost,
        unknown_event_types=unknown,
        unparsable_lines=bad,
    )
