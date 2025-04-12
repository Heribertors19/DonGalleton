# Diccionarios de conversión (deberían estar al inicio del archivo)
conversiones_sólidos = {
    'gramo': 0.001,          # 1 kg = 1000 g
    'kilogramo': 1,          # 1 kg = 1 kg
    'costal': 1,             # Definir costal como 1 kg (ajustar según necesidad)
    'taza': 0.25,            # 1 kg = 4 tazas (ajustar según unidad)
    'cucharada': 0.01        # 1 kg = 100 cucharadas (ajustar)
}

conversiones_líquidos = {
    'mililitro': 0.001,      # 1 L = 1000 mL
    'litro': 1,              # 1 L = 1 L
    'galon': 3.78541,        # 1 galón = 3.78541 L
    'taza': 0.25,            # 1 L = 4 tazas
    'cucharada': 0.015       # 1 L ≈ 67 cucharadas
}

def determinar_tipo_por_presentacion(presentacion):
    """Determina si el insumo es sólido, líquido o por unidad"""
    presentacion_lower = presentacion.lower()
    
    # Sólidos (masa)
    solidos_keywords = ['kg', 'kilo', 'gramo', 'g ', 'gr ', 'costal', 'bolsa', 'taza', 'cucharada']
    if any(keyword in presentacion_lower for keyword in solidos_keywords):
        return 'solido'
    
    # Líquidos (volumen)
    liquidos_keywords = ['lt', 'litro', 'ml', 'mililitro', 'galon', 'galón']
    if any(keyword in presentacion_lower for keyword in liquidos_keywords):
        return 'liquido'
    
    # Por defecto asumimos que es por unidades
    return 'unidad'

def convertir_a_unidad_base(cantidad, unidad_origen, presentacion):
    """Convierte la cantidad a la unidad base según el tipo de insumo"""
    tipo = determinar_tipo_por_presentacion(presentacion)
    
    if tipo == 'solido':
        factor = conversiones_sólidos.get(unidad_origen.lower(), 1)
        return cantidad * factor, 'kilogramo'
    elif tipo == 'liquido':
        factor = conversiones_líquidos.get(unidad_origen.lower(), 1)
        return cantidad * factor, 'litro'
    else:
        return cantidad, 'unidad'