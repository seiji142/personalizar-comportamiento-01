#!/usr/bin/env python3
"""
Función simple de validación de email.
Implementa un validador básico usando expresiones regulares.
"""

import re

# Patrón regex para validación básica de email
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')


def validate_email_simple(email):
  """
  Valida si una cadena tiene formato de email válido.

  Args:
    email (str): Cadena a validar.

  Returns:
    bool: True si el formato es válido, False en caso contrario.
  """
  if not isinstance(email, str):
    return False
  email = email.strip()
  # Longitud máxima según estándar RFC 5321
  if len(email) > 254:
    return False
  # Verificar que no esté vacío después de strip
  if not email:
    return False
  return bool(EMAIL_REGEX.match(email))