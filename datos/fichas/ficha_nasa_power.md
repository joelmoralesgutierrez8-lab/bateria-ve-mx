# Ficha de dataset: NASA POWER - temperatura mensual a 2 m (T2M, T2M_MAX, T2M_MIN)

- **Fuente oficial:** https://power.larc.nasa.gov/docs/services/api/temporal/monthly/
- **Origen geográfico:** Global, rejilla de resolución gruesa (decenas de km; por verificar la resolución exacta del producto)
- **Clima / condiciones:** Reanálisis; suaviza extremos locales
- **Periodo nominal:** el que pidas en config (por defecto 2016-2025)
- **Variables:** Temperatura a 2 m promedio, máxima y mínima mensual
- **Licencia:** Datos abiertos de NASA POWER (citar según power.larc.nasa.gov/docs/methodology/citations/)
- **Estado del procesamiento:** 4,320 filas procesadas. Columnas con faltantes (%): ninguna. Periodo observado: 2016-01-01 a 2025-12-01.

## Sesgos y limitaciones conocidos
- Reanálisis, no estación: subestima picos de calor locales, que son los que más degradan baterías.
- Temperatura del aire no es temperatura del paquete de baterías.
