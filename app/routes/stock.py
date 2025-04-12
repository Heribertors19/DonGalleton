from flask import Blueprint, url_for, redirect, flash,render_template,request
from app.models import TipoGalleta,LoteGalleta,Receta
from app import db
from sqlalchemy import func
from flask import current_app
import base64
from datetime import datetime
import logging
stock_bp = Blueprint('stock', __name__, url_prefix='/stock')


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
@stock_bp.route('/galletas', methods=['GET'])
def cookie_stock():
    logging.info('Cargando el stock de las galleatas')
    try:
        # Obtención de parámetros de búsqueda y filtro desde la URL
        search_query = request.args.get('search', '')
        tipo_filter = request.args.get('tipo', '')

        # Consulta SQL optimizada con filtros de búsqueda y tipo
        from sqlalchemy import and_, func

        query = db.session.query(
            TipoGalleta.idTipoGalleta,
            TipoGalleta.nombre,
            TipoGalleta.costo,
            Receta.imagen,
            Receta.pesoIndividualGalleta,
            func.coalesce(func.sum(LoteGalleta.cantidadDisponible), 0).label('stock')
        ).join(
            Receta, 
            and_(
                TipoGalleta.idReceta == Receta.idReceta,
                Receta.estatus == 'ACTIVO'
            )
        ).outerjoin(
            LoteGalleta,
            and_(
                TipoGalleta.idTipoGalleta == LoteGalleta.idTipoGalleta,
                LoteGalleta.estatus == 'terminada'
            )
        ).group_by(
            TipoGalleta.idTipoGalleta,
            TipoGalleta.nombre,
            TipoGalleta.costo,
            Receta.imagen,
            Receta.pesoIndividualGalleta
        ).having(
            func.coalesce(func.sum(LoteGalleta.cantidadDisponible), 0) >= 0
        ).order_by(
            TipoGalleta.nombre.asc()
        )
        # Si hay un filtro por tipo de galleta, lo aplicamos
        if tipo_filter:
            query = query.filter(TipoGalleta.idTipoGalleta == tipo_filter)

        # Si hay un término de búsqueda, lo aplicamos en el nombre de la galleta
        if search_query:
            query = query.filter(TipoGalleta.nombre.ilike(f"%{search_query}%"))

        # Ejecutamos la consulta con los filtros aplicados
        galletas = query.group_by(TipoGalleta.idTipoGalleta, Receta.imagen, Receta.pesoIndividualGalleta).all()

        datos = []
        for idx, g in enumerate(galletas, 1):
            # Procesamiento de imagen (se mantiene igual)
            img = url_for('static', filename='img/default.png')
            if g.imagen:
                try:
                    if isinstance(g.imagen, bytes):
                        img_str = g.imagen.decode('utf-8')
                    else:
                        img_str = str(g.imagen)
                    
                    if img_str.startswith('data:image'):
                        img = img_str
                    elif img_str.startswith('/9j/'):
                        img = f"data:image/jpeg;base64,{img_str}"
                    elif img_str.startswith('iVBORw0KGgo'):
                        img = f"data:image/png;base64,{img_str}"
                    elif isinstance(g.imagen, bytes):
                        header = g.imagen[:4]
                        if header.startswith(b'\xFF\xD8'):
                            img = f"data:image/jpeg;base64,{base64.b64encode(g.imagen).decode('utf-8')}"
                        elif header.startswith(b'\x89PNG'):
                            img = f"data:image/png;base64,{base64.b64encode(g.imagen).decode('utf-8')}"
                        else:
                            raise ValueError("Formato de imagen no soportado")
                    else:
                        raise ValueError("Formato de imagen no soportado")
                except Exception as e:
                    current_app.logger.error(f"Error imagen ID {g.idTipoGalleta}: {str(e)}")

            # Agregar datos a la lista
            datos.append({
                'id': g.idTipoGalleta,
                'nombre': g.nombre,
                'imagen': img,
                'stock': g.stock,
                'costo': f"${g.costo:.2f}",
                'peso': f"{g.pesoIndividualGalleta}g"  # Usando el campo específico
            })
        # Obtener todos los tipos de galleta para el filtro de selección
        tipos_galletas = TipoGalleta.query.all()
        # Si se ha filtrado alguna búsqueda, mostrar el primer registro (opcional)
        if datos:
            primera = datos[0]
        # Renderizamos la plantilla con los datos y los tipos de galleta para el filtro
        return render_template('stock/stock_completo.html', galletas=datos, tipos_galletas=tipos_galletas)

    except Exception as e:
        current_app.logger.error(f"Error en cookie_stock: {str(e)}", exc_info=True)
        flash("Error al cargar el stock", "danger")
        return redirect(url_for('stock.cookie_stock'))

##################################################################
@stock_bp.route('/actualizar-stock', methods=['POST'])
def update_stock():
    """Ajustar el stock (usado despues de registrar mermas)"""
    pass
#################################################################
@stock_bp.route('/verificar-stock-produccion', methods=['GET'])
def check_stock_production():
    logging.info('verificacion de stock')
    """Verifica el stock y sugiere órdenes de producción si es necesario."""
    from sqlalchemy import func

    # Obtener tipos de galleta con stock bajo (ejemplo: menos de 100 unidades)
    tipos_con_stock_bajo = db.session.query(
        TipoGalleta.idTipoGalleta,
        TipoGalleta.nombre,
        func.sum(LoteGalleta.cantidadDisponible).label('stock_actual')
    ).join(LoteGalleta).group_by(TipoGalleta.idTipoGalleta).having(
        func.sum(LoteGalleta.cantidadDisponible) < 100  # Ajusta este valor según tu necesidad
    ).all()

    # Si hay tipos con stock bajo, redirigir a creación automática de orden
    if tipos_con_stock_bajo:
        tipo_a_producir = tipos_con_stock_bajo[0]  # Prioriza el primero (puedes mejorar esta lógica)
        flash(f"Stock bajo detectado: {tipo_a_producir.nombre} ({tipo_a_producir.stock_actual} unidades)", 'warning')
        return redirect(url_for('produccion.crear_orden_automatica', id_tipo=tipo_a_producir.idTipoGalleta))

    flash("Stock suficiente, no se requieren nuevas órdenes de producción.", 'info')
    return redirect(url_for('stock.cookie_stock'))  # Redirige al listado de stock
#################################################################
@stock_bp.route('/sugerir-ordenes', methods=['GET'])
def sugerir_ordenes_produccion():
    logging.info('verificacion de stock')
    """Muestra tipos de galleta con stock bajo para generar órdenes manuales."""
    # Consulta SQLAlchemy: Tipos con stock disponible < stock mínimo
    subquery = (
        db.session.query(
            LoteGalleta.idTipoGalleta,
            func.sum(LoteGalleta.cantidadDisponible).label('stock_actual')
        )
        .filter(LoteGalleta.estatus != 'terminada')
        .group_by(LoteGalleta.idTipoGalleta)
        .subquery()
    )

    tipos_con_stock_bajo = (
    db.session.query(
        TipoGalleta.idTipoGalleta,
        TipoGalleta.nombre,
        TipoGalleta.stock_minimo,
        func.coalesce(subquery.c.stock_actual, 0).label('stock_actual')  # Reemplaza NULL con 0
    )
    .outerjoin(subquery, TipoGalleta.idTipoGalleta == subquery.c.idTipoGalleta)
    .filter(func.coalesce(subquery.c.stock_actual, 0) < TipoGalleta.stock_minimo)  # Maneja casos NULL
    .all()
)

    return render_template(
        'stock/sugerir_ordenes.html',
        tipos=tipos_con_stock_bajo
    )
#################################################################
@stock_bp.route('/crear-orden', methods=['POST'])
def crear_orden():
    logging.info('Creacion de ordenes de compra')
    try:
        # Obtener el id_tipo_galleta del formulario
        id_tipo_galleta = request.form.get('id_tipo_galleta')
        if not id_tipo_galleta:
            flash('Debe seleccionar un tipo de galleta', 'danger')
            return redirect(url_for('stock.ver_stock'))  

        # Obtener la receta asociada al tipo de galleta seleccionado
        tipo_galleta = TipoGalleta.query.filter_by(idTipoGalleta=id_tipo_galleta).first()
        if not tipo_galleta:
            flash('Tipo de galleta no encontrado', 'danger')
            return redirect(url_for('stock.galletas'))

        receta = tipo_galleta.receta  # La receta asociada al tipo de galleta
        if not receta:
            flash('Receta no encontrada para este tipo de galleta', 'danger')
            return redirect(url_for('stock.galletas'))

        # Crear nuevo lote de galletas con los datos de la receta
        nuevo_lote = LoteGalleta(
            idTipoGalleta=id_tipo_galleta,
            cantidadProducida=0,
            cantidadDisponible=0,
            estatus='sin_iniciar',
            receta=receta  # Asegúrate de que `receta` es un objeto válido
        )

        db.session.add(nuevo_lote)
        db.session.commit()

        flash(f'Orden de producción creada exitosamente con la receta: {receta.nombre}', 'success')
        return redirect(url_for('stock.cookie_stock'))  

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al crear orden: {str(e)}", exc_info=True)  # Para registrar el error
        flash(f'Error al crear orden: {str(e)}', 'danger')
        return redirect(url_for('stock.cookie_stock'))

#################################################################

#################################################################