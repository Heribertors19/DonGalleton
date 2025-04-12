from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app, jsonify, make_response
from flask_wtf import FlaskForm, RecaptchaField
from wtforms import StringField, PasswordField, SubmitField, SelectField,HiddenField
from wtforms.validators import InputRequired, Length, EqualTo, ValidationError, DataRequired
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import Usuario
from app.models import Rol 
from app import db 
from app import mail
import re
from app.services.UsuarioService import UsuarioService
from datetime import datetime, timedelta
from flask_login import login_user, logout_user, login_required, current_user
import pytz
import secrets
from functools import wraps  
from flask import abort  
import logging
from flask_mail import Message
from werkzeug.security import check_password_hash
from datetime import datetime, timedelta
from flask_login import login_user
import random
import logging

#logging.basicConfig(
    #filename='app_logs.log', 
    #level=logging.ERROR, 
    #format='%(asctime)s - %(levelname)s - %(message)s',  )



zona_horaria_mexico = pytz.timezone("America/Mexico_City")


DIAS_VALIDEZ_CONTRASENIA = 90 

usuarioService = UsuarioService()

# Blueprint para autenticación
auth = Blueprint("auth", __name__, template_folder="../templates/auth")


contraseñas_inseguras = {
    "12345678", "contraseña", "123456789", "qwerty", "abc123456789", "111111111",
    "contraseña1", "123123123123", "bienvenido", "admin"
}

# Función para sanitizar entradas y evitar XSS y otros problemas
def sanitizar_input(input_data):
    sanitized = input_data.strip()
    sanitized = re.sub(r'<|>|&|/|;', '', sanitized)  # Elimina caracteres peligrosos
    return sanitized


def validar_email(form, field):
    sanitized_data = sanitizar_input(field.data)
    # Expresión regular básica para validar email
    patron_email = r"^[\w\.-]+@[\w\.-]+\.\w{2,}$"

    if not re.match(patron_email, sanitized_data):
        raise ValidationError("Ingresa un correo electrónico válido.")
    
    field.data = sanitized_data
# Validaciones de campos
def validar_usuario(form, field):
    sanitized_data = sanitizar_input(field.data)
    if not re.match("^[a-zA-Z0-9]*$", sanitized_data):
        raise ValidationError("El nombre de usuario solo puede contener letras y números.")
    field.data = sanitized_data

def validar_nombre(form, field):
    sanitized_data = sanitizar_input(field.data)
    if not re.match(r"^[a-zA-Z\s]+$", sanitized_data):
        raise ValidationError("El nombre solo puede contener letras y espacios.")
    field.data = sanitized_data

def validar_apellido(form, field):
    sanitized_data = sanitizar_input(field.data)
    if not re.match("^[a-zA-Z]*$", sanitized_data):
        raise ValidationError("El apellido solo puede contener letras.")
    field.data = sanitized_data

def validar_contrasenia(form, field):
    password = sanitizar_input(field.data)
    if not re.search(r'[A-Z]', password):  
        raise ValidationError("La contraseña debe contener al menos una letra mayúscula.")
    if not re.search(r'[a-z]', password):  
        raise ValidationError("La contraseña debe contener al menos una letra minúscula.")
    if not re.search(r'\d', password):  
        raise ValidationError("La contraseña debe contener al menos un número.")
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):  
        raise ValidationError("La contraseña debe contener al menos un carácter especial.")
    field.data = password

def validar_seguridad_contrasenia(form, field):
    password = sanitizar_input(field.data)
    if password in contraseñas_inseguras:
        raise ValidationError("La contraseña ingresada es demasiado común. Usa una más segura.")
    field.data = password


class LoginForm(FlaskForm):
    usuario = StringField("Usuario", validators=[InputRequired(), Length(min=4, max=50), validar_usuario])
    contrasenia = PasswordField("Contraseña", validators=[InputRequired(), Length(min=6)])
    recaptcha = RecaptchaField()
    submit = SubmitField("Iniciar Sesión")

class CambioContraseniaForm(FlaskForm):
    nueva_contrasenia = PasswordField("Nueva Contraseña", validators=[InputRequired()])
    confirmar_contrasenia = PasswordField("Confirmar Contraseña", validators=[InputRequired()])
    submit = SubmitField("Cambiar Contraseña")

class RegistroForm(FlaskForm):
    usuario = StringField("Usuario", validators=[InputRequired(), Length(min=4, max=50), validar_usuario])
    nombre = StringField("Nombre", validators=[InputRequired(), Length(min=4, max=50), validar_nombre])
    apellidoPaterno = StringField("Apellido paterno", validators=[InputRequired(), Length(min=4, max=50), validar_apellido])
    idRol = SelectField("Rol", choices=[
        ('1', 'Administrador'),
        ('2', 'Empleado')
    ], validators=[DataRequired(message="Selecciona un rol.")])
    apellidoMaterno = StringField("Apellido materno", validators=[Length(min=4, max=50), validar_apellido])
    contrasenia = PasswordField("Contraseña", validators=[InputRequired(), Length(min=8), validar_contrasenia, validar_seguridad_contrasenia])
    confirm_contrasenia = PasswordField("Confirmar Contraseña", validators=[InputRequired(), EqualTo("contrasenia", message="Las contraseñas deben coincidir.")])
    email = StringField("Email", validators=[InputRequired(), Length(min=4, max=40), validar_email])
    submit = SubmitField("Registrarse")



class RegistroCForm(FlaskForm):
    usuario = StringField("Usuario", validators=[InputRequired(), Length(min=4, max=50), validar_usuario])
    nombre = StringField("Nombre", validators=[InputRequired(), Length(min=4, max=50), validar_nombre])
    apellidoPaterno = StringField("Apellido paterno", validators=[InputRequired(), Length(min=4, max=50), validar_apellido])
    apellidoMaterno = StringField("Apellido materno", validators=[Length(min=4, max=50), validar_apellido])
    contrasenia = PasswordField("Contraseña", validators=[InputRequired(), Length(min=8), validar_contrasenia, validar_seguridad_contrasenia])
    confirm_contrasenia = PasswordField("Confirmar Contraseña", validators=[InputRequired(), EqualTo("contrasenia", message="Las contraseñas deben coincidir.")])
    email = StringField("Email", validators=[InputRequired(), Length(min=4, max=40), validar_email])
    submit = SubmitField("Registrarse")

class EliminarUsuarioForm(FlaskForm):
     usuario = StringField('Nombre de Usuario', validators=[DataRequired(), Length(min=3, max=50)])
     nombre = StringField('Nombre', validators=[DataRequired(), Length(min=2, max=50)])
     apellidoPaterno = StringField('Apellido Paterno', validators=[DataRequired(), Length(min=2, max=50),validar_apellido])
     apellidoMaterno = StringField('Apellido Materno', validators=[DataRequired(), Length(min=2, max=50),validar_apellido])
     idRol = StringField('Rol',validators=[DataRequired(), Length(min=3, max=50)])
     descripcion = StringField('Descripcion', validators=[DataRequired(), Length(min=3, max=50)])
     estatus = StringField('Estatus', validators=[DataRequired(), Length(min=2, max=50)])
   
     submit = SubmitField('Eliminar Usuario')

class VerificarCodigoForm(FlaskForm):
    codigo = StringField('Código')
    submit = SubmitField('Verificar')

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, Optional

class ModificarUsuarioForm(FlaskForm):
    nombreUsuario = StringField("Nombre de usuario", validators=[InputRequired(), Length(min=4, max=50), validar_usuario])
    nombre = StringField("Nombre",validators=[InputRequired(), Length(min=4, max=50), validar_nombre])
    apellidoPaterno = StringField("Apellido paterno",validators=[InputRequired(), Length(min=4, max=50), validar_apellido])
    apellidoMaterno = StringField("Apellido materno",validators=[InputRequired(), Length(min=4, max=50), validar_apellido])
    email = StringField("Email", validators=[InputRequired(), Length(min=10, max=40),validar_email])
    contrasenia = PasswordField("Contraseña", validators=[InputRequired(), Length(min=8), validar_contrasenia, validar_seguridad_contrasenia])
    confirm_contrasenia = PasswordField("Confirmar contraseña",validators=[InputRequired(), EqualTo("contrasenia", message="Las contraseñas deben coincidir.")])
    idRol = SelectField("Rol", choices=[
        ('1', 'Administrador'),
        ('2', 'Usuario')
    ], validators=[DataRequired(message="Selecciona un rol.")])
    estatus = SelectField("estatus", choices=[
        ('ACTIVO'),
        ('INACTIVO')
    ], validators=[DataRequired(message="Selecciona un estatus.")])

    estatus_bloqueo = SelectField("estatus_bloqueo", choices=[
        ('ACTIVADO'),
        ('DESACTIVADO')
    ], validators=[DataRequired(message="Selecciona un estatus de bloqueo.")])

    submit = SubmitField("Modificar")


MAX_INTENTOS_FALLIDOS = 3
@auth.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        if current_user.idRol == 1:
            return redirect(url_for("home.home"))
        elif current_user.idRol == 2:
            return redirect(url_for("ventas_bp.home_ventas"))
        elif current_user.idRol == 3:
            return redirect(url_for("cocina_bp.home_cocina"))
        else:
            flash("Rol no válido.", "danger")
            return redirect(url_for("auth.logout"))

    form = LoginForm()
    if form.validate_on_submit():
        try:
            usuario = Usuario.query.filter_by(nombreUsuario=form.usuario.data).first()
            if usuario:
                if usuario.estatus_bloqueo == "ACTIVADO":
                    flash("Su cuenta ha sido bloqueada. Contacte al administrador.", "error")
                    return render_template("login.html", form=form)
                
                if check_password_hash(usuario.contrasenia, form.contrasenia.data):
                    if usuario.intentos_fallidos > 0:
                        usuario.intentos_fallidos = 0
                        db.session.commit()
                    
                    codigo_verificacion = random.randint(100000, 999999)
                    session['codigo_verificacion'] = codigo_verificacion
                    session['nombreUsuario'] = usuario.nombreUsuario

                    mensaje = Message(
                        "Código de verificación",
                        recipients=[usuario.email],
                        body=f"Tu código de verificación es: {codigo_verificacion}"
                    )
                    mail.send(mensaje)

                    flash("Se ha enviado un código de verificación a tu correo electrónico.", "info")
                    return redirect(url_for("auth.verificar_codigo"))
                else:
                    usuario.intentos_fallidos += 1
                    
                    if usuario.intentos_fallidos >= MAX_INTENTOS_FALLIDOS:
                        usuario.estatus_bloqueo = "ACTIVADO"
                        flash("Demasiados intentos fallidos. Su cuenta ha sido bloqueada. Contacte al administrador.", "error")
                    
                    db.session.commit()
                    
                    if usuario.intentos_fallidos < MAX_INTENTOS_FALLIDOS:
                        flash(f"Contraseña incorrecta. Intento {usuario.intentos_fallidos} de {MAX_INTENTOS_FALLIDOS}.", "error")
            else:
                flash("Usuario no encontrado", "error")
        except Exception as e:
            flash(f"Ha ocurrido un error inesperado: {str(e)}", "error")
            logging.error(f"Error en inicio de sesión: {str(e)}")
    return render_template("login.html", form=form)



@auth.route("/verificar_codigo", methods=["GET", "POST"])
def verificar_codigo():
    form = VerificarCodigoForm()
    if form.validate_on_submit():
        codigo_usuario = form.codigo.data
        if int(codigo_usuario) == session.get('codigo_verificacion'):
            # Código correcto, iniciar sesión
            usuario = Usuario.query.get(session.get('nombreUsuario'))
            
            # Actualizar la última sesión del usuario
            usuario.ultima_sesion =  datetime.now(zona_horaria_mexico)  # Hora actual en la zona horaria configurada
            usuario.intentos_fallidos = 0  # Restablecer intentos fallidos
            db.session.commit()

            login_user(usuario)
            flash("Inicio de sesión exitoso.", "success")

            # Redirigir según el rol del usuario
            if usuario.idRol == 1:
                return redirect(url_for("home.home"))  # Si el rol es 1, redirigir a home.home
            elif usuario.idRol == 2:
                return redirect(url_for("inicio.inicio")) 
            elif usuario.idRol == 3:
                return redirect(url_for("homec.homec"))  # Si el rol es 2, redirigir a inicio.inicio
            else:
                flash("Rol no identificado.", "error")
                return redirect(url_for("auth.login"))  # Si el rol no es 1 ni 2, redirigir al login

        else:
            flash("Código incorrecto. Intenta nuevamente.", "error")
            return render_template("verificar_codigo.html")

    return render_template("verificar_codigo.html", form=form) 



@auth.route("/registro", methods=["GET", "POST"])
@login_required
def registro():
    form = RegistroForm()

    if form.validate_on_submit():
        try:
            usuario = usuarioService.obtenerUsuarioPorNombre(form.usuario.data)

            if usuario:
                flash("El usuario ya existe", "error")
            elif not form.idRol.data:
                flash("Debe seleccionar un rol.", "error")
            else:
                # Valores predeterminados
                estatus = 'ACTIVO'
                estatus_bloqueo = 'DESACTIVADO'

                usuarioService.crearUsuario(
                    nombreUsuario=form.usuario.data,
                    contrasenia=form.contrasenia.data,
                    confirmContrasenia=form.confirm_contrasenia.data,
                    nombre=form.nombre.data,
                    apellidoPaterno=form.apellidoPaterno.data,
                    apellidoMaterno=form.apellidoMaterno.data,
                    idRol=form.idRol.data,
                    estatus=estatus,
                    estatus_bloqueo=estatus_bloqueo,
                    email=form.email.data
                )

                flash("Usuario registrado con éxito", "success")
                return redirect(url_for("home.home"))

        except ValueError as e:
            flash(f"Error de validación: {str(e)}", "error")
            logging.error(f"{datetime.now(zona_horaria_mexico)} - Error de validación en registro: {str(e)}")

        except ConnectionError as e:
            flash("Error de conexión con la base de datos. Intenta nuevamente.", "error")
            logging.error(f"{datetime.now(zona_horaria_mexico)} - Error de conexión en registro: {str(e)}")

        except Exception as e:
            flash(f"Ha ocurrido un error inesperado: {str(e)}", "error")
            logging.error(f"{datetime.now(zona_horaria_mexico)} - Error en registro: {str(e)}")

    # Mostrar errores de validación del formulario
    if form.errors:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{form[field].label.text}: {error}", "error")

    return render_template("registro.html", form=form)


@auth.route("/modificar_usuario/<nombreUsuario>", methods=["GET", "POST"])
@login_required
def modificar_usuario(nombreUsuario):
    usuario = Usuario.query.filter_by(nombreUsuario=nombreUsuario).first()

    if not usuario:
        flash("Usuario no encontrado", "error")
        return redirect(url_for("auth.reporte"))

    # Si es GET, crear el formulario con los datos del usuario
    if request.method == "GET":
        form = ModificarUsuarioForm(obj=usuario)
    else:
        form = ModificarUsuarioForm()  # Para POST, instanciar sin datos por seguridad

    # Obtener los roles y asignarlos al formulario
    roles = usuarioService.obtenerRoles()
    form.idRol.choices = [(rol.idRol, rol.descripcion) for rol in roles]

    if form.validate_on_submit():
        try:
            if form.nombreUsuario.data != usuario.nombreUsuario:
                usuario_existente = Usuario.query.filter_by(nombreUsuario=form.nombreUsuario.data).first()
                if usuario_existente:
                    flash("El nombre de usuario ya está en uso.", "error")
                    return render_template("modi.html", form=form, usuario=usuario)

            # Actualizar los campos
            usuario.nombreUsuario = form.nombreUsuario.data
            usuario.nombre = form.nombre.data
            usuario.apellidoPaterno = form.apellidoPaterno.data
            usuario.apellidoMaterno = form.apellidoMaterno.data
            usuario.idRol = form.idRol.data
            usuario.estatus = form.estatus.data
            usuario.estatus_bloqueo = form.estatus_bloqueo.data
            usuario.email = form.email.data

            # Solo actualizar contraseña si se ingresó una nueva
            if form.contrasenia.data:
                usuario.contrasenia = generate_password_hash(form.contrasenia.data)

            db.session.commit()
            flash("Usuario modificado correctamente.", "success")
            return redirect(url_for("auth.reporte"))

        except Exception as e:
            flash(f"Error al modificar el usuario: {str(e)}", "error")
            logging.error(f"Error al modificar usuario {nombreUsuario}: {str(e)}")

    return render_template("modi.html", form=form, usuario=usuario)





@login_required
@auth.route("/logout")
def logout():
    logout_user()
    session.clear()
    # Agregar estas cabeceras adicionales
    response = redirect(url_for("auth.login"))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    flash("Sesión cerrada correctamente.", "success")
    return response










@auth.route('/desactivar/<nombreUsuario>')
@login_required
def desactivarU(nombreUsuario):
    usuario = Usuario.query.filter_by(nombreUsuario=nombreUsuario).first()
    if not usuario:
        flash('Usuario no encontrado.', 'error')
    else:
        usuario.estatus = 'Inactivo'
        db.session.commit()
        flash('Usuario desactivado correctamente.', 'success')
    
    return redirect(url_for('auth.reporte'))

@auth.route("/desbloquear", methods=["GET", "POST"])
@login_required
def desbloquear():
    if not current_user.is_authenticated:
        return jsonify({'error': 'NO AUTORIZADO'}), 401
    if current_user.idRol != 1:  
        flash("No tienes permisos para realizar esta acción.", "error")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        try:
            nombre_usuario = request.form.get("nombre_usuario")  

            usuario = Usuario.query.filter_by(nombreUsuario=nombre_usuario).first()

            if usuario:
                usuario.estatus_bloqueo = "DESACTIVADO"
                usuario.intentos_fallidos = 0 
                db.session.commit()
                flash(f"El usuario {usuario.nombreUsuario} ha sido desbloqueado.", "success")
            else:
                flash("Usuario no encontrado.", "error")
        except Exception as e:
            flash(f"Ha ocurrido un error inesperado al desbloquear: {str(e)}", "error")
            print(f"Error en desbloqueo: {e}")

    usuarios_bloqueados = Usuario.query.filter_by(estatus_bloqueo="ACTIVADO").all()
    return render_template("modificarU.html", usuarios=usuarios_bloqueados)



@auth.route('/reporte', methods=['GET', 'POST'])
@login_required
def reporte():
    usuario = Usuario.query.all()  
    return render_template('modificarU.html', usuario=usuario)



@auth.route("/cambiar_contrasenia", methods=["GET", "POST"])
@login_required
def cambiar_contrasenia():
    form = CambioContraseniaForm()
    usuario = Usuario.query.filter_by(nombreUsuario="usuario_actual").first()  # Obtener al usuario actual

    # Verificar si se ha cumplido el periodo de 30 días desde el último cambio
    if usuario and datetime.utcnow() - usuario.fechaUltimoCambio > timedelta(days=1):
        if form.validate_on_submit():
            if form.nueva_contrasenia.data == form.confirmar_contrasenia.data:
                # Actualizar la contraseña
                usuario.contrasenia = generate_password_hash(form.nueva_contrasenia.data)
                usuario.fechaUltimoCambio = datetime.utcnow()  # Actualizar la fecha del último cambio
                db.session.commit()
                flash("Contraseña cambiada con éxito.", "success")
                return redirect(url_for("auth.login"))
            else:
                flash("Las contraseñas no coinciden.", "error")

        return render_template("cambiarC.html", form=form)
    else:
        flash("No es necesario cambiar la contraseña aún.", "info")
        #return redirect(url_for("home.home"))




#REGISTRO CLIENTEEEE
@auth.route("/registroC", methods=["GET", "POST"])
def registroC():
    form = RegistroCForm()

    if form.validate_on_submit():
        try:
            usuario = usuarioService.obtenerUsuarioPorNombre(form.usuario.data)

            if usuario:
                flash("El usuario ya existe", "error")
            else:
                # Valores predeterminados
                estatus = 'ACTIVO'
                estatus_bloqueo = 'DESACTIVADO'
                id_rol_cliente = 3  # ID de rol para cliente

                usuarioService.crearUsuario(
                    nombreUsuario=form.usuario.data,
                    contrasenia=form.contrasenia.data,
                    confirmContrasenia=form.confirm_contrasenia.data,
                    nombre=form.nombre.data,
                    apellidoPaterno=form.apellidoPaterno.data,
                    apellidoMaterno=form.apellidoMaterno.data,
                    idRol=id_rol_cliente,  # Asignar directamente
                    estatus=estatus,
                    estatus_bloqueo=estatus_bloqueo,
                    email=form.email.data
                )

                flash("Usuario registrado con éxito", "success")
                return redirect(url_for("homec.homec"))

        except ValueError as e:
            flash(f"Error de validación: {str(e)}", "error")
            logging.error(f"{datetime.now(zona_horaria_mexico)} - Error de validación en registro: {str(e)}")

        except ConnectionError as e:
            flash("Error de conexión con la base de datos. Intenta nuevamente.", "error")
            logging.error(f"{datetime.now(zona_horaria_mexico)} - Error de conexión en registro: {str(e)}")

        except Exception as e:
            flash(f"Ha ocurrido un error inesperado: {str(e)}", "error")
            logging.error(f"{datetime.now(zona_horaria_mexico)} - Error en registro: {str(e)}")

    # Mostrar errores de validación del formulario
    if form.errors:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{form[field].label.text}: {error}", "error")

    return render_template("registroC.html", form=form)





#--------------------------------------------------------------

@auth.route('/api/daily_sales', methods=['GET'])
def daily_sales():
    try:
        # Get today's date
        today = datetime.now().date()
        
        # Query top 3 cookies sold today
        sales_data = db.session.query(
            TipoGalleta.nombre.label('label'),
            func.sum(DetalleVenta.cantidad).label('data'),
            func.sum(DetalleVenta.cantidad * DetalleVenta.costoActual).label('total_ventas'),
            Receta.imagen
        ).join(Venta, DetalleVenta.idVenta == Venta.idVenta)\
         .join(TipoGalleta, DetalleVenta.idTipoGalleta == TipoGalleta.idTipoGalleta)\
         .join(Receta, TipoGalleta.idReceta == Receta.idReceta)\
         .filter(func.date(Venta.fechaVenta) == today)\
         .group_by(TipoGalleta.idTipoGalleta, Receta.imagen)\
         .order_by(func.sum(DetalleVenta.cantidad).desc())\
         .limit(3).all()

        processed_sales = []
        for sale in sales_data:
            processed_sales.append({
                'label': sale.label,
                'data': float(sale.data),
                'total_ventas': float(sale.total_ventas),
                'image': process_cookie_image(sale.imagen)
            })

        # Get total sales for today
        total_ventas = db.session.query(
            func.sum(DetalleVenta.cantidad * DetalleVenta.costoActual)
        ).join(Venta, DetalleVenta.idVenta == Venta.idVenta)\
         .filter(func.date(Venta.fechaVenta) == today).scalar() or 0.0

        # Get previous day sales
        yesterday = today - timedelta(days=1)
        venta_pasada = db.session.query(
            func.sum(DetalleVenta.cantidad * DetalleVenta.costoActual)
        ).join(Venta, DetalleVenta.idVenta == Venta.idVenta)\
         .filter(func.date(Venta.fechaVenta) == yesterday).scalar() or 0.0

        # Calculate percentage difference
        diferencia_porcentual = 0.0
        if venta_pasada > 0:
            diferencia_porcentual = ((total_ventas - venta_pasada) / venta_pasada) * 100

        return jsonify({
            'status': 'success',
            'sales_data': processed_sales,
            'total_ventas': float(total_ventas),
            'venta_pasada': float(venta_pasada),
            'diferencia_porcentual': round(diferencia_porcentual, 2)
        })

    except Exception as e:
        current_app.logger.error(f"Error en daily_sales: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500

@auth.route('/api/ventas_por_galleta', methods=['GET'])
def ventas_por_galleta():
    try:
        # Query sales by cookie type
        ventas = db.session.query(
            TipoGalleta.nombre.label('nombre_galleta'),
            func.sum(DetalleVenta.cantidad).label('piezas_vendidas'),
            func.sum(DetalleVenta.cantidad * DetalleVenta.costoActual).label('total_ventas'),
            Receta.imagen
        ).join(Venta, DetalleVenta.idVenta == Venta.idVenta)\
         .join(TipoGalleta, DetalleVenta.idTipoGalleta == TipoGalleta.idTipoGalleta)\
         .join(Receta, TipoGalleta.idReceta == Receta.idReceta)\
         .group_by(TipoGalleta.idTipoGalleta, Receta.imagen)\
         .order_by(func.sum(DetalleVenta.cantidad).desc()).all()

        processed_ventas = []
        for venta in ventas:
            processed_ventas.append({
                'nombre_galleta': venta.nombre_galleta,
                'piezas_vendidas': int(venta.piezas_vendidas),
                'total_ventas': float(venta.total_ventas),
                'image': process_cookie_image(venta.imagen)
            })

        return jsonify({
            'status': 'success',
            'data': processed_ventas
        })

    except Exception as e:
        current_app.logger.error(f"Error en ventas_por_galleta: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500

@auth.route('/ventas-diarias', methods=['GET'])
def ventas_diarias():
    try:
        today = datetime.now().date()
        
        # Get daily sales data
        sales_data = db.session.query(
            TipoGalleta.nombre.label('label'),
            func.sum(DetalleVenta.cantidad).label('data'),
            func.sum(DetalleVenta.cantidad * DetalleVenta.costoActual).label('total_ventas'),
            Receta.imagen
        ).join(Venta, DetalleVenta.idVenta == Venta.idVenta)\
         .join(TipoGalleta, DetalleVenta.idTipoGalleta == TipoGalleta.idTipoGalleta)\
         .join(Receta, TipoGalleta.idReceta == Receta.idReceta)\
         .filter(func.date(Venta.fechaVenta) == today)\
         .group_by(TipoGalleta.idTipoGalleta, Receta.imagen)\
         .order_by(func.sum(DetalleVenta.cantidad).desc())\
         .limit(3).all()

        processed_sales = [{
            'label': sale.label,
            'data': float(sale.data),
            'total_ventas': float(sale.total_ventas),
            'image': process_cookie_image(sale.imagen)
        } for sale in sales_data]

        # Get sales by cookie type
        ventas_galletas = db.session.query(
            TipoGalleta.nombre.label('nombre_galleta'),
            func.sum(DetalleVenta.cantidad).label('piezas_vendidas'),
            func.sum(DetalleVenta.cantidad * DetalleVenta.costoActual).label('total_ventas'),
            Receta.imagen
        ).join(Venta, DetalleVenta.idVenta == Venta.idVenta)\
         .join(TipoGalleta, DetalleVenta.idTipoGalleta == TipoGalleta.idTipoGalleta)\
         .join(Receta, TipoGalleta.idReceta == Receta.idReceta)\
         .group_by(TipoGalleta.idTipoGalleta, Receta.imagen)\
         .order_by(func.sum(DetalleVenta.cantidad).desc()).all()

        processed_ventas = [{
            'nombre_galleta': venta.nombre_galleta,
            'piezas_vendidas': int(venta.piezas_vendidas),
            'total_ventas': float(venta.total_ventas),
            'image': process_cookie_image(venta.imagen)
        } for venta in ventas_galletas]

        # Get totals
        total_ventas = db.session.query(
            func.sum(DetalleVenta.cantidad * DetalleVenta.costoActual)
        ).join(Venta, DetalleVenta.idVenta == Venta.idVenta)\
         .filter(func.date(Venta.fechaVenta) == today).scalar() or 0.0

        yesterday = today - timedelta(days=1)
        venta_pasada = db.session.query(
            func.sum(DetalleVenta.cantidad * DetalleVenta.costoActual)
        ).join(Venta, DetalleVenta.idVenta == Venta.idVenta)\
         .filter(func.date(Venta.fechaVenta) == yesterday).scalar() or 0.0

        diferencia_porcentual = 0.0
        if venta_pasada > 0:
            diferencia_porcentual = ((total_ventas - venta_pasada) / venta_pasada) * 100

        return render_template(
            'ventas_diarias.html',
            sales_data=processed_sales,
            total_ventas=float(total_ventas),
            venta_pasada=float(venta_pasada),
            diferencia_porcentual=round(diferencia_porcentual, 2),
            ventas_galletas=processed_ventas
        )

    except Exception as e:
        current_app.logger.error(f"Error en ventas_diarias: {str(e)}", exc_info=True)
        return render_template('error.html', error_message=str(e))

@auth.route('/dashboard', methods=['GET'])
def dashboard():
    try:
        today = datetime.now().date()
        
        # Get daily sales data
        sales_data = db.session.query(
            TipoGalleta.nombre.label('label'),
            func.sum(DetalleVenta.cantidad).label('data'),
            func.sum(DetalleVenta.cantidad * DetalleVenta.costoActual).label('total_ventas'),
            Receta.imagen
        ).join(Venta, DetalleVenta.idVenta == Venta.idVenta)\
         .join(TipoGalleta, DetalleVenta.idTipoGalleta == TipoGalleta.idTipoGalleta)\
         .join(Receta, TipoGalleta.idReceta == Receta.idReceta)\
         .filter(func.date(Venta.fechaVenta) == today)\
         .group_by(TipoGalleta.idTipoGalleta, Receta.imagen)\
         .order_by(func.sum(DetalleVenta.cantidad).desc())\
         .limit(3).all()

        processed_sales = [{
            'label': sale.label,
            'data': float(sale.data),
            'total_ventas': float(sale.total_ventas),
            'image': process_cookie_image(sale.imagen)
        } for sale in sales_data]

        # Get totals
        total_ventas = db.session.query(
            func.sum(DetalleVenta.cantidad * DetalleVenta.costoActual)
        ).join(Venta, DetalleVenta.idVenta == Venta.idVenta)\
         .filter(func.date(Venta.fechaVenta) == today).scalar() or 0.0

        yesterday = today - timedelta(days=1)
        venta_pasada = db.session.query(
            func.sum(DetalleVenta.cantidad * DetalleVenta.costoActual)
        ).join(Venta, DetalleVenta.idVenta == Venta.idVenta)\
         .filter(func.date(Venta.fechaVenta) == yesterday).scalar() or 0.0

        diferencia_porcentual = 0.0
        if venta_pasada > 0:
            diferencia_porcentual = ((total_ventas - venta_pasada) / venta_pasada) * 100

        return render_template(
            'dashboard.html',
            sales_data=processed_sales,
            total_ventas=float(total_ventas),
            venta_pasada=float(venta_pasada),
            diferencia_porcentual=round(diferencia_porcentual, 2)
        )

    except Exception as e:
        current_app.logger.error(f"Error en dashboard: {str(e)}", exc_info=True)
        return render_template('error.html', error_message=str(e))

@auth.route('/api/least_sold_cookie', methods=['GET'])
def least_sold_cookie():
    try:
        least_sold = VentaService.VentaService.get_least_sold_cookie()
        
        if least_sold:
            return jsonify({
                'status': 'success',
                'data': {
                    'id': least_sold['id'],
                    'nombre_galleta': least_sold['nombre_galleta'],
                    'total_vendido': least_sold['total_vendido'],
                    'precio_unitario': least_sold['precio_unitario'],
                    'total_ventas': least_sold['total_ventas'],
                    'image': process_cookie_image(least_sold['imagen'])
                }
            })
        else:
            return jsonify({
                'status': 'success',
                'data': None,
                'message': 'No hay galletas vendidas aún'
            })

    except Exception as e:
        current_app.logger.error(f"Error en least_sold_cookie: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500


import base64
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app, jsonify
from flask_wtf import FlaskForm, RecaptchaField
from sqlalchemy import func
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import InputRequired, Length, EqualTo, ValidationError, DataRequired
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from functools import wraps
from datetime import datetime, timedelta
import re
import pytz
import logging

from app.models import DetalleVenta, Receta, TipoGalleta, Usuario, Rol, Venta
from app import db
from app.models.LoteGalletas import LoteGalleta
from app.services import VentaService
#--------------------------------------------------------------------------------------------------------
@auth.route('/galletas', methods=['GET'])
def cookie_stock():
    try:
        search_query = request.args.get('search', '')
        tipo_filter = request.args.get('tipo', '')

        query = db.session.query(
            TipoGalleta.idTipoGalleta,
            TipoGalleta.nombre,
            TipoGalleta.costo,
            Receta.imagen,
            Receta.pesoIndividualGalleta,
            func.coalesce(func.sum(LoteGalleta.cantidadDisponible), 0).label('stock')
        ).join(Receta, TipoGalleta.idReceta == Receta.idReceta)\
         .outerjoin(LoteGalleta, TipoGalleta.idTipoGalleta == LoteGalleta.idTipoGalleta)

        if tipo_filter:
            query = query.filter(TipoGalleta.idTipoGalleta == tipo_filter)

        if search_query:
            query = query.filter(TipoGalleta.nombre.ilike(f"%{search_query}%"))

        galletas = query.group_by(TipoGalleta.idTipoGalleta, Receta.imagen, Receta.pesoIndividualGalleta).all()

        datos = []
        for g in galletas:
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
                except Exception as e:
                    current_app.logger.error(f"Error imagen ID {g.idTipoGalleta}: {str(e)}")

            datos.append({
                'id': g.idTipoGalleta,
                'nombre': g.nombre,
                'imagen': img,
                'stock': g.stock,
                'costo': f"${g.costo:.2f}",
                'peso': f"{g.pesoIndividualGalleta}g"
            })

        tipos_galletas = TipoGalleta.query.all()
        return render_template('stock/stock_completo.html', galletas=datos, tipos_galletas=tipos_galletas)

    except Exception as e:
        current_app.logger.error(f"Error en cookie_stock: {str(e)}", exc_info=True)
        flash("Error al cargar el stock", "danger")
        return redirect(url_for('auth.cookie_stock'))
    
    
def process_cookie_image(image_data, default_image='default_cookie3.svg'):

    # Default fallback image
    default_img_url = url_for('static', filename=f'img/{default_image}')
    
    if image_data is None:
        return default_img_url
    
    try:
        # Handle string input
        if isinstance(image_data, str):
            # Already a data URI or URL
            if image_data.startswith(('data:image', 'http://', 'https://', '/')):
                return image_data
            # JPEG base64 string
            elif image_data.startswith('/9j/'):
                return f"data:image/jpeg;base64,{image_data}"
            # PNG base64 string
            elif image_data.startswith('iVBORw0KGgo'):
                return f"data:image/png;base64,{image_data}"
            # Other string - try to decode as base64
            else:
                try:
                    decoded = base64.b64decode(image_data)
                    return f"data:image/jpeg;base64,{base64.b64encode(decoded).decode('utf-8')}"
                except:
                    return default_img_url
        
        # Handle bytes input
        elif isinstance(image_data, bytes):
            # Check for common image headers
            header = image_data[:4]
            
            # JPEG magic number
            if header.startswith(b'\xFF\xD8'):
                return f"data:image/jpeg;base64,{base64.b64encode(image_data).decode('utf-8')}"
            # PNG magic number
            elif header.startswith(b'\x89PNG'):
                return f"data:image/png;base64,{base64.b64encode(image_data).decode('utf-8')}"
            # Assume it's already a base64 encoded string in bytes
            else:
                try:
                    decoded_str = image_data.decode('utf-8')
                    if decoded_str.startswith(('data:image', 'http://', 'https://', '/')):
                        return decoded_str
                    return f"data:image/jpeg;base64,{decoded_str}"
                except UnicodeDecodeError:
                    return default_img_url
        
        # Unsupported format
        return default_img_url
    
    except Exception as e:
        current_app.logger.error(f"Error processing cookie image: {str(e)}")
        return default_img_url