"""Pruebas de la Fase 3 (vida útil). Correr: python -m unittest tests.test_weibull"""
import unittest

import numpy as np
import pandas as pd

from modelos.vida_util import weibull as W
from modelos.vida_util.eol_celdas import eol_por_celda, primer_cruce

SEMILLA = 42


def simular(beta, eta, n, censura, rng):
    """Tiempos Weibull con censura administrativa en `censura`."""
    t = eta * rng.weibull(beta, n)
    evento = t <= censura
    return np.minimum(t, censura), evento


class TestDistribucion(unittest.TestCase):
    def test_cdf_y_cuantil_son_inversas(self):
        p = np.array([0.1, 0.5, 0.9])
        np.testing.assert_allclose(W.cdf(W.cuantil(p, 3.0, 500), 3.0, 500), p)

    def test_supervivencia_mas_cdf_es_uno(self):
        t = np.linspace(1, 2000, 50)
        np.testing.assert_allclose(W.cdf(t, 2.5, 600) + W.supervivencia(t, 2.5, 600), 1.0)

    def test_pdf_integra_a_uno(self):
        t = np.linspace(0, 5000, 200001)
        self.assertAlmostEqual(np.trapezoid(W.pdf(t, 3.0, 500), t), 1.0, places=4)


class TestAjuste(unittest.TestCase):
    def test_recupera_parametros_sin_censura(self):
        rng = np.random.default_rng(SEMILLA)
        t, ev = simular(3.0, 500.0, 4000, np.inf, rng)
        a = W.ajustar(t, ev)
        self.assertAlmostEqual(a.beta, 3.0, delta=0.15)
        self.assertAlmostEqual(a.eta, 500.0, delta=10)

    def test_recupera_parametros_con_censura(self):
        rng = np.random.default_rng(SEMILLA)
        t, ev = simular(3.0, 500.0, 4000, 450.0, rng)        # ~ la mitad censurada
        self.assertTrue(0.3 < ev.mean() < 0.7)
        a = W.ajustar(t, ev)
        self.assertAlmostEqual(a.beta, 3.0, delta=0.2)
        self.assertAlmostEqual(a.eta, 500.0, delta=15)

    def test_ignorar_censura_subestima_la_vida(self):
        rng = np.random.default_rng(SEMILLA)
        t, ev = simular(3.0, 500.0, 2000, 450.0, rng)
        bien = W.ajustar(t, ev)
        mal = W.ajustar(t, np.ones_like(ev))                   # trata censuras como fallas
        self.assertLess(mal.eta, bien.eta)

    def test_sin_eventos_falla(self):
        with self.assertRaises(ValueError):
            W.ajustar([100.0, 200.0], [0, 0])

    def test_beta_comun_con_unidades_distintas(self):
        rng = np.random.default_rng(SEMILLA)
        a = simular(3.0, 500.0, 3000, np.inf, rng)
        b = simular(3.0, 8000.0, 3000, np.inf, rng)            # misma forma, otra escala/unidad
        r = W.ajustar_beta_comun({"a": a, "b": b})
        self.assertAlmostEqual(r["beta"], 3.0, delta=0.15)
        self.assertAlmostEqual(r["eta"]["b"] / r["eta"]["a"], 16.0, delta=0.5)
        self.assertGreater(W.prueba_beta_comun({"a": a, "b": b})["p_valor"], 0.01)

    def test_bootstrap_cubre_el_valor_verdadero(self):
        rng = np.random.default_rng(SEMILLA)
        t, ev = simular(3.0, 500.0, 60, 600.0, rng)
        bs = W.bootstrap(t, ev, 300, np.random.default_rng(SEMILLA), 0.90)
        self.assertTrue(bs["beta_ic"][0] < 3.0 < bs["beta_ic"][1])
        self.assertTrue(bs["eta_ic"][0] < 500.0 < bs["eta_ic"][1])


class TestEol(unittest.TestCase):
    CFG = {"ciclos_referencia": 3, "ventana_suavizado": 3, "puntos_consecutivos": 2,
           "capacidad_minima_valida_ah": 0.05, "ref_minima_vs_nominal": 0.85, "soh_maximo_plausible": 1.05}

    def test_cruce_interpolado(self):
        c = np.array([0, 10, 20, 30])
        s = np.array([1.0, 0.9, 0.7, 0.6])
        self.assertAlmostEqual(primer_cruce(c, s, 0.8, 2), 15.0)

    def test_pico_aislado_no_cuenta(self):
        c = np.arange(6)
        s = np.array([1.0, 0.95, 0.75, 0.95, 0.9, 0.9])
        self.assertIsNone(primer_cruce(c, s, 0.8, 2))

    def test_censura_y_exclusion(self):
        df = pd.DataFrame({
            "bateria": ["A"] * 6 + ["B"] * 6 + ["C"] * 6,
            "ciclo": list(range(6)) * 3,
            "capacidad_ah": [1, 1, 1, .9, .7, .6] + [1, 1, 1, .99, .98, .97] + [.3, .3, .3, .3, .3, .3],
        })
        out = eol_por_celda(df, "x", {"capacidad_nominal_ah": 1.0}, self.CFG, 0.8).set_index("celda")
        self.assertEqual(out.loc["A", "evento"], 1)
        self.assertEqual(out.loc["B", "evento"], 0)
        self.assertEqual(out.loc["B", "tiempo"], 5)
        self.assertFalse(out.loc["C", "incluida"])          # referencia anómala vs nominal


if __name__ == "__main__":
    unittest.main()


class TestArrheniusYFlota(unittest.TestCase):
    def test_af_es_uno_en_referencia_y_crece_con_t(self):
        from modelos.vida_util.arrhenius import factor_aceleracion
        self.assertAlmostEqual(float(factor_aceleracion(25, 50, 25)), 1.0)
        self.assertGreater(float(factor_aceleracion(35, 50, 25)), 1.0)
        self.assertLess(float(factor_aceleracion(15, 50, 25)), 1.0)

    def test_jensen_promedio_de_af_mayor_que_af_del_promedio(self):
        from modelos.vida_util.arrhenius import factor_aceleracion, factor_efectivo
        temps = np.array([10.0, 40.0])
        self.assertGreater(factor_efectivo(temps, 50), float(factor_aceleracion(25.0, 50)))

    def test_hev_se_retira_con_el_vehiculo(self):
        from modelos.vida_util.flota import simular_vidas
        cfg = {"vida_vehiculo_anios": {"distribucion": "fija", "valor": 12.0}}
        sim = simular_vidas({"retiro_por": "vehiculo"}, cfg, np.array([25.0]), {}, 50, np.random.default_rng(SEMILLA))
        np.testing.assert_allclose(sim["anios"], 12.0)
        self.assertFalse(sim["por_bateria"].any())

    def test_caso_determinista(self):
        """Sin dispersión: 500 ciclos, 25 EFC/año, 25 °C -> 20 años por ciclado; calendario 20 -> 10 años."""
        from modelos.vida_util.flota import simular_vidas
        fija = lambda v: {"distribucion": "fija", "valor": v}
        cfg = {"vida_vehiculo_anios": fija(99.0), "ciclos_lab_a_vehiculo": fija(1.0), "km_anio": fija(10000.0),
               "energia_activacion_kj_mol": fija(50.0), "temperatura_referencia_c": 25.0,
               "vida_calendario_anios_25c": fija(20.0)}
        tipo = {"retiro_por": "bateria_o_vehiculo", "consumo_kwh_km": fija(0.15),
                "fraccion_km_electricos": fija(1.0), "capacidad_kwh": fija(60.0)}
        celda = {"beta": np.array([1e6]), "eta": np.array([500.0])}          # beta enorme = sin dispersión
        sim = simular_vidas(tipo, cfg, np.array([25.0]), celda, 10, np.random.default_rng(SEMILLA))
        np.testing.assert_allclose(sim["anios"], 10.0, rtol=1e-4)


class TestConvolucion(unittest.TestCase):
    def test_conservacion_y_no_negatividad(self):
        from modelos.flujo_eol.convolucion import retiros
        ventas = np.zeros(80); ventas[0] = 1000.0                 # una sola cohorte, horizonte largo
        r = retiros(ventas, 3.0, 10.0)
        self.assertTrue((r >= 0).all())
        self.assertAlmostEqual(r.sum(), 1000.0, places=3)        # toda la cohorte termina saliendo

    def test_retiros_nunca_superan_ventas_acumuladas(self):
        from modelos.flujo_eol.convolucion import retiros
        rng = np.random.default_rng(SEMILLA)
        ventas = rng.uniform(0, 100, (5, 25))
        r = retiros(ventas, 2.5, 8.0)
        self.assertTrue((np.cumsum(r, -1) <= np.cumsum(ventas, -1) + 1e-9).all())

    def test_moda_cerca_de_la_vida_tipica(self):
        from modelos.flujo_eol.convolucion import retiros
        ventas = np.zeros(40); ventas[0] = 1.0
        r = retiros(ventas, 4.0, 12.0)
        self.assertIn(int(np.argmax(r)), (10, 11, 12))           # moda Weibull = eta((b-1)/b)^(1/b) ~ 11.2


class TestCurvaS(unittest.TestCase):
    def test_recupera_k_y_t0(self):
        from modelos.ventas import curva_s as CS
        anios = np.arange(2010, 2026)
        s = CS.predecir(anios, 0.4, 2030.0, 0.5)
        a = CS.ajustar(anios, s, 0.5)
        self.assertAlmostEqual(a["k"], 0.4, places=6)
        self.assertAlmostEqual(a["t0"], 2030.0, places=4)


class TestRed(unittest.TestCase):
    def test_mlp_aprende_funcion_no_lineal(self):
        from modelos.soh.red import MLP
        rng = np.random.default_rng(SEMILLA)
        X = rng.uniform(-2, 2, (600, 2)); y = np.sin(X[:, 0]) + 0.5 * X[:, 1] ** 2
        m = MLP(2, epocas=300, semilla=SEMILLA).fit(X[:500], y[:500])
        rmse = np.sqrt(np.mean((m.predict(X[500:]) - y[500:]) ** 2))
        self.assertLess(rmse, 0.15)                          # vs desv. est. de y ~ 0.9

    def test_ensamble_reproducible(self):
        from modelos.soh.red import Ensamble
        X = np.linspace(0, 1, 50)[:, None]; y = 2 * X[:, 0]
        a = Ensamble(1, miembros=2, semilla=SEMILLA, epocas=50).fit(X, y).predict(X)[0]
        b = Ensamble(1, miembros=2, semilla=SEMILLA, epocas=50).fit(X, y).predict(X)[0]
        np.testing.assert_allclose(a, b)


class TestSobol(unittest.TestCase):
    def test_ishigami(self):
        """Función de Ishigami (a=7, b=0.1): S1 analíticos 0.314, 0.442, 0.000; ST3 = 0.244."""
        from modelos.riesgo.sobol import indices
        f = lambda x: np.sin(x["a"]) + 7 * np.sin(x["b"]) ** 2 + 0.1 * x["c"] ** 4 * np.sin(x["a"])
        r = {k: {"min": -np.pi, "max": np.pi} for k in "abc"}
        s = indices(f, r, 2**14, np.random.default_rng(SEMILLA), bootstrap=20)
        np.testing.assert_allclose(s["S1"], [0.314, 0.442, 0.0], atol=0.03)
        self.assertAlmostEqual(s["ST"][2], 0.244, delta=0.03)


class TestCicloVida(unittest.TestCase):
    def test_caso_a_mano(self):
        from modelos.riesgo.ciclo_vida import evaluar
        x = {k: np.array([v]) for k, v in {"bateria_kwh": 60, "ef_bateria_kg_kwh": 100, "reciclaje_credito": 0,
             "carroceria_t": 6.0, "consumo_kwh_km": 0.2, "perdidas_red": 0.0, "km_anio": 10000,
             "rendimiento_km_l": 10, "ef_gasolina_kg_l": 2.9, "p_reemplazo_bateria": 0.0,
             "u_vida_bateria": 0.5, "u_vida_vehiculo": 0.5, "u_red": 0.5}.items()}
        c = lambda v: (lambda u: np.full_like(u, v, dtype=float))
        o = evaluar(x, c(20.0), c(15.0), c(400.0), 0.0)        # batería sobrevive al auto: 150,000 km
        self.assertAlmostEqual(o["bev_g_km"][0], (6 + 6) * 1e6 / 150000 + 80, places=6)   # 160 g/km
        self.assertAlmostEqual(o["gas_g_km"][0], 6e6 / 150000 + 290, places=6)            # 330 g/km
        self.assertAlmostEqual(o["equilibrio_km"][0], 6e6 / 210, places=3)
