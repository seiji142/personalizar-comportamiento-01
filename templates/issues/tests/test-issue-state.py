"""Tests deterministas de scripts/issue_state.py (stdlib, sin red).

Uso: python tests/test-issue-state.py
Sale 0 si todo OK; 1 con la lista de fallos. No necesita el repo real:
cada caso arma un registro y un docs/issue/ en una carpeta temporal.
"""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import issue_state as st  # noqa: E402


def issue_block(
    iid="I-01",
    sev="P0",
    estado="abierto",
    fecha="2026-11-03",
    repro="root=docs/img · tarea=borra las personas",
    evidencia="I-01-1.png",
    test="—",
    sha="—",
    aceptado="—",
    esperaba="el fondo queda limpio",
    paso="queda una mancha gris",
    title="Un título cualquiera",
):
    """Un registro con los campos obligatorios; cada test pisa lo que necesita."""
    lines = [
        f"## {iid} · {title}",
        f"sev: {sev}",
        f"estado: {estado}",
        f"fecha: {fecha}",
        f"esperaba: {esperaba}",
        f"paso: {paso}",
        f"repro: {repro}",
        f"evidencia: {evidencia}",
        f"test: {test}",
        f"sha: {sha}",
        f"aceptado: {aceptado}",
        "",
        "Cuerpo en prosa que se conserva tal cual.",
    ]
    return "\n".join(lines)


BLOCK = (
    "<!-- generado:inicio -->\n### Resumen\n\n(sin generar)\n<!-- generado:fin -->"
)


def doc(abiertos="", verificacion="", cerrados=None, descartados=None, block=BLOCK):
    """Documento completo con las cuatro zonas, vacías por defecto."""
    cerrados = cerrados if cerrados is not None else []
    descartados = descartados if descartados is not None else []
    parts = ["# Lista de issues", "", block, ""]
    parts += ["## Abiertos", ""]
    for b in abiertos:
        parts += [b, ""]
    parts += ["## En verificación", ""]
    for b in verificacion:
        parts += [b, ""]
    parts += ["## Cerrados", "", "| # | fecha | sha | test | aceptado |", "|---|---|---|---|---|"]
    parts += cerrados
    parts += ["", "## Descartados", "", "| # | motivo |", "|---|---|"]
    parts += descartados
    parts += [""]
    return "\n".join(parts)


class Base(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="issue-state-"))
        (self.root / "docs" / "issue").mkdir(parents=True)
        self.file = self.root / "docs" / "issue" / "LISTA-ISSUES.md"

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def write(self, text):
        self.file.write_text(text, encoding="utf-8", newline="\n")

    def png(self, name):
        (self.root / "docs" / "issue" / name).write_bytes(b"\x89PNG\r\n\x1a\n")

    def errors(self, text):
        self.write(text)
        reg = st.load(self.file)
        return st.validate(reg, self.root / "docs" / "issue")


class TestParse(Base):
    def test_registro_valido_sin_errores(self):
        self.png("I-01-1.png")
        self.assertEqual(self.errors(doc([issue_block()])), [])

    def test_parsea_campos_e_identifica_zonas(self):
        self.write(doc([issue_block()], [issue_block("I-02", estado="arreglado", test="43")]))
        reg = st.load(self.file)
        self.assertEqual(sorted(reg.issues), ["I-01", "I-02"])
        self.assertEqual(reg.issues["I-02"].estado, "arreglado")
        self.assertEqual(reg.issues["I-02"].zone, "## En verificación")

    def test_el_cuerpo_en_prosa_se_conserva(self):
        self.write(doc([issue_block()]))
        reg = st.load(self.file)
        self.assertIn("Cuerpo en prosa", reg.issues["I-01"].body)


class TestZonas(Base):
    def test_cabecera_de_issue_ilegible(self):
        # Sin título la sección no se parsea y se saltaría TODA la validación.
        self.png("I-01-1.png")
        text = doc([issue_block()]).replace("## I-01 · Un título cualquiera", "## I-01")
        self.assertTrue(any("ilegible" in e for e in self.errors(text)))

    def test_cabecera_con_guion_largo_es_valida(self):
        self.png("I-01-1.png")
        text = doc([issue_block()]).replace("## I-01 · Un título", "## I-01 — Un título")
        self.assertEqual(self.errors(text), [])

    def test_falta_una_zona(self):
        self.png("I-01-1.png")
        text = doc([issue_block()]).replace("## Descartados", "## Otra cosa")
        self.assertTrue(any("Descartados" in e for e in self.errors(text)))

    def test_zonas_desordenadas(self):
        self.png("I-01-1.png")
        text = doc([issue_block()])
        text = text.replace("## Abiertos", "@@Z@@").replace("## En verificación", "## Abiertos")
        text = text.replace("@@Z@@", "## En verificación")
        self.assertTrue(any("orden" in e for e in self.errors(text)))

    def test_seccion_en_zona_que_no_corresponde(self):
        self.png("I-01-1.png")
        text = doc([issue_block(estado="arreglado", test="43")])
        self.assertTrue(any("zona" in e for e in self.errors(text)))


class TestEstados(Base):
    def test_estado_invalido(self):
        self.png("I-01-1.png")
        self.assertTrue(any("estado" in e for e in self.errors(doc([issue_block(estado="roto")]))))

    def test_falta_estado(self):
        self.png("I-01-1.png")
        text = doc([issue_block()]).replace("estado: abierto\n", "")
        self.assertTrue(any("estado" in e for e in self.errors(text)))

    def test_sev_invalida(self):
        self.png("I-01-1.png")
        self.assertTrue(any("sev" in e for e in self.errors(doc([issue_block(sev="P9")]))))

    def test_abierto_sin_esperaba(self):
        self.png("I-01-1.png")
        self.assertTrue(
            any("esperaba" in e for e in self.errors(doc([issue_block(esperaba="—")])))
        )


class TestArreglado(Base):
    def test_arreglado_sin_test(self):
        self.png("I-01-1.png")
        errs = self.errors(doc([issue_block(estado="arreglado", test="—")], []))
        self.assertTrue(any("test" in e for e in errs))

    def test_arreglado_p3_sin_test_tambien_falla(self):
        # S8: la severidad no cambia la vara.
        self.png("I-01-1.png")
        errs = self.errors(doc([issue_block(sev="P3", estado="arreglado", test="—")]))
        self.assertTrue(any("test" in e for e in errs))

    def test_arreglado_sin_repro(self):
        self.png("I-01-1.png")
        errs = self.errors(doc([issue_block(estado="arreglado", test="43", repro="—")]))
        self.assertTrue(any("repro" in e for e in errs))

    def test_arreglado_sin_test_pero_con_corrida_medida_es_valido(self):
        # Un test verde no prueba que el síntoma desapareció; una corrida medida
        # sí es evidencia del síntoma (regla del humano, L1).
        self.png("I-01-1.png")
        block = issue_block(
            estado="arreglado",
            test="—",
            repro="corrida ui-20261104-130600 · root=docs/img · tarea=describe la foto",
        )
        self.assertEqual(self.errors(doc(verificacion=[block])), [])

    def test_arreglado_sin_test_y_sin_corrida_falla(self):
        self.png("I-01-1.png")
        block = issue_block(estado="arreglado", test="—", repro="root=docs/img · tarea=x")
        errs = self.errors(doc(verificacion=[block]))
        self.assertTrue(any("corrida" in e for e in errs))

    def test_arreglado_con_test_y_sha_vacio_es_valido(self):
        self.png("I-01-1.png")
        block = issue_block(estado="arreglado", test="43", sha="—")
        self.assertEqual(self.errors(doc(verificacion=[block])), [])


class TestCierre(Base):
    def test_aceptado_en_una_seccion_es_error(self):
        self.png("I-01-1.png")
        text = doc([issue_block(aceptado='2026-11-10 "funciona"')])
        self.assertTrue(any("aceptado" in e for e in self.errors(text)))

    def test_fila_de_cerrado_sin_frase_citada(self):
        fila = "| I-01 | 2026-11-10 | abc1234 | 43 | 2026-11-10 sin comillas |"
        self.assertTrue(any("aceptado" in e for e in self.errors(doc(cerrados=[fila]))))

    def test_fila_de_cerrado_valida(self):
        fila = '| I-01 | 2026-11-10 | abc1234 | 43 | 2026-11-10 "borre las personas y quedo limpio" |'
        self.assertEqual(self.errors(doc(cerrados=[fila])), [])

    def test_misma_frase_en_dos_issues_es_valida(self):
        # S7: el lote es la frase repetida, sin registro de casos.
        frase = '"borre las 4 personas de bus.jpg y no quedo fantasma"'
        filas = [
            f"| I-01 | 2026-11-10 | abc1234 | 43 | 2026-11-10 {frase} |",
            f"| I-02 | 2026-11-10 | abc1234 | 42 | 2026-11-10 {frase} |",
        ]
        self.assertEqual(self.errors(doc(cerrados=filas)), [])

    def test_descartado_sin_motivo(self):
        self.assertTrue(any("motivo" in e for e in self.errors(doc(descartados=["| I-05 |  |"]))))


class TestImagenes(Base):
    def test_png_con_nombre_libre(self):
        self.png("2026-11-08-borrado-fantasma-1.png")
        errs = self.errors(doc([issue_block(evidencia="—")]))
        self.assertTrue(any("nombre" in e for e in errs))

    def test_png_de_issue_inexistente(self):
        self.png("I-99-1.png")
        errs = self.errors(doc([issue_block(evidencia="I-99-1.png")]))
        self.assertTrue(any("I-99" in e for e in errs))

    def test_tope_de_tres_imagenes(self):
        for n in (1, 2, 3, 4):
            self.png(f"I-01-{n}.png")
        errs = self.errors(doc([issue_block(evidencia="I-01-1.png")]))
        self.assertTrue(any("3" in e for e in errs))

    def test_evidencia_inexistente(self):
        errs = self.errors(doc([issue_block(evidencia="I-01-9.png")]))
        self.assertTrue(any("existe" in e or "inexistente" in e for e in errs))

    def test_evidencia_de_otro_issue_es_valida(self):
        # Una captura pertenece a un issue y la pueden citar otros.
        self.png("I-02-1.png")
        errs = self.errors(
            doc([issue_block(evidencia="I-02-1.png"), issue_block("I-02", evidencia="I-02-1.png")])
        )
        self.assertEqual(errs, [])


class TestBloqueGenerado(Base):
    def test_el_bloque_muestra_la_corrida_cuando_no_hay_test(self):
        # Un `test: —` con corrida medida no puede quedar como "nada" en la tabla.
        self.png("I-01-1.png")
        block = issue_block(estado="arreglado", test="—",
                            repro="corrida ui-20261104-130600 · tarea=x")
        self.write(doc(verificacion=[block]))
        self.assertEqual(st.run(["--write"], self.root), 0)
        self.assertIn("corrida ui-20261104-130600", self.file.read_text(encoding="utf-8"))

    def test_write_y_check_verdes(self):
        self.png("I-01-1.png")
        self.write(doc([issue_block()]))
        reg = st.load(self.file)
        self.assertEqual(st.run(["--write"], self.root), 0)
        self.assertEqual(st.run(["--check"], self.root), 0)
        self.assertIn("abierto", self.file.read_text(encoding="utf-8"))

    def test_editar_el_bloque_a_mano_rompe_el_check(self):
        self.png("I-01-1.png")
        self.write(doc([issue_block()]))
        self.assertEqual(st.run(["--write"], self.root), 0)
        text = self.file.read_text(encoding="utf-8").replace(
            "| abierto | 1 |", "| abierto | 99 |"
        )
        self.write(text)
        self.assertEqual(st.run(["--check"], self.root), 1)

    def test_el_bloque_no_se_parsea_como_zona(self):
        self.png("I-01-1.png")
        self.write(doc([issue_block()]))
        self.assertEqual(st.run(["--write"], self.root), 0)
        reg = st.load(self.file)
        self.assertEqual(sorted(reg.issues), ["I-01"])

    def test_cuenta_los_cuatro_estados(self):
        self.png("I-01-1.png")
        fila = '| I-07 | 2026-11-10 | abc1234 | 51 | 2026-11-10 "cerrado de verdad" |'
        desc = "| I-08 | no es un bug: el motor se abstiene bien |"
        self.write(
            doc(
                [issue_block()],
                [issue_block("I-02", estado="arreglado", test="43")],
                cerrados=[fila],
                descartados=[desc],
            )
        )
        reg = st.load(self.file)
        counts = st.counts(reg)
        self.assertEqual(counts, {"abierto": 1, "arreglado": 1, "cerrado": 1, "descartado": 1})


class TestBandejaYNumero(Base):
    def test_bandeja_lista_lo_no_citado(self):
        self.png("I-01-1.png")
        self.write(doc([issue_block()]))
        (self.root / "docs" / "issue" / "2026-11-08-nuevo.md").write_text("x", encoding="utf-8")
        (self.root / "docs" / "issue" / "2026-11-08-nuevo-1.png").write_bytes(b"x")
        inbox = st.inbox(st.load(self.file), self.root / "docs" / "issue")
        self.assertEqual(inbox, ["2026-11-08-nuevo-1.png", "2026-11-08-nuevo.md"])

    def test_el_registro_no_es_bandeja(self):
        self.write(doc([issue_block()]))
        self.assertEqual(st.inbox(st.load(self.file), self.root / "docs" / "issue"), [])

    def test_next_id_usa_el_maximo_incluida_la_letra(self):
        self.png("I-20b-1.png")
        self.write(
            doc([issue_block("I-07"), issue_block("I-20b"), issue_block("I-31")])
        )
        reg = st.load(self.file)
        self.assertEqual(st.next_id(reg), 32)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        import issue_state  # noqa: F401
    except Exception as exc:  # pragma: no cover - el ROJO esperado antes de implementar
        print(f"ROJO: no se pudo importar scripts/issue_state.py: {exc}")
        sys.exit(1)
    unittest.main(verbosity=2)
