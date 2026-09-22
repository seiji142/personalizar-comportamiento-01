#!/usr/bin/env python3
"""
Tests unitarios del merge por test ID en save_incremental (tarea #12).

Cubre el bug: `existing["models"][label] = cases` reemplazaba el bloque
completo del modelo, perdiendo los tests no re-ejecutados cuando se corria
con `--only-failures`.

Casos:
- Conserva tests no re-ejecutados del reporte anterior.
- Reemplaza el test re-ejecutado (nuevo valor pisa el viejo).
- No toca modelos que no aparecen en el resultado nuevo.
- Modelo nuevo se agrega al reporte existente.
- Reporte previo sin el modelo crea la entrada desde cero.

Ejecutar: python -m unittest test_report_merge -v
"""

import json
import os
import sys
import unittest
import importlib.util


def _load_run_advanced():
    """Carga run_advanced_tests.py como modulo (no es un package)."""
    script_path = os.path.join(os.path.dirname(__file__), "run_advanced_tests.py")
    spec = importlib.util.spec_from_file_location("run_advanced_tests", script_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


run_advanced = _load_run_advanced()


class TestMergeModelsReport(unittest.TestCase):

    def setUp(self):
        self.merge = run_advanced.merge_models_report

    def test_conserva_tests_no_reejecutados(self):
        existing = {
            "models": {
                "api/qwen/qwen3.8-27b": {
                    "A1": {"status": "PASS"},
                    "D1": {"status": "FAIL"},
                }
            }
        }
        # Solo se re-ejecuto D1 (caso parcial, estilo --only-failures)
        new_results = {
            "api/qwen/qwen3.8-27b": {
                "D1": {"status": "PASS"}
            }
        }
        merged = self.merge(existing, new_results)
        model = merged["models"]["api/qwen/qwen3.8-27b"]
        # A1 no re-ejecutado se conserva; D1 se actualiza
        self.assertEqual(model["A1"]["status"], "PASS")
        self.assertEqual(model["D1"]["status"], "PASS")

    def test_reejecutado_pisa_anterior(self):
        existing = {
            "models": {
                "api/qwen/qwen3.8-27b": {"C2": {"status": "FAIL"}}
            }
        }
        new_results = {
            "api/qwen/qwen3.8-27b": {"C2": {"status": "PASS"}}
        }
        model = self.merge(existing, new_results)["models"]["api/qwen/qwen3.8-27b"]
        self.assertEqual(model["C2"]["status"], "PASS")

    def test_no_toca_otros_modelos(self):
        existing = {
            "models": {
                "opencode/big-pickle": {"B1": {"status": "PASS"}},
                "api/qwen/qwen3.8-27b": {"D1": {"status": "FAIL"}},
            }
        }
        new_results = {
            "api/qwen/qwen3.8-27b": {"D1": {"status": "PASS"}}
        }
        merged = self.merge(existing, new_results)
        self.assertEqual(merged["models"]["opencode/big-pickle"]["B1"]["status"], "PASS")
        self.assertEqual(merged["models"]["api/qwen/qwen3.8-27b"]["D1"]["status"], "PASS")

    def test_modelo_nuevo_se_agrega(self):
        existing = {
            "models": {
                "opencode/big-pickle": {"B1": {"status": "PASS"}}
            }
        }
        new_results = {
            "api/qwen/qwen3.8-27b": {"D1": {"status": "PASS"}}
        }
        merged = self.merge(existing, new_results)
        self.assertIn("api/qwen/qwen3.8-27b", merged["models"])
        self.assertTrue("opencode/big-pickle" in merged["models"])

    def test_reporte_vacio_crea_desde_cero(self):
        existing = {}
        new_results = {
            "api/qwen/qwen3.8-27b": {"B1": {"status": "PASS"}}
        }
        merged = self.merge(existing, new_results)
        self.assertEqual(
            merged["models"]["api/qwen/qwen3.8-27b"]["B1"]["status"],
            "PASS",
        )

    def test_sin_models_previos_inicializa(self):
        existing = {"timestamp": "x"}  # reporte sin key "models"
        new_results = {"api/qwen/qwen3.8-27b": {"A1": {"status": "PASS"}}}
        merged = self.merge(existing, new_results)
        self.assertIn("models", merged)
        self.assertIn("timestamp", merged)  # metadata no se pierde


if __name__ == "__main__":
    unittest.main()