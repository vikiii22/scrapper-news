## Orquestación del nuevo flujo de trabajo

### 1. Planificación
- Entra en modo planificación para CUALQUIER tarea no trivial (mas de tres pasos o decisiones arquitectonicas)
- Si algo sale mal, para y vuelve a planificar de inmediato, no sigas forzando
- Usa el modo planificacion para los pasos de verificación, no solo para la construcción del código
-  Escribe especificaciones detalladas por adelantado para reducir la ambigüedad

### 2. Estrategia de subagentes
- Usa Subagentes con frecuencia para mantener limpia la ventana del contexto principal
- Delega la investigación, exploración y análisis paralelo a subagentes
- Para problemas complejos, dedica más capacidad de computo mediante subagentes
- Una tarea por subagente para una ejecución focalizada

### 3. Bucle de automejora
- Tras cualquier corrección del usuario: actualiza `tasks/lessons.md` con el patrón
- Escribe reglas para ti mismo que eviten el mismo error en el futuro
- Itera implacablemente sobre estas lecciones hasta que la tasa de errores disminuya
- Revisa las lecciones al incio de la sesión para el proyecto correspondiente

### 4. Verificación antes de finalizar
- Nunca marques una tarea como completada sin demostrarq que funciona
- Compara la diferencia (diff) de comportamiento entre la rama principal y tus cambios cuando sea relevante
- Preguntate: ¿Aprobaría esto un ingeniero senior (Staff Engineer)?
- Ejecuta tests, comprueba logs, y demuestra la correccion del codigo

### 5. Exige elegancia (Equilibrado)
- Para cambios no triviales: haz una pausa y pregunta "¿Hay una forma más elegante?"
- Si un arreglo parece un parche (hacky): "Sabiendo todo lo que sé ahora, implementa la solución elegante"
- Omite esto para arreglos simples y obvios; no hagas sobreingieneria
- Cuestiona tu propio trabajo antes de presentarlo

### 6. Corrección de errores autonoma
- Cuando recibas un informe de error: simplemente arreglalo. No pidas que te lleven de la mano.
- Identifica logs, errores o tests que falla y luego resuelvelos
- Cero necesidad de cambio de contexto por parte del usuario
- Ve a arreglar los tests de CI que fallan sin que te digan como

## Gestion de tareas

1. **Planificar primero**: Escribe el plan en `tasks/todo.md` con elementos verificables
2. **Verificar plan**: Confirma antes de comenzar la implementacion
3. **Seguir el progreso**: Marca los elementos como completados a medida que avances
4. **Explicar cambios**: Resumen de alto nivel en cada caso
5. **Documentar resultados**: Añade una sección de revisión a `tasks/todo.md`
6. **Captura Lecciones**: Actualiza `tasks/lessons.md` despues de las correcciones

## Principios fundamentales
- **Simplicidad primero**: Haz que cada cambio sea lo mas simple posible. Afecta al minimo codigo necesario.
- **Sin pereza**: Encuentra las causa raiz. Nada de arreglos temporales. Estandares de desarrollo senior.
- **Impacto minimo**: Los cambios solo deben tocar lo necesario. Evita introducir errores.

## Cambios a realizar
- **Agregar mas información**: Desde la web `https://www.eduardolosilla.es/` podemos obtener que apuestas está haciendo la gente, en %jugados, tenemos %LAE que no se en que se basa y tenemos %probables, que es, según los datos actuales de la liga, la probabilidad de que gane ese equipo. La idea es juntarlo con nuestros datos para hacer predicciones mas precisas. y que si por ejemplo tenemos la casuistica de: Local (1)
36.1%
Empate (X)
26.3%
Visitante (2)
37.6%
Que quede más claro quien puede ser un ganador, o si por lo contrario, lo más razonable es un empate.