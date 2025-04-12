from datetime import datetime
from venv import logger
from flask import current_app
from app import db
from sqlalchemy import text
import json

class CompraService:
    
    @staticmethod
    def get_compras(search=None):
        """
        Obtiene el listado de compras con opción de búsqueda
        """
        try:
            query = text("""
                SELECT 
                    c.idCompra as id,
                    CONCAT('CMP-', c.idCompra) as numero_compra,
                    p.nombre as proveedor,
                    DATE_FORMAT(c.fechaCompra, '%d/%m/%Y') as fecha,
                    CAST(c.costoTotal AS DECIMAL(10,2)) as total,
                    COUNT(dc.idDetalleCompra) as detalles
                FROM compra c
                JOIN proveedor p ON c.idProveedor = p.idProveedor
                LEFT JOIN detallecompra dc ON c.idCompra = dc.idCompra
                GROUP BY c.idCompra
                ORDER BY 1 DESC
            """)
            
            result = db.session.execute(query, {'search': search})
            compras = []
            for row in result:
                compras.append({
                    'id': row.id,
                    'numero_compra': row.numero_compra,
                    'proveedor': row.proveedor,
                    'fecha': row.fecha if row.fecha else 'Sin fecha',
                    'total': row.total,
                    'detalles': row.detalles
                })
            return compras
            
        except Exception as e:
            logger.error(f"Error al obtener compras: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def realizar_compra(id_proveedor, fecha_compra, insumos):
        """
        Versión mejorada con manejo robusto de respuestas
        """
        response_template = {
            'success': False,
            'message': 'Error desconocido',
            'id_compra': None,
            'total': 0.0
        }

        try:
            # Validación básica
            if not insumos or len(insumos) == 0:
                raise ValueError("Debe incluir al menos un insumo")

            # Preparar los datos de insumos
            insumos_data = []
            for insumo in insumos:
                if not all(key in insumo for key in ['id', 'cantidad', 'precio']):
                    raise ValueError("Datos de insumo incompletos")
                
                insumo_data = {
                    "idInsumo": int(insumo['id']),
                    "cantidad": int(insumo['cantidad']),
                    "precioUnitario": float(insumo['precio'])
                }
                
                if 'fechaCaducidad' in insumo:
                    insumo_data["fechaCaducidad"] = insumo['fechaCaducidad']
                
                insumos_data.append(insumo_data)
            
            # Calcular el costo total
            costo_total = sum(item['cantidad'] * item['precioUnitario'] for item in insumos_data)
            
            # Usar conexión directa
            conn = db.engine.raw_connection()
            try:
                cursor = conn.cursor()
                
                # Llamar al procedimiento
                cursor.callproc('RealizarCompra', [
                    int(id_proveedor),
                    fecha_compra,
                    float(costo_total),
                    json.dumps(insumos_data),
                    0,  # placeholder para p_idCompra (OUT)
                    ''   # placeholder para p_mensaje (OUT)
                ])
                
                # Obtener los parámetros OUT
                cursor.execute("SELECT @_RealizarCompra_4, @_RealizarCompra_5")
                result = cursor.fetchone()
                
                if result and result[0]:  # Si hay resultado y id_compra no es NULL
                    response_template.update({
                        'success': True,
                        'id_compra': result[0],
                        'total': costo_total,
                        'message': result[1] or 'Compra realizada con éxito'
                    })
                else:
                    error_msg = result[1] if result else "Error al registrar la compra"
                    response_template['message'] = error_msg
                
                conn.commit()
                
            except Exception as e:
                conn.rollback()
                current_app.logger.error(f"Error en realizar_compra: {str(e)}", exc_info=True)
                response_template['message'] = f"Error en el servidor: {str(e)}"
            finally:
                if 'cursor' in locals():
                    cursor.close()
                if 'conn' in locals():
                    conn.close()

        except ValueError as ve:
            response_template['message'] = f"Error de validación: {str(ve)}"
        except Exception as e:
            response_template['message'] = f"Error inesperado: {str(e)}"

        # Asegurar que siempre devolvemos un objeto válido
        return response_template    
    @staticmethod
    def get_detalle_compra(id_compra):
        """
        Obtiene los detalles de una compra específica con todos los campos reales
        """
        try:
            # Obtener información básica de la compra
            query_compra = text("""
                SELECT 
                    c.idCompra as id,
                    CONCAT('CMP-', c.idCompra) as numero_compra,
                    p.nombre as proveedor,
                    DATE_FORMAT(c.fechaCompra, '%d/%m/%Y') as fecha,
                    CAST(c.costoTotal AS DECIMAL(10,2)) as total
                FROM compra c
                JOIN proveedor p ON c.idProveedor = p.idProveedor
                WHERE c.idCompra = :id_compra
            """)
            
            compra = db.session.execute(query_compra, {'id_compra': id_compra}).fetchone()
            
            if not compra:
                return None
            
            # Obtener detalles de la compra con todos los campos
            query_detalles = text("""
                SELECT 
                    i.nombre as nombre,
                    dc.cantidad as cantidad,
                    dc.cantidadDisponible as cantidad_disponible,
                    dc.precioUnitario as precio,
                    dc.fechaCaducidadInsumo as fecha_caducidad
                FROM detallecompra dc
                JOIN insumo i ON dc.idInsumo = i.idInsumo
                WHERE dc.idCompra = :id_compra
            """)
            
            detalles = db.session.execute(query_detalles, {'id_compra': id_compra}).fetchall()
            
            return {
                'compra': {
                    'id': compra.id,
                    'numero_compra': compra.numero_compra,
                    'proveedor': compra.proveedor,
                    'fecha': compra.fecha,
                    'total': float(compra.total) if compra.total else 0.0
                },
                'detalles': [{
                    'nombre': detalle.nombre,
                    'cantidad': detalle.cantidad,
                    'cantidad_disponible': detalle.cantidad_disponible,
                    'precio': float(detalle.precio) if detalle.precio else 0.0,
                    'fecha_caducidad': detalle.fecha_caducidad.strftime('%d/%m/%Y') if detalle.fecha_caducidad else None
                } for detalle in detalles]
            }
            
        except Exception as e:
            logger.error(f"Error al obtener detalles de compra: {str(e)}", exc_info=True)
            raise
            
    @staticmethod
    def get_proveedores():
        """
        Obtiene proveedores activos
        """
        try:
            result = db.session.execute(text("""
                SELECT idProveedor, nombre 
                FROM proveedor 
                WHERE estatus = 1
                ORDER BY nombre
            """))
            
            return [{
                'id': row.idProveedor,
                'nombre': row.nombre
            } for row in result]
            
        except Exception as e:
            logger.error(f"Error al obtener proveedores: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def get_insumos():
        """
        Obtiene insumos activos con información de proveedor
        """
        try:
            query = text("""
                SELECT 
                    i.idInsumo, 
                    i.nombre AS nombre_insumo, 
                    pi.nombre AS nombre_presentacion, 
                    i.precioActual,
                    i.idProveedor AS id_proveedor,
                    p.nombre AS nombre_proveedor
                FROM insumo i
                JOIN presentacioninsumo pi ON i.idPresentacion = pi.idPresentacionInsumo
                JOIN proveedor p ON i.idProveedor = p.idProveedor
                WHERE i.estatus = 1
                ORDER BY i.nombre
            """)
            result = db.session.execute(query)
            
            insumos = []
            for row in result:
                insumo = {
                    'id': row.idInsumo,
                    'nombre': row.nombre_insumo,
                    'presentacion': row.nombre_presentacion,
                    'precio': float(row.precioActual) if row.precioActual else 0.0,
                    'idProveedor': row.id_proveedor,
                    'nombreProveedor': row.nombre_proveedor
                }
                insumos.append(insumo)
            
            return insumos
        except Exception as e:
            current_app.logger.error(f"Error al obtener insumos: {str(e)}", exc_info=True)
            raise