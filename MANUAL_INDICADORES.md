# Manual Técnico de Indicadores - Tablero de Control ABBAMAT

Este documento detalla la lógica de cálculo de todos los indicadores (KPIs) y tiempos mostrados en el Dashboard, así como su equivalencia con los datos del ERP.

---

## 1. Tiempos Principales (Relacionados con el ERP)

### 🟢 Tiempo Planificado
*   **Definición**: Es la capacidad teórica total de trabajo de la planta.
*   **Cálculo**: Suma de las horas de turno configuradas para cada máquina marcada como **Activa**. 
    *   *Ejemplo*: Si 10 máquinas tienen turno de 07 a 16 hs (9 hs), el Tiempo Planificado será 90 horas.
    *   **Equivalencia ERP**: Se relaciona con la columna verde (**Horas Máquina Disponibles**), pero el Dashboard considera el turno completo de todas las máquinas de la planta, no solo de las que tienen órdenes.

### 🟠 Tiempo Real
*   **Definición**: Es el tiempo de ocupación física de las máquinas.
*   **Cálculo**: Suma de todos los minutos de producción y paradas registrados en la base de datos SQL Server (`V_TMAN`).
*   **Equivalencia ERP**: Coincide con la columna naranja (**Tiempo Producción**). Incluye los registros "Sin Asignar" en el total global.

### 🟡 Tiempo Estándar (Ideal)
*   **Definición**: Es el tiempo que "debería" haber tomado la producción si se cumplieran los tiempos de cotización al 100%.
*   **Cálculo**: Suma de `(Tiempo Cotizado × Cantidad Producida)` para cada registro.
*   **Equivalencia ERP**: Coincide exactamente con la columna amarilla (**Tiempo Std.**).

### 🔴 Tiempo Perdido
*   **Definición**: Representa las horas de turno donde la máquina estuvo "en silencio" (sin registros).
*   **Cálculo**: Se calcula máquina por máquina: `Máximo de (0, Tiempo Planificado - Tiempo Real)`. 
    *   Si una máquina tiene 9 hs de turno y solo produjo 4 hs, se suman **5 hs** de pérdida.
    *   Si produjo 10 hs (más que el turno), se suman **0 hs** de pérdida (no resta la pérdida de otras).
*   **Equivalencia ERP**: No existe como celda única en el ERP, pero es la suma de todas las diferencias positivas entre la columna Verde y la Naranja.

---

## 2. Indicadores de Eficiencia (OEE)

### 📈 Rendimiento (Productividad)
*   **Cálculo**: `(Tiempo Estándar / Tiempo Real) × 100`.
*   **Significado**: Mide qué tan rápido se trabajó mientras las máquinas estaban encendidas. Un 110% significa que se produjo más rápido que lo cotizado. Un 80% significa que hubo lentitud.

### ⏱️ Disponibilidad (Smart Availability)
*   **Fórmula**: `(Tiempo Real Operativo / Tiempo de Turno Transcurrido) × 100`
*   **Lógica Inteligente**: A diferencia de otros indicadores, este tablero se adapta a la hora actual para no castigar el inicio del turno.
    *   **Hoy (Tiempo Real)**: El denominador es el tiempo transcurrido desde las **07:00 AM** hasta el momento de la consulta.
    *   **Histórico**: Se utiliza el turno completo fijo (9 horas).
*   **Significado**: Mide qué tan bien estamos aprovechando el tiempo del turno. Una meta cercana al 100% indica que no hubo baches de tiempo sin reportes desde que arrancó el día.
*   **Ejemplo**: A las 10:00 AM han pasado 180 min. Si el operario trabajó 150 min, la disponibilidad es del 83.3%.

### 🛡️ Calidad
*   **Cálculo**: `((Cantidad Real - Cantidad Rechazada) / Cantidad Real) × 100`.
*   **Significado**: Mide el porcentaje de piezas buenas. Actualmente, el sistema asume 100% hasta que se implemente la carga de rechazos.

### 🏆 OEE Global
*   **Cálculo**: `(Disponibilidad × Rendimiento × Calidad) / 10000`.
*   **Significado**: El indicador maestro. Refleja la eficiencia total de la planta considerando tiempo, velocidad y calidad.

---

## 3. Funciones Especiales

### 🔢 Formato Decimal vs. Reloj
*   **Reloj**: Muestra los tiempos de forma humana (ej: `10 hs 30 min`). Útil para lectura rápida.
*   **Decimal**: Muestra los valores idénticos al ERP (ej: `10.50`). Útil para auditoría y cruce de datos con Excel.

### ❓ Sin Asignar
*   **Definición**: Registros de producción que llegaron desde SQL Server con el campo de máquina vacío.
*   **Impacto**: Se muestran en una tarjeta aparte para no "ensuciar" las estadísticas de las máquinas individuales, pero se **suman** al total de la planta para que el Tiempo Real y la Cantidad coincidan con los totales del ERP.

---

## 4. Guía Visual del Layout (Tarjetas)

El Dashboard principal está organizado en bloques lógicos para facilitar la lectura:

### 🔵 Panel Superior: OEE Global
*   Es el resumen ejecutivo. Muestra el promedio de toda la planta mediante velocímetros (Gauges).
*   **OEE Global**: El porcentaje grande en el título es la eficiencia combinada. Si está arriba del 85%, la planta está en niveles de "Clase Mundial".

### 🟢 Tarjeta: Disponibilidad (Tiempos)
*   **Enfoque**: ¿Cuánto tiempo estuvieron las máquinas ocupadas respecto al turno?
*   **Gráfico**: Compara la barra de **Planificado** (100%) contra lo que realmente se trabajó (**Real**) y el tiempo que las máquinas estuvieron paradas (**Paradas**).
*   **Uso**: Si la barra de "Paradas" es alta, hay un problema de falta de carga de trabajo o muchas máquinas rotas.

### 🌿 Tarjeta: Rendimiento (Cantidades)
*   **Enfoque**: ¿Qué tan rápido se produjo mientras la máquina estaba andando?
*   **Cant. Planificada**: Es la cantidad teórica que "debería" haberse hecho en las horas de producción real.
*   **Gráfico**: Compara lo que se esperaba producir (**Cant Planif**) contra lo que realmente se reportó (**Cant Real**).
*   **Uso**: Si la barra de "Cant Real" es más alta que la "Cant Planif", tus operarios están superando los tiempos estándar de cotización.

### 🟠 Tarjeta: Calidad
*   **Enfoque**: ¿Cuántas piezas salieron bien?
*   **Gráfico**: Compara piezas **Aceptadas** contra **Rechazadas**.
*   **Interpretación**: Una barra de "Rechazadas" visible es una alerta roja de desperdicio de material.

### 🔘 Tarjeta: Sin Asignar (Gris)
*   **Enfoque**: Transparencia de datos.
*   **Contenido**: Muestra el total de producción que llegó del ERP pero no tiene un ID de máquina válido o pertenece a una máquina que marcaste como "Inactiva".
*   **Importante**: Estos valores ya están sumados en las tarjetas de arriba para que el total de planta sea real. Esta tarjeta está solo para que sepas por qué a veces la suma de "máquina por máquina" no da el total general (porque falta este remanente).

---

*Este manual se actualizará a medida que se incorporen nuevas funcionalidades.*
