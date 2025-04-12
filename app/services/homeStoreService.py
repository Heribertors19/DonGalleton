import datetime
import random

from flask import json
from app import db
from sqlalchemy.sql import text
import logging

logger = logging.getLogger(__name__)

class HomeStoreService:
    @staticmethod
    def get_all_galletas():
        try:
            query = text("""
                SELECT id, nombre_galleta as nombre, precio_unitario as precio,
                       imagen, peso_por_galleta as peso, cantidad_disponible as stock,
                       cantidad_disponible > 0 as disponible, ingredientes_principales as ingredientes
                FROM vista_catalogo_galletas
                ORDER BY nombre_galleta;
            """)
            result = db.session.execute(query)
            return [dict(row._mapping) for row in result]
        except Exception as e:
            logger.error(f"Error al obtener galletas: {str(e)}", exc_info=True)
            return []

    @staticmethod
    def get_galletas_destacadas(limit=3):
        try:
            query = text(f"""
                SELECT id, nombre_galleta as nombre, precio_unitario as precio,
                       imagen, cantidad_disponible as stock
                FROM vista_catalogo_galletas
                ORDER BY cantidad_disponible DESC
                LIMIT {limit};
            """)
            result = db.session.execute(query)
            return [dict(row._mapping) for row in result]
        except Exception as e:
            logger.error(f"Error al obtener galletas destacadas: {str(e)}", exc_info=True)
            return []

    @staticmethod
    def registrar_pedido(datos_pedido):
        """
        Registra un nuevo pedido con validación reforzada
        """
        try:
            # Validación de campos requeridos
            required_fields = ['fechaEntrega', 'idTipoGalleta', 'cantidad']
            if not all(field in datos_pedido for field in required_fields):
                return {'success': False, 'message': 'Faltan campos requeridos en el pedido'}

            # Validación de tipos
            try:
                id_galleta = int(datos_pedido['idTipoGalleta'])
                cantidad = int(datos_pedido['cantidad'])
                
                if id_galleta <= 0 or cantidad <= 0:
                    return {'success': False, 'message': 'ID y cantidad deben ser valores positivos'}
            except (ValueError, TypeError):
                return {'success': False, 'message': 'ID y cantidad deben ser números enteros'}

            # Llamada al procedimiento almacenado
            query = text("""
                CALL RegistrarPedido(
                    'jdsalagu',
                    :fecha_entrega,
                    :id_tipo_galleta,
                    :cantidad,
                    'online',
                    1,
                    @id_pedido,
                    @numero_pedido,
                    @mensaje
                )
            """)
            
            params = {
                'fecha_entrega': datos_pedido['fechaEntrega'],
                'id_tipo_galleta': datos_pedido['idTipoGalleta'],
                'cantidad': datos_pedido['cantidad']
            }

            db.session.execute(query, params)
            
            # Obtener resultados
            result = db.session.execute(text("SELECT @id_pedido, @numero_pedido, @mensaje"))
            row = result.fetchone()

            if row and row[0] > 0:  # Éxito
                db.session.commit()
                return {
                    'success': True,
                    'id_pedido': row[0],
                    'numero_pedido': row[1],
                    'message': row[2]
                }
            else:  # Error
                db.session.rollback()
                return {
                    'success': False,
                    'message': row[2] if row else 'Error desconocido en el procedimiento'
                }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error al registrar pedido: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f"Error en base de datos: {str(e)}"
            }