# Sensibilidad: retiro de la batería al 70 % de SoH en lugar de 80 %

**Por qué:** las garantías de las armadoras suelen cubrir hasta 70 % de capacidad (8 años / 160,000 km) y la literatura
reporta baterías retiradas con 70–80 %. El escenario base del repo usa 80 %, el extremo alto.

**Cómo se calculó (19 nov 2026), sobre una copia del repo con la semilla 42:**
1. En `modelos/config_fase3.yaml`: `umbrales_soh.eol_vehiculo: 0.70` y `vida_calendario_anios_25c` escalado ×1.5
   (min 22.5, moda 30, max 37.5), porque perder 30 % por calendario toma más que perder 20 % (supuesto lineal; si la
   pérdida calendario sigue raíz del tiempo, el factor sería mayor y la diferencia también).
2. `python -m modelos.ejecutar_vida_util` (escribe `eol_celdas.csv`; el bootstrap de Weibull falla para NASA y
   Oxford porque casi ninguna celda llega a 70 %, pero la flota usa solo CALCE, cuyas 6 celdas sí llegan).
3. `python -m modelos.ejecutar_vida_flota` y `python -m modelos.ejecutar_flujo_eol`.
4. La corrida a 80 % en el mismo entorno reproduce los resultados del repo (diferencia máxima 0.0003 t).

**Resultado (escenario base, mediana):**

| Año | Retiro al 80 % | Retiro al 70 % | Diferencia |
|---|---|---|---|
| 2026 | 330 t | 301 t | −9 % |
| 2030 | 2,137 t | 1,838 t | −14 % |
| 2035 | 11,356 t | 9,499 t | −16 % |
| 2040 | 38,657 t | 32,980 t | −15 % |
| Acumulado 2026–2035 | 39,223 t (400 mil baterías) | 32,944 t (369 mil baterías) | −16 % |

Con retiro al 70 %, la batería BEV dura en mediana 19.5 años sola (vs. 14.1) y solo 28 % de los BEV salen por la
batería (vs. 52 %): el auto suele terminar antes. **La conclusión de la brecha no cambia:** con 0 t/año de reciclaje
autorizado para litio, el déficit en 2035 sigue siendo total (9,499 t en lugar de 11,356 t).

Archivos: `retiros_umbral_80_vs_70.csv` (por año y tipo), `vida_flota_umbral_80_vs_70.csv` (por entidad y tipo).
