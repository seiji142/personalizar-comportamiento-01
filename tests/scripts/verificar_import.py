#!/usr/bin/env python3
"""Verificar __file__ real de model_runner.py al importar."""
import os
import sys

sys.path.insert(0, os.path.join(os.getcwd(), "tests", "lib"))

import model_runner

print(f"model_runner.__file__: {model_runner.__file__}")
print(f"dirname:               {os.path.dirname(model_runner.__file__)}")
print(f"PROJECT_ROOT:          {model_runner.PROJECT_ROOT}")
print(f"TEST_PROJECT:          {model_runner.TEST_PROJECT}")
print(f"TEST_PROJECT exists:   {os.path.exists(model_runner.TEST_PROJECT)}")
