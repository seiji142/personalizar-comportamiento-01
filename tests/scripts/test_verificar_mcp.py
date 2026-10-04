#!/usr/bin/env python3
"""
Tests unitarios de verificar_mcp_esquema.py (tarea 16N).

El script parsea el log de OpenCode y dictamina por server si su
conexion esta VIVA o MUERTA (cierre posterior al ultimo uso ->
el proceso largo no reconecta -> reiniciar OpenCode).

Ejecutar: python -m unittest test_verificar_mcp -v (desde tests/scripts)
"""

import importlib.util
import os
import unittest


def _load():
    path = os.path.join(os.path.dirname(__file__), "verificar_mcp_esquema.py")
    spec = importlib.util.spec_from_file_location("verificar_mcp_esquema", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


vmc = _load()


def _line(ts, msg, extra=""):
    return (f"timestamp={ts} level=INFO run=abc123 "
            f"message={msg} {extra}".rstrip())


class TestParseLine(unittest.TestCase):

    def test_sin_timestamp_es_none(self):
        self.assertIsNone(vmc.parse_line("linea sin evento"))

    def test_cierre_con_server(self):
        ev = vmc.parse_line(_line("2026-09-28T12:34:19Z",
                                  '"MCP connection closed"', "server=brain-ai"))
        self.assertEqual(ev["server"], "brain-ai")
        self.assertEqual(ev["message"], "MCP connection closed")

    def test_permiso_extrae_tool(self):
        ev = vmc.parse_line(_line("2026-09-28T12:00:00Z",
                                  "evaluated permission=brain-ai_memory_search"))
        self.assertEqual(ev["permission"], "brain-ai_memory_search")


class TestAnalyze(unittest.TestCase):

    def test_uso_posterior_al_cierre_es_vivo(self):
        lines = [
            _line("2026-09-28T12:34:19Z", '"MCP connection closed"',
                  "server=brain-ai"),
            _line("2026-09-28T23:05:00Z",
                  "evaluated permission=brain-ai_memory_search"),
        ]
        info = vmc.analyze(lines)["brain-ai"]
        self.assertEqual(info["last_closed"], "2026-09-28T12:34:19Z")
        self.assertEqual(info["last_use"], "brain-ai_memory_search")
        self.assertEqual(info["verdict"], "VIVO")

    def test_cierre_sin_uso_posterior_es_muerto(self):
        lines = [
            _line("2026-09-28T10:00:00Z",
                  "evaluated permission=brain-ai_memory_search"),
            _line("2026-09-28T12:34:19Z", '"MCP connection closed"',
                  "server=brain-ai"),
        ]
        info = vmc.analyze(lines)["brain-ai"]
        self.assertEqual(info["verdict"], "MUERTO: reiniciar OpenCode")

    def test_unavailable_queda_registrado(self):
        lines = [_line("2026-09-28T12:00:00Z", "x",
                       "server unavailable key=brain-ai")]
        info = vmc.analyze(lines)["brain-ai"]
        self.assertEqual(info["last_unavailable"], "2026-09-28T12:00:00Z")

    def test_uso_se_atribuye_al_server_correcto(self):
        lines = [
            _line("2026-09-28T12:00:00Z", '"MCP connection closed"',
                  "server=git_publisher"),
            _line("2026-09-28T12:01:00Z",
                  "evaluated permission=git_publisher_git_ver_estado"),
            _line("2026-09-28T12:02:00Z",
                  "evaluated permission=brain-ai_memory_search"),
        ]
        servers = vmc.analyze(lines)
        self.assertEqual(
            servers["git_publisher"]["last_use"],
            "git_publisher_git_ver_estado")
        # brain-ai nunca aparecio en server=/unavailable: no se inventa
        self.assertNotIn("brain-ai", servers)


if __name__ == "__main__":
    unittest.main()
