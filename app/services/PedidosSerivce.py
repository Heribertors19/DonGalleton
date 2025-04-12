from app import db
from sqlalchemy import text
from datetime import datetime

class PedidosService:
    @staticmethod
    def get_all_pedidos(filtro_estado=None, search_query=None):
        # Consulta base
        query = """
           SELECT 
                p.idPedido,
                p.numeroPedido AS numero_pedido,
                p.fechaCreacion AS fecha_creacion,
                p.fechaEntrega AS fecha_entrega,
                p.estatus AS estado,
                CONCAT(u.nombre, ' ', u.apellidoPaterno, ' ', u.apellidoMaterno) AS cliente,
                u.email AS contacto,
                v.precioTotal AS total,
                DATEDIFF(p.fechaEntrega, CURDATE()) AS dias_para_entrega
            FROM 
                pedido p
            LEFT JOIN 
                venta v ON p.idVenta = v.idVenta
            LEFT JOIN 
                usuario u ON p.nombreUsuario = u.nombreUsuario
            WHERE 1=1
        """
        
        # Parámetros para la consulta
        params = {}
        
        # Aplicar filtros si existen
        if filtro_estado and filtro_estado.lower() != 'all':
            query += " AND p.estatus = :estado"
            params['estado'] = filtro_estado
            
        if search_query:
            query += " AND (p.numeroPedido LIKE :search OR u.nombre LIKE :search OR CONCAT(u.nombre, ' ', u.apellidoPaterno, ' ', u.apellidoMaterno) LIKE :search)"
            params['search'] = f'%{search_query}%'
        
        # Ordenamiento
        query += " ORDER BY p.fechaCreacion DESC"
        
        try:
            result = db.session.execute(text(query), params)
            
            pedidos = []
            for row in result:
                pedido = {
                    'id': row.idPedido,
                    'numero_pedido': row.numero_pedido,
                    'fecha_creacion': row.fecha_creacion.strftime('%Y-%m-%d %H:%M:%S') if row.fecha_creacion else '',
                    'fecha_entrega': row.fecha_entrega.strftime('%Y-%m-%d') if row.fecha_entrega else '',
                    'estado': row.estado if row.estado else 'Sin estado',
                    'cliente': row.cliente if row.cliente else 'Cliente no especificado',
                    'contacto': row.contacto if row.contacto else '',
                    'total': float(row.total) if row.total is not None else 0.0,
                    'dias_para_entrega': row.dias_para_entrega if row.dias_para_entrega is not None else 0
                }
                pedidos.append(pedido)
            
            return pedidos
            
        except Exception as e:
            print(f"Error al obtener pedidos: {str(e)}")
            return []


    @staticmethod
    def get_estado_clase(estado):
        """
        Devuelve clases CSS según el estado del pedido
        """
        if not estado:
            return 'bg-gray-100 text-gray-800'
            
        estado = estado.lower()
        
        clases = {
            'pendiente': 'bg-blue-100 text-blue-800',
            'en proceso': 'bg-yellow-100 text-yellow-800',
            'completado': 'bg-green-100 text-green-800',
            'entregado': 'bg-purple-100 text-purple-800',
            'cancelado': 'bg-gray-100 text-gray-800',
            'atrasado': 'bg-red-100 text-red-800'
        }
        
        return clases.get(estado, 'bg-gray-100 text-gray-800')
    
    @staticmethod
    def actualizar_estado_pedido(pedido_id, nuevo_estado):
        try:
            # Validar los estados permitidos según la tabla pedido (estatus)
            estados_permitidos = ['pendiente', 'en proceso', 'completado', 'entregado', 'cancelado', 'atrasado']
            
            if nuevo_estado.lower() not in estados_permitidos:
                print(f"Estado no permitido: {nuevo_estado}")
                return False

            # Actualizar el estado en la tabla pedido
            query = text("""
                UPDATE pedido 
                SET estatus = :nuevo_estado 
                WHERE idPedido = :pedido_id
            """)
            
            db.session.execute(query, {
                'nuevo_estado': nuevo_estado.lower(),
                'pedido_id': pedido_id
            })
            
            # Si el estado es "entregado", también actualizamos el estado en la tabla venta
            if nuevo_estado.lower() == 'entregado':
                venta_query = text("""
                    UPDATE venta v
                    JOIN pedido p ON v.idVenta = p.idVenta
                    SET v.estado = 'completado'
                    WHERE p.idPedido = :pedido_id
                """)
                db.session.execute(venta_query, {'pedido_id': pedido_id})
            
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Error al actualizar estado del pedido {pedido_id}: {str(e)}")
            return False
    @staticmethod
    def get_pedido_detalle(pedido_id):
        try:
            # Consulta corregida con manejo de valores nulos y sintaxis GROUP_CONCAT correcta
            query = """
                SELECT 
                    p.idPedido,
                    p.numeroPedido AS numero_pedido,
                    p.fechaCreacion AS fecha_creacion,
                    p.fechaEntrega AS fecha_entrega,
                    p.estatus AS estado,
                    u.nombre AS nombreUsuario,
                    u.apellidoPaterno,
                    u.apellidoMaterno,
                    u.email AS emailUsuario,
                    v.idVenta,
                    v.fechaVenta,
                    v.precioTotal,
                    v.estado AS estadoVenta,
                    GROUP_CONCAT(DISTINCT CONCAT(tg.nombre, ' (', dv.cantidad, ' x $', dv.costoActual, ' - ', dv.tiposVentaNombre, 
                                CASE WHEN dv.ventaEquivalenciaPiezas IS NOT NULL 
                                    THEN CONCAT(' - ', dv.ventaEquivalenciaPiezas, ' piezas') 
                                    ELSE '' END, 
                                ')') SEPARATOR '; ') AS detallesProductos,
                    GROUP_CONCAT(DISTINCT tg.nombre SEPARATOR ', ') AS nombresProductos,
                    GROUP_CONCAT(DISTINCT dv.cantidad SEPARATOR ', ') AS cantidadesProductos,
                    GROUP_CONCAT(DISTINCT dv.costoActual SEPARATOR ', ') AS preciosProductos
                FROM 
                    pedido p
                LEFT JOIN 
                    usuario u ON p.nombreUsuario = u.nombreUsuario
                LEFT JOIN 
                    venta v ON p.idVenta = v.idVenta
                LEFT JOIN 
                    detalleventa dv ON v.idVenta = dv.idVenta
                LEFT JOIN 
                    tipogalleta tg ON dv.idTipoGalleta = tg.idTipoGalleta
                WHERE 
                    p.idPedido = :pedido_id
                GROUP BY 
                    p.idPedido, p.numeroPedido, p.fechaCreacion, p.fechaEntrega, p.estatus,
                    u.nombre, u.apellidoPaterno, u.apellidoMaterno, u.email,
                    v.idVenta, v.fechaVenta, v.precioTotal, v.estado
            """
            
            result = db.session.execute(text(query), {'pedido_id': pedido_id}).fetchone()
            
            if not result:
                print(f"No se encontró el pedido con ID: {pedido_id}")
                return None
            
            # Procesar los productos concatenados con manejo de errores
            productos = []
            if result.detallesProductos:
                try:
                    # Separamos por '; ' ya que es el separador definido en la consulta
                    productos_raw = result.detallesProductos.split('; ')
                    for prod in productos_raw:
                        # Ejemplo de formato: "Galleta Chocolate (2 x $15.00 - Venta por caja - 24 piezas)"
                        if '(' in prod and ')' in prod:
                            # Extraer nombre del producto
                            nombre_part = prod.split('(')[0].strip()
                            details_part = prod.split('(')[1].replace(')', '')
                            
                            # Separar los componentes
                            parts = details_part.split(' - ')
                            
                            # Procesar cantidad y precio (primer segmento)
                            cantidad_precio = parts[0].split(' x $')
                            if len(cantidad_precio) == 2:
                                cantidad = int(cantidad_precio[0].strip())
                                precio = float(cantidad_precio[1].strip())
                                
                                # Procesar tipo de venta y piezas (si existen)
                                tipo_venta = parts[1] if len(parts) > 1 else None
                                piezas = parts[2].replace(' piezas', '') if len(parts) > 2 else None
                                
                                productos.append({
                                    'nombre': nombre_part,
                                    'cantidad': cantidad,
                                    'precio_unitario': precio,
                                    'subtotal': cantidad * precio,
                                    'tipo_venta': tipo_venta,
                                    'piezas': piezas
                                })
                except Exception as e:
                    print(f"Error al procesar productos: {str(e)}")
                    productos = []  # Si hay error, devolver lista vacía
            
            # Estructurar los datos del pedido con manejo de valores nulos
            pedido = {
                'idPedido': result.idPedido,
                'numero_pedido': result.numero_pedido,
                'fecha_creacion': result.fecha_creacion.strftime('%Y-%m-%d %H:%M:%S') if result.fecha_creacion else None,
                'fecha_entrega': result.fecha_entrega.strftime('%Y-%m-%d') if result.fecha_entrega else None,
                'estado': result.estado if result.estado else 'Sin estado',
                'cliente': f"{result.nombreUsuario or ''} {result.apellidoPaterno or ''} {result.apellidoMaterno or ''}".strip(),
                'contacto': result.emailUsuario or '',
                'total': float(result.precioTotal) if result.precioTotal is not None else 0.0,
                'productos': productos,
                'id_venta': result.idVenta,
                'fecha_venta': result.fechaVenta.strftime('%Y-%m-%d %H:%M:%S') if result.fechaVenta else None,
                'estado_venta': result.estadoVenta or '',
                'nombres_productos': result.nombresProductos or '',
                'cantidades_productos': result.cantidadesProductos or '',
                'precios_productos': result.preciosProductos or ''
            }
            
            return pedido
            
        except Exception as e:
            print(f"Error al obtener detalle del pedido {pedido_id}: {str(e)}")
            return None