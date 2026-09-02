#!/usr/bin/env python3
"""
Genera un reporte HTML con las respuestas completas de los tests.

Uso:
  python generate_html_report.py

Genera archivos HTML en src/doc/LECCIONES/ con las respuestas de cada modelo.
"""

import json
import os
from datetime import datetime


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
QUESTIONS_FILE = os.path.join(PROJECT_ROOT, "src", "doc", "ESTRUCTURA", "advanced_questions.json")
REPORT_FILE = os.path.join(PROJECT_ROOT, "advanced_validation_report.json")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "src", "doc", "LECCIONES")


def load_questions():
    """Carga las preguntas desde advanced_questions.json."""
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        return {q["id"]: q for q in json.load(f)}


def load_results():
    """Carga los resultados desde advanced_validation_report.json."""
    with open(REPORT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def escape_html(text):
    """Escapa caracteres HTML."""
    if not text:
        return ""
    return (text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;"))


def generate_html(results, questions, model_id):
    """Genera HTML para un modelo específico."""
    cases = results["models"].get(model_id, {})
    
    # Calcular estadísticas
    total = len(cases)
    passed = sum(1 for c in cases.values() if c.get("status") == "PASS")
    failed = sum(1 for c in cases.values() if c.get("status") == "FAIL")
    errors = sum(1 for c in cases.values() if c.get("status") == "ERROR")
    total_time = sum(c.get("time_seconds", 0) for c in cases.values())
    total_tokens = sum(c.get("tokens_used", 0) for c in cases.values())
    avg_time = total_time / total if total > 0 else 0
    
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Respuestas {model_id} - Suite D</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            margin: 0; 
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
        .meta {{ color: #666; margin-bottom: 20px; }}
        .stats {{
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
        .stat-label {{ color: #666; margin-top: 5px; }}
        .test-card {{
            background: white;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .test-header {{
            padding: 15px 20px;
            border-left: 5px solid #007bff;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
        }}
        .test-header.pass {{ border-left-color: #28a745; background: #d4edda; }}
        .test-header.fail {{ border-left-color: #dc3545; background: #f8d7da; }}
        .test-header.error {{ border-left-color: #ffc107; background: #fff3cd; }}
        .test-title {{ font-size: 1.2em; font-weight: bold; }}
        .test-meta {{ color: #666; font-size: 0.9em; }}
        .test-body {{ padding: 20px; }}
        .section {{ margin-bottom: 15px; }}
        .section-title {{ 
            font-weight: bold; 
            color: #333; 
            margin-bottom: 8px;
            padding-bottom: 5px;
            border-bottom: 1px solid #eee;
        }}
        .prompt {{ 
            background: #f8f9fa; 
            padding: 15px; 
            border-radius: 4px;
            font-style: italic;
            white-space: pre-wrap;
        }}
        .response {{ 
            background: #fff; 
            padding: 15px; 
            border: 1px solid #ddd;
            border-radius: 4px;
            white-space: pre-wrap;
            max-height: 400px;
            overflow-y: auto;
        }}
        .tool-calls-container {{
            display: flex;
            flex-direction: column;
            gap: 10px;
        }}
        .tool-call {{
            background: #e7f3ff;
            padding: 12px;
            border-radius: 4px;
            border-left: 3px solid #007bff;
        }}
        .tool-call.success {{ border-left-color: #28a745; background: #d4edda; }}
        .tool-call.error {{ border-left-color: #dc3545; background: #f8d7da; }}
        .tool-name {{ font-weight: bold; color: #007bff; }}
        .tool-args {{ font-size: 0.9em; color: #666; margin-top: 8px; }}
        .tool-args pre {{ 
            background: #f8f9fa; 
            padding: 8px; 
            border-radius: 4px;
            overflow-x: auto;
            font-size: 0.85em;
        }}
        .tool-result {{ font-size: 0.9em; color: #28a745; margin-top: 8px; }}
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 0.9em;
            font-weight: bold;
        }}
        .badge-pass {{ background: #28a745; color: white; }}
        .badge-fail {{ background: #dc3545; color: white; }}
        .badge-error {{ background: #ffc107; color: #333; }}
        .test-info {{
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
        }}
        .test-info-item {{
            display: flex;
            align-items: center;
            gap: 5px;
        }}
        .no-tools {{ color: #999; font-style: italic; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Respuestas completas - {escape_html(model_id)}</h1>
        <p class="meta">Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value">{passed}/{total}</div>
                <div class="stat-label">Tests PASS</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{total_time:.1f}s</div>
                <div class="stat-label">Tiempo total</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{total_tokens:,}</div>
                <div class="stat-label">Tokens totales</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{avg_time:.1f}s</div>
                <div class="stat-label">Promedio/test</div>
            </div>
        </div>
        
        <h2>Detalle por test</h2>
"""
    
    for test_id in ["D1", "D2", "D3", "D4", "D5", "D6", "D7", "D9"]:
        if test_id not in cases:
            continue
        
        case = cases[test_id]
        q = questions.get(test_id, {})
        
        prompt = q.get("prompt", "N/A")
        response = case.get("response_full", "")
        tools = case.get("tool_calls", [])
        time_s = case.get("time_seconds", 0)
        tokens = case.get("tokens_used", 0)
        status = case.get("status", "UNKNOWN")
        name = case.get("name", test_id)
        
        status_lower = status.lower()
        badge_class = f"badge-{status_lower}"
        
        # Formatear tool calls
        if tools:
            tools_html = '<div class="tool-calls-container">'
            for tc in tools:
                args_str = json.dumps(tc.get('arguments', {}), ensure_ascii=False, indent=2)
                result_str = tc.get('result', 'N/A')
                success = tc.get('success', False)
                success_icon = "✅" if success else "❌"
                tc_class = "success" if success else "error"
                
                tools_html += f"""<div class="tool-call {tc_class}">
                    <span class="tool-name">{success_icon} {escape_html(tc['name'])}</span>
                    <div class="tool-args"><strong>Argumentos:</strong><pre>{escape_html(args_str[:500])}</pre></div>
                    <div class="tool-result"><strong>Resultado:</strong> {escape_html(str(result_str)[:300])}</div>
                </div>"""
            tools_html += '</div>'
        else:
            tools_html = '<span class="no-tools">No se ejecutaron tools</span>'
        
        html += f"""
        <div class="test-card">
            <div class="test-header {status_lower}">
                <div>
                    <span class="test-title">{test_id}: {escape_html(name)}</span>
                    <div class="test-meta">{escape_html(q.get('category', ''))}</div>
                </div>
                <div class="test-info">
                    <div class="test-info-item">
                        <span class="badge {badge_class}">{status}</span>
                    </div>
                    <div class="test-info-item">
                        <strong>Tiempo:</strong> {time_s}s
                    </div>
                    <div class="test-info-item">
                        <strong>Tokens:</strong> {tokens:,}
                    </div>
                </div>
            </div>
            <div class="test-body">
                <div class="section">
                    <div class="section-title">Pregunta</div>
                    <div class="prompt">{escape_html(prompt)}</div>
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
    
    html += """
    </div>
</body>
</html>"""
    
    return html


def main():
    """Función principal."""
    print("Generando reporte HTML...")
    
    results = load_results()
    questions = load_questions()
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    generated = []
    
    for model_id in results.get("models", {}):
        html = generate_html(results, questions, model_id)
        safe_name = model_id.replace("/", "_").replace("\\", "_")
        filename = f"respuestas_{safe_name}.html"
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)
        
        generated.append(filepath)
        print(f"✅ Generado: {filepath}")
        print(f"   Modelo: {model_id}")
        print(f"   Tests: {len(results['models'][model_id])}")
    
    print(f"\n total: {len(generated)} archivos HTML generados")


if __name__ == "__main__":
    main()
