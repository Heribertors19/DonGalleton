from flask import Blueprint,request,redirect,render_template,flash, url_for, current_app
from app.models import LoteGalleta,TipoGalleta,Receta,IngredienteReceta,Insumo,UnidadMedida,DetalleCompra
from sqlalchemy.orm import joinedload
from app import db
from sqlalchemy import case, desc
import base64
from sqlalchemy import func,or_
import logging
from flask_login import login_user, logout_user, login_required, current_user

produccion_bp = Blueprint('produccion', __name__ , url_prefix='/produccion')


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
#################################################################################
@produccion_bp.route('/ordenes')
@login_required
def lista_ordenes():
    logging.info('Listado de ordenes')
    # Consulta que incluye el tipo de galleta mediante joinedload y ordena los resultados
    ordenes = LoteGalleta.query.options(
        db.joinedload(LoteGalleta.tipo_galleta)  # Carga el tipo de galleta relacionado
    ).order_by(
        db.case((LoteGalleta.estatus == 'sin_iniciar', 0), else_=1),  
        LoteGalleta.fechaPreparacion.desc(),
        LoteGalleta.cantidadProducida
    ).all()
    
    return render_template('produccion/lista_ordenes.html', ordenes=ordenes)
###################################################################################
@produccion_bp.route('/orden/<int:id_lote>')
def ver_orden(id_lote):
    logging.info('ver ordenes')
    try:
        # Primero obtenemos el lote con su tipo de galleta
        lote = db.session.query(LoteGalleta)\
            .options(joinedload(LoteGalleta.tipo_galleta))\
            .filter(LoteGalleta.idLoteGalleta == id_lote)\
            .first_or_404()

        # Consulta equivalente a tu SQL de Workbench
        detalle_receta = db.session.query(
            TipoGalleta.idTipoGalleta,
            TipoGalleta.nombre.label('nombre_galleta'),
            Receta.galletasProducidas.label('cantidad_producida'),
            Receta.pesoIndividualGalleta.label('peso_individual'),
            func.length(Receta.imagen).label('imagen_length'),
            Receta.instrucciones.label('instrucciones'),
            func.group_concat(
                func.concat(Insumo.nombre, ' - ', IngredienteReceta.cantidad, ' ', UnidadMedida.abreviatura)
                .op('SEPARATOR')(', ')
            ).label('ingredientes')
        ).join(Receta, TipoGalleta.idReceta == Receta.idReceta)\
        .outerjoin(IngredienteReceta, Receta.idReceta == IngredienteReceta.idReceta)\
        .outerjoin(Insumo, IngredienteReceta.idInsumo == Insumo.idInsumo)\
        .outerjoin(UnidadMedida, IngredienteReceta.idUnidadMedida == UnidadMedida.idUnidadMedida)\
        .filter(TipoGalleta.idTipoGalleta == lote.tipo_galleta.idTipoGalleta)\
        .group_by(TipoGalleta.idTipoGalleta, Receta.idReceta)\
        .first()
        # Verificar el valor de detalle_receta antes de procesarlo
        current_app.logger.debug(f"Detalle receta: {detalle_receta}")

        if not detalle_receta:
            raise ValueError("No se encontró la receta asociada")

        # Verifica que ingredientes no sea None
        ingredientes_lista = detalle_receta.ingredientes.split(', ') if detalle_receta.ingredientes else []

        # Procesar imagen para el template
        imagen_base64 = None
        if lote.tipo_galleta.receta.imagen:
            from base64 import b64encode
            imagen_base64 = b64encode(lote.tipo_galleta.receta.imagen).decode('utf-8')

        # Formatear ingredientes como lista
        ingredientes_lista = detalle_receta.ingredientes.split('\n') if detalle_receta.ingredientes else []

        return render_template('produccion/detalle_orden.html',
                            lote=lote,
                            detalle_receta=detalle_receta,
                            estados=ESTADOS_PRODUCCION,
                            hora_local=lote.fecha_local.strftime("%H:%M %p") if lote.fecha_local else "N/A",
                            ingredientes=ingredientes_lista,
                            imagen_base64=imagen_base64)
        
    except Exception as e:
        current_app.logger.error(f"Error en ver_orden {id_lote}: {str(e)}")
        
        flash(f"Error al cargar los detalles de la orden: {str(e)}", "danger")
        return redirect(url_for('produccion.lista_ordenes'))

###################################################################################
@produccion_bp.route('/receta/<int:id_receta>')
def obtener_receta(id_receta):
    logging.info('tomar la receta')
    receta = Receta.query.get_or_404(id_receta)
    
    # Procesar la imagen si existe
    imagen_base64 = None
    if receta.imagen:
        imagen_base64 = base64.b64encode(receta.imagen).decode('utf-8')
    
    # Obtener los ingredientes asociados a la receta
    ingredientes = db.session.query(
        Insumo.nombre,
        IngredienteReceta.cantidad,
        Insumo.unidadMedida
    ).join(
        IngredienteReceta,
        IngredienteReceta.idInsumo == Insumo.idInsumo
    ).filter(
        IngredienteReceta.idReceta == id_receta
    ).all()
    
    # Formatear las instrucciones para el template
    instrucciones_formateadas = []
    if receta.instrucciones:
        instrucciones_formateadas = [
            f"- {instruccion.strip()}" 
            for instruccion in receta.instrucciones.split('\n') 
            if instruccion.strip()
        ]
    
    return render_template(
        'produccion/detalle_receta.html',
        receta=receta,
        imagen_base64=imagen_base64,
        ingredientes=ingredientes,
        instrucciones=instrucciones_formateadas
    )

#################################################################################
@produccion_bp.route('/orden/<int:id_lote>/actualizar', methods=['GET', 'POST'])
def actualizar_etapa(id_lote):
    logging.info('Actualizacion de etapas')
    lote = LoteGalleta.query.get_or_404(id_lote)
    
    if request.method == 'POST':
        try:
            nuevo_estatus = request.form['nuevo_estatus']
            
            if nuevo_estatus not in ESTADOS_PRODUCCION:
                flash('Estado inválido', 'danger')
                return redirect(url_for('produccion.actualizar_etapa', id_lote=id_lote))
            
            lote.estatus = nuevo_estatus
            db.session.commit()
            flash('Estado actualizado correctamente', 'success')
            return redirect(url_for('produccion.ver_orden', id_lote=id_lote))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar: {str(e)}', 'danger')
    
    # GET: Mostrar formulario
    return render_template('produccion/actualizar_estado.html', 
                         lote=lote, 
                         estados=ESTADOS_PRODUCCION)
##################################################################################
@produccion_bp.route('/orden/<int:id_lote>/confirmar-terminar', methods=['POST'])
def confirmar_terminar_orden(id_lote):
    logging.info('terminar la orden de produccion')
    """Muestra el modal de confirmación antes de terminar la orden"""
    lote = LoteGalleta.query.get_or_404(id_lote)
    
    if 'galletas_buenas' not in request.form:
        flash('Debe ingresar la cantidad producida', 'danger')
        return redirect(url_for('produccion.ver_orden', id_lote=id_lote))
    
    try:
        cantidad = int(request.form['galletas_buenas'])
        if cantidad <= 0:
            raise ValueError("La cantidad debe ser positiva")
            
        # Mostramos la misma vista pero con el modal visible
        return render_template('produccion/detalle_orden.html',
                           lote=lote,
                           estados=ESTADOS_PRODUCCION,
                           hora_local=lote.fecha_local.strftime("%H:%M %p"),
                           cantidad_pendiente=cantidad)
    
    except ValueError:
        return redirect(url_for('produccion.ver_orden', id_lote=id_lote))
##################################################################################
@produccion_bp.route('/orden/<int:id_lote>/terminar', methods=['POST'])
def terminar_orden(id_lote):
    logging.info('terminar la orden de produccion')
    print("\n[1] Iniciando terminación de orden")

    # 1. Obtener el lote
    lote = LoteGalleta.query.get_or_404(id_lote)
    print(f"[2] Lote obtenido: ID={lote.idLoteGalleta}, Estatus={lote.estatus}, CantidadProducida={lote.cantidadProducida}")

    # 2. Validar cantidad de galletas
    galletas_buenas = request.form.get('galletas_buenas', '').strip()
    print(f"[3] Cantidad recibida de galletas buenas (string): '{galletas_buenas}'")

    if not galletas_buenas.isdigit():
        print("[4] ERROR: La cantidad ingresada no es un número válido")
        return redirect(url_for('produccion.ver_orden', id_lote=id_lote))

    galletas_buenas = int(galletas_buenas)
    print(f"[5] Cantidad validada de galletas buenas (int): {galletas_buenas}")

    try:
        # 3. Obtener la receta asociada al lote
        receta = Receta.query.get(lote.receta_id)
        if not receta:
            print("[6] ERROR: Receta no encontrada para el lote")
            return redirect(url_for('produccion.ver_orden', id_lote=id_lote))

        print(f"[7] Receta obtenida: ID={receta.idReceta}, Galletas esperadas por receta={receta.galletasProducidas}")

        # 4. Obtener ingredientes y stock disponible
        ingredientes = db.session.query(
            IngredienteReceta.idInsumo,
            IngredienteReceta.cantidad,
            Insumo.nombre.label('nombre_insumo'),
            func.sum(DetalleCompra.cantidadDisponible).label('stock_disponible')
        ).join(
            Insumo, IngredienteReceta.idInsumo == Insumo.idInsumo
        ).outerjoin(
            DetalleCompra, Insumo.idInsumo == DetalleCompra.idInsumo
        ).filter(
            IngredienteReceta.idReceta == receta.idReceta,
            or_(
                DetalleCompra.cantidadDisponible > 0,
                DetalleCompra.idDetalleCompra.is_(None)
            )
        ).group_by(
            IngredienteReceta.idInsumo,
            IngredienteReceta.cantidad,
            Insumo.nombre
        ).all()

        print(f"[8] Ingredientes obtenidos: {len(ingredientes)} encontrados")

        # 5. Verificar stock y calcular necesidades
        insumos_a_descontar = []
        insumos_faltantes = []

        for ingrediente in ingredientes:
            cantidad_necesaria = (ingrediente.cantidad / receta.galletasProducidas) * galletas_buenas
            stock_disponible = ingrediente.stock_disponible or 0
            print(f"[9] Insumo: {ingrediente.nombre_insumo} | Necesario: {cantidad_necesaria} | Stock disponible: {stock_disponible}")

            if stock_disponible < cantidad_necesaria:
                print(f"[10] ERROR: Stock insuficiente para {ingrediente.nombre_insumo}")
                insumos_faltantes.append({
                    'nombre': ingrediente.nombre_insumo,
                    'requerido': round(cantidad_necesaria, 2),
                    'disponible': round(stock_disponible, 2)
                })
            else:
                insumos_a_descontar.append({
                    'idInsumo': ingrediente.idInsumo,
                    'cantidad': cantidad_necesaria,
                    'nombre': ingrediente.nombre_insumo
                })
        if insumos_faltantes:
            # Mostrar alerta usando flash con los insumos faltantes
            faltantes_texto = ', '.join(
                f"{i['nombre']} (Requerido: {i['requerido']}, Disponible: {i['disponible']})"
                for i in insumos_faltantes
            )
            flash(f'No hay suficiente stock para los siguientes insumos: {faltantes_texto}', 'danger')
            return redirect(url_for('produccion.ver_orden', id_lote=id_lote))

        # 6. Actualizar el lote
        lote.cantidadProducida = galletas_buenas
        lote.cantidadDisponible = galletas_buenas
        lote.estatus = 'terminada'
        lote.fechaPreparacion = db.func.now()
        db.session.add(lote)

        print(f"[12] Lote actualizado: ID={lote.idLoteGalleta}, Producidas={lote.cantidadProducida}, Disponible={lote.cantidadDisponible}, Estatus={lote.estatus}")

        # 7. Descontar insumos (FIFO)
        for insumo in insumos_a_descontar:
            cantidad_restante = insumo['cantidad']
            print(f"[13] Procesando descuento para insumo: {insumo['nombre']}, Total a descontar: {cantidad_restante}")

            lotes_compra = DetalleCompra.query\
                .filter(
                    DetalleCompra.idInsumo == insumo['idInsumo'],
                    DetalleCompra.cantidadDisponible > 0
                )\
                .order_by(DetalleCompra.fechaCaducidadInsumo.asc())\
                .all()

            print(f"[14] Lotes de compra encontrados: {len(lotes_compra)}")

            for lote_compra in lotes_compra:
                if cantidad_restante <= 0:
                    break
                
                a_descontar = min(cantidad_restante, lote_compra.cantidadDisponible)
                print(f"[15] LoteCompra ID={lote_compra.idDetalleCompra} | Antes: {lote_compra.cantidadDisponible} | Descontando: {a_descontar}")
                lote_compra.cantidadDisponible -= a_descontar
                cantidad_restante -= a_descontar
                db.session.add(lote_compra)

            print(f"[16] Descuento completo para insumo: {insumo['nombre']}")

        db.session.commit()
        print("[17] Transacción confirmada en la base de datos")
        return redirect(url_for('produccion.lista_ordenes'))

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al terminar producción: {str(e)}", exc_info=True)
        print(f"[ERROR] Ocurrió un error al terminar producción: {str(e)}")
        flash(f'Error al terminar producción: {str(e)}', 'danger')
        return redirect(url_for('produccion.ver_orden', id_lote=id_lote))


#################################################################################################
def calcular_costo_produccion(id_receta):
    logging.info('calcular los costos de procuccion')
    """Calcula el costo de producción de una receta"""
    from app.models import IngredienteReceta, Insumo, Receta  # Importaciones necesarias

    receta = Receta.query.get(id_receta)
    if not receta:
        return None

    costo_total = 0
    ingredientes = IngredienteReceta.query.filter_by(idReceta=id_receta).all()
    for ingrediente in ingredientes:
        insumo = Insumo.query.get(ingrediente.idInsumo)
        if insumo:
            costo_insumo = ingrediente.cantidad * insumo.precioUnitario
            costo_total += costo_insumo
    if receta.galletasProducidas > 0:
        costo_unitario = costo_total / receta.galletasProducidas
    else:
        costo_unitario = 0
    return costo_total, costo_unitario

#################################################################################################
@produccion_bp.route('/actualizar-costos/<int:id_tipo>', methods=['POST'])
def actualizar_costos(id_tipo):
    logging.info('actualizacion de costos')
    """Actualiza los costos de producción de un tipo de galleta"""
    tipo_galleta = TipoGalleta.query.get_or_404(id_tipo)
    
    if not tipo_galleta.receta:
        flash("No se encontró la receta asociada", 'danger')
        return redirect(url_for('produccion.lista_ordenes'))

   
    costo_total, costo_unitario = calcular_costo_produccion(tipo_galleta.idReceta)
    
    tipo_galleta.costoProduccionUnitario = costo_unitario
    tipo_galleta.costoProduccionTotal = costo_total

    try:
        db.session.commit()
        flash("Costos actualizados correctamente", 'success')
    except Exception as e:
        db.session.rollback()
        flash(f"Error al actualizar costos: {str(e)}", 'danger')

    return redirect(url_for('produccion.lista_ordenes'))
#################################################################################################
@produccion_bp.route('/nueva-orden-automatica/<int:id_tipo>', methods=['GET'])
def crear_orden_automatica(id_tipo):
    logging.info('Crear ordenes en automatico')
    """Crea una orden de producción automática basada en stock bajo."""
    tipo_galleta = TipoGalleta.query.get_or_404(id_tipo)

    try:
        # Lógica para cantidad a producir (ejemplo: 200 unidades o fórmula personalizada)
        cantidad_a_producir = 200  # Puedes calcular esto dinámicamente
        nuevo_lote = LoteGalleta(
            idTipoGalleta=id_tipo,
            cantidadProducida=0,  # Se actualizará al terminar
            cantidadDisponible=0,
            estatus='sin_iniciar',
            es_automatica=True  # Agrega este campo al modelo si quieres trackear órdenes automáticas
        )

        db.session.add(nuevo_lote)
        db.session.commit()

        flash(f"Orden automática creada para {tipo_galleta.nombre} (Stock bajo)", 'success')
        return redirect(url_for('produccion.ver_orden', id_lote=nuevo_lote.idLoteGalleta))

    except Exception as e:
        db.session.rollback()
        flash(f"Error al crear orden automática: {str(e)}", 'danger')
        return redirect(url_for('stock.cookie_stock'))
##############################################################################################################

ESTADOS_PRODUCCION = [
    'sin_iniciar',
    'en_preparacion',
    'amasando',
    'cortando',
    'mezclando',
    'cocinando',
    'enfriando',
    'terminada'
]