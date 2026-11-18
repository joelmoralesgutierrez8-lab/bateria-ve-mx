"""Genera el extenso técnico en HTML (tablero + procedimiento matemático y estadístico).

Uso, desde la raíz del proyecto:
    python -m modelos.generar_extenso

Entradas : docs/plantilla_extenso.html, resultados/fase3..fase7/*, resultados/figuras/*.png,
           modelos/config_fase3.yaml, datos/procesado/*.csv (solo para contar registros)
Salida   : docs/extenso_bateria_ve_mx.html (un solo archivo: figuras y KaTeX embebidos, funciona sin internet)

Todas las cifras de las tablas se leen de los archivos de resultados; nada se teclea a mano. Si cambias un
resultado y vuelves a correr los ejecutores, vuelve a correr este script.

Datos de portada que debes revisar: UNIDAD y EQUIPO (abajo). Logotipos: coloca los archivos oficiales en
docs/logos/ con los nombres de docs/logos/LEEME.txt.
"""
from __future__ import annotations

import base64
import datetime as dt
import json
import math
from pathlib import Path

import pandas as pd
import yaml

RAIZ = Path(__file__).resolve().parents[1]
RES = RAIZ / "resultados"
DOCS = RAIZ / "docs"

# ------------------------------------------------------------------ datos de portada (EDITAR)
UNIDAD = "Campus Puebla"
EQUIPO = [
    ("Sofía del Carmen Peña Ramírez", "Licenciatura en Ciencia de Datos", "datos, modelos y análisis estadístico"),
    ("[Nombre del integrante]", "Ingeniería en Sistemas Automotrices", "lectura técnica del vehículo y la batería"),
]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre"]
TIPOS = ["BEV", "PHEV", "HEV"]


# ------------------------------------------------------------------ formato
def n(x, d=0):
    """Número con separador de miles (coma) y punto decimal; signo menos tipográfico."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "—"
    if round(x, d) == 0:
        x = 0.0                                                # evita "−0.000"
    s = f"{x:,.{d}f}"
    return s.replace("-", "−")


def p_valor(p):
    return "< 0.001" if p < 0.001 else n(p, 3)


def ic(a, b, d=0):
    """Intervalo: 23–60 si ambos extremos son positivos; [−0.007, 0.005] si alguno es negativo."""
    if min(a, b) < 0:
        return f"[{n(a, d)}, {n(b, d)}]"
    return f"{n(a, d)}–{n(b, d)}"


def tabla(cab, filas, num=(), destacar=(), clase=""):
    """cab: encabezados; filas: listas de celdas (str); num: índices de columnas numéricas."""
    th = "".join(f'<th class="n">{c}</th>' if i in num else f"<th>{c}</th>" for i, c in enumerate(cab))
    cuerpo = []
    for k, f in enumerate(filas):
        td = "".join(f'<td class="n">{c}</td>' if i in num else f"<td>{c}</td>" for i, c in enumerate(f))
        cuerpo.append(f'<tr class="destaca">{td}</tr>' if k in destacar else f"<tr>{td}</tr>")
    return f'<div class="tabla-scroll"><table class="{clase}"><thead><tr>{th}</tr></thead><tbody>{"".join(cuerpo)}</tbody></table></div>'


def cv_weibull(beta):
    g1, g2 = math.gamma(1 + 1 / beta), math.gamma(1 + 2 / beta)
    return math.sqrt(g2 / g1**2 - 1)


def imagen(nombre):
    ruta = RES / "figuras" / nombre
    return "data:image/png;base64," + base64.b64encode(ruta.read_bytes()).decode()


# ------------------------------------------------------------------ tablas
def t_simbolos():
    filas = [
        (r"\(\mathrm{SoH}_n,\ Q_n\)", r"estado de salud y capacidad (Ah) en la medición \(n\)", "3"),
        (r"\(t_i,\ \delta_i\)", r"tiempo observado de la celda \(i\) e indicador de evento (1 = llegó a 80%, 0 = censurada)", "3–4"),
        (r"\(\beta,\ \eta\)", r"forma y escala de la distribución de Weibull", "4–5, 8"),
        (r"\(F,\ S,\ f,\ h\)", r"distribución acumulada, supervivencia, densidad y tasa de falla", "4"),
        (r"\(\ell,\ \Lambda\)", r"log-verosimilitud y estadístico de razón de verosimilitudes", "4"),
        (r"\(E_a,\ R,\ T\)", r"energía de activación, constante de los gases, temperatura absoluta (K)", "5"),
        (r"\(\mathrm{AF},\ \mathrm{EFC},\ \phi\)", r"factor de aceleración térmica, ciclos equivalentes por año, factor laboratorio→vehículo", "5"),
        (r"\(s(t),\ s_{\max},\ k,\ t_0\)", r"participación de mercado, techo, tasa de crecimiento, año del punto medio", "6"),
        (r"\(y_t=\ln(1+V_t)\)", r"ventas mensuales en escala logarítmica", "7"),
        (r"\(V(c),\ p(a),\ R(y)\)", r"ventas de la cohorte \(c\), fracción que sale a la edad \(a\), retiros del año \(y\)", "8"),
        (r"\(W_\ell,\ \mathbf b_\ell,\ \alpha,\ \lambda\)", r"pesos y sesgos de la capa \(\ell\), tasa de aprendizaje, regularización", "9"),
        (r"\(I_{\text{red}},\ E_b,\ D^*\)", r"intensidad de la red (g/kWh), fabricación de batería (kg/kWh), km de equilibrio", "10"),
        (r"\(S_i,\ S_{T_i}\)", r"índices de Sobol de primer orden y total", "10"),
        (r"\(\tau,\ S\)", r"tau de Kendall y estadístico de Mann–Kendall", "11"),
    ]
    return tabla(["Símbolo", "Significado", "Cap."], filas)


def t_fuentes():
    pro = RAIZ / "datos" / "procesado"

    def cuenta(nombre):
        f = pro / f"{nombre}.csv"
        return n(len(pd.read_csv(f))) if f.exists() else "—"

    filas = [
        ("INEGI, RAIAVL", "Ventas mensuales de vehículos ligeros por entidad y tipo (BEV, PHEV, HEV), 2016–2026",
         cuenta("inegi_ventas_entidad_mes"), "Curva S, series de tiempo, cohortes, reparto por estado"),
        ("CENACE", "Generación mensual del Sistema Eléctrico Nacional por tecnología",
         cuenta("cenace_generacion_mensual"), "Intensidad de carbono de la red (g CO₂e/kWh)"),
        ("NASA PCoE", "Ciclado de 34 celdas 18650 (2 Ah) a 4, 24 y 43 °C", cuenta("bateria_nasa_pcoe"),
         "Weibull, red neuronal, transferencia térmica"),
        ("CALCE (U. de Maryland)", "Ciclado de 6 celdas CS2 (1.1 Ah, LiCoO₂) a 1C y 25 °C", cuenta("bateria_calce"),
         "Weibull de referencia para la flota"),
        ("Oxford Battery Degradation", "8 celdas Kokam (0.74 Ah) con perfil de manejo urbano Artemis",
         cuenta("bateria_oxford"), "Weibull, red neuronal"),
        ("NASA POWER", "Temperatura mensual en las 32 capitales, 2016–2025", cuenta("nasa_power_temperatura"),
         "Arrhenius por estado"),
        ("USGS, Mineral Commodity Summaries 2026", "Producción, reservas e importaciones de minerales de baterías",
         cuenta("usgs_minerales"), "Quién paga: minerales"),
        ("Landsat 8/9, Colección 2, nivel 2", "NDVI anual en tres zonas mineras, 2014–2025",
         cuenta("vegetacion_ndvi_zonas"), "Tendencia de vegetación"),
        ("GREET (Argonne) y literatura", "kg CO₂e por kWh de batería fabricada (LFP, NMC111, NMC811)",
         cuenta("greet_batpac_parametros"), "Fabricación de la batería"),
    ]
    return tabla(["Fuente", "Contenido", "Registros", "Uso en el proyecto"], filas, num={2})


def t_eol(eol, wb):
    unidades = dict(zip(wb.conjunto, wb.unidad_tiempo))
    filas = []
    for conj, nombre in [("calce", "CALCE"), ("nasa_pcoe", "NASA PCoE"), ("oxford", "Oxford")]:
        d = eol[eol.conjunto == conj]
        u = d[d.incluida]
        filas.append((nombre, n(len(d)), n(len(u)), n(int(u.evento.sum())), n(int((u.evento == 0).sum())),
                      n(int((~d.incluida).sum())), unidades.get(conj, "")))
    return tabla(["Conjunto", "Celdas", "Usadas", "Con EoL", "Censuradas", "Excluidas", "Unidad de tiempo"],
                 filas, num={1, 2, 3, 4, 5})


def t_weibull(wb):
    nombres = {"calce": "CALCE", "nasa_pcoe": "NASA PCoE", "oxford": "Oxford"}
    filas = []
    for _, r in wb.iterrows():
        filas.append((nombres[r.conjunto], f"{int(r.n)} ({int(r.n_eventos)}/{int(r.n - r.n_eventos)})",
                      f"<b>{n(r.beta, 2)}</b>", ic(r.beta_ic_bajo, r.beta_ic_alto, 2), f"<b>{n(r.eta)}</b>",
                      ic(r.eta_ic_bajo, r.eta_ic_alto), n(r.b10), n(r.mediana), n(cv_weibull(r.beta), 3),
                      n(r.replicas_descartadas)))
    return tabla(["Conjunto", "n (fallas/cens.)", "β", "β IC 90%", "η", "η IC 90%", "B10", "Mediana", "CV",
                  "Réplicas desc."], filas, num=set(range(1, 10)))


def t_lrt(bc):
    lr = bc["prueba_lr"]
    filas = [
        ("β libre: CALCE / NASA / Oxford", " / ".join(n(lr["beta_por_grupo"][c], 2) for c in ("calce", "nasa_pcoe", "oxford"))),
        ("β común (modelo restringido)", n(bc["beta"], 2)),
        ("η con β común: CALCE / NASA / Oxford", " / ".join(n(bc["eta"][c], 1) for c in ("calce", "nasa_pcoe", "oxford"))),
        ("Estadístico Λ", n(lr["estadistico_lr"], 2)),
        ("Grados de libertad", n(lr["grados_libertad"])),
        ("Valor p (χ²)", n(lr["p_valor"], 4)),
    ]
    return tabla(["Concepto", "Valor"], filas, num={1})


def t_flota(fl):
    estados = ["Campeche", "Quintana Roo", "Yucatán", "Sinaloa", "Jalisco", "Nuevo León", "Puebla",
               "Ciudad de México", "Tlaxcala"]
    b = fl[(fl.tipo == "BEV") & fl.entidad.isin(estados)].sort_values("temp_media_c", ascending=False)
    filas = [(r.entidad, n(r.temp_media_c, 1), n(r.af_mediano, 2), n(r.efc_anio_mediano, 1),
              n(r.mediana_bateria_sola_anios, 1), n(r.beta_flota, 2), n(r.eta_flota_anios, 1), n(r.mediana_anios, 1),
              n(100 * r.pct_retiro_por_bateria)) for r in b.itertuples()]
    return tabla(["Estado", "T media (°C)", "AF mediano", "EFC/año", "Batería sola (años)", "β flota",
                  "η flota (años)", "Retiro mediano (años)", "% retiro por batería"], filas, num=set(range(1, 9)))


def t_curva_s(cs):
    filas = [(r.escenario, r.tipo, n(100 * r.s_max), n(r.k, 3), ic(r.k_p5, r.k_p95, 3), n(r.t0, 1))
             for r in cs.itertuples()]
    return tabla(["Escenario", "Tipo", "Techo s_max (%)", "k̂ (1/año)", "k IC 90%", "t̂₀ (año)"], filas, num={2, 3, 4, 5},
                 destacar={i for i, r in enumerate(cs.itertuples()) if r.escenario == "base"})


def t_backtest(bt):
    b = bt[bt.escenario == "base"]
    filas = []
    for tipo in TIPOS:
        d = b[b.tipo == tipo]
        for r in d.itertuples():
            filas.append((tipo, str(r.anio), n(r.real), n(r.curva_s), n(100 * (r.curva_s / r.real - 1)), n(r.ingenuo),
                          n(100 * (r.ingenuo / r.real - 1))))
        mc = 100 * (abs(d.curva_s - d.real) / d.real).mean()
        mi = 100 * (abs(d.ingenuo - d.real) / d.real).mean()
        filas.append((f"<b>{tipo}</b>", "<b>MAPE</b>", "", "", f"<b>{n(mc)}%</b>", "", f"<b>{n(mi)}%</b>"))
    return tabla(["Tipo", "Año", "Real", "Curva S", "Error (%)", "Crecimiento ingenuo", "Error (%)"], filas,
                 num={2, 3, 4, 5, 6})


def t_diag(dg):
    def kpss(p):
        return "≤ 0.01" if p <= 0.01 else ("≥ 0.10" if p >= 0.1 else n(p, 3))

    filas = [(r.tipo, n(r.fuerza_tendencia_stl, 2), n(r.fuerza_estacional_stl, 2), p_valor(r.adf_p_log), kpss(r.kpss_p_log),
              p_valor(r.adf_p_dif), kpss(r.kpss_p_dif),
              f"{r.sarima_orden.replace(' ', '')}{r.sarima_estacional.replace(' ', '').replace(',12)', ')')}₁₂",
              n(r.sarima_aic, 1), n(r.ljungbox_p_lag12, 3)) for r in dg.itertuples()]
    return tabla(["Tipo", "F_T", "F_S", "ADF p (nivel)", "KPSS p (nivel)", "ADF p (dif.)", "KPSS p (dif.)", "SARIMA elegido",
                  "AIC", "Ljung–Box p (12)"], filas, num={1, 2, 3, 4, 5, 6, 8, 9})


NOMBRES_MODELO = {"naive_estacional": "Naive estacional", "deriva_estacional": "Deriva estacional", "sarima": "SARIMA",
                  "ets": "ETS amortiguado", "lightgbm": "LightGBM directo", "lstm": "LSTM"}


def t_valid(va):
    filas, dest = [], set()
    for tipo in TIPOS:
        d = va[va.tipo == tipo].sort_values("MASE")
        for k, r in enumerate(d.itertuples()):
            if k == 0:
                dest.add(len(filas))
            filas.append((tipo, NOMBRES_MODELO.get(r.modelo, r.modelo), n(r.MASE, 3), n(r.MAE), n(r.RMSE),
                          n(100 * r.MAPE, 1), n(r.n)))
    return tabla(["Tipo", "Modelo", "MASE (log)", "MAE (veh./mes)", "RMSE (veh./mes)", "MAPE (%)", "Pronósticos"],
                 filas, num={2, 3, 4, 5, 6}, destacar=dest)


def t_cob(cb):
    filas = [(r.tipo, n(100 * r.nivel_nominal), n(100 * r.cobertura_observada, 1), n(r.n)) for r in cb.itertuples()]
    return tabla(["Tipo", "Nivel nominal (%)", "Cobertura observada (%)", "Pronósticos"], filas, num={1, 2, 3})


def t_retiros(re):
    filas = []
    for anio in (2025, 2030, 2035, 2040):
        d = re[re.anio == anio]
        base = d[d.escenario == "base"]
        fila = [str(anio), n(base.unidades_p50.sum()), n(base.toneladas_p50.sum()), n(base.mwh_p50.sum())]
        for esc in ("bajo", "alto"):
            fila.append(n(d[d.escenario == esc].toneladas_p50.sum()))
        filas.append(fila)
    return tabla(["Año", "Unidades (base)", "Toneladas (base)", "MWh (base)", "Toneladas (bajo)", "Toneladas (alto)"],
                 filas, num={1, 2, 3, 4, 5})


def t_retiros_tipo(re):
    b = re[re.escenario == "base"]
    filas = []
    for tipo in TIPOS:
        for anio in (2030, 2035, 2040):
            r = b[(b.tipo == tipo) & (b.anio == anio)].iloc[0]
            filas.append((tipo, str(anio), n(r.unidades_p50), n(r.toneladas_p50), ic(r.toneladas_p5, r.toneladas_p95),
                          n(r.mwh_p50)))
    return tabla(["Tipo", "Año", "Unidades P50", "Toneladas P50", "Toneladas IC 90%", "MWh P50"], filas, num={2, 3, 4, 5})


def t_soh(sv):
    nombres = {"calce": "CALCE (h = 50 ciclos)", "nasa_pcoe": "NASA 24 °C (h = 5 ciclos)",
               "oxford": "Oxford (h = 500 ciclos de manejo)"}
    filas = []
    for conj in ("calce", "nasa_pcoe", "oxford"):
        d = sv[sv.conjunto == conj]
        m = d.groupby("modelo").rmse_soh_pp.mean()
        cob = d[d.modelo == "mlp_ensamble"].cobertura_2sd.mean()
        filas.append((nombres[conj], n(d.celda_prueba.nunique()), n(m["persistencia"], 2), n(m["lineal"], 2),
                      f"<b>{n(m['mlp_ensamble'], 2)}</b>", n(100 * cob)))
    return tabla(["Conjunto", "Celdas", "Persistencia", "Lineal", "MLP (ensamble)", "Cobertura ±2s (%)"], filas,
                 num={1, 2, 3, 4, 5})


def t_trans(tr):
    nombres = {"persistencia": "Persistencia", "lineal": "Extrapolación lineal", "mlp_ensamble": "MLP (ensamble)"}
    filas = [(nombres[r.modelo], n(r.n_prueba), n(r.rmse_soh_pp, 2), n(r.mae_soh_pp, 2),
              "—" if pd.isna(r.cobertura_2sd) else n(100 * r.cobertura_2sd)) for r in tr.itertuples()]
    mejor = int(tr.rmse_soh_pp.idxmin())
    return tabla(["Modelo", "Ventanas", "RMSE (pp)", "MAE (pp)", "Cobertura ±2s (%)"], filas, num={1, 2, 3, 4},
                 destacar={mejor})


def t_mc(mc):
    m = mc.set_index("variable")
    etiquetas = [("bev_g_km", "Eléctrico (BEV), g CO₂e/km", 0), ("gas_g_km", "Gasolina, g CO₂e/km", 0),
                 ("reduccion_pct", "Reducción del eléctrico (%)", 1), ("uso_bev_g_km", "Uso del eléctrico (red), g/km", 0),
                 ("uso_gas_g_km", "Uso del auto de gasolina, g/km", 0),
                 ("equilibrio_km", "Km para pagar la batería (equilibrio)", 0),
                 ("t_bat", "Vida de la batería BEV (años)", 1), ("t_veh", "Vida del vehículo (años)", 1)]
    filas = [(e, n(m.loc[v, "p5"], d), f"<b>{n(m.loc[v, 'p50'], d)}</b>", n(m.loc[v, "p95"], d)) for v, e, d in etiquetas]
    filas.append(("Probabilidad de que el eléctrico emita menos", "", f"<b>{n(100 * m.loc['prob_bev_mas_limpio', 'p50'], 1)}%</b>", ""))
    return tabla(["Variable", "P5", "P50", "P95"], filas, num={1, 2, 3})


ETIQUETAS_ENTRADA = {
    "bateria_kwh": ("Capacidad de la batería BEV", "kWh"),
    "ef_bateria_kg_kwh": ("Emisiones de fabricar la batería", "kg CO₂e/kWh"),
    "reciclaje_credito": ("Crédito de reciclaje", "fracción"),
    "carroceria_t": ("Fabricación del vehículo sin batería", "t CO₂e"),
    "consumo_kwh_km": ("Consumo del eléctrico", "kWh/km"),
    "perdidas_red": ("Pérdidas de transmisión y distribución", "fracción"),
    "km_anio": ("Kilómetros por año", "km"),
    "rendimiento_km_l": ("Rendimiento del auto de gasolina", "km/l"),
    "ef_gasolina_kg_l": ("Emisiones de la gasolina (pozo a rueda)", "kg CO₂e/l"),
    "p_reemplazo_bateria": ("Probabilidad de reemplazar la batería", "—"),
    "u_vida_bateria": ("Vida de la batería (cuantil de la flota)", "—"),
    "u_vida_vehiculo": ("Vida del vehículo (cuantil)", "—"),
    "u_red": ("Intensidad de la red (cuantil CENACE)", "—"),
}


def t_sobol(sb):
    sb = sb.sort_values("ST", ascending=False)
    filas = [(ETIQUETAS_ENTRADA.get(r.entrada, (r.entrada,))[0], n(r.ST, 3), ic(r.ST_p5, r.ST_p95, 3), n(r.S1, 3),
              ic(r.S1_p5, r.S1_p95, 3)) for r in sb.itertuples()]
    return tabla(["Entrada", "S<sub>T</sub>", "S<sub>T</sub> IC 90%", "S<sub>1</sub>", "S<sub>1</sub> IC 90%"], filas, num={1, 2, 3, 4}, destacar={0, 1})


def t_esc(es):
    filas = [(r.escenario_red, n(r.i_red_p50), f"{n(r.bev_p50)} ({ic(r.bev_p5, r.bev_p95)})", n(r.gas_p50),
              f"{n(r.reduccion_p50, 1)} ({ic(r.reduccion_p5, r.reduccion_p95)})", n(r.equilibrio_km_p50),
              n(100 * r.prob_bev_mas_limpio, 1)) for r in es.itertuples()]
    return tabla(["Escenario de red", "g CO₂e/kWh", "Eléctrico g/km P50 (IC 90%)", "Gasolina g/km", "Reducción % P50 (IC 90%)",
                  "Equilibrio (km)", "P(eléctrico emite menos) %"], filas, num={1, 3, 5, 6})


def t_ndvi(nd):
    nombres = {"mina_cu_cananea": "Cananea, Son. (cobre)", "mina_li_bacadehuachi": "Bacadéhuachi, Son. (litio)",
               "mina_mn_molango": "Molango, Hgo. (manganeso)"}
    filas = [(nombres.get(r.zona, r.zona), r.anios, n(r.tau_kendall, 3), p_valor(r.p_mann_kendall),
              f"{n(r.pendiente_por_anio, 4)} ({ic(r.pendiente_ic_bajo, r.pendiente_ic_alto, 4)})",
              n(r.ndvi_inicio_3a, 3), n(r.ndvi_fin_3a, 3), n(r.cambio_pct, 1)) for r in nd.itertuples()]
    return tabla(["Zona", "Años", "τ de Kendall", "p (Mann–Kendall)", "Pendiente/año (IC 90%)", "NDVI 3 primeros años",
                  "NDVI 3 últimos años", "Cambio (%)"], filas, num={2, 3, 4, 5, 6, 7},
                 destacar={i for i, r in enumerate(nd.itertuples()) if r.p_mann_kendall < 0.05})


def t_codigo():
    filas = [
        ("etl/", "Descarga, limpieza, manifiesto SHA-256, tabla de faltantes", "2"),
        ("modelos/vida_util/eol_celdas.py", "SoH, mediana móvil, cruce sostenido, censura y exclusiones", "3"),
        ("modelos/vida_util/weibull.py", "Weibull: F, S, f, h; MLE con censura; β común; razón de verosimilitudes; bootstrap", "4"),
        ("modelos/vida_util/arrhenius.py", "Factor de aceleración y su promedio mensual", "5"),
        ("modelos/vida_util/flota.py", "Simulación de vehículos y Weibull de flota por estado", "5"),
        ("modelos/ventas/preparar.py", "Series mensuales y anuales por tipo a partir de INEGI", "6–7"),
        ("modelos/ventas/curva_s.py", "Curva S por mínimos cuadrados ponderados en logit; bootstrap de residuos", "6"),
        ("modelos/ventas/corto_plazo.py", "Seis modelos, origen móvil y MASE en escala log", "7"),
        ("modelos/ejecutar_series.py", "STL, ADF, KPSS, Ljung–Box, cobertura de intervalos", "7"),
        ("modelos/flujo_eol/convolucion.py", "Convolución de cohortes y paso a toneladas", "8"),
        ("modelos/soh/red.py, datos.py", "MLP en NumPy (retropropagación, Adam), ensamble; ventanas de SoH", "9"),
        ("modelos/riesgo/ciclo_vida.py", "g CO₂e/km del eléctrico y de gasolina; punto de equilibrio", "10"),
        ("modelos/riesgo/sobol.py", "Estimadores de Saltelli y Jansen con bootstrap", "10"),
        ("modelos/ejecutar_etica.py", "Escenarios de red, Mann–Kendall, Theil–Sen, reparto de emisiones", "11"),
        ("modelos/ejecutar_figuras.py", "Las ocho figuras", "—"),
        ("modelos/config_fase3.yaml", "Todos los supuestos con su fuente", "A"),
    ]
    return tabla(["Archivo", "Qué hace", "Cap."], [(f"<code>{a}</code>", b, c) for a, b, c in filas])


def t_pruebas():
    filas = [
        ("Weibull", "9", "F y su cuantil son inversas; S + F = 1; f integra 1; recupera β y η con y sin censura; "
                         "ignorar la censura subestima la vida; sin eventos falla; β común con unidades distintas; "
                         "el bootstrap cubre el valor verdadero"),
        ("Fin de vida", "3", "cruce interpolado; un pico aislado no cuenta; censura y exclusión"),
        ("Arrhenius y flota", "3", "AF = 1 a 25 °C y crece con T; desigualdad de Jensen; la batería HEV se retira con el auto"),
        ("Convolución", "4", "caso determinista; conservación y no negatividad; retiros ≤ ventas acumuladas; moda cerca de la vida típica"),
        ("Curva S", "1", "recupera k y t₀ de datos simulados"),
        ("Red neuronal", "2", "aprende una función no lineal; el ensamble es reproducible con la semilla"),
        ("Sobol", "1", "recupera los índices analíticos de la función de Ishigami"),
        ("Ciclo de vida", "1", "coincide con un cálculo hecho a mano"),
    ]
    return tabla(["Grupo", "Pruebas", "Qué se verifica"], filas, num={1})


def t_supuestos(cfg):
    ent = cfg["riesgo"]["entradas"]
    filas = []
    for clave, v in ent.items():
        nombre, unidad = ETIQUETAS_ENTRADA.get(clave, (clave, ""))
        d = 3 if v["max"] < 1 else (2 if v["max"] < 10 else 0)
        fuente = v.get("fuente", "").replace("SUPUESTO", "<b>SUPUESTO</b>")
        filas.append((nombre, unidad, f"U({n(v['min'], d)}, {n(v['max'], d)})", fuente))
    filas.append(("Batería de plomo del auto de gasolina", "t CO₂e", n(cfg["riesgo"]["bateria_plomo_icev_t"], 2),
                  cfg["riesgo"].get("fuente_plomo", "")))
    vf = cfg["vida_flota"]
    ea = vf["energia_activacion_kj_mol"]
    filas += [
        ("Energía de activación (Arrhenius)", "kJ/mol", f"Triangular({ea['min']}, {ea['moda']}, {ea['max']})", ea["fuente"]),
        ("Kilómetros por año (flota)", "km", f"Lognormal, mediana {n(vf['km_anio']['mediana'])}, P90 {n(vf['km_anio']['p90'])}",
         vf["km_anio"]["fuente"]),
        ("Factor laboratorio → vehículo", "—", "U(1, 2)", vf["ciclos_lab_a_vehiculo"]["fuente"].replace("SUPUESTO", "<b>SUPUESTO</b>")),
        ("Vida calendario a 25 °C", "años", "Triangular(15, 20, 25)", vf["vida_calendario_anios_25c"]["fuente"].replace("SUPUESTO", "<b>SUPUESTO</b>")),
        ("Vida del vehículo", "años", "Weibull(β = 3, η = 16)", vf["vida_vehiculo_anios"]["fuente"].replace("SUPUESTO", "<b>SUPUESTO</b>")),
    ]
    return tabla(["Entrada", "Unidad", "Distribución", "Fuente"], filas)


def t_ventas(pv):
    b = pv[pv.escenario == "base"]
    filas = []
    for anio in (2026, 2030, 2035, 2040):
        d = b[b.anio == anio].set_index("tipo")
        filas.append([str(anio)] + [n(d.loc[t, "p50"]) for t in TIPOS] + [n(d.p50.sum())])
    return tabla(["Año", "BEV", "PHEV", "HEV", "Total"], filas, num={1, 2, 3, 4})


def equipo_html():
    out = []
    for nombre, programa, rol in EQUIPO:
        b = f'<b class="editar">{nombre}</b>' if nombre.startswith("[") else f"<b>{nombre}</b>"
        out.append(f'<div class="persona">{b}{programa} · {rol}</div>')
    return "\n    ".join(out)


def katex_html():
    v = DOCS / "vendor" / "katex"
    opciones = ("{delimiters:[{left:'$$',right:'$$',display:true},{left:'\\\\(',right:'\\\\)',display:false}],"
                "throwOnError:false}")
    if all((v / f).exists() for f in ("katex.min.js", "auto-render.min.js", "katex_embebido.css")):
        return ("<style>" + (v / "katex_embebido.css").read_text(encoding="utf-8") + "</style>\n"
                "<script>" + (v / "katex.min.js").read_text(encoding="utf-8") + "</script>\n"
                "<script>" + (v / "auto-render.min.js").read_text(encoding="utf-8") + "</script>\n"
                f'<script>document.addEventListener("DOMContentLoaded",function(){{renderMathInElement(document.body,{opciones});}});</script>')
    cdn = "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist"
    return (f'<link rel="stylesheet" href="{cdn}/katex.min.css">\n<script defer src="{cdn}/katex.min.js"></script>\n'
            f'<script defer src="{cdn}/contrib/auto-render.min.js" onload="renderMathInElement(document.body,{opciones});"></script>')


# ------------------------------------------------------------------ principal
def main() -> None:
    cfg = yaml.safe_load(open(RAIZ / "modelos" / "config_fase3.yaml", encoding="utf-8"))
    f3, f4, f5, f6, f7 = (RES / f"fase{i}" for i in range(3, 8))
    eol = pd.read_csv(f3 / "eol_celdas.csv")
    wb = pd.read_csv(f3 / "weibull_por_conjunto.csv")
    bc = json.loads((f3 / "weibull_beta_comun.json").read_text(encoding="utf-8"))
    fl = pd.read_csv(f3 / "vida_flota_entidad.csv")
    cs = pd.read_csv(f3 / "curva_s_parametros.csv")
    bt = pd.read_csv(f3 / "curva_s_backtest.csv")
    va = pd.read_csv(f3 / "ventas_validacion_corto_plazo.csv")
    pv = pd.read_csv(f3 / "ventas_proyeccion_anual.csv")
    re = pd.read_csv(f3 / "retiros_eol_anual.csv")
    dg = pd.read_csv(f4 / "diagnosticos.csv")
    cb = pd.read_csv(f4 / "cobertura_intervalos.csv")
    sv = pd.read_csv(f5 / "soh_validacion.csv")
    tr = pd.read_csv(f5 / "soh_transferencia.csv")
    mc = pd.read_csv(f6 / "co2_monte_carlo_resumen.csv")
    sb = pd.read_csv(f6 / "sobol_indices.csv")
    es = pd.read_csv(f6 / "escenarios_red.csv")
    nd = pd.read_csv(f7 / "ndvi_tendencias.csv")
    rp = pd.read_csv(f7 / "reparto_emisiones.csv")

    m = mc.set_index("variable")
    bev = fl[fl.tipo == "BEV"]
    caliente = bev.temp_media_c >= 24
    t40 = {e: re[(re.escenario == e) & (re.anio == 2040)].toneladas_p50.sum() / 1000 for e in ("bajo", "base", "alto")}
    fab, uso = rp.iloc[0], rp.iloc[1]
    hoy = dt.date.today()

    valores = {
        "CAMPUS": UNIDAD,
        "EQUIPO": equipo_html(),
        "FECHA": f"{MESES[hoy.month - 1].capitalize()} de {hoy.year}",
        "RED_P50": n(m.loc["reduccion_pct", "p50"]),
        "RED_P5": n(m.loc["reduccion_pct", "p5"]),
        "RED_P95": n(m.loc["reduccion_pct", "p95"]),
        "EQ_KM": n(round(m.loc["equilibrio_km", "p50"], -2)),
        "EQ_ANIOS": n(m.loc["equilibrio_km", "p50"] / cfg["vida_flota"]["km_anio"]["mediana"], 1),
        "PROB": n(100 * m.loc["prob_bev_mas_limpio", "p50"], 1),
        "T2040": n(t40["base"], 1), "T2040B": n(t40["bajo"], 1), "T2040A": n(t40["alto"], 1),
        "VIDA_CAL": n(bev[caliente].mediana_bateria_sola_anios.mean(), 1),
        "VIDA_RESTO": n(bev[~caliente].mediana_bateria_sola_anios.mean(), 1),
        "NDVI_CAN": n(nd.set_index("zona").loc["mina_cu_cananea", "cambio_pct"]),
        "BEV_P50": n(m.loc["bev_g_km", "p50"]), "GAS_P50": n(m.loc["gas_g_km", "p50"]),
        "FAB": n(fab.g_km_p50, 1), "FAB_PCT": n(fab.pct), "USO": n(uso.g_km_p50, 1), "USO_PCT": n(uso.pct),
        "TABLA_RETIROS": t_retiros(re), "TABLA_SIMBOLOS": t_simbolos(), "TABLA_FUENTES": t_fuentes(),
        "TABLA_EOL": t_eol(eol, wb), "TABLA_WEIBULL": t_weibull(wb), "TABLA_LRT": t_lrt(bc),
        "TABLA_FLOTA": t_flota(fl), "TABLA_CURVA_S": t_curva_s(cs), "TABLA_BACKTEST": t_backtest(bt),
        "TABLA_DIAG": t_diag(dg), "TABLA_VALID": t_valid(va), "TABLA_COB": t_cob(cb),
        "TABLA_RETIROS2": t_retiros_tipo(re), "TABLA_SOH": t_soh(sv), "TABLA_TRANS": t_trans(tr),
        "TABLA_MC": t_mc(mc), "TABLA_SOBOL": t_sobol(sb), "TABLA_ESC": t_esc(es), "TABLA_NDVI": t_ndvi(nd),
        "TABLA_CODIGO": t_codigo(), "TABLA_PRUEBAS": t_pruebas(), "TABLA_SUPUESTOS": t_supuestos(cfg),
        "TABLA_VENTAS": t_ventas(pv),
    }
    figuras = {f"FIG{i}": imagen(nombre) for i, nombre in enumerate(sorted(p.name for p in (RES / "figuras").glob("*.png")), 1)}

    html = (DOCS / "plantilla_extenso.html").read_text(encoding="utf-8")
    for clave, valor in valores.items():
        html = html.replace(f"@@{clave}@@", valor)
    faltan = sorted({t for t in html.split("@@")[1::2] if t.isupper() and not t.startswith(("FIG", "KATEX"))})
    if faltan:
        raise SystemExit(f"Marcadores sin valor en la plantilla: {faltan}")
    for clave, valor in figuras.items():                       # al final: base64 grande y KaTeX
        html = html.replace(f"@@{clave}@@", valor)
    html = html.replace("@@KATEX@@", katex_html())
    for logo in ("ipn", "ciencia_datos", "sistemas_automotrices"):   # logos oficiales: se incrustan si existen
        f = DOCS / "logos" / f"{logo}.png"
        if f.exists():
            html = html.replace(f'src="logos/{logo}.png"', 'src="data:image/png;base64,' + base64.b64encode(f.read_bytes()).decode() + '"')

    salida = DOCS / "extenso_bateria_ve_mx.html"
    salida.write_text(html, encoding="utf-8")
    (DOCS / "logos").mkdir(exist_ok=True)
    print(f"Listo: {salida.relative_to(RAIZ)} ({salida.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
