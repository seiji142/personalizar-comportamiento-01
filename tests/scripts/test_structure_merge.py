#!/usr/bin/env python3
"""
Tests unitarios del merge por test ID en test_ai_structure (tarea 16I).

Cubre el bug: `generate_report` reemplazaba `report["models"][label]`
entero con solo los re-ejecutados, y el gate `estructura_4x5` (exige n=5)
quedaba roto tras `--only-failures`. La avanzada ya mergea por ID
(`merge_models_report`, tarea #12); estructura guarda lista [{id, ...}]
y necesita `merge_structure_results`.

Casos:
- Conserva tests no re-ejecutados del reporte anterior.
- Reemplaza el test re-ejecutado (nuevo valor pisa el viejo).
- No toca modelos que no aparecen en el resultado nuevo.
- Orden: previos primero, nuevos al final.
- Listas vacias / sin id se toleran.

Ejecutar: python -m unittest test_structure_merge -v (desde tests/scripts)
"""

import importlib.util
import os
import unittest


def _load_structure():
    """Carga test_ai_structure.py como modulo (no es un package)."""
    script_path = os.path.join(os.path.dirname(__file__), "test_ai_structure.py")
    spec = importlib.util.spec_from_file_location("test_ai_structure", script_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


structure = _load_structure()


class TestMergeStructureResults(unittest.TestCase):

    def setUp(self):
        self.merge = structure.merge_structure_results

    def _r(self, tid, status):
        return {"id": tid, "target": "t", "description": "d",
                "status": status, "reply": "..."}

    def test_conserva_no_reejecutados(self):
        prev = [self._r("T1", "PASS"), self._r("T2", "PASS"),
                self._r("T3", "PASS"), self._r("T4", "FAIL"),
                self._r("T5", "PASS")]
        new = [self._r("T4", "PASS")]  # --only-failures re-ejecuto solo T4
        merged = self.merge(prev, new)
        self.assertEqual(len(merged), 5)  # gate estructura_4x5 intacto
        by_id = {r["id"]: r["status"] for r in merged}
        self.assertEqual(by_id["T4"], "PASS")
        self.assertEqual(by_id["T1"], "PASS")

    def test_reejecutado_pisa_anterior(self):
        prev = [self._r("T1", "FAIL")]
        merged = self.merge(prev, [self._r("T1", "PASS")])
        self.assertEqual(merged[0]["status"], "PASS")

    def test_orden_previos_primero(self):
        prev = [self._r("T2", "PASS")]
        new = [self._r("T1", "PASS")]
        merged = self.merge(prev, new)
        self.assertEqual([r["id"] for r in merged], ["T2", "T1"])

    def test_previo_vacio(self):
        merged = self.merge([], [self._r("T1", "PASS")])
        self.assertEqual(len(merged), 1)

    def test_nuevo_vacio_conserva(self):
        prev = [self._r("T1", "PASS")]
        self.assertEqual(self.merge(prev, []), prev)

    def test_entradas_sin_id_se_ignoran(self):
        prev = [{"status": "PASS"}]
        merged = self.merge(prev, [self._r("T1", "PASS")])
        self.assertEqual([r["id"] for r in merged], ["T1"])


if __name__ == "__main__":
    unittest.main()
