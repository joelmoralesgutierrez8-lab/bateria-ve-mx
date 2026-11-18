# Ficha de dataset: Li-ion Battery Aging Datasets (NASA Ames Prognostics Center of Excellence)

- **Fuente oficial:** https://www.nasa.gov/content/prognostics-center-of-excellence-data-set-repository
- **Origen geográfico:** Laboratorio NASA Ames, EE. UU. (celdas de prueba, no autos en uso real)
- **Clima / condiciones:** Cámara ambiental; varias temperaturas ambiente (por verificar cuáles en el README del dataset)
- **Periodo nominal:** Datos de laboratorio (publicado 2007-2010); no es una serie calendario
- **Variables:** Voltaje, corriente, temperatura, capacidad (Ah) por ciclo; impedancia
- **Licencia:** Datos públicos de NASA (por verificar términos de uso del repositorio)
- **Estado del procesamiento:** 2,769 filas procesadas. Columnas con faltantes (%): ninguna.

## Sesgos y limitaciones conocidos
- Celdas 18650 de 2 Ah de la época: química y diseño distintos a un paquete de VE actual.
- Pocas celdas (decenas) y perfiles de uso de laboratorio.
- Sin baja temperatura ni calor extremo comparable al norte de México (por verificar el rango real).
- Tratamiento aplicado en el ETL: se omitieron 4 ciclos de descarga sin capacidad registrada (Capacity vacío) en B0050 y 21 ciclos en B0052 (25 en total); el ETL deja un aviso en el log por cada uno. Los números de ciclo del procesado se cuentan solo sobre descargas con capacidad.
