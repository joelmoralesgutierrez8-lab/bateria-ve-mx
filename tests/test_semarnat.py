"""Pruebas de la Línea 2 (SEMARNAT, segunda vida y brecha) con datos SINTÉTICOS.
Ejecutar:  python -m unittest tests.test_semarnat -v"""
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from etl import semarnat as S
from modelos.segunda_vida import clasificacion as C


class TestClasificacionLitio(unittest.TestCase):
    def test_positivos(self):
        for t in ["Baterías de ion-litio", "Baterias De Litio Residuales", "Pilas secas, alcalinas, níquel-cadmio, litio",
                  "polímero de litio", "Baterías de metal litio instaladas en un equipo", "Baterias Alcalinas De Ion De Litio"]:
            self.assertTrue(S.es_litio(t), t)

    def test_negativos(self):
        for t in ["Hidróxido de litio", "Grasa lubricante con jabón de litio", "alfa-naftiltiourea",
                  "aluminio, berilio, calcio, litio, potasio", "Acumuladores de vehículos automotores conteniendo plomo", None]:
            self.assertFalse(S.es_litio(t), t)


class TestEntidades(unittest.TestCase):
    def test_clave_y_nombre(self):
        self.assertEqual(S.clave_entidad("9", "x"), 9)
        self.assertEqual(S.clave_entidad("", "Distrito Federal"), 9)
        self.assertEqual(S.clave_entidad(None, "Estado de México"), 15)
        self.assertEqual(S.clave_entidad("nan", "Nuevo León"), 19)
        self.assertIsNone(S.clave_entidad("99", "Atlántida"))

    def test_32_entidades_sin_perdida(self):
        nombres = list(S.ENTIDADES_INEGI.values())
        self.assertEqual(len(set(nombres)), 32)
        self.assertTrue(all(S.clave_entidad(None, n) == k for k, n in S.ENTIDADES_INEGI.items()))

    def test_numero(self):
        self.assertEqual(S.numero("20,358"), 20358.0)
        self.assertTrue(np.isnan(S.numero("")))


class TestDirectorio(unittest.TestCase):
    def test_lectura_cp1252_y_capacidad(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "Rubro1_Reciclaje_prueba.csv"
            txt = ("No.,Empresa,Dirección,Municipio,Clave Municipio,Estado,Clave Estado,Teléfono,Tipo de Residuo,"
                   "No. de Autorización,Vigencia Inicio,Vigencia Término,Capacidad (ton/año),,\n"
                   '1,"Uno, S.A.",calle,Monterrey,39,Nuevo León,19,1,Baterías plomo-ácido,A1,01/01/2020,01/01/2030,"14,000",,\n'
                   '2,"Dos, S.A.",calle,Toluca,106,Estado de México,,1,Baterías de ion-litio,A2,01/01/2020,01/01/2030,500,,\n'
                   ",,,,,,,,,,,,,,\n")
            p.write_bytes(txt.encode("cp1252"))
            d = S.limpiar_directorios(Path(tmp))
        self.assertEqual(len(d), 2)
        self.assertEqual(d["capacidad_t_anio"].sum(), 14500)
        self.assertEqual(list(d["entidad"]), ["Nuevo León", "México"])
        self.assertEqual(list(d["litio"]), [False, True])
        self.assertEqual(list(d["plomo"]), [True, False])


class TestDestinos(unittest.TestCase):
    def test_destinos_suman_el_total(self):
        rng = np.random.default_rng(42)
        for _ in range(50):
            u, t, pb, p = rng.uniform(0, 1e4), rng.uniform(0, 1e3), rng.uniform(), rng.uniform()
            r = C.destinos(u, t, pb, p)
            suma = r["toneladas_sale_por_vehiculo_soh_mayor_80"] + r["toneladas_segunda_vida_80_70"] + r["toneladas_reciclaje_directo"]
            self.assertAlmostEqual(suma, t, places=6)
            self.assertTrue(0 <= r["pct_apto_reuso_o_segunda_vida"] <= 100)

    def test_margen_y_clases(self):
        t80 = pd.DataFrame({"conjunto": ["a"] * 3, "celda": ["c1", "c2", "c3"], "tiempo": [100.0] * 3,
                            "ultimo_ciclo": [200.0] * 3, "incluida": True, "evento": 1})
        t70 = pd.DataFrame({"conjunto": ["a"] * 3, "celda": ["c1", "c2", "c3"], "tiempo": [130.0, 105.0, 110.0],
                            "incluida": True, "evento": [1, 1, 0]})
        m = C.margen_por_celda(t80, t70, 0.2)
        self.assertEqual(list(m["clase"]), ["apta", "no_apta", "indeterminada"])
        self.assertEqual(C.p_apta(m["clase"].to_numpy()), 0.5)


if __name__ == "__main__":
    unittest.main()
