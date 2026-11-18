"""Fase 8: las 4 gráficas clave del proyecto (PNG, 200 dpi) en resultados/figuras/.

Uso: python -m modelos.ejecutar_figuras   (requiere matplotlib y los resultados de las Fases 3, 6 y 7)
  1_toneladas_retiradas.png     toneladas de baterías que salen de vehículos 2024-2040, 3 escenarios + banda
  2_co2_por_escenario_red.png   g CO2e/km del BEV (mediana e intervalo 90%) vs gasolina, por escenario de red
  3_vida_bateria_vs_clima.png   vida mediana de la batería BEV por estado vs su temperatura media
  4_ndvi_minas.png              NDVI anual 2014-2025 en las tres zonas mineras
  5_weibull_supervivencia.png   supervivencia empírica (Kaplan-Meier) vs Weibull ajustada, por conjunto
  6_curva_s_participacion.png   participación de mercado observada y curva S (escenario base) a 2040
  7_validacion_mase.png         MASE por modelo y tipo en la validación de origen móvil
  8_sobol.png                   índices de Sobol de efecto total con intervalo de 90%
Paleta categórica de referencia (azul, naranja, aqua) validada para daltonismo; texto en tinta neutra.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
AZUL, NARANJA, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
GRIS, TINTA, TINTA2, FONDO, REJILLA = "#8a8984", "#0b0b0b", "#52514e", "#fcfcfb", "#e4e3df"


def estilo(ax, titulo, sub=None):
    ax.set_facecolor(FONDO)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    for s in ["left", "bottom"]:
        ax.spines[s].set_color(REJILLA)
    ax.tick_params(colors=TINTA2, labelsize=9)
    ax.grid(axis="y", color=REJILLA, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_title(titulo, loc="left", fontsize=12, color=TINTA, fontweight="bold", pad=22 if sub else 10)
    if sub:
        ax.text(0, 1.02, sub, transform=ax.transAxes, fontsize=9, color=TINTA2)


def fig_toneladas(salida):
    d = pd.read_csv(RAIZ / "resultados/fase3/retiros_eol_anual.csv")
    d = d[d.anio >= 2024]
    t = d.groupby(["escenario", "anio"])[["toneladas_p5", "toneladas_p50", "toneladas_p95"]].sum().reset_index()
    fig, ax = plt.subplots(figsize=(8, 4.6), facecolor=FONDO)
    b = t[t.escenario == "base"]
    ax.fill_between(b.anio, b.toneladas_p5, b.toneladas_p95, color=AZUL, alpha=0.12, linewidth=0,
                    label="Base: intervalo P5-P95")
    for esc, col, ls in [("alto", NARANJA, "--"), ("base", AZUL, "-"), ("bajo", AQUA, ":")]:
        s = t[t.escenario == esc]
        ax.plot(s.anio, s.toneladas_p50, color=col, lw=2, ls=ls, label=f"Escenario {esc} (mediana)")
        ax.annotate(f"{s.toneladas_p50.iloc[-1]/1000:.1f} mil t", (s.anio.iloc[-1], s.toneladas_p50.iloc[-1]),
                    xytext=(6, 0), textcoords="offset points", va="center", fontsize=9, color=TINTA)
    ax.set_xlim(2024, 2042.5)
    ax.set_xticks(range(2024, 2041, 2))
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v/1000:.0f} mil"))
    ax.set_ylabel("toneladas por año", color=TINTA2, fontsize=9)
    estilo(ax, "Baterías que salen de vehículos en México", "BEV + PHEV + HEV. La banda suma los P5 y P95 por tipo (conservadora).")
    ax.legend(frameon=False, fontsize=8.5, labelcolor=TINTA2, loc="upper left")
    fig.tight_layout()
    fig.savefig(salida / "1_toneladas_retiradas.png", dpi=200, facecolor=FONDO)
    plt.close(fig)


def fig_co2(salida):
    e = pd.read_csv(RAIZ / "resultados/fase6/escenarios_red.csv")
    etiquetas = ["Red fósil\n(+15%)", "Red actual\n(CENACE)", "Red limpia\n(mitad)", "Red muy limpia\n(~120 g/kWh)"]
    orden = [1, 0, 2, 3]
    e = e.iloc[orden].reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(8, 4.6), facecolor=FONDO)
    x = np.arange(len(e))
    ax.bar(x, e.bev_p50, width=0.5, color=AZUL, label="Auto eléctrico (BEV), mediana")
    ax.errorbar(x, e.bev_p50, yerr=[e.bev_p50 - e.bev_p5, e.bev_p95 - e.bev_p50], fmt="none",
                ecolor=TINTA2, elinewidth=1.2, capsize=4, label="Intervalo 90%")
    ax.axhline(e.gas_p50.iloc[0], color=NARANJA, lw=2, ls="--", label="Auto de gasolina, mediana")
    for i, r in e.iterrows():
        ax.text(i, 6, f"{r.bev_p50:.0f}\n−{r.reduccion_p50:.0f}%", ha="center", va="bottom", fontsize=9, color="white",
                fontweight="bold")
    ax.text(len(e) - 0.55, e.gas_p50.iloc[0] + 6, f"gasolina {e.gas_p50.iloc[0]:.0f}", ha="right", fontsize=9, color=TINTA)
    ax.set_xticks(x, etiquetas)
    ax.set_ylabel("g CO₂e por km (ciclo de vida)", color=TINTA2, fontsize=9)
    estilo(ax, "Emisiones por km: eléctrico vs gasolina en México",
           "Incluye mina, fabricación de batería y auto, y uso. Monte Carlo de 20,000 corridas.")
    ax.legend(frameon=False, fontsize=8.5, labelcolor=TINTA2, loc="upper right", bbox_to_anchor=(1, 0.93))
    fig.tight_layout()
    fig.savefig(salida / "2_co2_por_escenario_red.png", dpi=200, facecolor=FONDO)
    plt.close(fig)


def fig_clima(salida):
    v = pd.read_csv(RAIZ / "resultados/fase3/vida_flota_entidad.csv")
    b = v[v.tipo == "BEV"]
    fig, ax = plt.subplots(figsize=(8, 4.6), facecolor=FONDO)
    ax.scatter(b.temp_media_c, b.mediana_bateria_sola_anios, s=46, color=AZUL, edgecolor=FONDO, linewidth=1.5, zorder=3)
    for nombre, dx, dy in [("Ciudad de México", 6, 4), ("Tlaxcala", 6, 4), ("Jalisco", 6, 4), ("Nuevo León", 6, 4),
                           ("Sonora", -6, 10), ("Yucatán", -10, -14), ("Campeche", 6, 6)]:
        r = b[b.entidad == nombre].iloc[0]
        ax.annotate(nombre, (r.temp_media_c, r.mediana_bateria_sola_anios), xytext=(dx, dy), textcoords="offset points",
                    fontsize=8.5, color=TINTA, ha="right" if dx < 0 else "left")
    ax.set_xlabel("temperatura media anual de la capital (°C, NASA POWER 2016-2025)", color=TINTA2, fontsize=9)
    ax.set_ylabel("vida mediana de la batería (años)", color=TINTA2, fontsize=9)
    estilo(ax, "En los estados calurosos la batería dura casi la mitad",
           "BEV, años hasta 80% de capacidad. Un punto por estado; simulación de flota con Arrhenius.")
    fig.tight_layout()
    fig.savefig(salida / "3_vida_bateria_vs_clima.png", dpi=200, facecolor=FONDO)
    plt.close(fig)


def fig_ndvi(salida):
    n = pd.read_csv(RAIZ / "datos/procesado/vegetacion_ndvi_zonas.csv")
    t = pd.read_csv(RAIZ / "resultados/fase7/ndvi_tendencias.csv").set_index("zona")
    nombres = {"mina_mn_molango": ("Molango (manganeso), Hgo.", AQUA),
               "mina_li_bacadehuachi": ("Bacadéhuachi (litio), Son.", NARANJA),
               "mina_cu_cananea": ("Cananea (cobre), Son.", AZUL)}
    fig, ax = plt.subplots(figsize=(8, 4.6), facecolor=FONDO)
    for z, (nom, col) in nombres.items():
        g = n[n.zona == z].sort_values("anio")
        ax.plot(g.anio, g.ndvi_mediana, color=col, lw=2, marker="o", ms=4.5, mec=FONDO, mew=1.2)
        p = t.loc[z, "p_mann_kendall"]
        ax.annotate(f"{nom}\n{t.loc[z,'cambio_pct']:+.0f}%, p = {p:.3f}" if p >= 0.001 else f"{nom}\n{t.loc[z,'cambio_pct']:+.0f}%, p < 0.001",
                    (g.anio.iloc[-1], g.ndvi_mediana.iloc[-1]), xytext=(8, 0), textcoords="offset points",
                    va="center", fontsize=8.5, color=TINTA)
    ax.set_xlim(2013.5, 2030.5)
    ax.set_xticks(range(2014, 2026, 2))
    ax.spines["bottom"].set_bounds(2013.5, 2025.5)
    ax.set_ylim(0, 1)
    ax.set_ylabel("NDVI mediano anual (Landsat 8/9)", color=TINTA2, fontsize=9)
    estilo(ax, "Vegetación alrededor de las minas, 2014-2025",
           "Cambio 2014-16 vs 2023-25 y prueba de Mann-Kendall. Una tendencia no prueba que la cause la mina.")
    fig.tight_layout()
    fig.savefig(salida / "4_ndvi_minas.png", dpi=200, facecolor=FONDO)
    plt.close(fig)


def kaplan_meier(t, evento):
    orden = np.argsort(t)
    t, e = np.asarray(t)[orden], np.asarray(evento)[orden]
    n, s, xs, ys = len(t), 1.0, [0.0], [1.0]
    for i, (ti, ei) in enumerate(zip(t, e)):
        if ei:
            xs += [ti, ti]
            ys += [s, s * (1 - 1 / (n - i))]
            s *= 1 - 1 / (n - i)
    return np.array(xs), np.array(ys), t[e == 0]


def fig_weibull(salida):
    from modelos.vida_util import weibull as W
    eol = pd.read_csv(RAIZ / "resultados/fase3/eol_celdas.csv")
    par = pd.read_csv(RAIZ / "resultados/fase3/weibull_por_conjunto.csv").set_index("conjunto")
    fig, axs = plt.subplots(1, 3, figsize=(10, 3.6), facecolor=FONDO)
    nombres = {"calce": ("CALCE (25 °C)", "ciclos completos"), "nasa_pcoe": ("NASA PCoE (24 °C)", "ciclos"),
               "oxford": ("Oxford (40 °C)", "ciclos de manejo")}
    for ax, (c, (tit, uni)) in zip(axs, nombres.items()):
        g = eol[(eol.conjunto == c) & eol.incluida]
        x, y, cens = kaplan_meier(g.tiempo.to_numpy(), g.evento.astype(bool).to_numpy())
        tmax = max(g.tiempo.max(), par.loc[c, "eta"]) * 1.25
        tt = np.linspace(0, tmax, 300)
        ax.plot(tt, W.supervivencia(tt, par.loc[c, "beta"], par.loc[c, "eta"]), color=AZUL, lw=2, label="Weibull (MLE)")
        ax.step(np.append(x, tmax), np.append(y, y[-1]), where="post", color=TINTA2, lw=1.4, label="Kaplan-Meier")
        km = lambda v: y[np.searchsorted(x, v, side="right") - 1]
        ax.plot(cens, [km(v) for v in cens], "|", color=NARANJA, ms=10, mew=2, label="censurada")
        estilo(ax, tit)
        ax.text(0.03, 0.06, f"β = {par.loc[c,'beta']:.1f}\nη = {par.loc[c,'eta']:,.0f}", transform=ax.transAxes,
                fontsize=8.5, color=TINTA)
        ax.set_xlabel(uni, color=TINTA2, fontsize=8.5)
        ax.set_ylim(0, 1.05)
    axs[0].set_ylabel("S(t): fracción sin llegar a 80% SoH", color=TINTA2, fontsize=8.5)
    axs[0].legend(frameon=False, fontsize=7.5, labelcolor=TINTA2, loc="lower left", bbox_to_anchor=(0, 0.18))
    fig.tight_layout()
    fig.savefig(salida / "5_weibull_supervivencia.png", dpi=200, facecolor=FONDO)
    plt.close(fig)


def fig_curva_s(salida):
    import yaml
    from modelos.ventas.preparar import anual, serie_nacional_mensual
    from modelos.ventas import curva_s as CS
    cfg = yaml.safe_load(open(RAIZ / "modelos/config_fase3.yaml", encoding="utf-8"))["ventas"]
    a = anual(serie_nacional_mensual(pd.read_csv(RAIZ / "datos/procesado/inegi_ventas_entidad_mes.csv")),
              cfg["mercado_total_anual"], cfg["anio_parcial"])
    par = pd.read_csv(RAIZ / "resultados/fase3/curva_s_parametros.csv")
    fig, ax = plt.subplots(figsize=(8, 4.6), facecolor=FONDO)
    tt = np.arange(2016, 2041)
    for t, col in [("BEV", AZUL), ("PHEV", NARANJA), ("HEV", AQUA)]:
        r = par[(par.escenario == "base") & (par.tipo == t)].iloc[0]
        ax.plot(tt, 100 * CS.predecir(tt, r.k, r.t0, r.s_max), color=col, lw=2, ls="--")
        ax.plot(a.index, 100 * a[f"s_{t}"], color=col, lw=0, marker="o", ms=5, mec=FONDO, mew=1.2)
        ax.annotate(f"{t} (s_max = {r.s_max:.0%})", (2040, 100 * CS.predecir(2040, r.k, r.t0, r.s_max)),
                    xytext=(6, 0), textcoords="offset points", va="center", fontsize=8.5, color=TINTA)
    ax.set_xlim(2015.5, 2045.5)
    ax.set_xticks(range(2016, 2041, 4))
    ax.spines["bottom"].set_bounds(2015.5, 2040.5)
    ax.set_ylabel("% de las ventas de vehículos ligeros", color=TINTA2, fontsize=9)
    estilo(ax, "Participación de mercado: observada y curva S (escenario base)",
           "Puntos: INEGI 2016-2026 (2026 parcial). Líneas: s(t) = s_max / (1 + exp(-k (t - t0))).")
    fig.tight_layout()
    fig.savefig(salida / "6_curva_s_participacion.png", dpi=200, facecolor=FONDO)
    plt.close(fig)


def fig_mase(salida):
    v = pd.read_csv(RAIZ / "resultados/fase3/ventas_validacion_corto_plazo.csv")
    orden = ["naive_estacional", "deriva_estacional", "ets", "sarima", "lightgbm", "lstm"]
    etiq = {"naive_estacional": "Naive estacional", "deriva_estacional": "Deriva estacional", "ets": "ETS",
            "sarima": "SARIMA", "lightgbm": "LightGBM", "lstm": "LSTM"}
    fig, ax = plt.subplots(figsize=(8, 4.6), facecolor=FONDO)
    y = np.arange(len(orden))
    for k, (t, col) in enumerate([("BEV", AZUL), ("PHEV", NARANJA), ("HEV", AQUA)]):
        d = v[v.tipo == t].set_index("modelo").loc[orden]
        ax.barh(y + (k - 1) * 0.26, d.MASE, height=0.24, color=col, label=t)
    ax.set_yticks(y, [etiq[m] for m in orden])
    ax.invert_yaxis()
    ax.axvline(1, color=TINTA2, lw=1, ls=":")
    ax.grid(axis="x", color=REJILLA, linewidth=0.8)
    ax.set_xlabel("MASE en escala log (menor es mejor)", color=TINTA2, fontsize=9)
    estilo(ax, "Validación de origen móvil a 12 meses", "24 orígenes por tipo de vehículo; 222 pronósticos por modelo y tipo.")
    ax.grid(axis="y", visible=False)
    ax.legend(frameon=False, fontsize=8.5, labelcolor=TINTA2, loc="lower right")
    fig.tight_layout()
    fig.savefig(salida / "7_validacion_mase.png", dpi=200, facecolor=FONDO)
    plt.close(fig)


def fig_sobol(salida):
    s = pd.read_csv(RAIZ / "resultados/fase6/sobol_indices.csv").sort_values("ST").tail(8)
    etiq = {"rendimiento_km_l": "Rendimiento del auto de gasolina", "u_vida_vehiculo": "Vida del vehículo",
            "u_vida_bateria": "Vida de la batería", "km_anio": "km por año", "bateria_kwh": "Tamaño de batería (kWh)",
            "consumo_kwh_km": "Consumo del BEV (kWh/km)", "ef_bateria_kg_kwh": "CO2 de fabricar la batería",
            "p_reemplazo_bateria": "Prob. de reemplazar batería", "u_red": "Intensidad de la red (rango actual)"}
    fig, ax = plt.subplots(figsize=(8, 4.6), facecolor=FONDO)
    y = np.arange(len(s))
    ax.barh(y, s.ST, height=0.55, color=AZUL, label="Efecto total ST")
    ax.errorbar(s.ST, y, xerr=[s.ST - s.ST_p5, s.ST_p95 - s.ST], fmt="none", ecolor=TINTA2, capsize=3, elinewidth=1)
    ax.plot(s.S1, y, "o", color=NARANJA, ms=6, mec=FONDO, mew=1.2, label="Primer orden S1")
    ax.set_yticks(y, [etiq.get(e, e) for e in s.entrada])
    ax.grid(axis="x", color=REJILLA, linewidth=0.8)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("fracción de la varianza del ahorro gasolina − BEV (g CO2e/km)", color=TINTA2, fontsize=9)
    estilo(ax, "Análisis de sensibilidad global (Sobol)", "Saltelli/Jansen, N = 8,192 (122,880 evaluaciones); IC 90% por bootstrap.")
    ax.legend(frameon=False, fontsize=8.5, labelcolor=TINTA2, loc="lower right")
    fig.tight_layout()
    fig.savefig(salida / "8_sobol.png", dpi=200, facecolor=FONDO)
    plt.close(fig)


def main() -> None:
    salida = RAIZ / "resultados" / "figuras"
    salida.mkdir(parents=True, exist_ok=True)
    for f in (fig_toneladas, fig_co2, fig_clima, fig_ndvi, fig_weibull, fig_curva_s, fig_mase, fig_sobol):
        f(salida)
    print("Figuras en", salida)


if __name__ == "__main__":
    main()
