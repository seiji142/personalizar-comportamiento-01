#!/usr/bin/env python3
"""
Valida las respuestas del agente OpenCode (YO) contra los .ai/ rules.
No necesita API externa: lee agent_answers.json y verifica keywords localmente.
"""

import json
import re
import sys
from datetime import datetime

ANSWERS_FILE = "src/doc/ESTRUCTURA/agent_answers.json"
QUESTIONS_FILE = "src/doc/ESTRUCTURA/agent_questions.json"


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_validation(question, answer_text):
    reply = answer_text.lower()
    passed = True
    reasons = []

    for kw in question["expected_contains"]:
        if re.search(rf'\b{re.escape(kw.lower())}\b', reply) is None:
            passed = False
            reasons.append(f"Falta keyword: '{kw}'")

    for kw in question["expected_not_contains"]:
        if re.search(rf'\b{re.escape(kw.lower())}\b', reply) is not None:
            passed = False
            reasons.append(f"Contiene termino prohibido: '{kw}'")

    return {
        "status": "PASS" if passed else "FAIL",
        "reasons": reasons,
        "response_preview": answer_text[:200] + "..." if len(answer_text) > 200 else answer_text
    }


def generate_report(results):
    print("\n" + "=" * 60)
    print(" AUTO-VALIDACION DEL AGENTE OPENCODE  |", datetime.now().strftime("%Y-%m-%d %H:%M"))
    print("=" * 60)

    pass_count = fail_count = 0
    for r in results:
        status_icon = "PASS" if r["status"] == "PASS" else "FAIL"
        print(f"\n  [{status_icon}] Test {r['id']} ({r['target']}) -> {r['status']}")
        print(f"         {r['description']}")
        if r["reasons"]:
            for reason in r["reasons"]:
                print(f"         - {reason}")
        print(f"         Respuesta: {r['response_preview']}")
        if r["status"] == "PASS":
            pass_count += 1
        else:
            fail_count += 1

    print("\n" + "=" * 60)
    print(f" RESULTADO: {pass_count} PASS | {fail_count} FAIL | 0 ERROR")
    print("=" * 60)

    report = {
        "timestamp": datetime.now().isoformat(),
        "type": "agent_self_validation",
        "results": results,
        "summary": {"pass": pass_count, "fail": fail_count}
    }

    report_path = "agent_validation_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nReporte guardado en {report_path}")


def main():
    questions = load_json(QUESTIONS_FILE)
    answers = load_json(ANSWERS_FILE)

    # Index respuestas por id
    answers_by_id = {a["id"]: a["response"] for a in answers}

    missing_ids = [q["id"] for q in questions if q["id"] not in answers_by_id]
    if missing_ids:
        print(f"ERROR: Faltan respuestas para los tests: {missing_ids}")
        sys.exit(1)

    results = []
    for q in questions:
        answer_text = answers_by_id[q["id"]]
        res = run_validation(q, answer_text)
        res.update({
            "id": q["id"],
            "target": q["target"],
            "description": q["description"]
        })
        results.append(res)

    generate_report(results)


if __name__ == "__main__":
    main()
