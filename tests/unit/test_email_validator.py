#!/usr/bin/env python3
"""
Tests unitarios para la funcion de validacion de email simple.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from email_validator import validate_email_simple


class TestValidateEmailSimple(unittest.TestCase):
  """Tests para validate_email_simple."""

  def test_email_valido(self):
    """Emails con formato valido deben retornar True."""
    self.assertTrue(validate_email_simple("test@example.com"))
    self.assertTrue(validate_email_simple("user.name@domain.co"))
    self.assertTrue(validate_email_simple("user+tag@domain.org"))
    self.assertTrue(validate_email_simple("user123@domain.net"))

  def test_email_invalido(self):
    """Emails con formato invalido deben retornar False."""
    self.assertFalse(validate_email_simple("invalid"))
    self.assertFalse(validate_email_simple("@domain.com"))
    self.assertFalse(validate_email_simple("user@"))
    self.assertFalse(validate_email_simple("user@domain"))
    self.assertFalse(validate_email_simple("user domain.com"))
    self.assertFalse(validate_email_simple(""))

  def test_no_string(self):
    """No strings deben retornar False."""
    self.assertFalse(validate_email_simple(None))
    self.assertFalse(validate_email_simple(123))
    self.assertFalse(validate_email_simple([]))


if __name__ == "__main__":
  unittest.main()