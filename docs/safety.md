# Seguridad y límites

MILO se limita a cocina y educación nutricional general. No diagnostica, trata enfermedades ni prescribe dietas clínicas. El futuro agente detectará solicitudes de tratamiento, explicará sus límites y sugerirá consulta profesional cuando corresponda. Esa ruta conversacional todavía está pendiente de implementación y evaluación.

## Controles implementados

- Cálculos desde registros identificados, estado de preparación y procedencia.
- Ausentes como null y resultados incompletos explícitos.
- Sin conversiones automáticas de ingredientes, unidades o pesos crudos/cocinados.
- Restricciones: alergias/intolerancias con códigos del contrato, dieta vegetariana/vegana y exclusión por food_id. Tipos no soportados se rechazan.
- Alérgenos inherentes conocidos; productos compuestos ambiguos pendientes de etiqueta. No se certifica ausencia de trazas ni contaminación cruzada.
- Ajustar kcal no permite relajar restricciones; el objetivo lo proporciona el usuario.
- Claves fuera de Git y ninguna aritmética delegada al LLM.

## Controles pendientes

- System prompt personalizado y justificación final en README.
- Detección clínica probada con casos positivos y negativos.
- Resistencia a instrucciones maliciosas dentro de documentos.
- Citas respaldadas por evidencia realmente recuperada.
- Memoria por sesión, corrección/olvido y aislamiento entre usuarios.
- Límites de rondas, timeout, reintentos y errores de cuota.

Los ejemplos solo contienen perfiles sintéticos; no se almacenan datos personales reales.
