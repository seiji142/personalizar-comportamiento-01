#!/usr/bin/env python3
"""Analiza tiempos por test de las suites avanzada y de estructura.

Subplan: docs/PLAN_RUN_INSTRUMENTADO.md (Fase 0/2).

Produce:
  - total por modelo, top-N tests mas lentos, tests TIMEOUT/ERROR
  - overhead opcional si se pasa --wall-avanzada/--wall-estructura
    (overhead = wall - sum(time_seconds))

Uso:
  python scripts/analyze_times.py
  python scripts/analyze_times.py --wall-avanzada 987.5 --wall-estructura 310.2
"""

import argparse
import json
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ADVANCED = os.path.join(PROJECT_ROOT, "tests", "answers", "advanced_validation_report.json")
STRUCTURE = os.path.join(PROJECT_ROOT, "tests", "answers", "ai_validation_report.json")


def load(path):
    if not os.path.exists(path):
        print(f"[WARN] No existe {path}")
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def print_advanced(report, top_n):
    print("=" * 70)
    print("SUITE AVANZADA (advanced_validation_report.json)")
    print("=" * 70)
    for label, cases in report.get("models", {}).items():
        if not isinstance(cases, dict):
            continue
        rows = [
            (c.get("time_seconds") or 0, cid, c.get("status", "?"))
            for cid, c in cases.items() if isinstance(c, dict)
        ]
        if not rows:
            continue
        rows.sort(reverse=True)
        total = sum(t for t, _, _ in rows)
        bad = [(cid, st, t) for t, cid, st in rows if st in ("TIMEOUT", "ERROR")]
        near_cap = [(cid, st, t) for t, cid, st in rows if t >= 150]
        print(f"\n[{label}] n={len(rows)} total={total:.1f}s avg={total / len(rows):.1f}s")
        for t, cid, st in rows[:top_n]:
            print(f"  {cid:>4}: {t:>6.1f}s [{st}]")
        if near_cap:
            print(f"  >=150s (cerca de cap 180): {[(c, t) for c, _, t in near_cap]}")
        if bad:
            print(f"  TIMEOUT/ERROR: {[(c, s) for c, s, _ in bad]}")
        missing_d8 = "D8" not in cases
        missing_d9 = "D9" not in cases
        if missing_d8 or missing_d9:
            print(f"  FALTAN: {([x for x, m in [('D8', missing_d8), ('D9', missing_d9)] if m])}")


def print_structure(report, top_n):
    print("\n" + "=" * 70)
    print("SUITE ESTRUCTURA (ai_validation_report.json)")
    print("=" * 70)
    for label, data in report.get("models", {}).items():
        results = data.get("results", []) if isinstance(data, dict) else []
        if not results:
            continue
        rows = sorted(
            [(r.get("time_seconds") or 0, str(r.get("id")), r.get("status", "?")) for r in results],
            reverse=True,
        )
        total = sum(t for t, _, _ in rows)
        print(f"\n[{label}] n={len(rows)} total={total:.1f}s")
        for t, cid, st in rows[:top_n]:
            print(f"  T{cid}: {t:>6.1f}s [{st}]")
        for r in results:
            if str(r.get("id")) == "3":
                print(f"  T3 detalle: {r.get('status')} reasons={r.get('reasons')}")


def print_overhead(wall_adv, wall_struct, adv_report, struct_report):
    print("\n" + "=" * 70)
    print("OVERHEAD (wall - sum(time_seconds))")
    print("=" * 70)
    label = "opencode/mimo-v2.6-flash-free"
    cases = adv_report.get("models", {}).get(label, {})
    s_adv = sum((c.get("time_seconds") or 0) for c in cases.values() if isinstance(c, dict))
    if wall_adv is not None:
        ov = wall_adv - s_adv
        pct = (ov / wall_adv * 100) if wall_adv else 0
        print(f"Avanzada: wall={wall_adv:.1f}s sum={s_adv:.1f}s overhead={ov:.1f}s ({pct:.0f}%)")
        if ov / wall_adv > 0.3 if wall_adv else False:
            print("  -> overhead DOMINANTE: atacar runner/sleep/CLI, NO subir suite timeout")
        else:
            print("  -> tiempo dominante del MODELO: candidato a subir suite timeout")
    sdata = struct_report.get("models", {}).get(label, {})
    sres = sdata.get("results", []) if isinstance(sdata, dict) else []
    s_struct = sum((r.get("time_seconds") or 0) for r in sres)
    if wall_struct is not None:
        ov = wall_struct - s_struct
        pct = (ov / wall_struct * 100) if wall_struct else 0
        print(f"Estructura: wall={wall_struct:.1f}s sum={s_struct:.1f}s overhead={ov:.1f}s ({pct:.0f}%)")


def main():
    ap = argparse.ArgumentParser(description="Analiza tiempos por test")
    ap.add_argument("--top", type=int, default=8, help="Top-N tests lentos")
    ap.add_argument("--wall-avanzada", type=float, default=None,
                    help="Wall-clock de la suite avanzada en segundos")
    ap.add_argument("--wall-estructura", type=float, default=None,
                    help="Wall-clock de la suite de estructura en segundos")
    args = ap.parse_args()

    adv = load(ADVANCED)
    struct = load(STRUCTURE)
    print_advanced(adv, args.top)
    print_structure(struct, args.top)
    if args.wall_avanzada is not None or args.wall_estructura is not None:
        print_overhead(args.wall_avanzada, args.wall_estructura, adv, struct)


if __name__ == "__main__":
    main()
