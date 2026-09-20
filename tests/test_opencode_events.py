"""Tests del parser NDJSON de OpenCode."""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests.lib.opencode_events import parse_ndjson, ToolCall, TokenUsage

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "opencode_sample.ndjson")


def _read_fixture():
    with open(FIXTURE, "rb") as f:
        raw = f.read()
    if raw[:2] == b'\xff\xfe':
        return raw.decode('utf-16-le')
    return raw.decode('utf-8')


def test_parser_contra_fixture_real():
    parsed = parse_ndjson(_read_fixture().splitlines())
    assert parsed.tool_calls, "El fixture deberia contener al menos una tool call"
    assert any(tc.name == "read" for tc in parsed.tool_calls)
    assert parsed.tokens.total > 0
    assert parsed.text
    assert not parsed.unknown_event_types, parsed.unknown_event_types


def test_tool_calls_tienen_datos():
    parsed = parse_ndjson(_read_fixture().splitlines())
    read_calls = [tc for tc in parsed.tool_calls if tc.name == "read"]
    assert len(read_calls) >= 1
    tc = read_calls[0]
    assert tc.status == "completed"
    assert "filePath" in tc.args
    assert tc.output is not None
    assert len(tc.output) > 0


def test_tokens_acumulados():
    parsed = parse_ndjson(_read_fixture().splitlines())
    assert parsed.tokens.input > 0
    assert parsed.tokens.output > 0


def test_memory_used_no_es_heuristico():
    lines = ['{"type":"text","part":{"type":"text","text":"Segun mi memoria del episodio 3..."}}']
    parsed = parse_ndjson(lines)
    assert parsed.memory_used is False


def test_memory_used_por_tool_real():
    lines = ['{"type":"tool_use","part":{"type":"tool","tool":"read","callID":"c1","state":{"status":"completed","input":{"filePath":"/proj/memory/ep3.md"},"output":"..."}}}']
    parsed = parse_ndjson(lines)
    assert parsed.memory_used is True


def test_memory_used_por_tool_name():
    lines = ['{"type":"tool_use","part":{"type":"tool","tool":"brain_ai_memory_search","callID":"c2","state":{"status":"completed","input":{"query":"test"},"output":"..."}}}']
    parsed = parse_ndjson(lines)
    assert parsed.memory_used is True


def test_files_read():
    parsed = parse_ndjson(_read_fixture().splitlines())
    files = parsed.files_read
    assert len(files) >= 1
    assert any("ai_validation_report" in f for f in files)


def test_lineas_vacias():
    parsed = parse_ndjson(["", "  ", "\n"])
    assert parsed.text == ""
    assert parsed.tool_calls == []
    assert parsed.unparsable_lines == 0


def test_lineas_rotas():
    parsed = parse_ndjson(["esto no es json", '{"type":"text","part":{"type":"text","text":"hola"}}'])
    assert parsed.text == "hola"
    assert parsed.unparsable_lines == 1
