#!/usr/bin/env python3
"""Deteccion y parseo de 429 (TPD diario vs transitorio) — tarea 15.

Funciones puras para decidir si un 429 es "cuota diaria agotada"
(BLOCKED_TPD, fail-fast, ver docs/PLAN_TPD_429.md) o transitorio
(retry 5/10/20s existente en model_runner.py:288-319, NO se toca).

Formato real de Groq (23/09/2026):
    ... on tokens per day (TPD): Limit 200000, Used 198485, Requested 4646.
    Please try again in 22m32.591999999s. Need more tokens? ...

Clases de 429 (plan §Historial):
    - Transitorio (RPM/ventana corta): "try again in 5s"  -> retry actual lo resuelve
    - TPD diario: "tokens per day" o espera >120s         -> retry actual no alcanza
"""

import json
import os
import re

# Estado/exit code para 429 TPD (cuota agotada != fallo del modelo)
BLOCKED_PREFIX = "[BLOCKED_TPD]"
EXIT_BLOCKED = 7

# Nombre del archivo que escribe tests/scripts/quota_probe.py (paso 0)
QUOTA_STATUS_FILENAME = "quota_status.json"

# Marcas de cuota diaria agotada (clase TPD)
TPD_MARKERS = ("tokens per day", "(tpd)")

# Si el 429 pide esperar mas de estos segundos, es TPD aunque no traiga
# el marcador (regla del plan: "try again in >2min")
TPD_WAIT_THRESHOLD_S = 120

# Hasta esta cantidad de segundos conviene esperar el tiempo EXACTO que
# pide la API en vez del backoff ciego 5/10/20s (paso 2 del plan)
MAX_EXACT_WAIT_S = 90

# Backoff por defecto (mismos valores que el retry existente)
DEFAULT_MAX_RETRIES = 3
DEFAULT_BASE_WAIT_S = 5

# Formatos observados: "22m32.591999999s", "9m17.712s", "1m30s", "5s"
_RE_TRY_M = re.compile(r"try again in\s+(\d+)m([\d.]+)s", re.IGNORECASE)
_RE_TRY_S = re.compile(r"try again in\s+([\d.]+)s\b", re.IGNORECASE)
_RE_USAGE = re.compile(r"Limit\s+(\d+),\s*Used\s+(\d+)", re.IGNORECASE)
_RE_IS_429 = re.compile(r"error code:\s*429|\b429\b|rate limit", re.IGNORECASE)

# Estados que evidencian un 429-TPD en un caso del reporte
_TPD_EVIDENCE_STATES = ("ERROR", "FAIL")


def parse_retry_after(message):
    """Segundos de espera indicados por el 429, o None si no trae 'try again in'."""
    if not message:
        return None
    m = _RE_TRY_M.search(message)
    if m:
        return int(m.group(1)) * 60 + float(m.group(2))
    m = _RE_TRY_S.search(message)
    if m:
        return float(m.group(1))
    return None


def parse_usage(message):
    """(used, limit) del 429, o (None, None) si no trae 'Limit X, Used Y'."""
    m = _RE_USAGE.search(message or "")
    if not m:
        return None, None
    return int(m.group(2)), int(m.group(1))


def parse_rate_limit(message):
    """Clasifica un mensaje de error.

    Returns:
        dict: {is_429, is_tpd, retry_after_s, used, limit}
    """
    text = message or ""
    is_429 = bool(_RE_IS_429.search(text))
    if not is_429:
        return {"is_429": False, "is_tpd": False, "retry_after_s": None,
                "used": None, "limit": None}
    retry_after = parse_retry_after(text)
    has_marker = any(marker in text.lower() for marker in TPD_MARKERS)
    is_tpd = has_marker or (retry_after is not None
                            and retry_after > TPD_WAIT_THRESHOLD_S)
    used, limit = parse_usage(text)
    return {"is_429": True, "is_tpd": is_tpd, "retry_after_s": retry_after,
            "used": used, "limit": limit}


def is_blocked_error(error):
    """True si el error de un runner es BLOCKED_TPD (fail-fast del paso 1)."""
    return bool(error) and str(error).startswith(BLOCKED_PREFIX)


def blocked_message(info=None, model_id=None):
    """Mensaje fail-fast para un 429 TPD (1 intento, sin reintentos)."""
    bits = ["cuota diaria (TPD) agotada"]
    if model_id:
        bits.append(f"modelo {model_id}")
    if info:
        if info.get("used") is not None and info.get("limit") is not None:
            bits.append(f"Used {info['used']}/{info['limit']}")
        if info.get("retry_after_s") is not None:
            bits.append(f"reintentar en {int(round(info['retry_after_s']))}s")
    return f"{BLOCKED_PREFIX} " + ", ".join(bits)


def compute_wait(retry, retry_after_s, base_wait=DEFAULT_BASE_WAIT_S):
    """Espera para un reintento 429 transitorio.

    - Si la API indica una espera exacta <=90s, se respeta (+1s de margen).
    - Si no, backoff exponencial (5s, 10s, 20s...): el retry ORIGINAL.
    - Esperas >120s son TPD y no llegan aqui (is_tpd las corta antes).
    """
    if retry_after_s is not None and 0 < retry_after_s <= MAX_EXACT_WAIT_S:
        return retry_after_s + 1
    return base_wait * (2 ** retry)


def classify_probe(ok, message):
    """Estado de una cuenta en el sondeo: OK | BLOCKED_TPD | TRANSIENT | ERROR."""
    if ok:
        return "OK"
    info = parse_rate_limit(message)
    if not info["is_429"]:
        return "ERROR"
    return "BLOCKED_TPD" if info["is_tpd"] else "TRANSIENT"


def case_has_tpd_evidence(case):
    """True si el caso documenta un 429-TPD (motivo real del ERROR/FAIL)."""
    if not isinstance(case, dict) or case.get("status") not in _TPD_EVIDENCE_STATES:
        return False
    parts = []
    reasons = case.get("reasons")
    if isinstance(reasons, list):
        parts.extend(str(r) for r in reasons)
    elif reasons:
        parts.append(str(reasons))
    for key in ("response_full", "response_preview", "reply", "error"):
        if case.get(key):
            parts.append(str(case[key]))
    blob = " ".join(parts).lower()
    return "429" in blob and any(marker in blob for marker in TPD_MARKERS)


def reclassify_report_tpd(report, model_labels=None):
    """Reclasifica a BLOCKED_TPD los casos ERROR/FAIL con evidencia de 429-TPD.

    Soporta ambos formatos de reporte:
      - avanzada:  models[label] = {case_id: {status, reasons, ...}}
      - estructura: models[label] = {"results": [{status, reply, ...}]}

    No borra campos ni inventa PASS: solo cambia el estado de casos que ya
    documentan textualmente un 429-TPD. Si model_labels viene, toca solo
    esos modelos. Retorna la cantidad de casos reclasificados.
    """
    models = (report or {}).get("models", {})
    changed = 0
    for label, data in models.items():
        if model_labels is not None and label not in model_labels:
            continue
        if not isinstance(data, dict):
            continue
        if isinstance(data.get("results"), list):
            cases = data["results"]
        else:
            cases = [c for c in data.values() if isinstance(c, dict) and "status" in c]
        for case in cases:
            if case_has_tpd_evidence(case):
                case["status"] = "BLOCKED_TPD"
                changed += 1
    return changed


def reclassify_file_tpd(report_path, model_labels=None):
    """I/O: aplica reclassify_report_tpd a un JSON de reporte. Retorna cambios."""
    if not report_path or not os.path.exists(report_path):
        return 0
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)
    except (json.JSONDecodeError, OSError):
        return 0
    changed = reclassify_report_tpd(report, model_labels=model_labels)
    if changed:
        tmp = report_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        os.replace(tmp, report_path)
    return changed
