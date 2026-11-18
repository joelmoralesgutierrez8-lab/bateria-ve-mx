"""Pruebas con datos SINTÉTICOS. Demuestran que la lógica del ETL funciona; NO prueban los archivos reales.
Ejecutar:  python -m unittest discover -s tests -v"""
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

from etl import descargas as D
from etl import limpieza as L


class TestInegi(unittest.TestCase):
    def _largo(self):
        return pd.DataFrame({
            "Año": ["2025", "2025", "2025", "2025", "2025", "2025"],
            "Mes": ["Enero", "Enero", "Febrero", "Febrero", "Marzo", "Marzo"],
            "Entidad Federativa": ["Puebla", "Puebla", "Puebla", "Puebla", "Puebla", "Puebla"],
            "Unidades vehiculares": ["Unidades Vehiculares Eléctricas", "Unidades Vehiculares Hibridas Plugin"] * 3,
            "Valor": ["10", "-", "12", "3", "-", "-"],
        })

    def test_formato_largo_y_meses_no_publicados(self):
        out = L.normalizar_ventas_inegi(self._largo())
        self.assertEqual(set(out["tipo"]), {"BEV", "PHEV"})
        self.assertEqual(out["fecha"].max(), pd.Timestamp("2025-02-01"))      # marzo aún no publicado
        fila = out[(out.fecha == "2025-01-01") & (out.tipo == "PHEV")].iloc[0]
        self.assertTrue(np.isnan(fila.unidades) and fila.sin_reporte)         # '-' = sin reporte, no cero

    def test_formato_ancho(self):
        ancho = pd.DataFrame({"Año": ["2024", "2024"], "Mes": ["Enero", "Febrero"],
                              "Entidad Federativa": ["Sonora", "Sonora"],
                              "Unidades Vehiculares Eléctricas": ["5", "7"],
                              "Unidades Vehiculares Hibridas Plugin": ["1", "2"],
                              "Unidades Vehiculares Hibridas": ["100", "120"]})
        out = L.normalizar_ventas_inegi(ancho)
        self.assertEqual(len(out), 6)
        self.assertEqual(out[(out.tipo == "HEV") & (out.mes == 2)].unidades.iloc[0], 120)
        nac = L.agregar_nacional(out)
        self.assertEqual(nac[(nac.tipo == "BEV") & (nac.fecha == "2024-01-01")].unidades.iloc[0], 5)

    def test_ventas_negativas_fallan(self):
        d = self._largo()
        d.loc[0, "Valor"] = "-5"      # '-5' NO es el guion de 'sin dato'
        with self.assertRaises(ValueError):
            L.normalizar_ventas_inegi(d)

    def test_region_sin_mapa_deja_nan(self):
        out = L.normalizar_ventas_inegi(self._largo())
        cw = pd.DataFrame({"entidad": ["Puebla"], "region_cenace": [""]})
        self.assertTrue(L.asignar_region(out, cw)["region_cenace"].isna().all())
        cw2 = pd.DataFrame({"entidad": ["Puebla"], "region_cenace": ["X"]})
        self.assertTrue((L.asignar_region(out, cw2)["region_cenace"] == "X").all())


class TestCenace(unittest.TestCase):
    def test_factor_implicito(self):
        cols = {"fecha": "f", "region": "r", "tecnologia": "t", "energia_mwh": "e"}
        raw = pd.DataFrame({"f": ["2025-01-01"] * 4, "r": ["A"] * 4,
                            "t": ["Eólica", "Ciclo Combinado", "Eólica", "Ciclo Combinado"],
                            "e": ["100", "300", "100", "300"]})
        gen = L.normalizar_generacion(raw, cols, ["eolic"])
        self.assertEqual(len(gen), 2)                                   # duplicado exacto eliminado
        fac = pd.DataFrame({"tecnologia": ["Eólica", "Ciclo Combinado"], "g_co2e_por_kwh": [10, 500]})
        r = L.factor_emision_implicito(gen, fac)
        self.assertAlmostEqual(r.g_co2e_por_kwh.iloc[0], (100 * 10 + 300 * 500) / 400)   # 376.25
        self.assertAlmostEqual(r.pct_limpia.iloc[0], 25.0)

    def test_tecnologia_sin_factor_falla(self):
        gen = pd.DataFrame({"fecha": [pd.Timestamp("2025-01-01")], "region": ["A"], "tecnologia": ["carbon"],
                            "energia_mwh": [10.0], "limpia": [False]})
        with self.assertRaises(ValueError):
            L.factor_emision_implicito(gen, pd.DataFrame({"tecnologia": ["eolica"], "g_co2e_por_kwh": [10]}))

    def test_columnas_incorrectas_fallan(self):
        with self.assertRaises(ValueError):
            L.normalizar_generacion(pd.DataFrame({"x": [1]}), {"fecha": "f", "region": "r",
                                                                "tecnologia": "t", "energia_mwh": "e"}, [])


class TestBaterias(unittest.TestCase):
    def test_soh_nasa(self):
        ciclos = [SimpleNamespace(type="charge", ambient_temperature=24, data=SimpleNamespace(Capacity=0)),
                  SimpleNamespace(type="discharge", ambient_temperature=24, data=SimpleNamespace(Capacity=2.0)),
                  SimpleNamespace(type="discharge", ambient_temperature=24, data=SimpleNamespace(Capacity=1.8))]
        d = L.soh_desde_capacidad(L.extraer_descargas_nasa(ciclos, "B0005"))
        self.assertEqual(list(d.ciclo), [1, 2])
        self.assertAlmostEqual(d.soh.iloc[1], 0.9)

    def test_nasa_mat_real_roundtrip(self):
        """Escribe un .mat con la estructura B0005.cycle(i).{type,ambient_temperature,data.Capacity} y lo lee."""
        from scipy.io import savemat
        tipo = np.dtype([("type", "O"), ("ambient_temperature", "O"), ("data", "O")])
        dato = np.dtype([("Capacity", "O")])
        def c(t, cap):
            d = np.zeros((1, 1), dtype=dato); d[0, 0]["Capacity"] = np.array([[cap]])
            r = np.zeros((1, 1), dtype=tipo)
            r[0, 0] = (t, np.array([[24.0]]), d)
            return r
        ciclos = np.zeros((1, 3), dtype=tipo)
        for i, (t, cap) in enumerate([("charge", 0.0), ("discharge", 2.0), ("discharge", 1.9)]):
            ciclos[0, i] = c(t, cap)[0, 0]
        raiz = np.zeros((1, 1), dtype=np.dtype([("cycle", "O")]))
        raiz[0, 0]["cycle"] = ciclos
        tmp = Path(tempfile.mkdtemp())
        try:
            savemat(tmp / "B0005.mat", {"B0005": raiz})
            out = L.leer_nasa_pcoe(tmp)
            self.assertEqual(len(out), 2)
            self.assertAlmostEqual(out.soh.iloc[1], 0.95)
        finally:
            shutil.rmtree(tmp)

    def test_calce_encadena_ciclos(self):
        # Arbin acumula Discharge_Capacity a lo largo del archivo: capacidad del ciclo = max - min
        f1 = pd.DataFrame({"Cycle_Index": [1, 1, 2, 2], "Discharge_Capacity(Ah)": [0.0, 1.0, 1.0, 1.98],
                           "Date_Time": pd.to_datetime(["2010-01-01"] * 4)})
        f2 = pd.DataFrame({"Cycle_Index": [1, 1], "Discharge_Capacity(Ah)": [0.0, 0.95],
                           "Date_Time": pd.to_datetime(["2010-02-01"] * 2)})
        out = L.capacidad_calce([f2, f1], "CS2_35")       # desordenados a propósito
        self.assertEqual(list(out.ciclo), [1, 2, 3])
        np.testing.assert_allclose(out.capacidad_ah, [1.0, 0.98, 0.95])

    def test_oxford(self):
        datos = {"Cell1": {"cyc0000": {"C1dc": {"q": np.array([0.0, -740.0])}},
                           "cyc0100": {"C1dc": {"q": np.array([0.0, -700.0])}}}}
        d = L.soh_desde_capacidad(L.extraer_oxford(datos))
        self.assertAlmostEqual(d.soh.iloc[1], 700 / 740)


class TestOtros(unittest.TestCase):
    def test_power_parser(self):
        resp = {"properties": {"parameter": {"T2M": {"202001": 15.5, "202002": -999, "202013": 16.0}}}}
        d = D.parsear_power_json(resp, "p1")
        self.assertEqual(len(d), 2)                                   # YYYY13 (promedio anual) descartado
        self.assertTrue(np.isnan(d.valor.iloc[1]))                    # -999 -> NaN
        with self.assertRaises(ValueError):
            D.parsear_power_json({}, "p1")
        L.limpiar_power(d)

    def test_greet_exige_trazabilidad(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            p = tmp / "g.csv"
            pd.DataFrame([{"parametro": "x", "valor": 1, "unidad": "u", "modelo_y_version": "GREET 2025",
                           "hoja_o_tabla": "", "fecha_extraccion": "2026-11-17"}]).to_csv(p, index=False)
            with self.assertRaises(ValueError):
                L.leer_greet_batpac(p)
        finally:
            shutil.rmtree(tmp)

    def test_usgs_filtra_minerales(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            pd.DataFrame({"Commodity": ["Lithium", "Gold", "Cobalt"], "Prod": [1, 2, 3]}).to_csv(tmp / "a.csv", index=False)
            out = L.leer_usgs(tmp, ["lithium", "cobalt"])
            self.assertEqual(sorted(out["commodity"]), ["Cobalt", "Lithium"])
        finally:
            shutil.rmtree(tmp)

    def test_ndvi_fuera_de_rango(self):
        with self.assertRaises(ValueError):
            L.limpiar_ndvi(pd.DataFrame({"ndvi_mediana": [0.2, 1.7]}))


if __name__ == "__main__":
    unittest.main()
