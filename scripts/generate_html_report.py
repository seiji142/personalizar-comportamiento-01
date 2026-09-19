#!/usr/bin/env python3
"""
Genera un reporte HTML consolidado responsive con TODOS los modelos.

Uso:
  python generate_html_report.py

Genera UN solo archivo HTML en docs/tests/ con:
- Stats globales
- Tabla resumen responsive (se convierte en cards en movil)
- Filtros por categoria y estado
- Busqueda en preguntas y respuestas
- Navegacion hamburger entre modelos en movil
- Respuestas expandibles sin limite de altura
- Codigo formateado con fondo oscuro
"""

import json
import os
from datetime import datetime


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TESTS_DIR = os.path.join(PROJECT_ROOT, "tests")
QUESTIONS_DIR = os.path.join(TESTS_DIR, "questions")
ADVANCED_QUESTIONS_FILE = os.path.join(QUESTIONS_DIR, "advanced_questions.json")
AI_STRUCTURE_QUESTIONS_FILE = os.path.join(QUESTIONS_DIR, "ai_structure_questions.json")
REPORT_FILE = os.path.join(TESTS_DIR, "answers", "advanced_validation_report.json")
AI_REPORT_FILE = os.path.join(TESTS_DIR, "answers", "ai_validation_report.json")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "docs", "tests")

# Nombres de los tests basados en los IDs
TEST_NAMES = {
    "T1": "Identidad del rol (system.md)",
    "T2": "Rechazo de codigo inseguro",
    "T3": "Conocimiento del stack real",
    "T4": "Activacion de roles especialistas",
    "T5": "Reglas inquebrantables ante conflicto",
}


def load_questions():
    """Carga los 2 archivos de preguntas y los merge por ID.
    Retorna: { "T1": {...}, "A1": {...}, ... }
    """
    all_questions = {}

    # T1-T5 desde ai_structure_questions.json
    if os.path.exists(AI_STRUCTURE_QUESTIONS_FILE):
        with open(AI_STRUCTURE_QUESTIONS_FILE, "r", encoding="utf-8") as f:
            for q in json.load(f):
                all_questions[f"T{q['id']}"] = q

    # A1-L1 desde advanced_questions.json
    if os.path.exists(ADVANCED_QUESTIONS_FILE):
        with open(ADVANCED_QUESTIONS_FILE, "r", encoding="utf-8") as f:
            for q in json.load(f):
                all_questions[q["id"]] = q

    return all_questions


def load_results():
    with open(REPORT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_json_safe(filepath):
    """Carga un JSON de forma segura. Retorna None si no existe."""
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def _normalize_structure_results(raw_results):
    """Normaliza una lista de resultados de tests de estructura a formato HTML."""
    results = {}
    for r in raw_results:
        test_id = f"T{r['id']}"
        results[test_id] = {
            "name": TEST_NAMES.get(test_id, f"Test {r['id']}"),
            "category": "structure",
            "status": r.get("status", "UNKNOWN"),
            "time_seconds": r.get("time_seconds", 0),
            "response_preview": r.get("reply_preview") or r.get("reply", ""),
            "response_full": r.get("reply", ""),
            "reasons": r.get("reasons", []),
            "tool_calls": [],
            "tokens_used": 0,
            "target": r.get("target", ""),
            "source": "ai_structure",
        }
    return results


def normalize_ai_report(data):
    """Normaliza ai_validation_report.json a formato comun.
    Soporta:
      - Formato nuevo: { models: { "model_name": { results: [...] } } }
      - Formato viejo: { mode: "model_name", results: [...] }
    Retorna: { "model_name": { "T1": {...}, ... }, ... }
    """
    if not data:
        return {}

    if "models" in data:
        return {
            model_name: _normalize_structure_results(model_data.get("results", []))
            for model_name, model_data in data["models"].items()
        }

    model = data.get("mode", "unknown")
    return {model: _normalize_structure_results(data.get("results", []))}


def merge_results(advanced_results, ai_data):
    """Une los resultados de los 2 reportes por nombre de modelo.
    Retorna: { "model_name": { "T1": {...}, ..., "A1": {...}, ... } }
    """
    ai_models = normalize_ai_report(ai_data)

    # Empezar con los resultados advanced
    merged = {}
    for model_name, cases in advanced_results.get("models", {}).items():
        merged[model_name] = dict(cases)

    # Agregar tests de ai_structure (T1-T5)
    for model_name, cases in ai_models.items():
        if model_name not in merged:
            merged[model_name] = {}
        merged[model_name].update(cases)

    return merged


def escape_html(text):
    if not text:
        return ""
    return (text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;"))


def get_model_stats(cases):
    total = len(cases)
    passed = sum(1 for c in cases.values() if c.get("status") == "PASS")
    failed = sum(1 for c in cases.values() if c.get("status") == "FAIL")
    errors = sum(1 for c in cases.values() if c.get("status") == "ERROR")
    timeouts = sum(1 for c in cases.values() if c.get("status") == "TIMEOUT")
    total_time = sum(c.get("time_seconds", 0) for c in cases.values())
    total_tokens = sum(c.get("tokens_used", 0) for c in cases.values())
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "timeouts": timeouts,
        "total_time": round(total_time, 1),
        "total_tokens": total_tokens,
        "avg_time": round(total_time / total, 1) if total > 0 else 0,
    }


def generate_html(results, questions, merged_models):
    """Genera el HTML consolidado con todos los modelos y tests agrupados."""
    test_ids = sorted(questions.keys(), key=lambda x: (x[0], int(x[1:])))

    # Definir orden de los grupos
    groups = [
        {"prefix": "T", "name": "Tests Basicos (.ai/ structure)", "icon": "T", "cls": "basic", "cat": "basic"},
        {"prefix": "V", "name": "Validacion de Respuestas", "icon": "V", "cls": "validation", "cat": "validation"},
        {"prefix": None, "name": "Tests Avanzados", "icon": "A", "cls": "advanced", "cat": None},
    ]

    # Construir model_data desde merged_models
    model_data = []
    for model_id, cases in merged_models.items():
        stats = get_model_stats(cases)
        model_data.append({
            "id": model_id,
            "cases": cases,
            "stats": stats,
        })

    model_data.sort(key=lambda m: m["stats"]["passed"], reverse=True)

    global_stats = {
        "total_models": len(model_data),
        "total_tests": sum(m["stats"]["total"] for m in model_data),
        "total_passed": sum(m["stats"]["passed"] for m in model_data),
        "total_failed": sum(m["stats"]["failed"] for m in model_data),
        "total_errors": sum(m["stats"]["errors"] for m in model_data),
        "total_tokens": sum(m["stats"]["total_tokens"] for m in model_data),
        "total_time": round(sum(m["stats"]["total_time"] for m in model_data), 1),
    }

    all_categories = set()
    for q in questions.values():
        all_categories.add(q.get("category", "other"))
    # Agregar categorias de los tests basico y validacion
    all_categories.add("basic")
    all_categories.add("validation")
    sorted_categories = sorted(all_categories)

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Reporte Consolidado - Suite de Validacion</title>
<style>
:root {{
  --blue: #2563eb;
  --blue-light: #dbeafe;
  --green: #16a34a;
  --green-light: #dcfce7;
  --red: #dc2626;
  --red-light: #fee2e2;
  --yellow: #ca8a04;
  --yellow-light: #fef9c3;
  --gray-50: #f9fafb;
  --gray-100: #f3f4f6;
  --gray-200: #e5e7eb;
  --gray-300: #d1d5db;
  --gray-400: #9ca3af;
  --gray-500: #6b7280;
  --gray-600: #4b5563;
  --gray-700: #374151;
  --gray-800: #1f2937;
  --gray-900: #111827;
  --radius: 10px;
  --shadow: 0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06);
  --shadow-md: 0 4px 6px rgba(0,0,0,0.07), 0 2px 4px rgba(0,0,0,0.06);
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: var(--gray-100);
  color: var(--gray-800);
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}}
.container {{ max-width: 1200px; margin: 0 auto; padding: 16px; }}

/* Header */
.header {{
  background: white;
  border-bottom: 1px solid var(--gray-200);
  padding: 16px 0;
  margin-bottom: 24px;
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: var(--shadow);
}}
.header-inner {{
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}}
.header h1 {{
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--gray-900);
}}
.header-meta {{
  font-size: 0.8rem;
  color: var(--gray-500);
}}

/* Hamburger */
.hamburger {{
  display: none;
  background: var(--blue);
  color: white;
  border: none;
  padding: 8px 14px;
  border-radius: 6px;
  font-size: 1.1rem;
  cursor: pointer;
  font-weight: 600;
}}
.hamburger:hover {{ opacity: 0.9; }}
.nav-overlay {{
  display: none;
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.4);
  z-index: 200;
}}
.nav-overlay.open {{ display: block; }}
.nav-drawer {{
  position: fixed;
  top: 0;
  left: 0;
  width: 280px;
  height: 100%;
  background: white;
  z-index: 201;
  transform: translateX(-100%);
  transition: transform 0.25s ease;
  overflow-y: auto;
  padding: 16px;
  box-shadow: var(--shadow-md);
}}
.nav-drawer.open {{ transform: translateX(0); }}
.nav-drawer h3 {{
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--gray-500);
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--gray-200);
}}
.nav-drawer a {{
  display: block;
  padding: 10px 12px;
  margin-bottom: 4px;
  border-radius: 6px;
  text-decoration: none;
  color: var(--gray-700);
  font-size: 0.9rem;
  transition: background 0.15s;
}}
.nav-drawer a:hover {{ background: var(--blue-light); color: var(--blue); }}
.nav-drawer .nav-score {{
  float: right;
  font-size: 0.8rem;
  color: var(--gray-500);
}}
.nav-close {{
  position: absolute;
  top: 12px;
  right: 12px;
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: var(--gray-500);
}}

/* Stats grid */
.stats-grid {{
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 24px;
}}
.stat-card {{
  background: white;
  padding: 16px;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  text-align: center;
}}
.stat-value {{
  font-size: 1.8rem;
  font-weight: 700;
  color: var(--blue);
  line-height: 1.2;
}}
.stat-value.green {{ color: var(--green); }}
.stat-value.red {{ color: var(--red); }}
.stat-label {{
  font-size: 0.75rem;
  color: var(--gray-500);
  margin-top: 4px;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}}

/* Toolbar: filtros + busqueda */
.toolbar {{
  background: white;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 12px 16px;
  margin-bottom: 20px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}}
.toolbar-group {{
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}}
.toolbar-group label {{
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--gray-500);
  letter-spacing: 0.03em;
}}
.filter-btn {{
  padding: 4px 10px;
  border: 1px solid var(--gray-300);
  border-radius: 20px;
  background: white;
  color: var(--gray-600);
  font-size: 0.78rem;
  cursor: pointer;
  transition: all 0.15s;
  font-weight: 500;
}}
.filter-btn:hover {{ border-color: var(--blue); color: var(--blue); }}
.filter-btn.active {{ background: var(--blue); color: white; border-color: var(--blue); }}
.filter-btn.active-fail {{ background: var(--red); color: white; border-color: var(--red); }}
.filter-btn.active-error {{ background: var(--yellow); color: white; border-color: var(--yellow); }}
.search-input {{
  flex: 1;
  min-width: 200px;
  padding: 6px 12px;
  border: 1px solid var(--gray-300);
  border-radius: 6px;
  font-size: 0.85rem;
  outline: none;
  transition: border-color 0.15s;
}}
.search-input:focus {{ border-color: var(--blue); box-shadow: 0 0 0 3px rgba(37,99,235,0.1); }}
.btn-expand-all {{
  padding: 4px 12px;
  border: 1px solid var(--gray-300);
  border-radius: 6px;
  background: white;
  color: var(--gray-600);
  font-size: 0.8rem;
  cursor: pointer;
  white-space: nowrap;
}}
.btn-expand-all:hover {{ background: var(--gray-100); }}

/* Model tabs (desktop) */
.model-tabs {{
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}}
.model-tab {{
  padding: 8px 16px;
  background: white;
  border: 2px solid var(--gray-200);
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  font-size: 0.85rem;
  text-decoration: none;
  color: var(--gray-700);
  transition: all 0.15s;
  display: flex;
  align-items: center;
  gap: 8px;
}}
.model-tab:hover {{ border-color: var(--blue); background: var(--blue-light); }}
.model-tab.active {{ border-color: var(--blue); background: var(--blue); color: white; }}
.model-tab .tab-score {{
  font-size: 0.75rem;
  opacity: 0.8;
  font-weight: 400;
}}

/* Model section */
.model-section {{
  background: white;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  margin-bottom: 20px;
  overflow: hidden;
}}
.model-header {{
  padding: 14px 16px;
  background: var(--gray-50);
  border-bottom: 1px solid var(--gray-200);
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}}
.model-name {{ font-size: 1.1rem; font-weight: 700; }}
.model-type {{ color: var(--gray-500); font-size: 0.85rem; margin-left: 8px; }}
.model-meta {{
  display: flex;
  gap: 16px;
  font-size: 0.8rem;
  color: var(--gray-600);
}}
.model-meta strong {{ color: var(--gray-800); }}
.model-body {{ padding: 12px; }}

/* Test card */
.test-card {{
  border: 1px solid var(--gray-200);
  border-radius: 8px;
  margin-bottom: 8px;
  overflow: hidden;
  transition: box-shadow 0.15s;
}}
.test-card:hover {{ box-shadow: var(--shadow-md); }}
.test-header {{
  padding: 10px 14px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  gap: 8px;
  min-height: 44px;
}}
.test-header:hover {{ background: var(--gray-50); }}
.test-header.pass {{ border-left: 4px solid var(--green); }}
.test-header.fail {{ border-left: 4px solid var(--red); }}
.test-header.error {{ border-left: 4px solid var(--yellow); }}
.test-header.timeout {{ border-left: 4px solid var(--gray-400); }}
.test-left {{ display: flex; align-items: center; gap: 8px; flex-wrap: wrap; min-width: 0; }}
.test-right {{ display: flex; align-items: center; gap: 8px; flex-shrink: 0; }}
.test-title {{ font-weight: 600; font-size: 0.9rem; white-space: nowrap; }}
.test-meta {{ color: var(--gray-500); font-size: 0.75rem; white-space: nowrap; }}
.badge {{
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}}
.badge-pass {{ background: var(--green); color: white; }}
.badge-fail {{ background: var(--red); color: white; }}
.badge-error {{ background: var(--yellow); color: white; }}
.badge-timeout {{ background: var(--gray-400); color: white; }}

/* Category label */
.cat-label {{
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.65rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  flex-shrink: 0;
}}
.cat-jailbreak {{ background: #fee2e2; color: #991b1b; }}
.cat-code_style {{ background: #cffafe; color: #155e75; }}
.cat-structure {{ background: #ede9fe; color: #5b21b6; }}
.cat-factuality {{ background: #ffedd5; color: #9a3412; }}
.cat-role {{ background: #d1fae5; color: #065f46; }}
.cat-language {{ background: #f3f4f6; color: #374151; }}
.cat-memory {{ background: #dbeafe; color: #1e40af; }}
.cat-config {{ background: #dcfce7; color: #166534; }}
.cat-hierarchy {{ background: #fce7f3; color: #9d174d; }}
.cat-verification {{ background: #e5e7eb; color: #1f2937; }}
.cat-basic {{ background: #f0f9ff; color: #0c4a6e; }}
.cat-validation {{ background: #ecfdf5; color: #065f46; }}

/* Group headers */
.group-header {{
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  margin: 16px 0 8px 0;
  background: var(--gray-50);
  border: 1px solid var(--gray-200);
  border-radius: 8px;
  font-weight: 700;
  font-size: 0.85rem;
  color: var(--gray-700);
}}
.group-header:first-child {{
  margin-top: 0;
}}
.group-header .group-icon {{
  width: 28px;
  height: 28px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.9rem;
  flex-shrink: 0;
}}
.group-header .group-icon.basic {{ background: #dbeafe; color: #1e40af; }}
.group-header .group-icon.validation {{ background: #dcfce7; color: #166534; }}
.group-header .group-icon.advanced {{ background: #ede9fe; color: #5b21b6; }}
.group-header .group-count {{
  margin-left: auto;
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--gray-500);
}}

/* Test details */
.test-details {{
  padding: 14px;
  border-top: 1px solid var(--gray-200);
  background: var(--gray-50);
  display: none;
}}
.test-details.open {{ display: block; }}
.detail-section {{ margin-bottom: 14px; }}
.detail-section:last-child {{ margin-bottom: 0; }}
.detail-label {{
  font-weight: 700;
  color: var(--gray-600);
  margin-bottom: 6px;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}}
.detail-content {{
  background: white;
  padding: 12px;
  border: 1px solid var(--gray-200);
  border-radius: 6px;
  font-size: 0.85rem;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 500px;
  overflow-y: auto;
}}
.detail-content.code-block {{
  background: var(--gray-900);
  color: #e5e7eb;
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 0.8rem;
  padding: 14px;
  overflow-x: auto;
}}
.detail-content.full-height {{
  max-height: none;
}}
.expand-response {{
  background: none;
  border: 1px solid var(--gray-300);
  border-radius: 4px;
  padding: 4px 10px;
  font-size: 0.75rem;
  cursor: pointer;
  color: var(--gray-600);
  margin-top: 6px;
}}
.expand-response:hover {{ background: var(--gray-100); }}

/* Tool calls */
.tool-call {{
  background: var(--blue-light);
  padding: 10px 12px;
  border-radius: 6px;
  margin-bottom: 6px;
  border-left: 3px solid var(--blue);
  font-size: 0.8rem;
}}
.tool-call.success {{ border-left-color: var(--green); background: var(--green-light); }}
.tool-call.error {{ border-left-color: var(--red); background: var(--red-light); }}
.tool-call strong {{ color: var(--gray-800); }}
.tool-call small {{ color: var(--gray-600); display: block; margin-top: 4px; word-break: break-all; }}
.no-tools {{ color: var(--gray-400); font-style: italic; font-size: 0.8rem; }}

/* Back to top */
.back-to-top {{
  position: fixed;
  bottom: 20px;
  right: 20px;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: var(--blue);
  color: white;
  border: none;
  font-size: 1.2rem;
  cursor: pointer;
  box-shadow: var(--shadow-md);
  display: none;
  z-index: 50;
  align-items: center;
  justify-content: center;
}}
.back-to-top.visible {{ display: flex; }}

/* No results */
.no-results {{
  text-align: center;
  padding: 40px 16px;
  color: var(--gray-500);
  font-size: 0.95rem;
}}

/* === RESPONSIVE === */
@media (max-width: 768px) {{
  .container {{ padding: 10px; }}
  .header-inner {{ flex-direction: column; align-items: flex-start; }}
  .hamburger {{ display: inline-block; }}
  .model-tabs {{ display: none; }}

  .stats-grid {{ grid-template-columns: repeat(2, 1fr); gap: 8px; }}
  .stat-card {{ padding: 12px 8px; }}
  .stat-value {{ font-size: 1.4rem; }}

  .toolbar {{
    flex-direction: column;
    align-items: stretch;
    padding: 10px 12px;
  }}
  .toolbar-group {{ flex-wrap: wrap; }}
  .search-input {{ min-width: 0; width: 100%; }}

  /* Table -> cards */
  .summary-table {{ display: block; overflow-x: auto; }}
  .summary-table thead {{ display: none; }}
  .summary-table tbody {{ display: block; }}
  .summary-table tr {{
    display: block;
    background: white;
    border: 1px solid var(--gray-200);
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 10px;
    box-shadow: var(--shadow);
  }}
  .summary-table td {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 5px 0;
    border: none;
    font-size: 0.85rem;
  }}
  .summary-table td::before {{
    content: attr(data-label);
    font-weight: 600;
    color: var(--gray-500);
    font-size: 0.75rem;
    text-transform: uppercase;
    flex-shrink: 0;
    margin-right: 12px;
  }}

  .model-header {{
    flex-direction: column;
    align-items: flex-start;
  }}
  .model-meta {{ flex-wrap: wrap; gap: 8px; }}

  .test-header {{
    flex-direction: column;
    align-items: flex-start;
    gap: 6px;
  }}
  .test-right {{ width: 100%; justify-content: space-between; }}

  .detail-content {{ max-height: none; }}

  .back-to-top {{ bottom: 14px; right: 14px; width: 40px; height: 40px; }}
}}

@media (max-width: 480px) {{
  .stats-grid {{ grid-template-columns: 1fr 1fr; gap: 6px; }}
  .stat-value {{ font-size: 1.2rem; }}
  .stat-label {{ font-size: 0.65rem; }}
  .header h1 {{ font-size: 1rem; }}
}}
</style>
</head>
<body>

<!-- Header -->
<div class="header">
  <div class="header-inner">
    <div style="display:flex; align-items:center; gap:10px;">
      <button class="hamburger" onclick="toggleNav()" aria-label="Menu">&#9776; Modelos</button>
      <div>
        <h1>Reporte Consolidado</h1>
        <div class="header-meta">Suite de Validacion | {timestamp}</div>
      </div>
    </div>
  </div>
</div>

<!-- Nav drawer (movil) -->
<div class="nav-overlay" id="navOverlay" onclick="toggleNav()"></div>
<div class="nav-drawer" id="navDrawer">
  <button class="nav-close" onclick="toggleNav()">&times;</button>
  <h3>Modelos</h3>
"""

    for i, md in enumerate(model_data):
        s = md["stats"]
        html += f'  <a href="#model-{i}" onclick="toggleNav()">{escape_html(md["id"])} <span class="nav-score">{s["passed"]}/{s["total"]}</span></a>\n'

    html += """</div>

<div class="container">

<!-- Stats globales -->
<div class="stats-grid">
  <div class="stat-card">
    <div class="stat-value">""" + str(global_stats["total_models"]) + """</div>
    <div class="stat-label">Modelos</div>
  </div>
  <div class="stat-card">
    <div class="stat-value green">""" + str(global_stats["total_passed"]) + """/""" + str(global_stats["total_tests"]) + """</div>
    <div class="stat-label">Tests PASS</div>
  </div>
  <div class="stat-card">
    <div class="stat-value red">""" + str(global_stats["total_failed"]) + """</div>
    <div class="stat-label">Tests FAIL</div>
  </div>
  <div class="stat-card">
    <div class="stat-value">""" + f'{global_stats["total_time"]}' + """s</div>
    <div class="stat-label">Tiempo total</div>
  </div>
</div>

<!-- Toolbar -->
<div class="toolbar">
  <div class="toolbar-group">
    <label>Estado:</label>
    <button class="filter-btn active" onclick="filterStatus('all', this)">Todos</button>
    <button class="filter-btn" onclick="filterStatus('pass', this)">PASS</button>
    <button class="filter-btn" onclick="filterStatus('fail', this)">FAIL</button>
    <button class="filter-btn" onclick="filterStatus('error', this)">ERROR</button>
  </div>
  <div class="toolbar-group">
    <label>Categoria:</label>
"""

    for cat in sorted_categories:
        html += f'    <button class="filter-btn" onclick="filterCategory(\'{cat}\', this)">{escape_html(cat)}</button>\n'

    html += """  </div>
  <input type="text" class="search-input" id="searchInput" placeholder="Buscar en preguntas o respuestas..." oninput="applyFilters()">
  <button class="btn-expand-all" id="btnExpandAll" onclick="toggleExpandAll()">Expandir todo</button>
</div>

<!-- Tabs desktop -->
<div class="model-tabs">
"""

    for i, md in enumerate(model_data):
        s = md["stats"]
        active = "active" if i == 0 else ""
        html += f'  <a href="#model-{i}" class="model-tab {active}">{escape_html(md["id"])} <span class="tab-score">({s["passed"]}/{s["total"]})</span></a>\n'

    html += "</div>\n\n"

    # Secciones por modelo
    for i, md in enumerate(model_data):
        cases = md["cases"]
        s = md["stats"]
        model_type = "API (Groq)" if md["id"].startswith("api/") else "Nativo (OpenCode)"

        html += f'<div class="model-section" id="model-{i}">\n'
        html += f'  <div class="model-header">\n'
        html += f'    <div><span class="model-name">{escape_html(md["id"])}</span><span class="model-type">({model_type})</span></div>\n'
        html += f'    <div class="model-meta"><span>Score: <strong>{s["passed"]}/{s["total"]}</strong></span><span>Tiempo: <strong>{s["total_time"]}s</strong></span><span>Tokens: <strong>{s["total_tokens"]:,}</strong></span></div>\n'
        html += f'  </div>\n'
        html += f'  <div class="model-body">\n'

        # Agrupar tests por grupo
        for group in groups:
            prefix = group["prefix"]
            if prefix is not None:
                group_test_ids = [tid for tid in test_ids if tid.startswith(prefix)]
                merged_ids = [tid for tid in cases.keys() if tid.startswith(prefix) and tid not in group_test_ids]
            else:
                # Catch-all: tests que no son T ni V
                group_test_ids = [tid for tid in test_ids if not tid.startswith("T") and not tid.startswith("V")]
                merged_ids = [tid for tid in cases.keys() if not tid.startswith("T") and not tid.startswith("V") and tid not in group_test_ids]
            group_test_ids = sorted(set(group_test_ids + merged_ids), key=lambda x: (x[0], int(x[1:])))

            if not group_test_ids:
                continue

            # Contar tests en este grupo
            group_total = len(group_test_ids)
            group_passed = sum(1 for tid in group_test_ids if cases.get(tid, {}).get("status") == "PASS")

            # Header del grupo
            html += f'<div class="group-header"><span class="group-icon {group["cls"]}">{group["icon"]}</span> {group["name"]}<span class="group-count">{group_passed}/{group_total} PASS</span></div>\n'

            for test_id in group_test_ids:
                if test_id not in cases:
                    continue

                case = cases[test_id]
                q = questions.get(test_id, {})
                status = case.get("status", "UNKNOWN")
                status_lower = status.lower()
                badge_class = f"badge-{status_lower}"
                header_class = status_lower
                # Determinar categoria para el label
                if test_id.startswith("T"):
                    category = "basic"
                    cat_class = "cat-basic"
                elif test_id.startswith("V"):
                    category = "validation"
                    cat_class = "cat-validation"
                else:
                    category = q.get("category", case.get("category", "other"))
                    cat_class = f"cat-{category}"

                time_s = case.get("time_seconds", 0)
                tokens = case.get("tokens_used", 0)
                response = case.get("response_full", "") or case.get("response_preview", "")
                tools = case.get("tool_calls", [])
                prompt = q.get("prompt", "N/A")
                test_name = case.get("name", q.get("name", ""))

                if tools:
                    tools_html = ""
                    for tc in tools:
                        result_str = tc.get("result", "N/A")
                        success = tc.get("success", False)
                        icon = "+" if success else "x"
                        tc_cls = "success" if success else "error"
                        tools_html += f'<div class="tool-call {tc_cls}"><strong>{icon} {escape_html(tc["name"])}</strong><small>{escape_html(str(result_str)[:300])}</small></div>\n'
                else:
                    tools_html = '<span class="no-tools">Sin tool calls</span>'

                response_escaped = escape_html(response)
                prompt_escaped = escape_html(prompt)

                html += f'''    <div class="test-card" data-status="{status_lower}" data-category="{category}" data-search="{escape_html((prompt + " " + response).lower())}">
      <div class="test-header {header_class}" onclick="this.nextElementSibling.classList.toggle('open')">
        <div class="test-left">
          <span class="cat-label {cat_class}">{category}</span>
          <span class="test-title">{test_id}: {escape_html(test_name)}</span>
        </div>
        <div class="test-right">
          <span class="test-meta">{time_s}s | {tokens}t</span>
          <span class="badge {badge_class}">{status}</span>
        </div>
      </div>
      <div class="test-details">
        <div class="detail-section">
          <div class="detail-label">Pregunta</div>
          <div class="detail-content">{prompt_escaped}</div>
        </div>
        <div class="detail-section">
          <div class="detail-label">Tool Calls</div>
          {tools_html}
        </div>
        <div class="detail-section">
          <div class="detail-label">Respuesta completa</div>
          <div class="detail-content">{response_escaped}</div>
          <button class="expand-response" onclick="toggleFullHeight(this)">Ver completa</button>
        </div>
      </div>
    </div>
'''

        html += "  </div>\n</div>\n\n"

    html += """<div class="no-results" id="noResults" style="display:none;">No se encontraron tests con los filtros seleccionados.</div>

</div>

<button class="back-to-top" id="backToTop" onclick="window.scrollTo({top:0,behavior:'smooth'})">&#8593;</button>

<script>
function toggleNav() {
  document.getElementById('navDrawer').classList.toggle('open');
  document.getElementById('navOverlay').classList.toggle('open');
}

let activeStatus = 'all';
let activeCategories = new Set();

function filterStatus(status, btn) {
  activeStatus = status;
  document.querySelectorAll('.toolbar-group:first-child .filter-btn').forEach(b => b.className = 'filter-btn');
  if (status === 'all') btn.classList.add('active');
  else if (status === 'pass') btn.classList.add('active');
  else if (status === 'fail') btn.classList.add('active-fail');
  else if (status === 'error') btn.classList.add('active-error');
  applyFilters();
}

function filterCategory(cat, btn) {
  if (activeCategories.has(cat)) {
    activeCategories.delete(cat);
    btn.classList.remove('active');
  } else {
    activeCategories.add(cat);
    btn.classList.add('active');
  }
  applyFilters();
}

function applyFilters() {
  const search = document.getElementById('searchInput').value.toLowerCase();
  const cards = document.querySelectorAll('.test-card');
  let visible = 0;

  cards.forEach(card => {
    const status = card.dataset.status;
    const category = card.dataset.category;
    const searchText = card.dataset.search;

    let show = true;
    if (activeStatus !== 'all' && status !== activeStatus) show = false;
    if (activeCategories.size > 0 && !activeCategories.has(category)) show = false;
    if (search && !searchText.includes(search)) show = false;

    card.style.display = show ? '' : 'none';
    if (show) visible++;
  });

  document.getElementById('noResults').style.display = visible === 0 ? '' : 'none';
}

let allExpanded = false;
function toggleExpandAll() {
  allExpanded = !allExpanded;
  document.querySelectorAll('.test-details').forEach(el => {
    el.classList.toggle('open', allExpanded);
  });
  document.getElementById('btnExpandAll').textContent = allExpanded ? 'Contraer todo' : 'Expandir todo';
}

function toggleFullHeight(btn) {
  const content = btn.previousElementSibling;
  content.classList.toggle('full-height');
  btn.textContent = content.classList.contains('full-height') ? 'Contraer' : 'Ver completa';
}

// Back to top
window.addEventListener('scroll', () => {
  document.getElementById('backToTop').classList.toggle('visible', window.scrollY > 300);
});

// Smooth scroll para tabs
document.querySelectorAll('.model-tab').forEach(tab => {
  tab.addEventListener('click', function(e) {
    document.querySelectorAll('.model-tab').forEach(t => t.classList.remove('active'));
    this.classList.add('active');
  });
});
</script>
</body>
</html>"""

    return html


def main():
    print("Generando reporte HTML consolidado...")

    results = load_results()
    questions = load_questions()

    # Cargar reportes adicionales
    ai_data = load_json_safe(AI_REPORT_FILE)

    if ai_data:
        print(f"  [OK] ai_validation_report.json cargado ({ai_data.get('mode', '?')})")
    else:
        print("  [SKIP] ai_validation_report.json no encontrado")

    # Merge de los 2 reportes
    merged_models = merge_results(results, ai_data)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    html = generate_html(results, questions, merged_models)

    # Guardar versión datada (preserva historial)
    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename_dated = f"reporte_consolidado_{timestamp_str}.html"
    filepath_dated = os.path.join(OUTPUT_DIR, filename_dated)

    with open(filepath_dated, "w", encoding="utf-8") as f:
        f.write(html)

    # Sobreescribir el principal (acceso rápido)
    filename_main = "reporte_consolidado.html"
    filepath_main = os.path.join(OUTPUT_DIR, filename_main)

    with open(filepath_main, "w", encoding="utf-8") as f:
        f.write(html)

    # Contar tests por modelo
    total_tests_per_model = len(questions)

    # Contar por fuente
    t_count = sum(1 for k in questions if k.startswith("T"))
    a_count = len(questions) - t_count

    print(f"[OK] Archivado: {filepath_dated}")
    print(f"[OK] Actualizado: {filepath_main}")
    print(f"   Modelos: {len(merged_models)}")
    print(f"   Tests/modelo: {total_tests_per_model}")
    print(f"   Fuentes: ai_structure({t_count}) + advanced({a_count})")


if __name__ == "__main__":
    main()
