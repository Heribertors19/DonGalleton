from app import db
from sqlalchemy.sql import text

class VentaService:

    @staticmethod
    def get_daily_sales():
        try:
            query = text("""
                SELECT 
                    tipo_galleta,
                    cantidad_vendida,
                    total_ventas,
                    precio_promedio
                FROM vista_ventas_por_galleta
                ORDER BY total_ventas DESC
                LIMIT 3;
            """)
            result = db.session.execute(query).fetchall()

            sales_data = []
            for row in result:
                sales_data.append({
                    'label': row.tipo_galleta,
                    'data': float(row.cantidad_vendida),  # Cantidad en piezas
                    'total_ventas': float(row.total_ventas),
                    'precio_promedio': float(row.precio_promedio)
                })

            return sales_data
        except Exception as e:
            print(f"Error al obtener ventas diarias: {str(e)}")
            return []

    @staticmethod
    def get_total_daily_sales():
        try:
            query = text("""
                SELECT COALESCE(SUM(total_ventas), 0) AS total_ventas
                FROM vista_ventas_por_galleta
                WHERE EXISTS (
                    SELECT 1 FROM venta 
                    WHERE DATE(fechaVenta) = CURRENT_DATE
                    AND idVenta IN (
                        SELECT idVenta FROM detalleventa 
                        WHERE idTipoGalleta IN (
                            SELECT idTipoGalleta FROM tipogalleta
                        )
                    )
                );
            """)
            result = db.session.execute(query).fetchone()
            return float(result.total_ventas) if result and result.total_ventas is not None else 0.0
        except Exception as e:
            print(f"Error al obtener total diario: {e}")
            return 0.0

    @staticmethod
    def get_venta_pasada():
        try:
            query = text("""
                select * from ventas_totales_diarias;
            """)
            result = db.session.execute(query).fetchone()
            return float(result.total_ventas) if result and result.total_ventas is not None else 0.0
        except Exception as e:
            print(f"Error al obtener venta pasada: {e}")
            return 0.0

   

    @staticmethod
    def get_ventas_por_galleta():
        try:
            query = text("""
                SELECT 
                    tipo_galleta,
                    cantidad_vendida AS piezas_vendidas,
                    total_ventas
                FROM vista_ventas_por_galleta
                ORDER BY cantidad_vendida DESC;
            """)
            result = db.session.execute(query).fetchall()

            ventas_por_galleta = []
            for row in result:
                ventas_por_galleta.append({
                    'nombre_galleta': row.tipo_galleta,
                    'piezas_vendidas': int(row.piezas_vendidas),
                    'total_ventas': float(row.total_ventas)
                })

            return ventas_por_galleta
        except Exception as e:
            print(f"Error al obtener ventas por galleta: {str(e)}")
            return []
        
        
    @staticmethod
    def get_least_sold_cookie():
        try:
            query = text("""
                SELECT 
                    tg.idTipoGalleta,
                    tg.nombre AS nombre_galleta,
                    r.imagen as imagen,
                    IFNULL(SUM(dv.cantidad), 0) AS total_vendido,
                    tg.costo AS precio_unitario,
                    (IFNULL(SUM(dv.cantidad), 0) * tg.costo) AS total_ventas
                FROM 
                    tipogalleta tg
                LEFT JOIN 
                    detalleventa dv ON tg.idTipoGalleta = dv.idTipoGalleta
                LEFT JOIN
                    receta r on r.idReceta = tg.idReceta
                LEFT JOIN
                    venta v ON dv.idVenta = v.idVenta AND v.estado = 'completada'
                GROUP BY 
                    tg.idTipoGalleta, tg.nombre, tg.costo, r.imagen
                HAVING 
                    total_vendido > 0
                ORDER BY 
                    total_vendido ASC
                LIMIT 1;
            """)
            result = db.session.execute(query).fetchone()
            
            if result:
                
                
                return {
                    'id': result.idTipoGalleta,
                    'nombre_galleta': result.nombre_galleta,
                    'total_vendido': int(result.total_vendido),
                    'precio_unitario': float(result.precio_unitario),
                    'total_ventas': float(result.total_ventas),
                    'imagen': result.imagen
                }
            return None
        except Exception as e:
            print(f"\nERROR EN get_least_sold_cookie: {str(e)}\n")
            return None