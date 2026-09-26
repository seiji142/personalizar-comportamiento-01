#!/usr/bin/env python3
"""Suite runner: entrypoint UNICO para lanzar run_all_tests.py de forma segura.

LANZAR SOLO VIA la herramienta async de tests (task_id), p.ej.:
    run_tests(command="python scripts/suite_runner.py",
              cwd="<raiz del proyecto>",
              timeout=5400)

PROHIBIDO (fallos reales del 23/09/2026):
  - Foreground con timeout de 90 min (se interrumpe y deja huerfanos).
  - Lanzar el mismo comando N veces en paralelo (7 instancias se pisaron
    los reportes con --fresh).
  - Start-Process -NoNewWindow desde la herramienta shell (el hijo muere
    al cerrarse la consola del comando).
  - Polls con Start-Sleep encadenados; esperar la notificacion de fin.

Que hace este script (todo automatico):
  1. Lock exclusivo en tests/answers/.suite.lock  -> exit 2 si ya corre otro.
  2. Preflight -> exit 3 si falla:
       - mata mcp_bridge.py huerfanos
       - backup de reportes + summary a docs/backup_YYYYMMDD_HHMMSS/
       - verifica GROQ_CUENTA_1/2 presentes (sin imprimir valores)
       - sondeo de cuota por cuenta (quota_probe.py, 1 query minima c/u)
         -> tests/answers/quota_status.json (tarea 15, paso 0)
  3. Ejecuta run_all_tests.py; stdout+stderr -> tests/answers/suite_runner.log
  4. Postflight gates -> tests/answers/suite_verification.json
       summary_nuevo, summary_ok (OK/BLOCKED_TPD), api_disponible,
       avanzada (4 modelos x 23, estados PASS/BLOCKED_TPD),
       estructura (4 modelos x 5, estados PASS/BLOCKED_TPD), html_nuevo
  5. Exit: 0 todo OK · 1 algun gate fallo · 2 lock ocupado · 3 preflight

Si un solo gate falla: arreglar ESA pieza y re-run selectivo del script
afectado (--only del sub-script), NUNCA relanzar la suite entera.
"""

import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ANSWERS_DIR = os.path.join(PROJECT_ROOT, "tests", "answers")
LOCK_PATH = os.path.join(ANSWERS_DIR, ".suite.lock")
LOG_PATH = os.path.join(ANSWERS_DIR, "suite_runner.log")
VERIFY_PATH = os.path.join(ANSWERS_DIR, "suite_verification.json")
RUN_ALL = os.path.join(PROJECT_ROOT, "run_all_tests.py")
ENV_PATH = os.path.abspath(os.path.join(PROJECT_ROOT, "..", "Verificacion-modelos-ai", ".env"))
DOCS_DIR = os.path.join(PROJECT_ROOT, "docs")
QUOTA_PROBE = os.path.join(PROJECT_ROOT, "tests", "scripts", "quota_probe.py")
QUOTA_PATH = os.path.join(PROJECT_ROOT, "tests", "answers", "quota_status.json")

# Estados del sondeo de cuota que no impiden correr la API
QUOTA_OK_STATES = ("OK", "BLOCKED_TPD", "TRANSIENT")
# Estados de caso que aprueban el gate (BLOCKED_TPD = cuota agotada != fallo)
GATE_OK_STATES = ("PASS", "BLOCKED_TPD")

ADVANCED_LABELS = [
    "api/openai/gpt-oss-20b",
    "api/qwen/qwen3.8-27b",
    "opencode/big-pickle",
    "opencode/mimo-v2.6-flash-free",
]
STRUCTURE_LABELS = ADVANCED_LABELS

REQUIRED_ENV_KEYS = ["GROQ_CUENTA_1", "GROQ_CUENTA_2"]

EXIT_OK = 0
EXIT_GATE_FAIL = 1
EXIT_LOCKED = 2
EXIT_PREFLIGHT = 3


def _log(msg):
    stamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{stamp}] {msg}", flush=True)


def _pid_alive(pid):
    """True si el PID existe en Windows (OpenProcess)."""
    if pid <= 0:
        return False
    try:
        import ctypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if handle:
            kernel32.CloseHandle(handle)
            return True
        return False
    except Exception:
        return False


def acquire_lock():
    """Lock via O_CREAT|O_EXCL (atomico en Windows).

    El lock es el archivo mismo: si otro proceso vivo lo tiene, exit 2.
    Si el PID del lock esta muerto, se roba (sin locks rancios).
    No usamos msvcrt.locking: el lock obligatorio de Windows daba
    PermissionError al intentar leer el PID ajeno.
    """
    os.makedirs(ANSWERS_DIR, exist_ok=True)
    for attempt in (1, 2):
        try:
            fd = os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode("ascii"))
            os.close(fd)
            return
        except FileExistsError:
            try:
                with open(LOCK_PATH, "r", encoding="ascii") as f:
                    holder_pid = int((f.read() or "0").strip() or "0")
            except (OSError, ValueError):
                holder_pid = 0
            if holder_pid and holder_pid != os.getpid() and _pid_alive(holder_pid):
                print(
                    f"[LOCK] Ya hay un suite_runner activo (PID {holder_pid}). "
                    f"Sale con exit {EXIT_LOCKED}.",
                    flush=True,
                )
                sys.exit(EXIT_LOCKED)
            # Lock rancio (PID muerto o ilegible): robar y reintentar
            try:
                os.remove(LOCK_PATH)
            except OSError:
                pass
            if attempt == 2:
                print(
                    f"[LOCK] No se pudo adquirir el lock tras reintento. "
                    f"Exit {EXIT_LOCKED}.",
                    flush=True,
                )
                sys.exit(EXIT_LOCKED)
    sys.exit(EXIT_LOCKED)


def release_lock():
    try:
        with open(LOCK_PATH, "r", encoding="ascii") as f:
            holder = (f.read() or "").strip()
        if holder == str(os.getpid()):
            os.remove(LOCK_PATH)
    except OSError:
        pass


def preflight():
    """Exit EXIT_PREFLIGHT si algo bloquea el run. No corre la suite a medias."""
    # 1) mcp_bridge huerfanos
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
             "Where-Object { $_.CommandLine -match 'mcp_bridge\\.py' }).Count"],
            capture_output=True, text=True, timeout=30,
        )
        orphan_count = int((out.stdout or "0").strip() or "0")
    except Exception:
        orphan_count = -1
    if orphan_count > 0:
        _log(f"Preflight: matando {orphan_count} mcp_bridge huerfanos...")
        subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
             "Where-Object { $_.CommandLine -match 'mcp_bridge\\.py' } | "
             "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"],
            capture_output=True, text=True, timeout=60,
        )
        time.sleep(1)

    # 2) backup de reportes + summary
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(DOCS_DIR, f"backup_{ts}")
    os.makedirs(backup_dir, exist_ok=True)
    for name in ("advanced_validation_report.json",
                 "ai_validation_report.json",
                 "test_run_summary.json"):
        src = os.path.join(ANSWERS_DIR, name)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(backup_dir, name))
    _log(f"Preflight: backup en docs/backup_{ts}")

    # 3) keys presentes sin imprimir valores
    if not os.path.exists(ENV_PATH):
        _log(f"Preflight FALLO: no existe {ENV_PATH}")
        sys.exit(EXIT_PREFLIGHT)
    found = set()
    with open(ENV_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                found.add(line.split("=", 1)[0].strip())
    missing = [k for k in REQUIRED_ENV_KEYS if k not in found]
    if missing:
        _log(f"Preflight FALLO: keys faltantes (sin imprimir valores): {missing}")
        sys.exit(EXIT_PREFLIGHT)
    _log("Preflight: GROQ_CUENTA_1/2 presentes")

    # 4) sondeo de cuota por cuenta (paso 0, tarea 15): si el sondeo no
    # deja quota_status.json legible, no se corre la suite a ciegas
    _log("Preflight: sondeo de cuota por cuenta (1 query minima c/u)...")
    try:
        out = subprocess.run(
            [sys.executable, QUOTA_PROBE],
            cwd=PROJECT_ROOT, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=120,
        )
        if out.stdout:
            for line in out.stdout.strip().splitlines():
                _log(f"  sondeo: {line}")
        if out.returncode != 0:
            _log(f"Preflight FALLO: quota_probe rc={out.returncode} "
                 f"stderr={(out.stderr or '')[-300:]}")
            sys.exit(EXIT_PREFLIGHT)
    except Exception as e:
        _log(f"Preflight FALLO: no se pudo ejecutar el sondeo: {e}")
        sys.exit(EXIT_PREFLIGHT)
    try:
        with open(QUOTA_PATH, encoding="utf-8") as f:
            quota = json.load(f)
        accounts = quota.get("accounts", {})
        if not accounts:
            raise ValueError("sin cuentas en quota_status.json")
        for account, res in accounts.items():
            status = res.get("status")
            if status not in QUOTA_OK_STATES:
                _log(f"Preflight: {account} = {status} (no es cuota; "
                     f"la API puede fallar y el gate api_disponible lo dira)")
    except Exception as e:
        _log(f"Preflight FALLO: quota_status.json ilegible: {e}")
        sys.exit(EXIT_PREFLIGHT)
    _log("Preflight: sondeo de cuota OK -> " +
         ", ".join(f"{a}={r.get('status')}" for a, r in accounts.items()))


def run_suite():
    """Ejecuta run_all_tests.py; devuelve returncode. Log con timestamps."""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    started = time.time()
    with open(LOG_PATH, "w", encoding="utf-8") as logf:
        logf.write(f"=== suite_runner start {datetime.now().isoformat()} ===\n")
        logf.flush()
        proc = subprocess.Popen(
            [sys.executable, RUN_ALL],
            cwd=PROJECT_ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            stamp = datetime.now().strftime("%H:%M:%S")
            logf.write(f"[{stamp}] {line}")
        rc = proc.wait()
        elapsed = round(time.time() - started, 1)
        logf.write(f"=== suite_runner end rc={rc} elapsed={elapsed}s ===\n")
    _log(f"run_all_tests.py rc={rc} elapsed={elapsed}s")
    return rc, started, elapsed


def _mtime(path):
    return os.path.getmtime(path) if os.path.exists(path) else 0.0


def model_gate(filename, labels, expected_n, key):
    """Gate por modelo con conteo de ESTADOS (flaw del run 23/09, tarea 15).

    Antes solo se contaba n: gpt-oss paso los gates con 5 FAIL + 23 ERROR.
    Ahora exige n exacto y que todos los casos esten en GATE_OK_STATES
    (PASS, o BLOCKED_TPD cuando la cuota diaria esta agotada).
    """
    path = os.path.join(ANSWERS_DIR, filename)
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        models = data.get("models", {})
        detail = {}
        ok = True
        for lab in labels:
            entry = models.get(lab)
            if entry is None:
                detail[lab] = "AUSENTE"
                ok = False
                continue
            if key == "cases":
                cases = entry if isinstance(entry, dict) else {}
                statuses = [c.get("status") for c in cases.values()
                            if isinstance(c, dict)]
                n = len(cases)
            else:  # estructura: {timestamp, results: []}
                cases_list = entry.get("results", []) if isinstance(entry, dict) else []
                statuses = [r.get("status") for r in cases_list
                            if isinstance(r, dict)]
                n = len(cases_list)
            bad = [s for s in statuses if s not in GATE_OK_STATES]
            detail[lab] = f"n={n} bad={len(bad)}"
            ok = ok and n == expected_n and not bad
        return ok, detail
    except Exception as e:
        return False, {"_error": str(e)}


def summary_gate(summary_status):
    """summary_ok: OK y BLOCKED_TPD aprueban; FAIL/TIMEOUT/ERROR no."""
    bad = {k: s for k, s in summary_status.items()
           if s not in ("OK", "BLOCKED_TPD")}
    ok = bool(summary_status) and not bad
    return ok, bad


def api_disponible_gate(quota_path=QUOTA_PATH):
    """Gate api_disponible: el sondeo existe y clasifico cada cuenta.

    BLOCKED_TPD (cuota agotada) NO es FAIL: permite correr solo nativos.
    Solo un sondeo ausente/ilegible o una cuenta con estado no clasificado
    (ERROR de API) deja el gate en rojo.
    """
    try:
        with open(quota_path, encoding="utf-8") as f:
            quota = json.load(f)
        accounts = quota.get("accounts", {})
        if not accounts:
            return False, {"_error": "sin cuentas"}
        detail = {acct: res.get("status") for acct, res in accounts.items()}
        ok = all(res.get("status") in QUOTA_OK_STATES
                 for res in accounts.values())
        return ok, detail
    except Exception as e:
        return False, {"_error": str(e)}


def verify(started):
    """Gates post-run. Escribe suite_verification.json. Retorna (ok, gates)."""
    gates = {}

    summary_path = os.path.join(ANSWERS_DIR, "test_run_summary.json")
    gates["summary_nuevo"] = _mtime(summary_path) >= started - 5
    summary_status = {}
    try:
        with open(summary_path, encoding="utf-8") as f:
            summary = json.load(f)
        summary_status = {k: v.get("status") for k, v in summary.get("results", {}).items()}
    except Exception as e:
        summary_status = {"_error": str(e)}
    gates["summary_ok"], bad = summary_gate(summary_status)

    api_ok, api_detail = api_disponible_gate()
    gates["api_disponible"] = api_ok

    adv_ok, adv_detail = model_gate(
        "advanced_validation_report.json", ADVANCED_LABELS, 23, "cases")
    gates["avanzada_4x23"] = adv_ok

    st_ok, st_detail = model_gate(
        "ai_validation_report.json", STRUCTURE_LABELS, 5, "results")
    gates["estructura_4x5"] = st_ok

    html_path = os.path.join(DOCS_DIR, "tests", "reporte_consolidado.html")
    gates["html_nuevo"] = _mtime(html_path) >= started - 5

    all_ok = all(bool(v) for v in gates.values())
    payload = {
        "timestamp": datetime.now().isoformat(),
        "started": datetime.fromtimestamp(started).isoformat(),
        "all_ok": all_ok,
        "gates": gates,
        "summary_statuses": summary_status,
        "summary_bad": bad,
        "api_disponible_detail": api_detail,
        "avanzada_detail": adv_detail,
        "estructura_detail": st_detail,
        "log": LOG_PATH,
    }
    with open(VERIFY_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    _log(f"Gates: {gates} -> {'TODO OK' if all_ok else 'FALLO'}")
    _log(f"Verificacion: {VERIFY_PATH}")
    return all_ok, payload


def main():
    acquire_lock()
    try:
        _log("suite_runner: lock adquirido")
        preflight()
        rc, started, elapsed = run_suite()
        all_ok, payload = verify(started)
        print("\n=== SUITE VERIFICATION ===", flush=True)
        print(json.dumps(payload["gates"], indent=2), flush=True)
        if rc != 0 and not all_ok:
            sys.exit(EXIT_GATE_FAIL)
        if not all_ok:
            sys.exit(EXIT_GATE_FAIL)
        _log(f"Suite completa OK en {elapsed}s")
        sys.exit(EXIT_OK)
    finally:
        release_lock()


if __name__ == "__main__":
    main()
