"""Modelo de CO2 de ciclo de vida por km: auto eléctrico de batería (BEV) vs auto de gasolina, en México.

Para un vehículo con vida T_veh (años) y batería con vida T_bat:
  - Si T_bat >= T_veh: una batería, km de vida = km_anio * T_veh.
  - Si T_bat <  T_veh: con probabilidad p se reemplaza la batería (2 baterías, km = km_anio * T_veh);
    con 1 - p el auto se desecha cuando muere la batería (1 batería, km = km_anio * T_bat).
    Se usa el VALOR ESPERADO de las emisiones por km sobre esas dos ramas.
BEV  [g/km] = [carrocería + n_bat * kWh * EF_bat * (1 - crédito_reciclaje)] / km_vida
              + consumo * I_red * (1 + pérdidas)
Gas. [g/km] = [carrocería + batería de plomo] / (km_anio * T_veh) + EF_gasolina / rendimiento
Punto de equilibrio (km): distancia a la que el BEV acumula lo mismo que el de gasolina
              = (emisiones extra de fabricar el BEV) / (ahorro por km en uso).
"""
from __future__ import annotations

import numpy as np


def evaluar(x: dict, cuantil_bat, cuantil_veh, cuantil_red, plomo_t: float) -> dict:
    """x: dict de vectores (una muestra por posición). cuantil_*: funciones u -> valor."""
    t_bat = cuantil_bat(x["u_vida_bateria"])
    t_veh = cuantil_veh(x["u_vida_vehiculo"])
    i_red = cuantil_red(x["u_red"])                                    # g CO2e/kWh generado
    bat_t = x["bateria_kwh"] * x["ef_bateria_kg_kwh"] * (1 - x["reciclaje_credito"]) / 1000.0  # t CO2e
    uso_bev = x["consumo_kwh_km"] * i_red * (1 + x["perdidas_red"])    # g/km

    muere_antes = t_bat < t_veh
    p = np.where(muere_antes, x["p_reemplazo_bateria"], 0.0)
    km_largo = x["km_anio"] * t_veh
    km_corto = x["km_anio"] * np.minimum(t_bat, t_veh)
    fab_reemplazo = (x["carroceria_t"] + 2 * bat_t) * 1e6 / km_largo     # g/km
    fab_desecho = (x["carroceria_t"] + bat_t) * 1e6 / np.where(muere_antes, km_corto, km_largo)
    bev = p * fab_reemplazo + (1 - p) * fab_desecho + uso_bev

    uso_gas = x["ef_gasolina_kg_l"] * 1000.0 / x["rendimiento_km_l"]   # g/km
    gas = (x["carroceria_t"] + plomo_t) * 1e6 / km_largo + uso_gas

    extra_fab = (bat_t - plomo_t) * 1e6                                # g
    ahorro = uso_gas - uso_bev
    equilibrio = np.where(ahorro > 0, extra_fab / np.maximum(ahorro, 1e-9), np.inf)
    return {"bev_g_km": bev, "gas_g_km": gas, "reduccion_pct": 100 * (1 - bev / gas),
            "uso_bev_g_km": uso_bev, "uso_gas_g_km": uso_gas, "equilibrio_km": equilibrio,
            "i_red": i_red, "t_bat": t_bat, "t_veh": t_veh}
