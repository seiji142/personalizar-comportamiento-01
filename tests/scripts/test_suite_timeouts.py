#!/usr/bin/env python3
"""Tests de los timeouts por paso de run_all_tests.py (tarea 16G).

run_all_tests.py no se puede importar (ejecuta la suite al importarse), asi
que el test parsea su fuente. La invariante: cada cap de paso tiene que ser
>= maximo teorico/medido de sus hijos, si no el proceso se mata a mitad de
corrida y el merge de resultados se pierde.

Evidencia del 28/09 (tests/answers/test_run_summary.json):
  run_advanced_tests.py --api qwen/qwen3.8-27b -> TIMEOUT 1200
  (la suma de los 23 tests de qwen = 1598s, imposible dentro de 1200s).

Ejecutar: python tests/scripts/test_suite_timeouts.py -v
"""

import os
import re
import sys
import unittest

RUN_ALL = os.path.join(os.path.dirname(__file__), "..", "..", "run_all_tests.py")

# Maximos teoricos por hijo
STRUCTURE_API_MAX_S = 5 * 30      # 5 tests x timeout=30s de query_api
STRUCTURE_NATIVE_MAX_S = 5 * 180  # 5 tests x QUERY_TIMEOUT=180s
ADVANCED_NATIVE_MEASURED_S = 694  # mimo 28/09 (el mayor de los nativos)
ADVANCED_API_MEASURED_S = 1598    # qwen 28/09 (suma de los 23 tests)


def _source():
    with open(RUN_ALL, encoding="utf-8") as f:
        return f.read()


def _constant(name):
    m = re.search(rf"^{name}\s*=\s*(\d+)\s*$", _source(), re.M)
    if not m:
        raise AssertionError(f"constante {name} no encontrada en run_all_tests.py")
    return int(m.group(1))


class TestSuiteTimeouts(unittest.TestCase):
    def test_estructura_api_cubre_maximo_teorico(self):
        cap = _constant("STRUCTURE_API_TIMEOUT_S")
        self.assertGreaterEqual(cap, STRUCTURE_API_MAX_S,
                                f"cap {cap}s < maximo teorico {STRUCTURE_API_MAX_S}s")

    def test_estructura_nativa_cubre_maximo_teorico(self):
        cap = _constant("STRUCTURE_NATIVE_TIMEOUT_S")
        self.assertGreaterEqual(cap, STRUCTURE_NATIVE_MAX_S,
                                f"cap {cap}s < maximo teorico {STRUCTURE_NATIVE_MAX_S}s")

    def test_avanzada_api_cubre_qwen_medido(self):
        """16G: con cap < 1598s qwen siempre muere a mitad de corrida."""
        cap = _constant("ADVANCED_API_TIMEOUT_S")
        self.assertGreaterEqual(cap, ADVANCED_API_MEASURED_S,
                                f"cap {cap}s < suma medida {ADVANCED_API_MEASURED_S}s")
        self.assertGreaterEqual(cap, 1800, "margen minimo para retries 429")

    def test_avanzada_nativa_cubre_nativo_medido(self):
        cap = _constant("ADVANCED_NATIVE_TIMEOUT_S")
        self.assertGreaterEqual(cap, ADVANCED_NATIVE_MEASURED_S,
                                f"cap {cap}s < maximo medido {ADVANCED_NATIVE_MEASURED_S}s")

    def test_los_runs_usan_las_constantes(self):
        """Ningun run_cmd de modelos vuelve a un timeout numerado inline.

        El unico numero admitido es el default de la firma run_cmd(...,
        timeout=300); los callsites usan constantes.
        """
        src = _source()
        inline = []
        for i, line in enumerate(src.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue  # comentarios citan timeouts de otros archivos
            if re.search(r"timeout=\d+", stripped) and "def run_cmd" not in stripped:
                inline.append((i, stripped))
        self.assertEqual(inline, [], f"timeouts numerados en run_all_tests.py: {inline}")
        for const in ("STRUCTURE_API_TIMEOUT_S", "ADVANCED_API_TIMEOUT_S",
                      "STRUCTURE_NATIVE_TIMEOUT_S", "ADVANCED_NATIVE_TIMEOUT_S"):
            self.assertIn(f"timeout={const}", src)


if __name__ == "__main__":
    unittest.main()
