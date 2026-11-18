# Ficha de dataset: Energía generada por tipo de tecnología (CENACE, Sistema de Información del Mercado)

- **Fuente oficial:** https://www.cenace.gob.mx/Paginas/SIM/Reportes/EnergiaGeneradaTipoTec.aspx
- **Origen geográfico:** México; nivel nacional (SEN). Verificado: CENACE solo publica generación liquidada por tecnología para el SEN completo, sin desglose por Gerencia de Control Regional (se usa SEN como línea base nacional).
- **Clima / condiciones:** No aplica
- **Periodo nominal:** 2016-05 a 2026-10 (126 meses, Liquidación Original L0, verificado en SIM)
- **Variables:** Energía (MWh) por tecnología (11 tecnologías: Eólica, Fotovoltaica, Biomasa, Carboeléctrica, Ciclo Combinado, Combustión Interna, Geotermoeléctrica, Hidroeléctrica, Nucleoeléctrica, Térmica Convencional, Turbo Gas), fecha y sistema (SEN)
- **Licencia:** Datos abiertos/públicos del Sistema de Información del Mercado (SIM) de CENACE
- **Estado del procesamiento:** 126 filas procesadas. Columnas con faltantes (%): ninguna. Periodo observado: 2016-05-01 a 2026-10-01.

## Sesgos y limitaciones conocidos
- CENACE solo publica la generación liquidada por tipo de tecnología a nivel nacional (Sistema = SEN), sin desagregar por las 8 Gerencias de Control Regional ni por los 3 sistemas interconectados (SIN, BCA, BCS). Se utiliza el SEN como línea base nacional mientras se evalúa si existe fuente regional por tecnología.
- IPCC AR5 (Anexo III, Tabla A.III.2) no reporta medianas de ciclo de vida separadas para térmica convencional (combustóleo), turbogás (ciclo abierto) ni combustión interna (diésel/combustóleo); mientras no se incorpore una segunda fuente citada para esas 3 tecnologías, quedan registradas como faltantes en tabla_datos_faltantes.
- PROVISIONAL (actualizado 2026-11-18): para no dejar huecos se asignaron factores aproximados en factores_emision_por_tecnologia.csv: turbogás = 490 g CO2e/kWh (mediana de ciclo combinado, probablemente SUBESTIMA porque el ciclo abierto es menos eficiente); térmica convencional y combustión interna = 820 g CO2e/kWh (mediana de carbón, usada como cota alta). Son supuestos, no valores medidos; sustituir por régimen térmico del COPAR (CFE) + factores IPCC 2006 y probarlos en el análisis de sensibilidad.
- Con la nueva legislación eléctrica de 2025 la CRE se extinguió y pasó a ser la Comisión Nacional de Energía (CNE): los nombres y rutas institucionales pueden haber cambiado.
- Generación liquidada (L0) despachada en el mercado eléctrico mayorista: no incluye generación distribuida exenta ni autoconsumo fuera del MEM.
- El factor oficial FESEN (SEMARNAT, usa datos de la CRE/CNE) es un solo número nacional anual.
