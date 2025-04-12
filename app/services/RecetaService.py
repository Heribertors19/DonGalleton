from app.models import Receta, IngredienteReceta
from app import db

class RecetaService:
    @staticmethod
    def crearReceta(nombre, galletasProducidas, pesoIndividualGalleta, imagen, instrucciones):
     nuevaReceta = Receta(
     nombre=nombre,
     galletasProducidas=galletasProducidas,
     pesoIndividualGalleta=pesoIndividualGalleta,
     imagen=imagen,  # Guardar la ruta de la imagen
     instrucciones=instrucciones
     )
    
     db.session.add(nuevaReceta)
     db.session.commit()  # Guardamos primero la receta para obtener su I 
     return nuevaReceta

    @staticmethod
    def obtenerRecetaPorNombre(nombre):
     return Receta.query.filter_by(nombre=nombre).first()

