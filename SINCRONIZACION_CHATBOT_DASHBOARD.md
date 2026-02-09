# Sincronización de Datos: Chatbot vs Dashboard

## Problema Identificado

Los datos mostrados por el chatbot AI y el tablero principal estaban desincronizados debido a diferencias en la lógica de cálculo del OEE y otros KPIs.

## Análisis de Diferencias

### 1. **Tiempo "Sin Asignar" no se incluía en el chatbot**

**Dashboard (`views.py` líneas 1083-1088):**
```python
# Sumar el tiempo sin asignar a los acumuladores
h_unassigned_std = unassigned_std / 60.0
h_unassigned_prod = unassigned_time / 60.0

total_horas_std += h_unassigned_std
total_horas_prod += h_unassigned_prod
```

**Chatbot (`ai_logic.py` - ANTES):**
- No consideraba el tiempo de trabajo "sin asignar" (máquinas inactivas o sin configurar)
- Esto causaba que los totales globales fueran menores que en el dashboard

### 2. **Cálculo del OEE Global**

Ambos sistemas usan la misma fórmula:
```python
OEE = (Horas_Estándar / Horas_Disponibles) * 100
```

Pero el chatbot no sumaba el tiempo "sin asignar" a las horas estándar y productivas.

## Cambios Implementados

### 1. **Detección de Tiempo "Sin Asignar"** (líneas 110-117)

```python
unassigned_std_mins = 0.0
unassigned_prod_mins = 0.0

# Obtener IDs de máquinas inactivas
maquinas_inactivas_ids = set()
for conf in active_configs:
    if not conf.activa:
        maquinas_inactivas_ids.add(conf.id_maquina)
```

### 2. **Clasificación de Registros** (líneas 133-154)

```python
# Detectar si es "Sin Asignar" (máquina vacía o inactiva)
is_unassigned = (not mid or mid in maquinas_inactivas_ids)
if mid == 'MAC40':  # NLX siempre se considera asignada
    is_unassigned = False

if is_valid_prod:
    if is_mat:
        # Matricería: estándar = real
        if is_unassigned:
            unassigned_std_mins += dur
            unassigned_prod_mins += dur
        else:
            total_std_mins += dur
            total_prod_mins += dur
    else:
        # Producción normal: usar estándar del ERP
        if is_unassigned:
            unassigned_std_mins += std
            unassigned_prod_mins += dur
        else:
            total_std_mins += std
            total_prod_mins += dur
```

### 3. **Suma de Totales Globales** (líneas 157-162)

```python
# Sumar el tiempo sin asignar a los totales (sincronizado con dashboard líneas 1083-1088)
h_unassigned_std = unassigned_std_mins / 60.0
h_unassigned_prod = unassigned_prod_mins / 60.0

h_prod = (total_prod_mins / 60.0) + h_unassigned_prod
h_std = (total_std_mins / 60.0) + h_unassigned_std
```

### 4. **Mejora en el Reporte** (líneas 173-175)

Agregamos más detalles al reporte del chatbot:
```python
resp += f"• <b>Horas Estándar:</b> {h_std:.2f} hs<br>"
resp += f"• <b>Horas Productivas:</b> {h_prod:.2f} hs<br>"
resp += f"• <b>Horas Disponibles:</b> {total_horas_disp:.2f} hs<br><br>"
```

## Resultado

Ahora el chatbot calcula los KPIs de la misma manera que el dashboard:

- ✅ **OEE Global**: Sincronizado
- ✅ **Disponibilidad**: Sincronizado
- ✅ **Rendimiento**: Sincronizado
- ✅ **Tiempo Sin Asignar**: Incluido en totales
- ✅ **Lógica de Matricería**: Idéntica
- ✅ **Exclusión de Descansos**: Idéntica

## Verificación

Para verificar que los datos coinciden:

1. Abrir el dashboard principal
2. Anotar los valores de OEE, Disponibilidad y Rendimiento
3. Preguntar al chatbot: "¿Cómo va el día hoy?"
4. Comparar los valores - deberían ser idénticos

## Notas Técnicas

- La lógica de "matricería" (tiempo estándar = tiempo real) se mantiene igual en ambos sistemas
- Los descansos se excluyen correctamente de la producción válida
- La máquina MAC40 (NLX) siempre se considera asignada, incluso si no tiene configuración
