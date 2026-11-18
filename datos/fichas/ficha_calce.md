# Ficha de dataset: CALCE Battery Data (Univ. de Maryland)

- **Fuente oficial:** https://calce.umd.edu/data
- **Origen geográfico:** Laboratorio en EE. UU.
- **Clima / condiciones:** Pruebas en cámara (la página lista OCV de -10 a 50 °C para algunas celdas; los ciclos CS2 por verificar)
- **Periodo nominal:** CS2 registrado 2010-2013 (según un resumen de la literatura)
- **Variables:** Ciclado de celdas prismáticas CS2 (LiCoO2, 1100 mAh), cilíndricas y otras; archivos Excel de Arbin
- **Licencia:** Términos de uso en la página del grupo (por verificar texto; pide citar las publicaciones asociadas)
- **Estado del procesamiento:** 5,686 filas procesadas. Columnas con faltantes (%): ninguna.

## Sesgos y limitaciones conocidos
- Celdas pequeñas de electrónica portátil (CS2), no paquetes automotrices.
- Algunas celdas (CS2_8, CS2_21) están en .txt de CADEX y se omiten en este ETL.
