#!/usr/bin/env python3
"""Unit tests de la tarea 15: deteccion 429 TPD (cuota agotada != fallo).

Cubre: parser de 429 (TPD vs transitorio), espera exacta <=90s, sondeo
(quota_probe), reclasificacion de reportes, reply_status (fix case-sensitivity
de test_ai_structure), corte de run_cases_for_model y gates de suite_runner.

Ejecutar:
  python tests/scripts/test_rate_limit_tpd.py
  python -m pytest tests/scripts/test_rate_limit_tpd.py -v
"""

import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "tests", "lib"))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "scripts"))

from rate_limit import (  # noqa: E402
    BLOCKED_PREFIX,
    case_has_tpd_evidence,
    classify_probe,
    compute_wait,
    blocked_message,
    is_blocked_error,
    parse_rate_limit,
    parse_retry_after,
    reclassify_file_tpd,
    reclassify_report_tpd,
)

TPD_GPT = (
    "Rate limit reached for model `openai/gpt-oss-20b` in organization "
    "`org_01knwtngbaexgs3km5eskg9ybz` service tier `on_demand` on tokens per "
    "day (TPD): Limit 200000, Used 198485, Requested 4646. Please try again "
    "in 22m32.591999999s. Need more tokens? Upgrade to Dev Tier today at "
    "https://console.groq.com/settings/billing"
)
TPD_QWEN = (
    "Rate limit reached for model `qwen/qwen3.8-27b` in organization "
    "`org_01kpm1mr8pf9y94mgx1qh5cavb` service tier `on_demand` on tokens per "
    "day (TPD): Limit 200000, Used 195679, Requested 5612. Please try again "
    "in 9m17.712s. Need more tokens? Upgrade to Dev Tier today at "
    "https://console.groq.com/settings/billing"
)
TPM_TRANSIENT = (
    "Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_x` "
    "service tier `on_demand` on tokens per minute (TPM): Limit 30000, "
    "Used 28000, Requested 1500. Please try again in 5s."
)
LONG_WAIT_NO_MARKER = (
    "Rate limit reached for model `x` on tokens per minute (TPM): "
    "Limit 100, Used 90. Please try again in 130s."
)


class TestParseRateLimit(unittest.TestCase):
    def test_mensaje_tpd_gpt_real(self):
        info = parse_rate_limit(TPD_GPT)
        self.assertTrue(info["is_429"])
        self.assertTrue(info["is_tpd"])
        self.assertEqual(info["used"], 198485)
        self.assertEqual(info["limit"], 200000)
        self.assertAlmostEqual(info["retry_after_s"], 22 * 60 + 32.591999999)

    def test_mensaje_tpd_qwen_real(self):
        info = parse_rate_limit(TPD_QWEN)
        self.assertTrue(info["is_tpd"])
        self.assertEqual(info["used"], 195679)
        self.assertAlmostEqual(info["retry_after_s"], 9 * 60 + 17.712)

    def test_tpm_transitorio_no_es_tpd(self):
        info = parse_rate_limit(TPM_TRANSIENT)
        self.assertTrue(info["is_429"])
        self.assertFalse(info["is_tpd"])
        self.assertEqual(info["retry_after_s"], 5.0)

    def test_espera_larga_sin_marcador_es_tpd(self):
        info = parse_rate_limit(LONG_WAIT_NO_MARKER)
        self.assertTrue(info["is_429"])
        self.assertTrue(info["is_tpd"])
        self.assertEqual(info["retry_after_s"], 130.0)

    def test_mensaje_sin_429(self):
        info = parse_rate_limit("connection reset by peer")
        self.assertFalse(info["is_429"])
        self.assertFalse(info["is_tpd"])
        self.assertIsNone(info["retry_after_s"])
        self.assertIsNone(info["used"])

    def test_mensaje_vacio(self):
        info = parse_rate_limit("")
        self.assertFalse(info["is_429"])

    def test_retry_after_formatos(self):
        self.assertEqual(parse_retry_after("try again in 5s"), 5.0)
        self.assertEqual(parse_retry_after("try again in 1m30s"), 90.0)
        self.assertEqual(parse_retry_after("try again in 2m"), None)
        self.assertIsNone(parse_retry_after("sin espera"))


class TestComputeWait(unittest.TestCase):
    def test_espera_exacta_cuando_la_indica_la_api(self):
        self.assertEqual(compute_wait(0, 45, 5), 46)  # exacta +1s de margen
        self.assertEqual(compute_wait(1, 30, 5), 31)

    def test_backoff_original_sin_indicacion(self):
        self.assertEqual(compute_wait(0, None, 5), 5)
        self.assertEqual(compute_wait(1, None, 5), 10)
        self.assertEqual(compute_wait(2, None, 5), 20)

    def test_espera_mayor_a_90_no_es_exacta(self):
        # >90s no se espera asi (si es >120s es TPD y no llega aqui)
        self.assertEqual(compute_wait(0, 91, 5), 5)
        self.assertEqual(compute_wait(2, 100, 5), 20)

    def test_margen_en_el_limite(self):
        self.assertEqual(compute_wait(0, 90, 5), 91)


class TestClassifyProbe(unittest.TestCase):
    def test_ok(self):
        self.assertEqual(classify_probe(True, ""), "OK")

    def test_blocked_tpd(self):
        self.assertEqual(classify_probe(False, TPD_GPT), "BLOCKED_TPD")

    def test_transient(self):
        self.assertEqual(classify_probe(False, TPM_TRANSIENT), "TRANSIENT")

    def test_error_sin_429(self):
        self.assertEqual(classify_probe(False, "Invalid API Key"), "ERROR")


class TestBlockedMessage(unittest.TestCase):
    def test_is_blocked_error(self):
        self.assertTrue(is_blocked_error(f"{BLOCKED_PREFIX} cuota diaria"))
        self.assertFalse(is_blocked_error("[RATE LIMIT] agotados"))
        self.assertFalse(is_blocked_error(None))
        self.assertFalse(is_blocked_error(""))

    def test_blocked_message_con_uso(self):
        msg = blocked_message(parse_rate_limit(TPD_GPT), "openai/gpt-oss-20b")
        self.assertTrue(msg.startswith(BLOCKED_PREFIX))
        self.assertIn("Used 198485/200000", msg)
        self.assertIn("reintentar en", msg)


class TestReclassify(unittest.TestCase):
    def _adv_case(self, status, text):
        return {"status": status, "reasons": [text], "response_full": text}

    def test_evidencia_tpd(self):
        case = self._adv_case("ERROR", f"[RATE LIMIT] 429 - {TPD_GPT}")
        self.assertTrue(case_has_tpd_evidence(case))

    def test_fail_sin_429_no_es_evidencia(self):
        case = self._adv_case("FAIL", "Falta keyword 'seguridad'")
        self.assertFalse(case_has_tpd_evidence(case))

    def test_pass_nunca_se_toca(self):
        case = self._adv_case("PASS", f"429 tokens per day {TPD_GPT}")
        self.assertFalse(case_has_tpd_evidence(case))

    def test_reclasifica_formato_avanzada(self):
        report = {"models": {
            "api/qwen/qwen3.8-27b": {
                "B1": self._adv_case("ERROR", f"429 tokens per day: {TPD_QWEN}"),
                "A1": self._adv_case("PASS", "ok"),
                "C1": self._adv_case("FAIL", "falta keyword"),
            },
            "opencode/big-pickle": {
                "B1": self._adv_case("ERROR", f"429 tokens per day {TPD_GPT}"),
            },
        }}
        changed = reclassify_report_tpd(
            report, model_labels={"api/qwen/qwen3.8-27b"})
        self.assertEqual(changed, 1)
        self.assertEqual(report["models"]["api/qwen/qwen3.8-27b"]["B1"]["status"],
                         "BLOCKED_TPD")
        self.assertEqual(report["models"]["api/qwen/qwen3.8-27b"]["A1"]["status"],
                         "PASS")
        self.assertEqual(report["models"]["api/qwen/qwen3.8-27b"]["C1"]["status"],
                         "FAIL")
        # Otro modelo no se toca sin label
        self.assertEqual(report["models"]["opencode/big-pickle"]["B1"]["status"],
                         "ERROR")

    def test_reclasifica_formato_estructura(self):
        report = {"models": {"api/openai/gpt-oss-20b": {
            "timestamp": "2026-09-23",
            "results": [
                {"id": 1, "status": "FAIL",
                 "reply": f"[ERROR] Error code: 429 - {TPD_GPT}",
                 "reasons": ["Falta keyword 'ingeniero'"]},
                {"id": 2, "status": "PASS", "reply": "hola ingeniero", "reasons": []},
            ],
        }}}
        changed = reclassify_report_tpd(report)
        self.assertEqual(changed, 1)
        results = report["models"]["api/openai/gpt-oss-20b"]["results"]
        self.assertEqual(results[0]["status"], "BLOCKED_TPD")
        self.assertEqual(results[1]["status"], "PASS")

    def test_reclassify_file_tpd(self):
        payload = {"models": {"m": {"B1": self._adv_case(
            "ERROR", f"429 tokens per day {TPD_GPT}")}}}
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "report.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f)
            self.assertEqual(reclassify_file_tpd(path), 1)
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(data["models"]["m"]["B1"]["status"], "BLOCKED_TPD")
            # Idempotente: ya reclasificado no vuelve a cambiar nada
            self.assertEqual(reclassify_file_tpd(path), 0)

    def test_reclassify_file_inexistente(self):
        self.assertEqual(reclassify_file_tpd("/no/existe.json"), 0)


class TestReplyStatus(unittest.TestCase):
    """Regression: el texto del 429 llegaba como '[ERROR]' en mayusculas,
    no casaba con '[error]' y se contaba como FAIL de comportamiento."""

    def setUp(self):
        import test_ai_structure
        self.mod = test_ai_structure

    def test_error_de_429_no_es_fail(self):
        reply = f"[ERROR] Error code: 429 - {TPD_GPT}"
        self.assertEqual(self.mod.reply_status(reply), "ERROR")

    def test_blocked_tpd_prefijo(self):
        self.assertEqual(
            self.mod.reply_status(f"{BLOCKED_PREFIX} cuota diaria"), "BLOCKED_TPD")
        self.assertEqual(
            self.mod.reply_status("[blocked_tpd] x"), "BLOCKED_TPD")

    def test_timeout_sigue_siendo_error(self):
        self.assertEqual(self.mod.reply_status("[TIMEOUT]"), "ERROR")

    def test_respuesta_normal_es_valida(self):
        self.assertIsNone(self.mod.reply_status("eres un ingeniero de software"))
        self.assertIsNone(self.mod.reply_status(""))


class TestRunCasesCortaEnBlocked(unittest.TestCase):
    def setUp(self):
        import run_advanced_tests
        self.mod = run_advanced_tests

    def test_rompe_el_loop_en_el_primer_blocked(self):
        class BlockedRunner:
            calls = 0

            def query(self, prompt):
                BlockedRunner.calls += 1
                return {"text": "", "tool_calls": [], "memory_used": False,
                        "error": f"{BLOCKED_PREFIX} cuota diaria (TPD) agotada"}

        questions = [{"id": f"T{i}", "name": "x", "category": "y", "prompt": "p"}
                     for i in range(5)]
        per_case = self.mod.run_cases_for_model(
            "api/qwen/qwen3.8-27b", BlockedRunner(), questions,
            report_path=None, all_results={})
        self.assertEqual(BlockedRunner.calls, 1)
        self.assertEqual(len(per_case), 1)
        self.assertEqual(per_case["T0"]["status"], "BLOCKED_TPD")

    def test_only_failures_incluye_blocked_tpd(self):
        payload = {"models": {"m": {
            "B1": {"status": "BLOCKED_TPD"},
            "A1": {"status": "PASS"},
            "C1": {"status": "FAIL"},
        }}}
        original = self.mod.REPORT_FILE
        try:
            with tempfile.TemporaryDirectory() as tmp:
                self.mod.REPORT_FILE = os.path.join(tmp, "r.json")
                with open(self.mod.REPORT_FILE, "w", encoding="utf-8") as f:
                    json.dump(payload, f)
                failed = self.mod.load_previous_failures()
                self.assertEqual(failed, {"B1", "C1"})
        finally:
            self.mod.REPORT_FILE = original


class TestGates(unittest.TestCase):
    def setUp(self):
        import suite_runner
        self.mod = suite_runner
        self._answers_dir = suite_runner.ANSWERS_DIR
        self._tmp = tempfile.TemporaryDirectory()
        suite_runner.ANSWERS_DIR = self._tmp.name

    def tearDown(self):
        self.mod.ANSWERS_DIR = self._answers_dir
        self._tmp.cleanup()

    def _write(self, name, payload):
        path = os.path.join(self._tmp.name, name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        return path

    def _adv(self, statuses):
        return {"models": {lab: {f"T{i}": {"status": st}
                                 for i, st in enumerate(statuss)}
                           for lab, statuss in statuses.items()}}

    def test_avanzada_todo_pass(self):
        labels = ["a", "b"]
        self._write("advanced_validation_report.json", self._adv(
            {lab: ["PASS"] * 23 for lab in labels}))
        ok, detail = self.mod.model_gate(
            "advanced_validation_report.json", labels, 23, "cases")
        self.assertTrue(ok, detail)

    def test_avanzada_un_fail_rompe(self):
        labels = ["a", "b"]
        st = {lab: ["PASS"] * 23 for lab in labels}
        st["a"] = ["FAIL"] + ["PASS"] * 22
        self._write("advanced_validation_report.json", self._adv(st))
        ok, _ = self.mod.model_gate(
            "advanced_validation_report.json", labels, 23, "cases")
        self.assertFalse(ok)

    def test_avanzada_blocked_tpd_no_rompe(self):
        labels = ["a", "b"]
        st = {lab: ["PASS"] * 23 for lab in labels}
        st["a"] = ["BLOCKED_TPD"] * 23
        self._write("advanced_validation_report.json", self._adv(st))
        ok, _ = self.mod.model_gate(
            "advanced_validation_report.json", labels, 23, "cases")
        self.assertTrue(ok)

    def test_avanzada_n_incorrecto_rompe(self):
        labels = ["a", "b"]
        self._write("advanced_validation_report.json", self._adv(
            {lab: ["PASS"] * 22 for lab in labels}))
        ok, _ = self.mod.model_gate(
            "advanced_validation_report.json", labels, 23, "cases")
        self.assertFalse(ok)

    def test_avanzada_modelo_ausente_rompe(self):
        self._write("advanced_validation_report.json", self._adv(
            {"a": ["PASS"] * 23}))
        ok, detail = self.mod.model_gate(
            "advanced_validation_report.json", ["a", "b"], 23, "cases")
        self.assertFalse(ok)
        self.assertEqual(detail["b"], "AUSENTE")

    def test_estructura_estados(self):
        labels = ["a", "b"]

        def mk(results_by_label):
            return {"models": {lab: {"timestamp": "x", "results": [
                {"id": i, "status": st} for i, st in enumerate(sts)]}
                for lab, sts in results_by_label.items()}}

        self._write("ai_validation_report.json", mk(
            {lab: ["PASS"] * 5 for lab in labels}))
        ok, _ = self.mod.model_gate(
            "ai_validation_report.json", labels, 5, "results")
        self.assertTrue(ok)

        self._write("ai_validation_report.json", mk(
            {lab: ["BLOCKED_TPD"] * 5 for lab in labels}))
        ok, _ = self.mod.model_gate(
            "ai_validation_report.json", labels, 5, "results")
        self.assertTrue(ok)

        bad = {lab: ["FAIL"] + ["PASS"] * 4 for lab in labels}
        self._write("ai_validation_report.json", mk(bad))
        ok, _ = self.mod.model_gate(
            "ai_validation_report.json", labels, 5, "results")
        self.assertFalse(ok)

    def test_summary_gate(self):
        self.assertTrue(self.mod.summary_gate(
            {"a": "OK", "b": "BLOCKED_TPD"})[0])
        ok, bad = self.mod.summary_gate({"a": "OK", "b": "FAIL"})
        self.assertFalse(ok)
        self.assertEqual(bad, {"b": "FAIL"})
        self.assertFalse(self.mod.summary_gate({})[0])

    def test_api_disponible_gate(self):
        self._write("quota_status.json", {"accounts": {
            "GROQ_CUENTA_1": {"status": "OK"},
            "GROQ_CUENTA_2": {"status": "BLOCKED_TPD"}}})
        ok, detail = self.mod.api_disponible_gate(
            os.path.join(self._tmp.name, "quota_status.json"))
        self.assertTrue(ok, detail)

        self._write("quota_status.json", {"accounts": {
            "GROQ_CUENTA_1": {"status": "ERROR"}}})
        ok, _ = self.mod.api_disponible_gate(
            os.path.join(self._tmp.name, "quota_status.json"))
        self.assertFalse(ok)

        ok, _ = self.mod.api_disponible_gate(
            os.path.join(self._tmp.name, "no_existe.json"))
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main(verbosity=2)
