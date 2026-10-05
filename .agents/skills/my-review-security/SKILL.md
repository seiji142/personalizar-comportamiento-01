---
name: my-review-security
description: Revisión de seguridad (auth, inyección, secretos, validación). Úsalo junto a my-review cuando el cambio toque rutas, inputs o credenciales.
---

# my-review-security — revisión de seguridad

Complementa a `my-review` (que no cubre seguridad). Revisa en este orden.
Sé puntual: archivo + línea + severidad (bloqueante/menor) + fix en 1 línea.

## 1. Autenticación y autorización
Rutas que mutan estado sin exigir login; auth falsificable (substring,
cookie sin firmar, cliente que decide); falta de CSRF en mutaciones web;
sesiones sin expiración ni flags (`HttpOnly`, `SameSite`).

## 2. Inyección y XSS
Inputs sin validar ni sanear que llegan a HTML (escapar), SQL/comandos
(parametrizar), cabeceras o cookies (whitelist). Límites de largo ausentes.

## 3. Secretos y transporte
Claves/tokens hardcodeados o en logs; secretos subidos al repo (revisar
`.gitignore`); endpoints sensibles sin TLS; errores que filtran internals.

## 4. Validación de entrada
Bordes: valores duplicados (`?q=a&q=b`), vacíos, sobrelargos, tipos
inesperados, métodos no contemplados. Cada borde: ¿qué responde el sistema?

## 5. Ítems extra (lista corta, auditoría externa)
- Authz/IDOR y escalada (no solo autenticación).
- Supply chain: dependencias nuevas sin lockfile ni registro oficial
  (nombres alucinados = slopsquatting).
- Secretos fuera de `.env`: historial git, logs, fixtures, stack traces.
- Superficie scripts/CI/skills/permisos: qué ejecuta cada pieza y con
  qué credenciales.

## Reglas
- Severidad honesta: bloqueante solo si es explotable en el contexto real
  del proyecto; lo demás es menor. En un fixture demo, dilo y baja el tono.
- Genérico: sin rutas ni stacks hardcodeados.
- Si no hay nada, dilo en una línea, no inventes hallazgos.
