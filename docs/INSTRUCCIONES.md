# MILO: paquete de materiales de arranque

**Estado: preparación, no corpus definitivo.**

## Documentos oficiales que debe descargar el desarrollador
1. AESAN PDF: https://www.aesan.gob.es/AECOSAN/docs/documentos/nutricion/RECOMENDACIONES_DIETETICAS.pdf
2. USDA Foundation Foods CSV ZIP: https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_foundation_food_csv_2026-10-29.zip
3. USDA diccionario PDF: https://fdc.nal.usda.gov/docs/Download_Field_Descriptions_Oct2020.pdf
4. OMS página de referencia (NO PDF directo): https://www.who.int/es/news-room/fact-sheets/detail/healthy-diet

No se han incluido aquí copias de documentos externos. El agente puede intentar descargarlos a data/raw, guardar hash SHA-256, registrar fecha, código HTTP, tamaño y licencia. Si falla la red debe informar; nunca simular descarga.

## Datos de arranque
- recipes_DRAFT.json: 12 ideas de recetas, **no listas para producción**: pasos genéricos, sin revisión de alérgenos, cantidades estimativas.
- foods_TEMPLATE.csv: esquema vacío. **No hay macros verificados en este paquete.**
- substitutions_DRAFT.json: relaciones para revisar y comprobar equivalencias.
- sources.json: registro de procedencia.

## Criterios de cierre
- >=3 documentos sustanciales o corpus equivalente ~20 páginas, trazable y legalmente reutilizable.
- Cada alimento con source_id y FDC ID verificable, estado crudo/cocido, nutrientes y unidad.
- Cada receta con ingredientes food_id válidos, instrucciones reales, alérgenos revisados y macros calculados por código.
- Pruebas unitarias contra casos conocidos y fallos explícitos cuando faltan datos.

## Notas
- No considerar documentos 'descargados' ni el recetario 'terminado' por el simple hecho de existir este paquete.
- Usar AESAN como corpus principal inicial (19 páginas) y ampliar con otros documentos autorizados para cumplir mínimo.
- El ZIP de USDA sirve para tabla estructurada; no debe tratarse como 20 páginas de teoría.
