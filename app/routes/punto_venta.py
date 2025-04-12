from flask import Blueprint, url_for, redirect, flash,render_template,request
from app.models import Venta, DetalleVenta, TipoGalleta, LoteGalleta,Receta,Pedido
from app import db
from datetime import datetime
from sqlalchemy import func,not_
from flask import current_app
import base64
from flask import session
import pdfkit
from flask import make_response, render_template_string
import logging
from sqlalchemy.orm import joinedload,aliased
from datetime import date

punto_venta_bp = Blueprint('punto_venta', __name__, template_folder='templates')



##############################################################################
# Registro de logs
##############################################################################
# Configurar logging
logging.basicConfig(
    level=logging.INFO,  # Puedes ajustar el nivel de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),  # Archivo donde se almacenarán los logs
        logging.StreamHandler()  # Imprime los logs en la consola
    ]
)
##############################################################################
# HELPERS
##############################################################################

def procesar_imagen_galleta(imagen_db, default_img='img/default.png'):
    logging.info('Procesando imagen')
    """
    Procesa imágenes desde la base de datos, manejando el caso de prefijos duplicados
    Args:
        imagen_db: Datos de imagen desde la BD (bytes, str, bytearray)
        default_img: Ruta a imagen por defecto (relativa a static)
    Returns:
        str: URL data:image válida o URL estática por defecto
    """
    if not imagen_db:
        return url_for('static', filename=default_img)
    
    try:
        # Convertir a string si son bytes
        if isinstance(imagen_db, (bytes, bytearray)):
            try:
                imagen_str = imagen_db.decode('utf-8')
            except UnicodeDecodeError:
                # Si no se puede decodificar, asumimos que son datos binarios directos
                return f"data:image/jpeg;base64,{base64.b64encode(imagen_db).decode('utf-8')}"
        else:
            imagen_str = str(imagen_db)

        # Caso especial: prefijo duplicado
        if imagen_str.startswith('data:image/jpeg;base64,data:image/jpeg;base64,'):
            # Extraer solo los datos base64 después del último prefijo
            base64_data = imagen_str.split(',')[-1]
            return f"data:image/jpeg;base64,{base64_data}"
        
        # Caso normal: ya tiene el formato correcto
        elif imagen_str.startswith(('data:image/', 'http://', 'https://')):
            return imagen_str
        
        # Caso: solo datos base64 sin prefijo
        elif len(imagen_str) > 100:  # Umbral para considerar como base64
            # Verificar si es base64 válido
            try:
                base64.b64decode(imagen_str)
                return f"data:image/jpeg;base64,{imagen_str}"
            except:
                pass
        
        # Si no reconocemos el formato, usar imagen por defecto
        return url_for('static', filename=default_img)
        
    except Exception as e:
        current_app.logger.error(f"Error procesando imagen: {str(e)}", exc_info=True)
        return url_for('static', filename=default_img)

def obtener_galletas_disponibles(filtro=None):
    logging.info('Cargando los datos d ela galletas')
    """Consulta galletas con stock disponible"""
    try:
        print("\nIniciando consulta de galletas disponibles...")  # Debug
        
        query = db.session.query(
            TipoGalleta.idTipoGalleta,
            TipoGalleta.nombre,
            TipoGalleta.costo,
            Receta.imagen,
            Receta.pesoIndividualGalleta,
            func.coalesce(func.sum(LoteGalleta.cantidadDisponible), 0).label('stock')
        ).join(
            Receta, TipoGalleta.idReceta == Receta.idReceta
        ).outerjoin(
            LoteGalleta, TipoGalleta.idTipoGalleta == LoteGalleta.idTipoGalleta
        ).filter(
            func.coalesce(LoteGalleta.cantidadDisponible, 0) > 0
        ).group_by(
            TipoGalleta.idTipoGalleta,
            Receta.imagen,
            Receta.pesoIndividualGalleta
        ).having(
            func.coalesce(func.sum(LoteGalleta.cantidadDisponible), 0) > 0
        )

        if filtro:
            print(f"Aplicando filtro: {filtro}")  # Debug
            query = query.filter(TipoGalleta.nombre.ilike(f"%{filtro}%"))

        galletas = query.all()
        print(f"Galletas encontradas: {len(galletas)}")  # Debug
        for g in galletas:
            print(f"ID: {g.idTipoGalleta}, Nombre: {g.nombre}, Stock: {g.stock}")  # Debug
        
        return galletas
        
    except Exception as e:
        print(f"Error en obtener_galletas_disponibles: {str(e)}")  # Debug
        raise
def formatear_detalle(detalle):
    """Formatea los detalles de venta para mostrar en la interfaz"""
    logging.info('formateo de detalles')

    try:
        if detalle.tiposVentaNombre == 'pieza':
            return f"{detalle.cantidad} pieza(s)"
        elif detalle.tiposVentaNombre == 'gramo':
            peso_total = detalle.cantidad * detalle.tipo_galleta.receta.pesoIndividualGalleta
            return f"{peso_total:.1f}g ({detalle.cantidad} piezas)"
        elif detalle.tiposVentaNombre == 'kilo':
            peso_total = (detalle.cantidad * detalle.tipo_galleta.receta.pesoIndividualGalleta) / 1000
            return f"{peso_total:.3f}kg ({detalle.cantidad} piezas)"
        else:
            return f"{detalle.cantidad} {detalle.tiposVentaNombre}"
    except Exception as e:
        current_app.logger.error(f"Error al formatear detalle: {str(e)}")
        return f"{detalle.cantidad} unidades"
def formatear_galleta(galleta_db):
    """Estructura los datos de galleta para el frontend con manejo robusto de errores"""
    if not galleta_db:
        return None
        
    try:
        return {
            'id': getattr(galleta_db, 'idTipoGalleta', None),
            'nombre': getattr(galleta_db, 'nombre', 'Desconocido'),
            'precio': float(getattr(galleta_db, 'costo', 0)),
            'imagen': procesar_imagen_galleta(getattr(galleta_db, 'imagen', None)),
            'peso': float(getattr(galleta_db, 'pesoIndividualGalleta', 0)),
            'stock': getattr(galleta_db, 'stock', 0),
            'pesoIndividualGalleta': float(getattr(galleta_db, 'pesoIndividualGalleta', 0)),
            'costo': float(getattr(galleta_db, 'costo', 0))
        }
    except Exception as e:
        current_app.logger.error(f"Error formateando galleta: {str(e)}")
        return None

def calcular_subtotal(venta_id):
    """Calcula el subtotal de una venta"""
    detalles = DetalleVenta.query.filter_by(idVenta=venta_id).all()
    return sum(d.cantidad * d.costoActual for d in detalles)

##############################################################################
# ROUTES
##############################################################################
@punto_venta_bp.route('/ventas_hoy', methods=['GET'])
def ventas_hoy():
    logging.info('Ventas del día Logs')
    """Mostrar ventas realizadas hoy"""
    try:
        current_app.logger.info("Iniciando ventas_hoy")
        
        # Obtener la fecha de hoy
        fecha_hoy = datetime.today().date()
        print(f"Fecha de hoy: {fecha_hoy}")  # Depuración: Mostrar la fecha actual

        # Obtener ventas realizadas hoy
        ventas_hoy = Venta.query.filter(Venta.fechaVenta == fecha_hoy).all()
        print(f"Ventas del día encontradas: {len(ventas_hoy)}")  # Depuración: Número de ventas encontradas

        # Obtener los detalles de esas ventas
        detalles_ventas_hoy = []
        for venta in ventas_hoy:
            detalles = db.session.query(DetalleVenta)\
                .join(TipoGalleta)\
                .filter(DetalleVenta.idVenta == venta.idVenta)\
                .all()
            print(f"Detalles de venta {venta.idVenta}: {len(detalles)} detalles encontrados")  # Depuración: Mostrar detalles de cada venta
            detalles_ventas_hoy.append((venta, detalles))
        
        # Depuración: Verificar la cantidad de ventas y detalles obtenidos
        print(f"Total de ventas y detalles recopilados: {len(detalles_ventas_hoy)}")

        # Renderizar template con las ventas del día
        return render_template(
            'punto_venta/ventas_hoy.html',
            detalles_ventas_hoy=detalles_ventas_hoy
        )
        
    except Exception as e:
        current_app.logger.error(f"Error al obtener ventas del día: {str(e)}", exc_info=True)
        flash("Error al cargar las ventas del día", "danger")
        
        # Depuración: Error en la ejecución
        print(f"Error al cargar las ventas del día: {str(e)}")

        return render_template('punto_venta/ventas_hoy.html', detalles_ventas_hoy=[])


@punto_venta_bp.route('/punto_venta', methods=['GET', 'POST'])
def interfaz_venta():
    logging.info('Punto de venta Logs')
    """Interfaz principal del punto de venta con lista lateral funcional"""
    try:
        current_app.logger.info("Iniciando interfaz_venta")
        
        # Manejar búsqueda
        filtro = request.form.get('busqueda', '').strip()
        current_app.logger.debug(f"Filtro de búsqueda: '{filtro}'")
        
        # Obtener y formatear galletas disponibles
        galletas_db = obtener_galletas_disponibles(filtro)
        galletas = []
        for g in galletas_db:
            try:
                galleta_formateada = formatear_galleta(g)
                if galleta_formateada:
                    galletas.append(galleta_formateada)
            except Exception as e:
                current_app.logger.error(f"Error formateando galleta: {str(e)}")
                continue
        
        current_app.logger.debug(f"Galletas disponibles formateadas: {len(galletas)}")
        
        # Obtener venta activa y productos agregados
        venta_activa = None
        detalles_venta = []
        subtotal = 0.00
        
        # Versión robusta para obtener venta activa
        try:
            if hasattr(Venta, 'estado'):
                venta_activa = Venta.query.filter_by(estado='en_proceso').first()
            elif hasattr(Venta, 'completada'):
                venta_activa = Venta.query.filter_by(completada=False)\
                                         .order_by(Venta.idVenta.desc()).first()
            else:
                venta_activa = Venta.query.order_by(Venta.idVenta.desc()).first()
            
            if venta_activa:
                current_app.logger.debug(f"Venta activa encontrada: ID {venta_activa.idVenta}")
                
                # Obtener detalles con join para asegurar relaciones y excluir ventas online
                pedidos_venta = aliased(Pedido)  
                detalles_venta = db.session.query(DetalleVenta)\
                    .join(TipoGalleta)\
                    .filter(
                        DetalleVenta.idVenta == venta_activa.idVenta,
                        DetalleVenta.tiposVentaNombre != 'venta_online',  # Filtro para excluir ventas online
                        not_(DetalleVenta.idVenta.in_(db.session.query(pedidos_venta.idVenta)))  # Filtro adicional
                    ).all()
                
                # Calcular subtotal solo con los detalles no online
                subtotal = sum(
                    d.cantidad * d.costoActual 
                    for d in detalles_venta 
                    if d.tiposVentaNombre != 'venta_online'
                )
                
                current_app.logger.debug("Productos en la venta actual (excluyendo online):")
                for detalle in detalles_venta:
                    current_app.logger.debug(
                        f"- ID: {detalle.idTipoGalleta}, "
                        f"Nombre: {detalle.tipo_galleta.nombre if detalle.tipo_galleta else 'N/A'}, "
                        f"Cantidad: {detalle.cantidad}, "
                        f"Precio: {detalle.costoActual}, "
                        f"Tipo: {detalle.tiposVentaNombre}"
                    )
        except Exception as db_error:
            current_app.logger.error(f"Error al obtener venta activa: {str(db_error)}")
        
        # Obtener ventas del día
        try:
            
            fecha_hoy = date.today()
            # Obtener las ventas del día con detalles
            ventas_hoy_detalles = Venta.query.options(joinedload(Venta.detalles)).filter(func.date(Venta.fechaVenta) == fecha_hoy).all()
            current_app.logger.debug(f"Ventas del día encontradas: {len(ventas_hoy_detalles)}")
            current_app.logger.debug(f"Ventas del día: {ventas_hoy_detalles}")

            # Si necesitas calcular el precioTotal, por ejemplo, sumando los subtotales de los detalles:
            for venta in ventas_hoy_detalles:
                precio_total = sum([detalle.cantidad * detalle.costoActual for detalle in venta.detalles])
                venta.precioTotal = precio_total  # Asumiendo que hay un campo precioTotal o calculando en tiempo real.

            # Verificar los detalles obtenidos
            current_app.logger.debug(f"Detalles de ventas hoy: {ventas_hoy_detalles}")
        except Exception as db_error:
            current_app.logger.error(f"Error al obtener ventas del día: {str(db_error)}")
            ventas_hoy = []
        
        # Renderizar template con todos los datos necesarios
        return render_template(
            'punto_venta/punto_venta.html',
            galletas=galletas,
            venta_activa=venta_activa,
            detalles_venta=detalles_venta,  # Ya filtrados para excluir online
            subtotal=subtotal,
            busqueda=filtro,
            ventas_hoy_detalles=ventas_hoy_detalles,# Aquí se pasan las ventas del día al template
            formatear_detalle=formatear_detalle
        )
        
    except Exception as e:
        current_app.logger.error(f"Error crítico en interfaz_venta: {str(e)}", exc_info=True)
        flash("Error al cargar el punto de venta", "danger")
        return render_template(
            'punto_venta/punto_venta.html',
            galletas=[],
            venta_activa=None,
            detalles_venta=[],
            subtotal=0.00,
            busqueda='',
            ventas_hoy=[],  # En caso de error, no se pasan ventas
            formatear_detalle=lambda x: str(x)
        )

@punto_venta_bp.route('/iniciar-venta', methods=['POST'])
def iniciar_venta():
    logging.info('Venta iniciada')
    """Crea una nueva venta"""
    try:
        # Verificar si ya hay una venta activa
        if Venta.query.filter_by(estado='en_proceso').first():
            flash("Ya hay una venta en curso", "warning")
            return redirect(url_for('punto_venta.interfaz_venta'))
        
        nueva_venta = Venta(
            fechaVenta=datetime.now(),
            precioTotal=0.00,
            estado='en_proceso'
        )
        db.session.add(nueva_venta)
        db.session.commit()
        flash("Venta iniciada correctamente", "success")
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al iniciar venta: {str(e)}")
        flash("Error al iniciar la venta", "danger")
    
    return redirect(url_for('punto_venta.interfaz_venta'))
@punto_venta_bp.route('/agregar-producto', methods=['POST'])
def agregar_producto():
    logging.info('Agregacion de galletas al carrito')
    try:
        # 1. Validar datos del formulario
        producto_id = request.form.get('producto_id', type=int)
        cantidad = request.form.get('cantidad', 1, type=float)
        tipo_venta = request.form.get('tipo_venta', 'pieza')
        es_beneficencia = request.form.get('es_beneficencia') == 'on'

        if not producto_id or cantidad <= 0:
            flash("Datos inválidos", "danger")
            return redirect(url_for('punto_venta.interfaz_venta'))

        # 2. Obtener o crear venta activa
        venta = Venta.query.filter_by(estado='en_proceso').first()
        if not venta:
            venta = Venta(
                fechaVenta=datetime.now(),
                precioTotal=0.00,
                estado='en_proceso'
            )
            db.session.add(venta)
            db.session.commit()

        # 3. Obtener información de la galleta
        galleta = TipoGalleta.query.get_or_404(producto_id)
        if not galleta.receta:
            flash("Producto no configurado correctamente", "danger")
            return redirect(url_for('punto_venta.interfaz_venta'))

        peso_individual = galleta.receta.pesoIndividualGalleta
        if peso_individual <= 0:
            flash("Peso no configurado para esta galleta", "danger")
            return redirect(url_for('punto_venta.interfaz_venta'))

        # 4. Calcular cantidad en piezas
        factores = {
            'pieza': 1,
            'gramo': 1 / peso_individual,
            'kilo': 1000 / peso_individual,
            'paquete_1kg': 1000 / peso_individual,
            'paquete_700gr': 700 / peso_individual
        }
        
        cantidad_piezas = round(cantidad * factores.get(tipo_venta, 1))
        if cantidad_piezas <= 0:
            flash("Cantidad inválida", "danger")
            return redirect(url_for('punto_venta.interfaz_venta'))

        # 5. Verificar stock disponible
        stock_disponible = sum(lote.cantidadDisponible for lote in galleta.lotes)
        if stock_disponible < cantidad_piezas:
            return redirect(url_for('punto_venta.interfaz_venta',sin_stock=True))

        # 6. Calcular precio
        precio_unitario = galleta.costo * (0.8 if es_beneficencia else 1.0)
        subtotal = cantidad_piezas * precio_unitario

        # 7. Crear detalle de venta
        nuevo_detalle = DetalleVenta(
            idVenta=venta.idVenta,
            idTipoGalleta=galleta.idTipoGalleta,
            cantidad=cantidad_piezas,
            costoActual=precio_unitario,
            tiposVentaNombre=tipo_venta,
            ventaEquivalenciaPiezas=cantidad_piezas
        )
        db.session.add(nuevo_detalle)
        
        # 8. Actualizar total de venta
        venta.precioTotal = calcular_subtotal(venta.idVenta)
        
        db.session.commit()

        flash(f"{galleta.nombre} agregado(a) correctamente", "success")
        return redirect(url_for('punto_venta.interfaz_venta'))

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error agregando producto: {str(e)}", exc_info=True)
        flash("Error al procesar el producto", "danger")
        return redirect(url_for('punto_venta.interfaz_venta'))
    
    
@punto_venta_bp.route('/finalizar-venta', methods=['POST'])
def finalizar_venta():
    logging.info('Venta finalizada')
    try:
        # 1. Iniciar transacción
        db.session.begin()
        
        # 2. Obtener venta con detalles
        venta = Venta.query.filter_by(estado='en_proceso').first()
        if not venta or not venta.detalles:
            db.session.rollback()
            flash("No hay productos para finalizar", "warning")
            return redirect(url_for('punto_venta.interfaz_venta'))

        # 3. Validar stock nuevamente
        for detalle in venta.detalles:
            galleta = detalle.tipo_galleta
            stock_disponible = sum(lote.cantidadDisponible for lote in galleta.lotes)
            
            if stock_disponible < detalle.ventaEquivalenciaPiezas:
                db.session.rollback()
                flash(f"Stock insuficiente para {galleta.nombre}. Disponible: {stock_disponible}", "danger")
                return redirect(url_for('punto_venta.interfaz_venta'))

        # 4. Actualizar stock (FIFO)
        for detalle in venta.detalles:
            cantidad_restante = detalle.ventaEquivalenciaPiezas
            galleta = detalle.tipo_galleta
            
            # Ordenar lotes por fecha más antigua
            lotes = sorted(galleta.lotes, key=lambda x: x.fechaPreparacion)
            
            for lote in lotes:
                if cantidad_restante <= 0:
                    break
                    
                if lote.cantidadDisponible > 0:
                    cantidad_a_descontar = min(lote.cantidadDisponible, cantidad_restante)
                    lote.cantidadDisponible -= cantidad_a_descontar
                    cantidad_restante -= cantidad_a_descontar

        # 5. Calcular el subtotal de cada detalle
        for detalle in venta.detalles:
            # Calcular el precio usando el método de detalle
            precio = detalle.calcular_precio(detalle.tipo_galleta)
            detalle.subtotal = precio  # Establecer el subtotal

        # 6. Confirmar venta
        venta.estado = 'completada'
        venta.fechaVenta = datetime.now()
        
        # 7. Hacer commit de TODO (venta + detalles + lotes actualizados)
        db.session.commit()
        
        # 8. Generar el ticket (sin PDF, solo HTML)
        rendered = render_template("punto_venta/ticket.html", venta=venta)
        
        # 9. Retornar el HTML con el ticket y permitir impresión
        return rendered

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error finalizando venta: {str(e)}", exc_info=True)
        flash("Error crítico al finalizar. Ningún cambio fue aplicado.", "danger")
    
    return redirect(url_for('punto_venta.interfaz_venta'))

from flask import flash, redirect, url_for
from sqlalchemy import text

@punto_venta_bp.route('/cancelar-venta', methods=['POST'])
def cancelar_venta():
    logging.info('Venta cancelada')
    venta_id = request.form.get('venta_id')
    print(f"[DEBUG] Forzando cancelación de venta ID: {venta_id}")
    
    if not venta_id:
        error_msg = 'ID de venta no proporcionado'
        print(f"[ERROR] {error_msg}")
        flash(error_msg, 'error')
        return redirect(url_for('punto_venta.interfaz_venta'))

    try:
        # Obtener la venta con detalles y pedidos asociados
        venta = Venta.query.get(venta_id)

        if not venta:
            error_msg = 'Venta no encontrada'
            print(f"[ERROR] {error_msg}")
            flash(error_msg, 'error')
            return redirect(url_for('punto_venta.interfaz_venta'))

        # Si hay detalles de venta y pedidos asociados, se eliminan junto con la venta
        print(f"[DEBUG] Eliminando la venta ID: {venta_id} con sus detalles y pedidos asociados...")
        
        db.session.delete(venta)  # Esto elimina la venta, y por la relación de cascada, elimina también los detalles y pedidos
        db.session.commit()
        
        print("[SUCCESS] Venta eliminada completamente sin restricciones")
        flash("Venta cancelada forzadamente con éxito", "success")
    
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Fallo crítico al cancelar la venta: {e}")
        flash(f"Error crítico al cancelar la venta: {str(e)}", "danger")
    
    return redirect(url_for('punto_venta.interfaz_venta'))



@punto_venta_bp.route('/eliminar-producto', methods=['POST'])
def eliminar_producto():
    logging.info('Producto eliminado de carrito')
    """Elimina un producto de la venta actual (versión sin JavaScript)"""
    try:
        # Verificar que existe una venta activa
        venta = Venta.query.filter_by(estado='en_proceso').first()
        if not venta:
            flash("No hay una venta activa", "warning")
            return redirect(url_for('punto_venta.interfaz_venta'))

        # Obtener el ID del detalle a eliminar
        id_detalle = request.form.get('id_detalle')
        if not id_detalle:
            flash("No se especificó producto a eliminar", "danger")
            return redirect(url_for('punto_venta.interfaz_venta'))

        # Buscar el detalle a eliminar
        detalle = DetalleVenta.query.filter_by(
            idDetalleVenta=id_detalle,
            idVenta=venta.idVenta
        ).first()

        if not detalle:
            flash("Producto no encontrado en la venta actual", "danger")
            return redirect(url_for('punto_venta.interfaz_venta'))

        # Guardar nombre para el mensaje
        producto = TipoGalleta.query.get(detalle.idTipoGalleta)
        nombre_producto = producto.nombre if producto else "Producto desconocido"

        # Eliminar el detalle
        db.session.delete(detalle)
        db.session.commit()

        flash(f"Producto '{nombre_producto}' eliminado correctamente", "success")
        return redirect(url_for('punto_venta.interfaz_venta'))

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al eliminar producto: {str(e)}")
        flash("Error al eliminar el producto", "danger")
        return redirect(url_for('punto_venta.interfaz_venta'))
    
###################################################################
#corte de caja
####################################################################
@punto_venta_bp.route('/corte-caja', methods=['POST', 'GET'])
def corte_caja():
    try:
        # Obtener la fecha de hoy
        fecha_hoy = date.today()

        # Obtener todas las ventas del día con sus detalles
        ventas_hoy = db.session.query(Venta).filter(
            func.date(Venta.fechaVenta) == fecha_hoy,
            Venta.estado == 'completada'
        ).all()


        # Crear una estructura para pasar los datos al template
        ventas_detalladas = []
        ventas_totales = 0

        for venta in ventas_hoy:
            detalles = db.session.query(
                DetalleVenta.cantidad,
                DetalleVenta.ventaEquivalenciaPiezas,
                DetalleVenta.tiposVentaNombre,
                TipoGalleta.nombre.label("nombreGalleta")
            ).join(TipoGalleta, DetalleVenta.idTipoGalleta == TipoGalleta.idTipoGalleta)\
             .filter(DetalleVenta.idVenta == venta.idVenta).all()

            venta_info = {
                "idVenta": venta.idVenta,
                "fechaVenta": venta.fechaVenta,
                "precioTotal": venta.precioTotal,
                "detalles": [{
                    "nombreGalleta": d.nombreGalleta,
                    "cantidad": d.cantidad,
                    "ventaEquivalenciaPiezas": d.ventaEquivalenciaPiezas,
                    "tiposVentaNombre": d.tiposVentaNombre
                } for d in detalles]
            }

            ventas_detalladas.append(venta_info)
            ventas_totales += venta.precioTotal

        if request.method == 'POST':
            # Obtener el efectivo recibido del formulario
            efectivo_recibido = request.form.get('efectivo_recibido', type=float)

            # Comprobar que el efectivo recibido no sea None
            if efectivo_recibido is not None:
                # Calcular la diferencia entre el efectivo recibido y las ventas totales
                diferencia = round(efectivo_recibido - round(ventas_totales,2), 2)
                flash(f"Corte de caja realizado. Diferencia: {diferencia:.2f}", "success")
            else:
                diferencia = 0  # En caso de que no se haya recibido efectivo

            return render_template('punto_venta/corte_caja.html',
                                   ventas_totales=ventas_totales,
                                   efectivo_recibido=efectivo_recibido,
                                   diferencia=diferencia,
                                   ventas_detalladas=ventas_detalladas)

        return render_template('punto_venta/corte_caja.html',
                               ventas_totales=ventas_totales,
                               ventas_detalladas=ventas_detalladas)

    except Exception as e:
        flash(f"Error al realizar el corte de caja: {str(e)}", "danger")
        return render_template('punto_venta/corte_caja.html')
