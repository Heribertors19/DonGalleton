from app import db
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import current_user, login_user, logout_user, login_required
import pytz
import secrets
from flask import make_response
from functools import wraps
from app.models import Menu

# Para manipulación de headers (si necesitas más control)
from flask import Response

# Para el middleware de no-cache (si lo separas en otro archivo)
from flask import after_this_request

home_bp = Blueprint("home", __name__, template_folder="../templates/home")
inicio_bp = Blueprint("inicio", __name__, template_folder="../templates/inicio")
home_c = Blueprint("homec", __name__, template_folder="../templates/homec")


#@home_bp.route("/")
#@login_required
#def home():
    #menus = Menu.query.filter_by(idRol=current_user.idRol).all()
    #return render_template("home.html", menus=menus)

def secure_route(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Verificar autenticación
        if not current_user.is_authenticated:
            flash("Por favor, inicia sesión para continuar.", "warning")
            return redirect(url_for('auth.login'))
        
        # Configurar headers de no-caché
        response = make_response(f(*args, **kwargs))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    return decorated_function


@home_bp.route("/home")
@login_required
def home():
    if current_user.idRol != 1:
        flash("No tienes permiso para acceder a esta página.", "danger")
        return redirect(url_for('auth.login'))

    menus = Menu.query.filter_by(idRol=1).all()

    # Gráfico de líneas: contar usuarios que iniciaron sesión por día (últimos 7 días)
    resultados = db.session.execute(text("""
        SELECT DATE(ultima_sesion) AS dia, COUNT(*) AS cantidad
        FROM usuario
        WHERE ultima_sesion IS NOT NULL
        GROUP BY dia
        ORDER BY dia DESC
        LIMIT 7
    """))

    dias = []
    cantidad_por_dia = []
    for fila in resultados:
        dias.append(fila.dia.strftime('%d/%m'))
        cantidad_por_dia.append(fila.cantidad)

    # Gráfico de anillo: conteo por tipo de usuario (idRol 2 y 3)
    roles = db.session.execute(text("""
        SELECT idRol, COUNT(*) as cantidad
        FROM usuario
        WHERE idRol IN (2, 3)
        GROUP BY idRol
    """))

    cantidad_por_rol = [0, 0]
    for r in roles:
        if r.idRol == 2:
            cantidad_por_rol[0] = r.cantidad
        elif r.idRol == 3:
            cantidad_por_rol[1] = r.cantidad

    # Tabla: últimos inicios de sesión
    ultimos_logins = db.session.execute(text("""
        SELECT u.nombre, u.nombreUsuario AS usuario, r.descripcion AS rol, u.ultima_sesion AS fecha
        FROM usuario u
        JOIN rol r ON u.idRol = r.idRol
        WHERE u.ultima_sesion IS NOT NULL
        ORDER BY u.ultima_sesion DESC
        LIMIT 10
    """)).fetchall()

    return render_template(
        "home.html",
        menus=menus,
        dias=dias[::-1],
        cantidad_por_dia=cantidad_por_dia[::-1],
        cantidad_por_rol=cantidad_por_rol,
        ultimos_logins=ultimos_logins
    )


@home_bp.route("/")
def h():
    return redirect(url_for('home.homeStore'))

@inicio_bp.route("/inicio")
@login_required
def inicio():
    if current_user.idRol == 2:
        menus = Menu.query.filter_by(idRol=2).all()
        return render_template("inicio.html", menus=menus)
    else:
      
        flash("No tienes permiso para acceder a esta página. Por favor, inicia sesión.", "danger")
        return redirect(url_for('auth.login')) 


@home_c.route("/homec")
@login_required
def homec():
    if current_user.idRol == 3:
        menus = Menu.query.filter_by(idRol=3).all()
        return render_template("homec.html", menus=menus)
    else:
        flash("No tienes permiso para acceder a esta página. Por favor, inicia sesión.", "danger")
        return redirect(url_for('auth.login')) 
    

import datetime
import traceback
from venv import logger
from sqlalchemy import  text
from app import db
from flask import Blueprint, json, jsonify, render_template, redirect, url_for, flash, request, make_response
from flask_login import current_user, login_required 
from functools import wraps
from app.models import  Menu
from flask_wtf.csrf import generate_csrf
from app.routes.auth import process_cookie_image
from app.services import CompraService, PedidosSerivce, StoreOnlineService
from functools import wraps
from flask import request, redirect, session, url_for
from flask_login import current_user



def auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

#-------------------------------------------------------------
@home_bp.route("/onlineStore")
#@login_required
def homeStore():
    try:
        galletas = StoreOnlineService.StoreService.get_all_galletas()
        destacadas = StoreOnlineService.StoreService.get_galletas_destacadas()
        
        for galleta in galletas:
            galleta['imagen'] = process_cookie_image(galleta.get('imagen'))
            galleta['disponible'] = galleta.get('stock', 0) > 0
        
        for destacada in destacadas:
            destacada['imagen'] = process_cookie_image(destacada.get('imagen'))
            destacada['disponible'] = destacada.get('stock', 0) > 0
        
        return render_template("homeStore.html", productos=galletas, destacadas=destacadas)
        
    except Exception as e:
        logger.error(f"Error en homeStore: {str(e)}", exc_info=True)
        flash("Error al cargar la tienda", "error")
        return redirect(url_for('auth.login'))
    
@home_bp.route('/api/csrf-token', methods=['GET'])
def get_csrf_token():
    token = generate_csrf()
    return jsonify({'csrf_token': token})

#-------------------------------------------------------------

@home_bp.route('/crear_pedidos', methods=['POST'])
def crear_pedido():
    try:
        data = request.get_json()
        logger.info(f"Datos recibidos para crear pedido: {data}")
        
        # Validación básica
        if not data or 'fechaEntrega' not in data or 'items' not in data:
            return jsonify({
                'success': False,
                'message': 'Se requieren fechaEntrega y items'
            }), 400

        # Validar items
        if not isinstance(data['items'], list) or len(data['items']) == 0:
            return jsonify({
                'success': False,
                'message': 'El pedido debe contener al menos un item'
            }), 400

        # Preparar parámetros para el procedimiento
        params = {
            'nombreUsuario': 'jdsalagu',  # Reemplaza con el usuario de sesión real
            'fecha_entrega': data['fechaEntrega'],
            'items': json.dumps(data['items'])  # Convertir a JSON string
        }

        logger.info(f"Parámetros para el procedimiento: {params}")

        # Llamar al procedimiento almacenado
        query = text("""
            CALL RegistrarPedido(
                :nombreUsuario,
                :fecha_entrega,
                :items,
                @idPedido,
                @numeroPedido,
                @mensaje
            )
        """)

        db.session.execute(query, params)
        
        # Obtener resultados
        result = db.session.execute(text("SELECT @idPedido, @numeroPedido, @mensaje"))
        row = result.fetchone()

        if row and row[0] > 0:  # Éxito
            db.session.commit()
            logger.info(f"Pedido creado exitosamente. ID: {row[0]}, Número: {row[1]}")
            return jsonify({
                'success': True,
                'id_pedido': row[0],
                'numero_pedido': row[1],
                'message': row[2] or 'Pedido registrado exitosamente'
            })
        else:  # Error
            db.session.rollback()
            error_msg = row[2] if row else 'Error desconocido al registrar el pedido'
            logger.error(f"Error al crear pedido: {error_msg}")
            return jsonify({
                'success': False,
                'message': error_msg
            }), 400

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al procesar pedido: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Error interno del servidor: {str(e)}'
        }), 500


#------------------------------------------------------------------
# Ruta para la vista HTML
@home_bp.route('/pedidos', methods=['GET'])
def listar_pedidos():
    filtro_estado = request.args.get('estado')
    search_query = request.args.get('search')
    
    pedidos = PedidosSerivce.PedidosService.get_all_pedidos(filtro_estado, search_query)
    return render_template('pedidos.html', pedidos=pedidos)


@home_bp.route('/pedidos/<int:pedido_id>', methods=['GET'])
def detalle_pedido_api(pedido_id):
    try:
        print(f"\n=== SOLICITUD DE DETALLE DE PEDIDO {pedido_id} ===")
        
        # Obtener los detalles del pedido
        detalle = PedidosSerivce.PedidosService.get_pedido_detalle(pedido_id)
        
        if not detalle:
            print(f"Pedido {pedido_id} no encontrado")
            return jsonify({
                'success': False,
                'error': 'Pedido no encontrado'
            }), 404
        
        # Imprimir detalles básicos en terminal
        print(f"\nDetalles del Pedido {pedido_id}:")
        print(f"Número: {detalle.get('numero_pedido', 'N/A')}")
        print(f"Cliente: {detalle.get('cliente', 'N/A')}")
        print(f"Estado: {detalle.get('estado', 'N/A')}")
        print(f"Fecha Creación: {detalle.get('fecha_creacion', 'N/A')}")
        print(f"Fecha Entrega: {detalle.get('fecha_entrega', 'N/A')}")
        print(f"Total: ${float(detalle.get('total', 0)):.2f}")
        
        # Procesar los productos con mejor manejo de errores
        productos = []
        if detalle.get('productos'):
            print("\nProductos:")
            for producto in detalle['productos']:
                try:
                    nombre = producto.get('nombre', 'Producto sin nombre').strip()
                    cantidad = int(producto.get('cantidad', 0))
                    precio = float(producto.get('precio_unitario', 0))
                    subtotal = cantidad * precio
                    tipo_venta = producto.get('tipo_venta', '')
                    piezas = producto.get('piezas', '')
                    
                    # Imprimir detalles del producto en terminal
                    product_info = f"- {nombre}: {cantidad} x ${precio:.2f} = ${subtotal:.2f}"
                    if tipo_venta:
                        product_info += f" | Tipo: {tipo_venta}"
                    if piezas:
                        product_info += f" | Piezas: {piezas}"
                    print(product_info)
                    
                    productos.append({
                        'nombre': nombre,
                        'cantidad': cantidad,
                        'precio_unitario': precio,
                        'subtotal': subtotal,
                        'tipo_venta': tipo_venta,
                        'piezas': piezas
                    })
                except Exception as e:
                    print(f"Error procesando producto: {producto} - {str(e)}")
                    continue
        else:
            print("\nNo se encontraron productos para este pedido")
        
        print("\n=== FIN DE DETALLES ===")
        
        # Estructurar la respuesta JSON con todos los campos
        respuesta = {
            'success': True,
            'pedido': {
                'id_pedido': detalle.get('idPedido'),
                'numero_pedido': detalle.get('numero_pedido'),
                'fecha_creacion': detalle.get('fecha_creacion'),
                'fecha_entrega': detalle.get('fecha_entrega'),
                'estado': detalle.get('estado', 'Sin estado'),
                'cliente': detalle.get('cliente', ''),
                'contacto': detalle.get('contacto', ''),
                'total': float(detalle.get('total', 0)),
                'productos': productos,
                'id_venta': detalle.get('id_venta'),
                'fecha_venta': detalle.get('fecha_venta'),
                'estado_venta': detalle.get('estado_venta', ''),
                'nombres_productos': detalle.get('nombres_productos', ''),
                'cantidades_productos': detalle.get('cantidades_productos', ''),
                'precios_productos': detalle.get('precios_productos', '')
            }
        }
        
        return jsonify(respuesta)
        
    except Exception as e:
        error_msg = f"Error en detalle_pedido_api para pedido {pedido_id}: {str(e)}"
        print(f"\n{error_msg}")
        return jsonify({
            'success': False,
            'error': error_msg,
            'traceback': traceback.format_exc()
        }), 500
        
@home_bp.route('/pedidos/<int:pedido_id>/estado', methods=['PUT'])
def actualizar_estado_pedido(pedido_id):
    try:
        # Obtener el nuevo estado del JSON recibido
        data = request.get_json()
        nuevo_estado = data.get('estado')
        
        if not nuevo_estado:
            return jsonify({
                'success': False,
                'error': 'Estado no proporcionado'
            }), 400

        # Actualizar el estado del pedido en la base de datos
        success = PedidosSerivce.PedidosService.actualizar_estado_pedido(pedido_id, nuevo_estado)
        
        if not success:
            return jsonify({
                'success': False,
                'error': 'No se pudo actualizar el estado del pedido. Estado no válido o pedido no encontrado.'
            }), 400

        # Obtener las clases CSS para el nuevo estado
        estado_clase = PedidosSerivce.PedidosService.get_estado_clase(nuevo_estado)
        
        return jsonify({
            'success': True,
            'estado': nuevo_estado,
            'estado_clase': estado_clase,
            'message': 'Estado actualizado correctamente'
        })

    except Exception as e:
        error_msg = f"Error al actualizar estado del pedido {pedido_id}: {str(e)}"
        print(f"\n{error_msg}")
        return jsonify({
            'success': False,
            'error': error_msg,
            'traceback': traceback.format_exc()
        }), 500
        
#---------------------------------------------------------------



@home_bp.route('/compras')
def listar_compras():
    try:
        search = request.args.get('search')
        compras = CompraService.CompraService.get_compras(search)
        return render_template('compras.html', compras=compras)
    except Exception as e:
        logger.error(f"Error al listar compras: {str(e)}", exc_info=True)
        return render_template('compras.html', compras=[], error=str(e))

@home_bp.route('/realizar-compra', methods=['POST'])
def realizar_compra():
    response_template = {
        'success': False,
        'message': 'Error desconocido',
        'id_compra': None,
        'total': 0.0
    }

    try:
        data = request.get_json()
        
        # Validación básica
        if not data or 'idProveedor' not in data or 'insumos' not in data:
            response_template['message'] = 'Datos incompletos'
            return jsonify(response_template), 400

        # Procesar compra
        resultado = CompraService.CompraService.realizar_compra(
            id_proveedor=data['idProveedor'],
            fecha_compra=datetime.now(),
            insumos=data['insumos']
        )

        # Asegurar que siempre devolvemos un objeto con la estructura esperada
        if not resultado:
            response_template['message'] = 'No se recibió respuesta del servicio'
            return jsonify(response_template), 500

        return jsonify({
            'success': resultado.get('success', False),
            'message': resultado.get('message', ''),
            'id_compra': resultado.get('id_compra'),
            'total': resultado.get('total', 0.0)
        })

    except Exception as e:
        logger.error(f"Error en realizar-compra: {str(e)}", exc_info=True)
        response_template['message'] = f'Error: {str(e)}'
        return jsonify(response_template), 500

@home_bp.route('/api/proveedores')
def api_proveedores():
    try:
        proveedores = CompraService.CompraService.get_proveedores()
        print("Proveedores obtenidos:", proveedores)  # Debug
        return jsonify(proveedores)
    except Exception as e:
        logger.error(f"Error en api_proveedores: {str(e)}", exc_info=True)
        return jsonify([])

@home_bp.route('/api/insumos')
def api_insumos():
    try:
        insumos = CompraService.CompraService.get_insumos()
        print("Insumos obtenidos:", insumos)  # Debug
        return jsonify(insumos)
    except Exception as e:
        logger.error(f"Error en api_insumos: {str(e)}", exc_info=True)
        return jsonify([])
    
@home_bp.route('/api/compras/<int:id_compra>/detalles')
def get_detalle_compra(id_compra):

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
            return jsonify({'success': False, 'message': 'Compra no encontrada'}), 404
        
        # Obtener detalles de la compra
        query_detalles = text("""
            SELECT 
                i.nombre as nombre,
                dc.cantidad as cantidad,
                dc.cantidadDisponible as cantidad_disponible,
                i.precioActual as precio
            FROM detallecompra dc
            JOIN insumo i ON dc.idInsumo = i.idInsumo
            WHERE dc.idCompra = :id_compra
        """)
        
        detalles = db.session.execute(query_detalles, {'id_compra': id_compra}).fetchall()
        
        return jsonify({
            'success': True,
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
                'precio': float(detalle.precio) if detalle.precio else 0.0
            } for detalle in detalles]
        })
        
    except Exception as e:
        logger.error(f"Error al obtener detalles de compra: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

