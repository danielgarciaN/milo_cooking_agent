# Datos y transformaciones — Sprint 1

## Procedencia

Selecciones: `food_selection.json` (65 Foundation), `food_selection_october.json` (cuatro actualizaciones completas) y `food_selection_sr.json` (cinco complementos SR Legacy). Cada entrada conserva ID, descripción original esperada, traducción, estado y revisión de alérgenos. Se rechazan descripciones que cambien para evitar remapeos silenciosos.

El CSV de octubre de 2026 pasa CRC pero carece de `food.csv` y `food_nutrient.csv`: `incomplete_archive`. La base es el CSV oficial de abril de 2026. Pan, tortilla y dos pastas se reemplazan completos con el JSON de octubre; no se mezclan nutrientes entre versiones de un registro.

SR Legacy añade IDs 171413 (aceite de oliva genérico), 171025 (girasol linoleico), 172421 (lentejas cocidas), 172475 (tofu firme con sulfato cálcico), 168874 (quinoa seca). Los aceites Foundation incompletos conservan sus ausencias: no reciben valores de SR Legacy. Total: 70 alimentos, 65 Foundation, 68 con macros completos.

## Relaciones USDA

1. `foundation_food.fdc_id` o `sr_legacy_food.fdc_id` delimita la familia.
2. `food.fdc_id` aporta descripción y `data_type`.
3. `food_nutrient.fdc_id` enlaza alimento y medición.
4. `food_nutrient.nutrient_id = nutrient.id` identifica nutriente y unidad.
5. `food_nutrient.amount` se conserva como Decimal por 100 g comestibles.

No confundir `nutrient.id` con `nutrient_nbr`. Las muestras/submuestras no son alimentos finales y no se promedian manualmente. Se detectan duplicados y unidades inesperadas. El JSON conserva estas relaciones dentro de `foodNutrients[].nutrient`.

| Campo | ID USDA | Unidad | Política |
|---|---|---|---|
| protein_g | 1003 | g | Publicado o null |
| carbs_g | 1005 | g | Carbohidratos por diferencia; no carbohidratos netos |
| fat_g | 1004 | g | Publicado o null |
| fiber_g | 1079 | g | Opcional; no inferir cero |
| kcal | 2048, 2047, 1008 | kcal | Preferir Atwater específico, después general, después energía publicada |

La precedencia de energía es una decisión documentada de MILO. Se conservan `nutrient_ids` y `nutrient_record_ids`. No se suman definiciones de energía, convierten kJ silenciosamente ni reconstruyen kcal. Cero publicado se conserva; ausencia se representa como null.

## Contratos y políticas

`Food` incluye nombres, IDs, estado, nutrientes/100 g, fuente, versión y revisión. `verified` significa identidad/esquema/valores contrastados con la fuente, no certificación clínica o de marca. `NutrientValues` admite Decimal finito no negativo o null. `RecipeIngredient` exige gramos positivos de porción comestible y estado explícito; rechaza otras unidades, booleanos, NaN e infinito. `Recipe` exige ingredientes, pasos y raciones enteras positivas.

`UserProfile` y `DietaryRestriction` contienen restricciones explícitas; su persistencia aún no existe. `NutritionResult` devuelve totales, valores por ración, completitud, ausencias y carácter aproximado. `ValidationResult` contiene errores bloqueantes, advertencias y alérgenos. `DataSource` conserva la procedencia documental.

Fórmula: `total = sum(gramos / 100 * nutriente_por_100g)`. División por raciones después de sumar. Un nutriente ausente en cualquier ingrediente produce null en el total de ese nutriente, no un subtotal presentado como total. Un ingrediente inexistente/no revisado hace desconocidos todos sus aportes. Estado incompatible produce error.

`complete` exige kcal/proteína/carbohidratos/grasa. La fibra ausente aparece en `missing`. `approximate` siempre es verdadero: las tablas representan alimentos de referencia. No se calculan valores por 100 g del plato cocinado sin peso final ni se inventan factores de rendimiento/retención.

Un producto compuesto identificado permite estimación numérica, pero bloquea la validación de la receta si sus alérgenos están pendientes. Alergias, exclusiones, preferencias negativas y dietas incompatibles impiden el ajuste. `adjust_portions` escala uniformemente a kcal objetivo por ración, conserva raciones y admite por defecto factor 0.5–2. No optimiza otros macros ni prescribe necesidades. Se mantiene precisión; redondear pesos exige recalcular. La receta ajustada conserva estado pendiente de revisión culinaria.

## Recetas

Los 12 borradores permanecen intactos. `prepare_recipes.py` concreta ingredientes de forma explícita: tomate roma, yogur entero, arroz blanco seco, salmón de cultivo y pavo picado cocinado. Los frutos rojos se concretan en 50 g de fresa + 50 g de frambuesa. Huevos sin cáscara, lentejas cocidas, garbanzos/atún escurridos. Se conservan cantidades originales salvo la división explícita de frutos rojos.

Se retiran etiquetas no demostradas `high_protein`, `budget`, `vegan` y `vegetarian`. Las dietas se evalúan desde ingredientes y perfil. Los tiempos son estimaciones editoriales, no ensayos de cocina.

Verificadas: r001, r002, r003, r006, r008, r010, r012. Pendientes: r004 (pasta/atún/tomate en conserva), r005 (garbanzos en conserva), r007 (pan), r009 (tortilla), r011 (tofu). Las doce tienen estimaciones de macros completas; la composición incierta mantiene cinco pendientes. La fibra puede ser null.

Temperaturas contrastadas con [FoodSafety.gov](https://www.foodsafety.gov/food-safety-charts/safe-minimum-internal-temperatures). No se han realizado pruebas físicas de cocina. La guía ampliada y las equivalencias de sustitución quedan pendientes.
