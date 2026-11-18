# Ficha de dataset: NDVI anual en zonas mineras (Landsat 8/9 Collection 2 Level-2 vía Microsoft Planetary Computer)

- **Fuente oficial:** https://planetarycomputer.microsoft.com/api/stac/v1
- **Origen geográfico:** Las zonas que definas en config/zonas_mineras.csv
- **Clima / condiciones:** Nubosidad filtrada con QA_PIXEL; regiones áridas tienen NDVI bajo de forma natural
- **Periodo nominal:** Landsat 8 desde 2013; por defecto 2014-2025
- **Variables:** NDVI mediano anual por zona
- **Licencia:** Datos Landsat de USGS/NASA abiertos (por verificar texto de la política de datos)
- **Estado del procesamiento:** 36 filas procesadas. Columnas con faltantes (%): ninguna. Periodo observado: 2014 a 2025.

## Sesgos y limitaciones conocidos
- El NDVI mide verdor, no biodiversidad ni calidad de agua/suelo.
- Sin zonas definidas por ti el dataset queda vacío: zonas mineras sin datos = brecha explícita.
- Landsat 30 m; minas pequeñas o subterráneas pueden no verse.
