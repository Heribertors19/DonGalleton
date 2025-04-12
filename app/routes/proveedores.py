from flask import (Blueprint, render_template, request, redirect, url_for, flash, session)
from app.models import Proveedor,Insumo,Compra
from datetime import datetime, timedelta
from app import db
from sqlalchemy import desc
import pytz
from flask import current_app
import base64
from sqlalchemy import func
from sqlalchemy import LargeBinary, cast
from sqlalchemy.orm import aliased, joinedload
import logging

proveedores_bp = Blueprint('proveedores', __name__)

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
###############################################################################
@proveedores_bp.route('/proveedores', methods=['GET'])
def interfaz_proveedores():
    # Ahora sí puedes usar joinedload con la relación insumos
    proveedores = (
        db.session.query(Proveedor)
        .filter(Proveedor.estatus != 2)
        .options(joinedload(Proveedor.insumos))
        .all()
    )

    proveedores_data = []
    for proveedor in proveedores:
        proveedores_data.append({
            'id': proveedor.idProveedor, 
            'nombre': proveedor.nombre,
            'telefono': proveedor.telefono,
            'direccion': proveedor.direccion,
            'email': proveedor.email,
            'insumos': [i.nombre for i in proveedor.insumos],
            'estatus': proveedor.estatus  # Agregamos el campo estatus
        })
    return render_template('proveedores/proveedores_inicio.html', proveedores=proveedores_data)
##################################################################################
@proveedores_bp.route('/ruta/nuevo-proveedor', methods=['GET', 'POST'])
def nuevo_proveedor():
    if request.method == 'POST':
        # Capturar los datos del formulario
        nombre = request.form['nombre']
        telefono = request.form['telefono']
        direccion = request.form['direccion']
        email = request.form['email']
        
        # Crear un nuevo proveedor con estatus por defecto en 1
        nuevo_proveedor = Proveedor(
            nombre=nombre,
            telefono=telefono,
            direccion=direccion,
            email=email,
            estatus=1  # Establecer estatus por defecto en 1
        )
        
        # Agregar el nuevo proveedor a la base de datos
        db.session.add(nuevo_proveedor)
        db.session.commit()

        # Flash mensaje de éxito y redirigir
        flash('Proveedor registrado exitosamente', 'success')
        return redirect(url_for('proveedores.interfaz_proveedores'))
    
    # Si es un GET, solo mostrar el formulario
    return render_template('proveedores/registro_proveedor.html')
######################################################################3
@proveedores_bp.route('/proveedores/editar/<int:id>', methods=['GET', 'POST'])
def editar_proveedor(id):
    proveedor = db.session.query(Proveedor).filter(Proveedor.idProveedor == id).first()

    # Verificar si el proveedor existe
    if proveedor is None:
        # Redirigir o mostrar un error si no se encuentra el proveedor
        return redirect(url_for('proveedores.interfaz_proveedores'))
    
    if request.method == 'GET':
        if proveedor:
            return render_template('proveedores/editar_proveedor.html', proveedor=proveedor)
        else:
            flash('Proveedor no encontrado', 'error')
            return redirect(url_for('proveedores.lista_proveedores'))
        
    if request.method == 'POST':
        # Aquí gestionamos la actualización del proveedor
        proveedor.nombre = request.form['nombre']
        proveedor.telefono = request.form['telefono']
        proveedor.direccion = request.form['direccion']
        proveedor.email = request.form['email']
        
        # Commit a la base de datos
        db.session.commit()
        
        # Después de actualizar, redirigimos a la lista de proveedores
        return redirect(url_for('proveedores.interfaz_proveedores'))

    # Si es GET, mostrar el formulario con los datos del proveedor
    return render_template('proveedores/editar_proveedor.html', proveedor=proveedor)
########################################################################################
@proveedores_bp.route('/proveedores/eliminar/<int:id>', methods=['POST'])
def eliminar_proveedor(id):
    proveedor = Proveedor.query.get(id)

    if proveedor is None:
        flash('Proveedor no encontrado', 'error')
        return redirect(url_for('proveedores.interfaz_proveedores'))

    proveedor.estatus = 2 
    db.session.commit()

    flash('Proveedor eliminado correctamente (lógicamente)', 'success')
    return redirect(url_for('proveedores.interfaz_proveedores'))
##########################################################################################
@proveedores_bp.route('/proveedores/ver/<int:id>', methods=['GET'])
def ver_proveedor(id):
    proveedor = Proveedor.query.get(id)

    if not proveedor:
        flash('Proveedor no encontrado', 'error')
        return redirect(url_for('proveedores.interfaz_proveedores'))
    
    # compras ya viene con los detalles si están relacionados
    compras = Compra.query.filter_by(idProveedor=id).all()

    return render_template('proveedores/ver_proveedor.html', proveedor=proveedor, compras=compras)

