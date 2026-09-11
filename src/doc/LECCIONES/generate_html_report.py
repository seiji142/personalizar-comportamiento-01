#!/usr/bin/env python3
"""
Genera un reporte HTML consolidado con TODOS los modelos.

Uso:
  python generate_html_report.py

Genera UN solo archivo HTML en src/doc/LECCIONES/ con:
- Tabla resumen de todos los modelos
- Secciones detalladas por modelo
- Navegación rápida entre modelos
"""

import json
import os
from datetime import datetime


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
QUESTIONS_FILE = os.path.join(PROJECT_ROOT, "src", "doc", "ESTRUCTURA", "advanced_questions.json")
REPORT_FILE = os.path.join(PROJECT_ROOT, "docs", "advanced_validation_report.json")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "src", "doc", "LECCIONES")


def load_questions():
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        return {q["id"]: q for q in json.load(f)}


def load_results():
    with open(REPORT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


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
    total_time = sum(c.get("time_seconds", 0) for c in cases.values())
    total_tokens = sum(c.get("tokens_used", 0) for c in cases.values())
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "total_time": round(total_time, 1),
        "total_tokens": total_tokens,
        "avg_time": round(total_time / total, 1) if total > 0 else 0,
    }


def generate_html(results, questions):
    models = results.get("models", {})
    test_ids = sorted(questions.keys(), key=lambda x: (x[0], int(x[1:])))
    
    # Preparar datos de modelos
    model_data = []
    for model_id, cases in models.items():
        stats = get_model_stats(cases)
        model_data.append({
            "id": model_id,
            "cases": cases,
            "stats": stats,
        })
    
    # Ordenar por score descendente
    model_data.sort(key=lambda m: m["stats"]["passed"], reverse=True)
    
    # Calcular totales globales
    global_stats = {
        "total_models": len(model_data),
        "total_tests": sum(m["stats"]["total"] for m in model_data),
        "total_passed": sum(m["stats"]["passed"] for m in model_data),
        "total_tokens": sum(m["stats"]["total_tokens"] for m in model_data),
        "total_time": round(sum(m["stats"]["total_time"] for m in model_data), 1),
    }
    
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reporte Consolidado - Suite de Validación</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            padding: 20px;
            background: #f5f5f5;
            color: #333;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        h1 {{ 
            color: #333; 
            margin-bottom: 10px;
            border-bottom: 3px solid #007bff;
            padding-bottom: 10px;
        }}
        h2 {{ 
            color: #333; 
            margin: 30px 0 15px 0;
            padding-bottom: 8px;
            border-bottom: 2px solid #007bff;
        }}
        h3 {{ color: #555; margin: 15px 0 10px 0; }}
        .meta {{ color: #666; margin-bottom: 20px; }}
        
        /* Stats globales */
        .global-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .stat-value {{ font-size: 2em; font-weight: bold; color: #007bff; }}
        .stat-label {{ color: #666; margin-top: 5px; font-size: 0.9em; }}
        
        /* Navegación tabs */
        .tabs {{
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}
        .tab {{
            padding: 10px 20px;
            background: white;
            border: 2px solid #ddd;
            border-radius: 8px;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.2s;
            text-decoration: none;
            color: #333;
        }}
        .tab:hover {{ border-color: #007bff; background: #f0f7ff; }}
        .tab.active {{ border-color: #007bff; background: #007bff; color: white; }}
        .tab .score {{ font-size: 0.85em; opacity: 0.8; }}
        
        /* Tabla resumen */
        .summary-table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}
        .summary-table th, .summary-table td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        .summary-table th {{
            background: #007bff;
            color: white;
            font-weight: bold;
        }}
        .summary-table tr:hover {{ background: #f8f9fa; }}
        .summary-table .score {{ font-weight: bold; }}
        .summary-table .score.perfect {{ color: #28a745; }}
        .summary-table .score.good {{ color: #ffc107; }}
        .summary-table .score.poor {{ color: #dc3545; }}
        
        /* Sección de modelo */
        .model-section {{
            background: white;
            margin-bottom: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .model-header {{
            padding: 15px 20px;
            background: #f8f9fa;
            border-bottom: 1px solid #eee;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
        }}
        .model-name {{ font-size: 1.3em; font-weight: bold; }}
        .model-stats {{
            display: flex;
            gap: 20px;
            font-size: 0.9em;
            color: #666;
        }}
        .model-body {{ padding: 20px; }}
        
        /* Test cards */
        .test-card {{
            border: 1px solid #ddd;
            border-radius: 6px;
            margin-bottom: 12px;
            overflow: hidden;
        }}
        .test-header {{
            padding: 10px 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            cursor: pointer;
        }}
        .test-header:hover {{ background: #f8f9fa; }}
        .test-header.pass {{ border-left: 4px solid #28a745; }}
        .test-header.fail {{ border-left: 4px solid #dc3545; }}
        .test-header.error {{ border-left: 4px solid #ffc107; }}
        .test-title {{ font-weight: bold; }}
        .test-meta {{ color: #666; font-size: 0.85em; }}
        .badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: bold;
        }}
        .badge-pass {{ background: #28a745; color: white; }}
        .badge-fail {{ background: #dc3545; color: white; }}
        .badge-error {{ background: #ffc107; color: #333; }}
        .test-details {{ 
            padding: 15px; 
            border-top: 1px solid #eee;
            background: #fafafa;
            display: none;
        }}
        .test-details.open {{ display: block; }}
        .section {{ margin-bottom: 12px; }}
        .section-title {{ 
            font-weight: bold; 
            color: #555; 
            margin-bottom: 6px;
            font-size: 0.9em;
        }}
        .response {{ 
            background: white; 
            padding: 12px; 
            border: 1px solid #ddd;
            border-radius: 4px;
            white-space: pre-wrap;
            font-size: 0.9em;
            max-height: 300px;
            overflow-y: auto;
        }}
        .tool-call {{
            background: #e7f3ff;
            padding: 8px 12px;
            border-radius: 4px;
            margin-bottom: 6px;
            border-left: 3px solid #007bff;
            font-size: 0.9em;
        }}
        .tool-call.success {{ border-left-color: #28a745; background: #d4edda; }}
        .tool-call.error {{ border-left-color: #dc3545; background: #f8d7da; }}
        .no-tools {{ color: #999; font-style: italic; font-size: 0.9em; }}
        
        /* Categorías */
        .category-label {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.75em;
            font-weight: bold;
            margin-right: 8px;
        }}
        .cat-jailbreak {{ background: #dc3545; color: white; }}
        .cat-code_style {{ background: #17a2b8; color: white; }}
        .cat-structure {{ background: #6f42c1; color: white; }}
        .cat-factuality {{ background: #fd7e14; color: white; }}
        .cat-role {{ background: #20c997; color: white; }}
        .cat-language {{ background: #6c757d; color: white; }}
        .cat-memory {{ background: #007bff; color: white; }}
        .cat-config {{ background: #28a745; color: white; }}
        .cat-hierarchy {{ background: #e83e8c; color: white; }}
        .cat-verification {{ background: #343a40; color: white; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Reporte Consolidado - Suite de Validación</h1>
        <p class="meta">Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Modelos: {global_stats['total_models']} | Tests/modelo: 23</p>
        
        <div class="global-stats">
            <div class="stat-card">
                <div class="stat-value">{global_stats['total_models']}</div>
                <div class="stat-label">Modelos evaluados</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{global_stats['total_passed']}/{global_stats['total_tests']}</div>
                <div class="stat-label">Tests PASS total</div>
            </div>
            <div class="stat-card">
                <div class="stat-card">
                <div class="stat-value">{global_stats['total_time']}s</div>
                <div class="stat-label">Tiempo total</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{global_stats['total_tokens']:,}</div>
                <div class="stat-label">Tokens totales</div>
            </div>
        </div>
        
        <h2>Tabla Resumen</h2>
        <table class="summary-table">
            <thead>
                <tr>
                    <th>Modelo</th>
                    <th>Tipo</th>
                    <th>Score</th>
                    <th>Tests PASS</th>
                    <th>Tests FAIL</th>
                    <th>Errors</th>
                    <th>Tiempo total</th>
                    <th>Promedio/test</th>
                    <th>Tokens</th>
                </tr>
            </thead>
            <tbody>
"""
    
    for md in model_data:
        s = md["stats"]
        model_type = "API" if md["id"].startswith("api/") else "Nativo"
        score_class = "perfect" if s["passed"] == s["total"] else ("good" if s["passed"] >= s["total"] * 0.8 else "poor")
        
        html += f"""                <tr>
                    <td><strong>{escape_html(md['id'])}</strong></td>
                    <td>{model_type}</td>
                    <td class="score {score_class}">{s['passed']}/{s['total']}</td>
                    <td>{s['passed']}</td>
                    <td>{s['failed']}</td>
                    <td>{s['errors']}</td>
                    <td>{s['total_time']}s</td>
                    <td>{s['avg_time']}s</td>
                    <td>{s['total_tokens']:,}</td>
                </tr>
"""
    
    html += """            </tbody>
        </table>
        
        <h2>Navegación rápida</h2>
        <div class="tabs">
"""
    
    for i, md in enumerate(model_data):
        s = md["stats"]
        active = "active" if i == 0 else ""
        html += f'            <a href="#model-{i}" class="tab {active}">{escape_html(md["id"])} <span class="score">({s["passed"]}/{s["total"]})</span></a>\n'
    
    html += """        </div>
"""
    
    # Secciones detalladas por modelo
    for i, md in enumerate(model_data):
        cases = md["cases"]
        s = md["stats"]
        model_type = "API (Groq)" if md["id"].startswith("api/") else "Nativo (OpenCode)"
        
        html += f"""
        <div class="model-section" id="model-{i}">
            <div class="model-header">
                <div>
                    <span class="model-name">{escape_html(md['id'])}</span>
                    <span style="color: #666; margin-left: 10px;">({model_type})</span>
                </div>
                <div class="model-stats">
                    <span>Score: <strong>{s['passed']}/{s['total']}</strong></span>
                    <span>Tiempo: <strong>{s['total_time']}s</strong></span>
                    <span>Tokens: <strong>{s['total_tokens']:,}</strong></span>
                </div>
            </div>
            <div class="model-body">
"""
        
        for test_id in test_ids:
            if test_id not in cases:
                continue
            
            case = cases[test_id]
            q = questions.get(test_id, {})
            status = case.get("status", "UNKNOWN")
            status_lower = status.lower()
            badge_class = f"badge-{status_lower}"
            header_class = status_lower
            category = q.get("category", "")
            cat_class = f"cat-{category}"
            time_s = case.get("time_seconds", 0)
            tokens = case.get("tokens_used", 0)
            response = case.get("response_full", "")
            tools = case.get("tool_calls", [])
            
            # Formatear tool calls
            if tools:
                tools_html = ""
                for tc in tools:
                    args_str = json.dumps(tc.get("arguments", {}), ensure_ascii=False, indent=2)
                    result_str = tc.get("result", "N/A")
                    success = tc.get("success", False)
                    success_icon = "✓" if success else "✗"
                    tc_class = "success" if success else "error"
                    tools_html += f'<div class="tool-call {tc_class}"><strong>{success_icon} {escape_html(tc["name"])}</strong><br><small>{escape_html(str(result_str)[:200])}</small></div>'
            else:
                tools_html = '<span class="no-tools">No ejecutó tools</span>'
            
            html += f"""
                <div class="test-card">
                    <div class="test-header {header_class}" onclick="this.nextElementSibling.classList.toggle('open')">
                        <div>
                            <span class="category-label {cat_class}">{category}</span>
                            <span class="test-title">{test_id}: {escape_html(case.get('name', ''))}</span>
                        </div>
                        <div>
                            <span class="test-meta">{time_s}s | {tokens} tokens</span>
                            <span class="badge {badge_class}">{status}</span>
                        </div>
                    </div>
                    <div class="test-details">
                        <div class="section">
                            <div class="section-title">Pregunta</div>
                            <div class="response">{escape_html(q.get('prompt', 'N/A'))}</div>
                        </div>
                        <div class="section">
                            <div class="section-title">Tool Calls</div>
                            {tools_html}
                        </div>
                        <div class="section">
                            <div class="section-title">Respuesta completa</div>
                            <div class="response">{escape_html(response)}</div>
                        </div>
                    </div>
                </div>
"""
        
        html += """            </div>
        </div>
"""
    
    html += """
    </div>
    <script>
        // Auto-expand first test of each model
        document.querySelectorAll('.test-details').forEach((el, i) => {
            if (i < 8) el.classList.add('open');
        });
    </script>
</body>
</html>"""
    
    return html


def main():
    print("Generando reporte HTML consolidado...")
    
    results = load_results()
    questions = load_questions()
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    html = generate_html(results, questions)
    
    filename = "reporte_consolidado.html"
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    
    print(f"✅ Generado: {filepath}")
    print(f"   Modelos: {len(results.get('models', {}))}")
    print(f"   Tests/modelo: {len(questions)}")


if __name__ == "__main__":
    main()
