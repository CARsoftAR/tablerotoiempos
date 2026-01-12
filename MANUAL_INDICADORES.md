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

### ⏱️ Disponibilidad
*   **Cálculo**: `(Tiempo Real / Tiempo Planificado) × 100`.
*   **Significado**: Mide qué porcentaje del turno estuviste realmente produciendo. Una baja disponibilidad indica falta de trabajo cargado o máquinas paradas por rotura/falta de personal.

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

*Este manual se actualizará a medida que se incorporen nuevas funcionalidades.*
