from app.models import IngredienteReceta, Insumo
from app import db

class IngredienteService:
    @staticmethod
    def obtenerIngredientes():
        # Consulta que obtiene todos los ingredientes y su nombre desde la tabla Insumos
        ingredientes = db.session.query(IngredienteReceta, Insumo).join(Insumo, IngredienteReceta.idInsumo == Insumo.idInsumo).all()
        return [{"idInsumo": i[0].idInsumo, "nombre": i[1].nombre} for i in ingredientes]
    
    @staticmethod
    def obtenerIngredientesPorNombre(nombre):
        # Consulta que busca ingredientes por nombre desde la tabla Insumos
        ingredientes = db.session.query(IngredienteReceta, Insumo).join(Insumo, IngredienteReceta.idInsumo == Insumo.idInsumo).filter(Insumo.nombre.ilike(f'%{nombre}%')).all()
        return [{"idInsumo": i[0].idInsumo, "nombre": i[1].nombre} for i in ingredientes]
