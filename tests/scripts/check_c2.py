import json

data = json.load(open('tests/answers/advanced_validation_report.json', 'r', encoding='utf-8'))

for model, tests in data['models'].items():
    if 'C2' in tests:
        t = tests['C2']
        status = t.get('status', 'N/A')
        reasons = t.get('reasons', [])
        full = t.get('response_full', '')
        print(f'=== {model} ===')
        print(f'Status: {status}')
        print(f'Reasons: {reasons}')
        print(f'Respuesta ({len(full)} chars):')
        print(full[:500])
        print()
