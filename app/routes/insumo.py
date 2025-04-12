from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app, jsonify, make_response
from wtforms import StringField, PasswordField, SubmitField, SelectField, HiddenField
from wtforms.validators import InputRequired, Length, EqualTo, ValidationError, DataRequired
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import Insumo, PresentacionInsumo, Categoria, Proveedor
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
from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange

insumo = Blueprint("insumo", __name__, template_folder="../templates/insumo")

class InsumoForm(FlaskForm):
    nombre = StringField('Nombre del Insumo', validators=[DataRequired(), Length(min=2, max=100)])
    
    precioActual = DecimalField('Precio Actual', 
                                validators=[DataRequired(), NumberRange(min=0)],
                                places=2,
                                render_kw={"step": "0.01"})

    idPresentacion = SelectField('Presentación', coerce=int, validators=[DataRequired()])
    idProveedor = SelectField('Proveedor', coerce=int, validators=[DataRequired()])
    idCategoria = SelectField('Categoría', coerce=int, validators=[DataRequired()])

    submit = SubmitField('Registrar Insumo')


from app import db
from sqlalchemy import text

@insumo.route('/vistaStock')
@login_required
def vistaStock():
    result = db.session.execute(text("SELECT * FROM stock")).fetchall()
    return render_template('vistaStock.html', stock=result)





@insumo.route('/reporteInsum', methods=['GET', 'POST'])
@login_required
def reporteInsum():
    insumo = Insumo.query.filter_by(estatus='ACTIVO').all()
    return render_template('reporteInsumo.html', insumo=insumo)


@insumo.route('/registroInsumo', methods=['GET', 'POST'])
@login_required
def registroInsumo():
    form = InsumoForm()


    presentaciones = PresentacionInsumo.query.all()
    proveedores = Proveedor.query.all()
    categorias = Categoria.query.all()

    form.idPresentacion.choices = [(str(p.idPresentacionInsumo), p.nombre) for p in presentaciones]
    form.idProveedor.choices = [(str(p.idProveedor), p.nombre) for p in proveedores]
    form.idCategoria.choices = [(str(c.idCategoria), c.nombreCategoria) for c in categorias]

    if form.validate_on_submit():
     
        print("Datos del formulario:")
        print(f"Nombre: {form.nombre.data}")
        print(f"Precio Actual: {form.precioActual.data}")
        print(f"ID Presentación Insumo: {form.idPresentacion.data}")
        print(f"ID Proveedor: {form.idProveedor.data}")
        print(f"ID Categoría: {form.idCategoria.data}")

        try:
            nuevo_insumo = Insumo(
                nombre=form.nombre.data,
                precioActual=form.precioActual.data,
                idPresentacion=form.idPresentacion.data,
                idProveedor=form.idProveedor.data,
                idCategoria=form.idCategoria.data,
                estatus='ACTIVO'
            )
            db.session.add(nuevo_insumo)
            db.session.commit()
            flash('Insumo registrado exitosamente', 'success')
            return redirect(url_for('insumo.reporteInsum'))  
        except Exception as e:
            db.session.rollback()
            flash(f'Ocurrió un error al registrar el insumo: {str(e)}', 'danger')
            print(f"Error al registrar insumo: {str(e)}") 

    return render_template('registroInsumo.html', form=form)



@insumo.route('/modificarI/<int:idInsumo>', methods=['GET', 'POST'])
@login_required
def modificarI(idInsumo):
    insumo = Insumo.query.get_or_404(idInsumo)
    form = InsumoForm(obj=insumo)

    # Cargar las opciones de los selects
    presentaciones = PresentacionInsumo.query.all()
    proveedores = Proveedor.query.all()
    categorias = Categoria.query.all()

    form.idPresentacion.choices = [(str(p.idPresentacionInsumo), p.nombre) for p in presentaciones]
    form.idProveedor.choices = [(str(p.idProveedor), p.nombre) for p in proveedores]
    form.idCategoria.choices = [(str(c.idCategoria), c.nombreCategoria) for c in categorias]

    if form.validate_on_submit():
        try:
            insumo.nombre = form.nombre.data
            insumo.precioActual = form.precioActual.data
            insumo.idPresentacion = form.idPresentacion.data
            insumo.idProveedor = form.idProveedor.data
            insumo.idCategoria = form.idCategoria.data

            db.session.commit()
            flash('Insumo modificado exitosamente', 'success')
            return redirect(url_for('insumo.reporteInsum'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ocurrió un error al modificar el insumo: {str(e)}', 'danger')
            print(f"Error al modificar insumo: {str(e)}")

    return render_template('modificarInsumo.html', form=form, insumo=insumo)



@insumo.route('/eliminarI/<int:idInsumo>')
@login_required
def eliminarI(idInsumo):
    insumo = Insumo.query.filter_by(idInsumo=idInsumo).first()
    if not insumo:
        flash('Insumo no encontrado.', 'error')
    else:
        insumo.estatus = 'Inactivo'
        db.session.commit()
        flash('Insumo desactivado correctamente.', 'success')
    
    return redirect(url_for('insumo.reporteInsum'))
