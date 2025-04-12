from flask import (Blueprint, render_template, request, redirect, url_for, flash, session)
from app.models import MermaGalleta, MermaInsumo, RegistroMerma, Insumo, PresentacionInsumo,TipoGalleta,LoteGalleta,Receta,DetalleCompra,CatUnidad
from datetime import datetime, timedelta
from app import db
from sqlalchemy import desc
import pytz
from flask import current_app
import base64
from sqlalchemy import func
from sqlalchemy import LargeBinary, cast
from sqlalchemy.orm import aliased
from flask_login import login_user, logout_user, login_required, current_user
import logging
mermas_bp = Blueprint('mermas', __name__)
UTC = pytz.utc


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
# Nuevas constantes de conversión (gramos como base)
CONVERSIONES = {
    'solido': {
        'miligramo': 0.001,
        'gramo': 1,
        'kilogramo': 1000,
        'libra': 453.592,
        'onza': 28.3495,
        'taza': 120,  
        'cucharada': 15,
        'cucharadita': 5
    },
    'liquido': {
        'mililitro': 1,
        'litro': 1000,
        'galon': 3785.41,
        'taza': 240,
        'cucharada': 15,
        'cucharadita': 5
    }
    
}
def convertir_solido_a_gramos(cantidad, unidad_origen):
    """Convierte cualquier unidad de sólido a gramos"""
    factor = CONVERSIONES['solido'].get(unidad_origen.lower(), 1)
    return cantidad * factor, 'gramo'

def convertir_liquido_a_mililitros(cantidad, unidad_origen):
    """Convierte cualquier unidad de líquido a mililitros"""
    factor = CONVERSIONES['liquido'].get(unidad_origen.lower(), 1)
    return cantidad * factor, 'mililitro'

def convertir_a_unidad_base(cantidad, unidad_origen, presentacion):
    """Función principal que decide qué conversión aplicar"""
    tipo = determinar_tipo_por_presentacion(presentacion)
    
    if tipo == 'unidad':
        return cantidad, 'unidad'
    elif tipo == 'solido':
        return convertir_solido_a_gramos(cantidad, unidad_origen)
    elif tipo == 'liquido':
        return convertir_liquido_a_mililitros(cantidad, unidad_origen)
@mermas_bp.route('/mermas')
def mermas():
    logging.info('mermas inicio')
    current_time = datetime.now(UTC)
    flash_time = session.get('flash_time')
    
    if isinstance(flash_time, datetime) and flash_time.tzinfo is None:
        flash_time = flash_time.replace(tzinfo=UTC)
    
    if flash_time and (current_time - flash_time) > timedelta(seconds=3):
        session.pop('_flashes', None)
    
    session['flash_time'] = current_time
    return render_template('/merma/merma.html')

@mermas_bp.route('/registrar-merma-insumos', methods=['GET', 'POST'])
def registrar_merma_insumos():
    logging.info('mermas insumos')
    print("\n=== INICIO registrar_merma_insumos ===")
    print(f"Método de solicitud: {request.method}")
    
    # Configuración inicial de sesión y flashes
    current_time = datetime.now(UTC)
    flash_time = session.get('flash_time')
    
    if flash_time and flash_time.tzinfo is None:
        flash_time = UTC.localize(flash_time)
    
    if flash_time and (current_time - flash_time) > timedelta(seconds=3):
        session.pop('_flashes', None)
    
    session['flash_time'] = current_time
    session.setdefault('insumos_agregados', [])
    
    if request.method == 'POST':
        action = request.form.get('action')
        if 'agregar_insumo' in request.form:
            return agregar_insumo()
        elif action == 'eliminar':
            return eliminar_insumo()
        elif action == 'registrar':
            # Aquí llamamos a la única versión de registrar_merma
            return registrar_merma()
    
    return render_template('merma/mermas_insumo.html', 
                         insumos_disponibles=obtener_insumos_disponibles(), 
                         insumos_agregados=session['insumos_agregados'], 
                         historial_mermas=obtener_historial_mermas())

def agregar_insumo():
    logging.info('agregacion de insumos')
    insumo_id = request.form['agregar_insumo']
    insumo = obtener_insumo_por_id(insumo_id)
    
    if insumo and not any(str(i['idInsumo']) == insumo_id for i in session['insumos_agregados']):
        session['insumos_agregados'].append({'idInsumo': insumo.idInsumo, 'nombre': insumo.nombre, 'presentacion': insumo.presentacion})
        session.modified = True
        flash('Insumo agregado correctamente', 'success')
    return redirect(url_for('mermas.registrar_merma_insumos'))

def eliminar_insumo():
    logging.info('eliminacion de insumos')
    insumo_id = request.form.get('insumo_id')
    session['insumos_agregados'] = [i for i in session['insumos_agregados'] if str(i['idInsumo']) != insumo_id]
    session.modified = True
    flash('Insumo eliminado correctamente', 'success')
    return redirect(url_for('mermas.registrar_merma_insumos'))

def registrar_merma():
    logging.info('registro de mermas insumos')
    if not session.get('insumos_agregados'):
        flash('Debes agregar al menos un insumo', 'error')
        return redirect(url_for('mermas.registrar_merma_insumos'))
    
    try:
        for insumo in session['insumos_agregados']:
            insumo_id = str(insumo['idInsumo'])
            # Obtener datos del formulario
            cantidad = request.form.get(f'cantidad_{insumo_id}')
            tipo_merma = request.form.get(f'tipo_merma_{insumo_id}')
            unidad = request.form.get(f'unidad_{insumo_id}')

            if not all([cantidad, tipo_merma, unidad]):
                flash('Todos los campos son obligatorios', 'error')
                return redirect(url_for('mermas.registrar_merma_insumos'))
            
            try:
                cantidad = float(cantidad)
                if cantidad <= 0:
                    raise ValueError("La cantidad debe ser positiva")
            except ValueError as ve:
                flash('La cantidad debe ser un número válido', 'error')
                return redirect(url_for('mermas.registrar_merma_insumos'))
            cantidad_gramos, unidad_base = convertir_a_unidad_base(
                cantidad, 
                unidad, 
                insumo['presentacion']
            )
            print(f"Conversión: {cantidad} {unidad} = {cantidad_gramos} {unidad_base}")

            # Crear registro en BD - TRANSACCIÓN PRINCIPAL
            try:
                db.session.begin()
                
                # 1. Insertar en RegistroMerma
                nuevo_registro = RegistroMerma(
                    categoria='insumos',
                    tipoMerma=tipo_merma,
                    fecha=datetime.now(),
                    cantidad=cantidad_gramos
                )
                db.session.add(nuevo_registro)
                db.session.flush()
                # 2. Insertar en MermaInsumo
                merma_insumo = MermaInsumo(
                    idRegistroMerma=nuevo_registro.idRegistroMerma,
                    idInsumo=int(insumo['idInsumo'])
                )
                db.session.add(merma_insumo)
                # 3. Actualizar inventario (descontar de detallecompra)
                if tipo_merma != 'merma_normal':  # Solo descontamos si no es merma normal de producción
                    insumo_obj = Insumo.query.get(int(insumo['idInsumo']))
                    if insumo_obj:
                        # Buscar lotes disponibles (FIFO)
                        lotes = DetalleCompra.query.filter(
                            DetalleCompra.idInsumo == insumo_obj.idInsumo,
                            DetalleCompra.cantidadDisponible > 0
                        ).order_by(DetalleCompra.fechaCaducidadInsumo).all()
                        
                        cantidad_a_descontar = cantidad_gramos
                        
                        for lote in lotes:
                            if cantidad_a_descontar <= 0:
                                break
                            
                            if lote.cantidadDisponible >= cantidad_a_descontar:
                                lote.cantidadDisponible -= cantidad_a_descontar
                                cantidad_a_descontar = 0
                            else:
                                cantidad_a_descontar -= lote.cantidadDisponible
                                lote.cantidadDisponible = 0
                            
                            db.session.add(lote)
                            print(f"✅ Lote {lote.idDetalleCompra} actualizado. Nuevo disponible: {lote.cantidadDisponible}")
                        
                        if cantidad_a_descontar > 0:
                            raise ValueError(f"No hay suficiente stock para descontar {cantidad_gramos}g de {insumo_obj.nombre}")

                db.session.commit()
            except Exception as e:
                db.session.rollback()
                flash(f'Error al registrar merma: {str(e)}', 'error')
                return redirect(url_for('mermas.registrar_merma_insumos'))
        
        session['insumos_agregados'] = []
        flash('Merma registrada exitosamente y stock actualizado', 'success')
        
    except Exception as e:
        flash(f'Error al registrar: {str(e)}', 'error')
    
    return redirect(url_for('mermas.registrar_merma_insumos'))

def obtener_insumo_por_id(insumo_id):
    logging.info('obtener insumos')
    insumo = db.session.query(
        Insumo.idInsumo, 
        Insumo.nombre, 
        func.coalesce(PresentacionInsumo.nombre, 'Sin presentación').label('presentacion'),
        func.coalesce(PresentacionInsumo.equivalenciaUnidadBase, 1).label('equivalenciaUnidadBase'),
        func.coalesce(CatUnidad.nombre, 'unidad').label('unidad_base')
    ).outerjoin(PresentacionInsumo, Insumo.idPresentacion == PresentacionInsumo.idPresentacionInsumo)\
     .outerjoin(CatUnidad, PresentacionInsumo.idUnidadBase == CatUnidad.idUnidad)\
     .filter(Insumo.idInsumo == insumo_id).first()
    return insumo

def obtener_insumos_disponibles():
    logging.info('obtener insumos')
    return db.session.query(
        Insumo.idInsumo, 
        Insumo.nombre, 
        func.coalesce(PresentacionInsumo.nombre, 'Sin presentación').label('presentacion')
    ).outerjoin(PresentacionInsumo, Insumo.idPresentacion == PresentacionInsumo.idPresentacionInsumo)\
     .all()

def obtener_historial_mermas():
    logging.info('obtener historial insumos')
    return db.session.query(
        Insumo.nombre.label('nombre_insumo'), 
        PresentacionInsumo.nombre.label('presentacion'),
        RegistroMerma.tipoMerma, 
        RegistroMerma.cantidad,
        CatUnidad.nombre.label('unidad_base'),
        RegistroMerma.fecha
    ).join(MermaInsumo, RegistroMerma.idRegistroMerma == MermaInsumo.idRegistroMerma)\
     .join(Insumo, MermaInsumo.idInsumo == Insumo.idInsumo)\
     .join(PresentacionInsumo, Insumo.idPresentacion == PresentacionInsumo.idPresentacionInsumo)\
     .join(CatUnidad, PresentacionInsumo.idUnidadBase == CatUnidad.idUnidad)\
     .filter(RegistroMerma.categoria == 'insumos')\
     .order_by(desc(RegistroMerma.fecha)).limit(50).all()

def determinar_tipo_por_presentacion(presentacion):
    """Determina si el insumo es sólido, líquido o por unidad con manejo de casos nulos"""
    if not presentacion or presentacion.lower() == 'sin presentación':
        return 'unidad'
    
    presentacion_lower = presentacion.lower()
    
    # Sólidos (masa)
    solidos_keywords = ['kg', 'kilo', 'gramo', 'g ', 'gr ', 'costal', 'bolsa', 'taza', 'cucharada',]
    if any(keyword in presentacion_lower for keyword in solidos_keywords):
        return 'solido'
    
    # Líquidos (volumen)
    liquidos_keywords = ['lt', 'litro', 'ml', 'mililitro', 'galon', 'galón']
    if any(keyword in presentacion_lower for keyword in liquidos_keywords):
        return 'liquido'
    
    return 'unidad'
#################################################################################################
#################################################################################################
@mermas_bp.route('/merma/merma-galletas', methods=['GET', 'POST'])
def mostrar_galletas_merma():
    try:
        # Obtener parámetros de selección
        seleccionadas = request.args.get('seleccionadas', '') or request.form.get('galletas_seleccionadas', '')
        galletas_seleccionadas_ids = [g.strip() for g in seleccionadas.split(',') if g.strip()]
        
        # Obtener datos actualizados de galletas con stock
        galletas_disponibles = obtener_galletas_con_stock()
        
        # Mapear stock disponible para validaciones
        stock_disponible = {str(g['id']): g['stock'] for g in galletas_disponibles}
        
        # Manejar acciones POST
        if request.method == 'POST':
            action = request.form.get('action')
            if action == 'eliminar_merma':
                return eliminar_galleta_list()
            if action == 'registrar_merma':
                return registrar_merma_galletas(galletas_seleccionadas_ids, stock_disponible)
            elif action == 'limpiar_seleccion':
                return redirect(url_for('mermas.mostrar_galletas_merma'))
        
        # Preparar datos para la vista
        galletas_seleccionadas = [
            g for g in galletas_disponibles
            if str(g['id']) in galletas_seleccionadas_ids
        ]
        
        # Consulta optimizada para historial de mermas
        merma_galleta = aliased(MermaGalleta)
        historial_mermas = db.session.query(
            RegistroMerma,
            TipoGalleta.nombre.label('nombre_galleta'),
            Receta.nombre.label('nombre_receta'),
            Receta.imagen
        ).join(
            merma_galleta, RegistroMerma.idRegistroMerma == merma_galleta.idRegistroMerma
        ).join(
            TipoGalleta, merma_galleta.idTipoGalleta == TipoGalleta.idTipoGalleta
        ).join(
            Receta, TipoGalleta.idReceta == Receta.idReceta
        ).filter(
            RegistroMerma.categoria == 'galletas'
        ).order_by(
            RegistroMerma.fecha.desc()
        ).limit(30).all()
        
        # Procesar imágenes para el template
        historial_procesado = []
        for registro, nombre_galleta, nombre_receta, imagen in historial_mermas:
            historial_procesado.append({
                'registro': registro,
                'nombre_galleta': nombre_galleta,
                'nombre_receta': nombre_receta,
                'imagen': procesar_imagen_galleta(imagen)
            })

        return render_template('merma/mermas_galleta.html',
                           galletas_disponibles=galletas_disponibles,
                           historial_mermas=historial_procesado,
                           galletas_seleccionadas=galletas_seleccionadas,
                           galletas_seleccionadas_ids=','.join(galletas_seleccionadas_ids))

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error en mostrar_galletas_merma: {str(e)}", exc_info=True)
        flash("Error crítico al procesar la solicitud", "danger")
        return redirect(url_for('mermas.mostrar_galletas_merma'))

###############################################################################################
@mermas_bp.route('/agregar-galleta', methods=['POST'])
def agregar_galleta_list():
    if request.method == 'POST':
        try:
            galleta_id = request.form.get('galleta_id', '').strip()
            current_selected = request.form.get('current_selected', '').strip()
            
            # Convertir a lista, filtrando valores vacíos/no numéricos
            galletas_seleccionadas = []
            if current_selected:
                galletas_seleccionadas = [x for x in current_selected.split(',') 
                                        if x.strip() and x.strip().isdigit()]
            
            # Validar y agregar nueva galleta
            if galleta_id and galleta_id.isdigit() and galleta_id not in galletas_seleccionadas:
                galletas_seleccionadas.append(galleta_id)
                flash("Galleta agregada a mermas", "success")
            
            return redirect(url_for('mermas.mostrar_galletas_merma',
                                seleccionadas=','.join(galletas_seleccionadas)))
            
        except Exception as e:
            current_app.logger.error(f"Error en agregar_galleta_list: {str(e)}", exc_info=True)
            flash("Error al agregar galleta", "danger")
            return redirect(url_for('mermas.mostrar_galletas_merma'))
######################################################################################
def procesar_imagen_galleta(imagen):
    if not imagen:
        return url_for('static', filename='img/default_cookie3.svg')
    
    try:
        # Si es bytes, decodificar a string
        if isinstance(imagen, bytes):
            try:
                imagen = imagen.decode('utf-8')
            except UnicodeDecodeError:
                # Si falla la decodificación UTF-8, podría ser binario real
                header = imagen[:4]
                if header.startswith(b'\xFF\xD8'):
                    return f"data:image/jpeg;base64,{base64.b64encode(imagen).decode('utf-8')}"
                elif header.startswith(b'\x89PNG'):
                    return f"data:image/png;base64,{base64.b64encode(imagen).decode('utf-8')}"
                return url_for('static', filename='img/default_cookie3.svg')
        
        # Si es string y ya es data URI
        if isinstance(imagen, str) and imagen.startswith('data:image/'):
            return imagen
        
        # Si es string que parece base64
        if isinstance(imagen, str) and len(imagen) > 100:  # Longitud arbitraria para base64
            try:
                base64.b64decode(imagen, validate=True)
                return f"data:image/jpeg;base64,{imagen}"
            except:
                pass
    
    except Exception as e:
        print(f"Error procesando imagen: {str(e)}")
    
    return url_for('static', filename='img/default_cookie3.svg')

#########################################################################################################################
@mermas_bp.route('/eliminar-galleta', methods=['POST'])
def eliminar_galleta_list():
    if request.method == 'POST':
        try:
            galleta_id = request.form.get('galleta_id')
            galletas_seleccionadas = request.form.get('galletas_seleccionadas', '').split(',')
            
            if galleta_id:
                galletas_seleccionadas = [g for g in galletas_seleccionadas if g != galleta_id]
                flash("Galleta eliminada correctamente", "success")
            
            return redirect(url_for('mermas.mostrar_galletas_merma',
                                seleccionadas=','.join(filter(None, galletas_seleccionadas))))
            
        except Exception as e:
            current_app.logger.error(f"Error al eliminar galleta: {str(e)}", exc_info=True)
            flash("Error técnico al eliminar galleta", "danger")
            return redirect(url_for('mermas.mostrar_galletas_merma'))
############################################################################################################################
def obtener_galletas_con_stock():
    """Consulta galletas con stock disponible y devuelve lista procesada"""
    galletas = db.session.query(
        TipoGalleta.idTipoGalleta,
        TipoGalleta.nombre,
        TipoGalleta.costo,
        Receta.imagen,
        Receta.pesoIndividualGalleta,
        func.coalesce(func.sum(LoteGalleta.cantidadDisponible), 0).label('stock')
    ).join(Receta, TipoGalleta.idReceta == Receta.idReceta)\
     .outerjoin(LoteGalleta, (TipoGalleta.idTipoGalleta == LoteGalleta.idTipoGalleta) & 
               (LoteGalleta.estatus == 'terminada'))\
     .group_by(TipoGalleta.idTipoGalleta, Receta.imagen, Receta.pesoIndividualGalleta)\
     .having(func.coalesce(func.sum(LoteGalleta.cantidadDisponible), 0) > 0)\
     .all()

    # Procesar datos para el template
    return [{
        'id': g.idTipoGalleta,
        'nombre': g.nombre,
        'imagen': procesar_imagen_galleta(g.imagen),
        'stock': g.stock,
        'costo': f"${g.costo:.2f}",
        'peso': f"{g.pesoIndividualGalleta}g"
    } for g in galletas]
##############################################################################
def registrar_merma_galletas(galletas_seleccionadas_ids, stock_disponible):
    """Función para registrar múltiples mermas de diferentes tipos de galletas"""
    logging.info('registro d emermas galleta')
    errores = []
    mermas_validas = []
    
    # Validar cada galleta seleccionada
    for galleta_id in galletas_seleccionadas_ids:
        
        cantidad_str = request.form.get(f'cantidad_{galleta_id}', '').strip()
        tipo_merma = request.form.get(f'tipo_merma_{galleta_id}', '').strip()
        
        # Validaciones básicas
        if not cantidad_str or not tipo_merma:
            error_msg = f"Faltan datos para la galleta ID {galleta_id}"
            errores.append(error_msg)
            continue
        
        try:
            cantidad = float(cantidad_str)
            
            if cantidad <= 0:
                error_msg = f"Cantidad debe ser mayor a cero para galleta ID {galleta_id}"
                errores.append(error_msg)
                continue
                
            # Verificar stock disponible
            stock_actual = stock_disponible.get(galleta_id)
            
            if stock_actual is None:
                error_msg = f"Galleta ID {galleta_id} no encontrada en inventario"
                errores.append(error_msg)
                continue
                
            if cantidad > stock_actual:
                error_msg = f"Stock insuficiente para galleta ID {galleta_id}. Disponible: {stock_actual}, Intentó: {cantidad}"
                errores.append(error_msg)
                continue
                
            mermas_validas.append({
                'id': galleta_id,
                'cantidad': cantidad,
                'tipo': tipo_merma
            })
            
        except ValueError as ve:
            error_msg = f"Cantidad no válida para galleta ID {galleta_id}"
            print(f"EXCEPCIÓN EN CONVERSIÓN: {ve} - {error_msg}")
            errores.append(error_msg)
    
    # Si hay errores, mostrarlos y salir
    if errores:
        for error in errores:
            flash(error, "danger")
        return redirect(url_for('mermas.mostrar_galletas_merma'))
    
    # Procesar mermas válidas
    if mermas_validas:
        try:
            # Registrar cada merma individualmente
            for merma in mermas_validas:
                print(f"\nRegistrando merma para galleta ID: {merma['id']}")
                
                # Crear registro principal de merma para ESTA galleta
                nueva_merma = RegistroMerma(
                    categoria='galletas',
                    tipoMerma=merma['tipo'],  # Usar el tipo específico de cada merma
                    fecha=datetime.now(),
                    cantidad=merma['cantidad']  # Solo la cantidad de esta merma
                )
                db.session.add(nueva_merma)
                db.session.flush()  # Para obtener el ID
                
                # Registrar relación galleta-merma
                merma_galleta = MermaGalleta(
                    idRegistroMerma=nueva_merma.idRegistroMerma,
                    idTipoGalleta=merma['id']
                )
                db.session.add(merma_galleta)
                
                # Actualizar stock en lotes (FIFO)
                cantidad_restante = merma['cantidad']
                lotes = LoteGalleta.query.filter_by(
                    idTipoGalleta=merma['id'],
                    estatus='terminada'
                ).order_by(LoteGalleta.fechaPreparacion).all()
                
                for lote in lotes:
                    if cantidad_restante <= 0:
                        break
                    
                    if lote.cantidadDisponible >= cantidad_restante:
                        lote.cantidadDisponible -= cantidad_restante
                        cantidad_restante = 0
                    else:
                        cantidad_restante -= lote.cantidadDisponible
                        lote.cantidadDisponible = 0
                
                if cantidad_restante > 0:
                    db.session.rollback()
                    flash(f"No hay suficiente stock para la galleta ID {merma['id']}", "danger")
                    return redirect(url_for('mermas.mostrar_galletas_merma'))
            
            # Confirmar todos los cambios
            db.session.commit()
            flash("Mermas registradas y stock actualizado correctamente", "success")
            return redirect(url_for('mermas.mostrar_galletas_merma'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al registrar merma: {str(e)}", exc_info=True)
            flash(f"Error al registrar las mermas: {str(e)}", "danger")
            return redirect(url_for('mermas.mostrar_galletas_merma'))
    
    flash("No hay mermas válidas para registrar", "warning")
    return redirect(url_for('mermas.mostrar_galletas_merma'))