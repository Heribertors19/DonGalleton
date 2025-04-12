import re
import os
import unicodedata
from flask import current_app
from app import create_app
from app.validaciones import determinar_tipo_por_presentacion, conversiones_líquidos, convertir_a_unidad_base
app = create_app()



# Definir la función para normalizar nombres
def normalizar_nombre(nombre):
    # Tomar solo la primera palabra antes del primer guion bajo
    nombre = nombre.split('_')[0]  # Esto extrae la primera palabra
    # Convertir a minúsculas (por si acaso)
    nombre = nombre.lower()
    # Eliminar caracteres especiales (excepto letras, números y espacios)
    nombre = re.sub(r'[^a-z0-9\s]', '', nombre)
    return nombre
def quitar_acentos(texto):
    return unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8')
# Definir la función para formatear nombres
def formatear_nombre(nombre):
    nombre = nombre.replace('_', ' ')  # Reemplaza guiones bajos por espacios
    nombre = nombre.title()  # Convierte la primera letra de cada palabra en mayúscula
    return nombre
def get_insumo_image(nombre_insumo):
    """
    Obtiene el nombre del archivo de imagen para un insumo basado en la primera palabra del nombre.
    Ejemplo: 'leche_entera' -> busca 'leche.svg'
    
    Args:
        nombre_insumo (str): Nombre del insumo desde la base de datos (ej. 'azucar_refinada')
    
    Returns:
        str: Nombre del archivo de imagen (ej. 'azucar.svg') o 'default_2.svg' si no se encuentra
    """
    # Reemplazar guiones bajos por espacios por si vienen así
    nombre_insumo = nombre_insumo.replace('_', ' ')
    
    # Extraer la primera palabra
    palabra_base = nombre_insumo.split(' ')[0].lower()
    
    # Quitar acentos
    palabra_base = quitar_acentos(palabra_base)

    # Lista de extensiones de imagen soportadas (prioridad SVG)
    extensiones = ['.svg', '.png', '.jpg', '.jpeg']
    
    # Buscar en el directorio de imágenes
    for ext in extensiones:
        nombre_archivo = f"{palabra_base}{ext}"
        ruta_imagen = os.path.join(current_app.static_folder, 'img', nombre_archivo)
        
        if os.path.exists(ruta_imagen):
            return nombre_archivo  # Ruta relativa desde static

    # Imagen por defecto si no encuentra coincidencias
    return "default_2.svg"
# Registrar las funciones como filtros de Jinja2
app.jinja_env.filters['normalizar_nombre'] = normalizar_nombre
app.jinja_env.filters['formatear_nombre'] = formatear_nombre


app.jinja_env.globals.update(normalizar_nombre=normalizar_nombre, formatear_nombre=formatear_nombre)
app.jinja_env.globals.update(get_insumo_image=get_insumo_image)
app.jinja_env.globals.update(
        determinar_tipo_por_presentacion=determinar_tipo_por_presentacion,
        convertir_cantidad=convertir_a_unidad_base
    )
if __name__ == "__main__":
    app.run(debug=True)