from app import db
from sqlalchemy import text
from flask import current_app

class StoreService:
    
    @staticmethod
    def get_all_galletas(filtros=None):
        """
        Obtiene todas las galletas del catálogo
        """
        try:
            query = text("""
                SELECT 
                    id,
                    nombre_galleta AS nombre,
                    precio_unitario AS precio,
                    imagen,
                    cantidad_disponible AS stock,
                    peso_por_galleta AS peso,
                    produccion_por_lote AS lote
                FROM vista_catalogo_galletas
                ORDER BY nombre_galleta
            """)
            
            result = db.session.execute(query).fetchall()
            
            galletas = []
            for row in result:
                galletas.append({
                    'id': row.id,
                    'nombre': row.nombre,
                    'precio': float(row.precio),
                    'imagen': row.imagen,
                    'stock': row.stock,
                    'peso': row.peso,
                    'lote': row.lote,
                    'disponible': row.stock > 0
                })
            
            return galletas
            
        except Exception as e:
            current_app.logger.error(f"Error en StoreService.get_all_galletas: {str(e)}", exc_info=True)
            return []

    @staticmethod
    def get_galletas_destacadas():
        """
        Obtiene las galletas destacadas (puedes modificar el criterio)
        """
        try:
            query = text("""
                SELECT 
                    id,
                    nombre_galleta AS nombre,
                    precio_unitario AS precio,
                    imagen,
                    cantidad_disponible AS stock,
                    peso_por_galleta AS peso,
                    produccion_por_lote AS lote
                FROM vista_catalogo_galletas
                ORDER BY stock DESC
                LIMIT 3
            """)
            
            result = db.session.execute(query).fetchall()
            
            destacadas = []
            for row in result:
                destacadas.append({
                    'id': row.id,
                    'nombre': row.nombre,
                    'precio': float(row.precio),
                    'imagen': row.imagen,
                    'stock': row.stock,
                    'peso': row.peso,
                    'lote': row.lote,
                    'disponible': row.stock > 0
                })
            
            return destacadas
            
        except Exception as e:
            current_app.logger.error(f"Error en StoreService.get_galletas_destacadas: {str(e)}", exc_info=True)
            return []