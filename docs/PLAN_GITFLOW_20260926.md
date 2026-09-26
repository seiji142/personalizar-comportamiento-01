# Plan — Adoptar gitflow-scaffold 2026.09.25 en personalizar-comportamiento-01

**Fecha:** 2026-09-26 · **Estado:** PENDIENTE (documentado, sin ejecutar)
**Fuente:** `Proyecto AI/templates/gitflow-scaffold` (VERSION 2026.09.25) ·
  referencia: `youtube-transcripts` commit `d4967b6` (patrón sin Pages).
**Decisiones del usuario:** merge clean-main→main primero · mantener
  clean-main · adaptar como youtube (sin deploy Pages).

## Check de ejecución

- [x] Fase 0 — Commit trabajo pendiente (12 paths suite de hoy) en clean-main + push
  (commit 507f051, 25/09)
- [x] Fase 1 — Copiar `scripts/gh-publish.ps1`, commit; PR clean-main→main
  + merge (sync 65 commits) — PR #1 creado y mergeado vía script 25/09;
  validación pre-PR: pytest unit + validators + rate_limit exit 0
- [x] Fase 2 — Crear `develop` desde `main` + push `-u origin develop` (25/09)
- [ ] Fase 3 — Kit en `develop`: `ci.yml` Python (pytest unit + validators +
  rate_limit), sección Ramas en `.ai/context.md`, Variante B + Publicación
  en `.ai/commands.md`
- [ ] Fase 4 — Protección `main` MANUAL en UI (Require PR + check `build`,
  SIN approvals)
- [ ] Fase 5 — Verificación (branches, status limpio, CI en próximo PR)
- [ ] No aplica: `deploy.yml`, `opencode.json` del kit

## Estado de partida (verificado 26/09, solo lectura)

- `main`: 2 commits (init+README), 65 atrás de `clean-main`; `clean-main`
  al día con `origin/clean-main`. Rama actual: `clean-main`.
- Sin `.github/`; `scripts/` propio sin colisiones (`suite_runner.py`,
  `generate_html_report.py`, `analyze_times.py`); `.ai/commands.md` y
  `.ai/context.md` existen (se agregan secciones, no se reemplazan).
- `gh` autenticado (seiji142, GH_TOKEN); PAT sin Administración (403 en
  lectura de protección) → protección manual en UI.
- `requirements.txt` liviano (fastapi/pytest/ruff/mypy); CI solo tests
  offline sin keys (suite, API y MCP quedan fuera del gate).
- `origin/HEAD` sin symref (detalle menor, no bloquea).

## Orden y reglas

- Fase 0 antes que todo (no perder trabajo sin commitear).
- Pre-PR (Fase 1): tests offline en verde (los mismos del futuro CI).
- NUNCA `gh pr create` / `gh pr merge` directos: todo vía
  `scripts/gh-publish.ps1` desde la raíz del repo.
- `main` solo se toca vía PR; trabajo diario en `develop`.
