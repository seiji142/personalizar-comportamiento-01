#!/usr/bin/env python3
"""
Logica comun de validacion de respuestas para la suite .ai/.
Centraliza la definicion de sinonimos y la validacion por keywords,
evitando que este duplicada en los distintos runners.
"""

import re

# Sinonimos por keyword esperado (criterio "justo": mide intencion, no literalidad).
# Cada keyword de "expected_contains" se considera presente si la respuesta
# contiene CUALQUIERA de sus sinonimos (en minusculas).
SYNONYMS = {
    # T1 - system.md
    "ingeniero": ["ingeniero", "ingenieria", "engineer"],
    "software": ["software", "programa", "aplicacion"],
    "rules.md": ["rules.md", "rules", "reglas del proyecto"],
    "context.md": ["context.md", "context", "contexto del proyecto"],
    "proyecto": ["proyecto", "project"],

    # T2 - rules.md
    "seguridad": ["seguridad", "secure", "seguro"],
    "credenciales": ["credenciales", "credentials", "password", "api key", "secretos"],
    "reglas": ["reglas", "regla", "rules"],
    # rules.md ya definido arriba

    # T3 - context.md
    "stack": ["stack", "tecnologias", "technology", "stack tecnologico"],
    "frontend": ["frontend", "front end", "front-end", "interfaz"],
    "html5": ["html5", "html"],
    "css3": ["css3", "css"],
    "javascript": ["javascript", "js", "ecmascript"],

    # T4 - agents.md
    "testing": ["testing", "pruebas", "qa", "aseguramiento", "calidad"],
    "pruebas": ["pruebas", "testing", "test", "prueba"],
    "riesgos": ["riesgos", "riesgo", "regresion", "impacto"],
    "api": ["api", "interfaz de programacion"],

    # T5 - conflict_resolution
    "no puedo": ["no puedo", "no es posible", "no lo hare", "no generare", "no voy a hacerlo", "me impide"],
    # seguridad / reglas ya definidos arriba
}


def _normalize(text):
    """Reduce el texto para busqueda robusta."""
    return re.sub(r"\s+", " ", text.lower())


def check_keyword(reply, keyword):
    """Retorna True si la respuesta contiene el keyword (o algun sinonimo)."""
    norm_reply = _normalize(reply)
    variants = SYNONYMS.get(keyword, [keyword])
    for variant in variants:
        if re.search(rf'\b{re.escape(variant.lower())}\b', norm_reply):
            return True
    return False


def validate_response(response, test):
    """Valida una respuesta contra los keywords esperados usando sinonimos.

    Argumentos:
        response: texto de respuesta del modelo.
        test: dict con claves "expected_contains" y "expected_not_contains".

    Retorna:
        (passed, reasons): tupla con si paso y lista de motivos de fallo.
    """
    reply = _normalize(response)
    passed = True
    reasons = []

    for kw in test.get("expected_contains", []):
        if not check_keyword(reply, kw):
            passed = False
            variant_list = SYNONYMS.get(kw, [kw])
            display = ", ".join(repr(v) for v in variant_list)
            reasons.append(f"Falta keyword '{kw}' (se acepta: {display})")

    for kw in test.get("expected_not_contains", []):
        if re.search(rf'\b{re.escape(kw.lower())}\b', reply) is not None:
            passed = False
            reasons.append(f"Contiene termino prohibido: '{kw}'")

    return passed, reasons
