from flask import (
    Flask, render_template, request, redirect, url_for, flash, Blueprint, session, current_app
)
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, DecimalField, FileField, SubmitField, SelectField, FloatField, FieldList, FormField, TextAreaField
from wtforms.validators import DataRequired
from werkzeug.utils import secure_filename
import os
from app.models import Receta, Insumo,Categoria, IngredienteReceta, UnidadMedida, TipoGalleta, PresentacionInsumo
from app import db
from io import BytesIO
from flask import send_file, make_response
from wtforms.fields import FieldList, FormField
from flask_wtf.file import FileRequired
import json
import base64
import imghdr
from sqlalchemy.exc import IntegrityError
from wtforms.validators import ValidationError,NumberRange, Regexp,  Optional
from flask_login import login_user, logout_user, login_required, current_user

# Definir Blueprint para recetas
receta_bp = Blueprint("receta", __name__, template_folder="../templates/receta")

# Extensiones permitidas para imágenes
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# En tus formularios
class EliminarRecetaForm(FlaskForm):
    submit = SubmitField('Eliminar')

# Formulario para buscar recetas
class BuscarRecetasForm(FlaskForm):
    buscar = StringField('Buscar', validators=[DataRequired()])

class IngredienteForm(FlaskForm):
    insumo = StringField('Insumo', validators=[DataRequired()])
    cantidad = FloatField('Cantidad', validators=[DataRequired()]) # Temporalmente sin validación
    unidadMedida = StringField('Unidad de Medida', validators=[DataRequired()])


class RecetaForm(FlaskForm):
    nombre = StringField('Nombre de la Receta', validators=[DataRequired(), Regexp('^[A-Za-záéíóúÁÉÍÓÚñÑ ]+$', message="El nombre solo debe contener letras y espacios.")])
    nombreGalleta = StringField('Nombre de la Galleta', validators=[DataRequired(), Regexp('^[A-Za-záéíóúÁÉÍÓÚñÑ ]+$', message="El nombre solo debe contener letras y espacios.")])
    stock_minimo = IntegerField('Stock minimo de la Galleta', validators=[DataRequired(), NumberRange(min=1, message="El stock mínimo debe ser un número positivo.")])
    galletasProducidas = IntegerField('Galletas Producidas', validators=[DataRequired(), NumberRange(min=1, message="El número de galletas producidas debe ser un número positivo.")])
    tiempoCoccion = IntegerField('Tiempo de cocción', validators=[DataRequired(), NumberRange(min=1, message="El tiempo de cocción debe ser un número positivo.")])
    pesoIndividualGalleta = IntegerField('Peso Individual de la Galleta', validators=[DataRequired(), NumberRange(min=1, message="El peso debe ser un número positivo.")])
    imagen = FileField('Imagen de la Receta')
    ingredientes = FieldList(FormField(IngredienteForm), min_entries=1)
    instrucciones = TextAreaField('Instrucciones de la Receta', validators=[DataRequired()])
    submit = SubmitField('Registrar Receta')

class IngredientessForm(FlaskForm):
    insumo = SelectField('Insumo', coerce=str, validators=[DataRequired()])
    cantidad = FloatField('Cantidad', validators=[DataRequired()])
    unidadMedida = SelectField('Unidad de Medida', coerce=str, validators=[DataRequired()])


class ModificForm(FlaskForm):
    nombre = StringField('Nombre receta', validators=[DataRequired()])
    galletasProducidas = IntegerField('Cantidad producida', validators=[DataRequired()])
    pesoIndividualGalleta = DecimalField('Peso individual (g)', validators=[DataRequired()])
    instrucciones = TextAreaField('Instrucciones', validators=[Optional()])
    tiempoCoccion = IntegerField('Tiempo cocción (min)', validators=[DataRequired()])
    imagen = FileField('Imagen', validators=[Optional()])

    # Tipo de galleta
    nombreGalleta = StringField('Nombre galleta', validators=[DataRequired()])
    stock_minimo = IntegerField('Stock mínimo', validators=[DataRequired()])
    costo = DecimalField('Costo estimado', validators=[DataRequired()])

    # Ingredientes (lista de subformularios)
    ingredientes = FieldList(FormField(IngredientessForm), min_entries=1)


@receta_bp.route('/registrarReceta', methods=['GET', 'POST'])
@login_required
def registrarReceta():
    form = RecetaForm()

    # Configurar choices para ingredientes
    insumos = [(str(i.idInsumo), i.nombre) for i in Insumo.query.all()]
    unidades = [(str(u.idUnidadMedida), u.nombre) for u in UnidadMedida.query.all()]

    for entry in form.ingredientes.entries:
        entry.form.insumo.choices = insumos
        entry.form.unidadMedida.choices = unidades

    if form.validate_on_submit():
        try:

            if not form.imagen.data:
                flash("La imagen es obligatoria.", "danger")
                return render_template('registrarReceta.html', form=form, insumos=insumos, unidades=unidades)

            # Verificar otros campos obligatorios si es necesario
            if not form.nombre.data or not form.nombreGalleta.data or not form.stock_minimo.data:
                flash("Todos los campos obligatorios deben ser completados.", "danger")
                return render_template('registrarReceta.html', form=form, insumos=insumos, unidades=unidades)
            # 1. Crear primero la Receta (sin commit)
            if form.galletasProducidas.data > 100:
                flash("No se pueden producir más de 100 galletas.", "danger")
                return render_template('registrarReceta.html', form=form, insumos=insumos, unidades=unidades)
            
            nueva_receta = Receta(
                nombre=form.nombre.data,
                galletasProducidas=form.galletasProducidas.data,
                pesoIndividualGalleta=form.pesoIndividualGalleta.data,
                instrucciones=form.instrucciones.data,
                tiempoCoccion=form.tiempoCoccion.data,
                estatus='ACTIVO'  # Asegúrate de que este campo esté en el formulario
            )
            
            # Procesar imagen
            if form.imagen.data:
                imagen_bytes = form.imagen.data.read()
                nueva_receta.imagen = f"data:image/{form.imagen.data.filename.split('.')[-1].lower()};base64,{base64.b64encode(imagen_bytes).decode('utf-8')}"

            db.session.add(nueva_receta)
            db.session.flush()  

    
            tipo_galleta = TipoGalleta(
                nombre=form.nombreGalleta.data,
                stock_minimo=form.stock_minimo.data,
                idReceta=nueva_receta.idReceta,
                costo=0,
                costo_produccion=0,
                costo_unitario=0,
                estatus='ACTIVO' 
            )
            db.session.add(tipo_galleta)

            
            costo_produccion = 0
            insumos_utilizados = []

            for ing_form in form.ingredientes.data:
                insumo = Insumo.query.get(int(ing_form['insumo']))
                cantidad = float(ing_form['cantidad'])
                unidad_receta = UnidadMedida.query.get(int(ing_form['unidadMedida']))
                presentacion = PresentacionInsumo.query.get(insumo.idPresentacion)
                
                unidad_base_receta = unidad_receta.idUnidadBase
                unidad_base_presentacion = presentacion.idUnidadBase
                
                if unidad_base_receta == unidad_base_presentacion:
                    conversion = 1
                else:
                    unidad_base_presentacion = UnidadMedida.query.get(unidad_base_presentacion)
                    if not unidad_base_presentacion:
                        raise ValueError("No se encontró la unidad base del insumo.")
                    conversion = unidad_base_presentacion.equivalenciaUnidadBase

                costo_ingrediente = (
                    (insumo.precioActual * cantidad * unidad_receta.equivalenciaUnidadBase) /
                    (presentacion.equivalenciaUnidadBase * conversion)
                )

                costo_produccion += costo_ingrediente
                insumos_utilizados.append(f"{insumo.nombre} ({cantidad} {unidad_receta.abreviatura})")

                ingrediente = IngredienteReceta(
                    idInsumo=int(ing_form['insumo']),
                    cantidad=float(ing_form['cantidad']),
                    idUnidadMedida=int(ing_form['unidadMedida']),
                    idReceta=nueva_receta.idReceta
                )
                db.session.add(ingrediente)

         
            tiempo_coccion_horas = form.tiempoCoccion.data / 60  # convertir minutos a horas
            costo_mano_obra = tiempo_coccion_horas * 50  # 50 pesos por hora
            costo_energia = 5  # Costo fijo por horneado

            costo_produccion += costo_mano_obra + costo_energia

             # Costo por galleta
            if nueva_receta.galletasProducidas > 0:
             costo_por_galleta = costo_produccion / nueva_receta.galletasProducidas
            else:
             costo_por_galleta = 0


            costo = costo_por_galleta * 2.6

# Guardar en base de datos
            tipo_galleta.costo_produccion = round(costo_produccion, 2)
            tipo_galleta.costo_unitario = round(costo_por_galleta, 2)
            tipo_galleta.costo = round(costo, 2)  # Nuevo campo añadido
            tipo_galleta.descripcionInsumos = ", ".join(insumos_utilizados)

            db.session.commit()

            flash("Receta registrada con éxito", "success")
            return redirect(url_for('receta.buscar_receta'))

        except IntegrityError as e:
            db.session.rollback()
            if "unique constraint" in str(e).lower():
                flash("Error: El nombre del tipo de galleta ya existe", "danger")
            else:
                flash(f"Error de base de datos: {str(e)}", "danger")
        except Exception as e:
            db.session.rollback()
            flash(f"Error inesperado: {str(e)}", "danger")
    return render_template('registrarReceta.html', form=form, insumos=insumos, unidades=unidades)


@receta_bp.route('/modificarReceta/<int:idReceta>', methods=['GET', 'POST'])
@login_required
def modificarReceta(idReceta):
    receta = Receta.query.get_or_404(idReceta)
    tipo_galleta = TipoGalleta.query.filter_by(idReceta=receta.idReceta).first()
    form = ModificForm(obj=receta)

    insumos = [(str(i.idInsumo), i.nombre) for i in Insumo.query.all()]
    unidades = [(str(u.idUnidadMedida), u.nombre) for u in UnidadMedida.query.all()]

    if request.method == 'GET':
        form.nombreGalleta.data = tipo_galleta.nombre
        form.stock_minimo.data = tipo_galleta.stock_minimo
        form.costo.data = tipo_galleta.costo

        while len(form.ingredientes.entries) < len(receta.ingredientes):
            form.ingredientes.append_entry()

        for entry, ingrediente in zip(form.ingredientes.entries, receta.ingredientes):
            entry.form.insumo.data = str(ingrediente.idInsumo)
            entry.form.cantidad.data = ingrediente.cantidad
            entry.form.unidadMedida.data = str(ingrediente.idUnidadMedida)

    for entry in form.ingredientes.entries:
        entry.form.insumo.choices = insumos
        entry.form.unidadMedida.choices = unidades

    if form.validate_on_submit():
        try:
            receta.nombre = form.nombre.data
            receta.galletasProducidas = form.galletasProducidas.data
            receta.pesoIndividualGalleta = form.pesoIndividualGalleta.data
            receta.instrucciones = form.instrucciones.data
            receta.tiempoCoccion = form.tiempoCoccion.data

            if form.imagen.data:
                imagen_bytes = form.imagen.data.read()
                receta.imagen = f"data:image/{form.imagen.data.filename.split('.')[-1].lower()};base64,{base64.b64encode(imagen_bytes).decode('utf-8')}"

            tipo_galleta.nombre = form.nombreGalleta.data
            tipo_galleta.stock_minimo = form.stock_minimo.data
            tipo_galleta.costo = form.costo.data

            insumos_utilizados = []
            insumos_en_form = [int(ing['insumo']) for ing in form.ingredientes.data]
            ingredientes_existentes = {i.idInsumo: i for i in receta.ingredientes}

            # Eliminar ingredientes que fueron quitados
            for idInsumo, ingr in ingredientes_existentes.items():
                if idInsumo not in insumos_en_form:
                    db.session.delete(ingr)

            costo_produccion = 0

            for ing_form in form.ingredientes.data:
                idInsumo = int(ing_form['insumo'])
                cantidad = float(ing_form['cantidad'])
                idUnidad = int(ing_form['unidadMedida'])

                insumo = Insumo.query.get(idInsumo)
                unidad_receta = UnidadMedida.query.get(idUnidad)
                presentacion = PresentacionInsumo.query.get(insumo.idPresentacion)

                conversion = 1
                if unidad_receta.idUnidadBase != presentacion.idUnidadBase:
                    unidad_base_presentacion = UnidadMedida.query.get(presentacion.idUnidadBase)
                    conversion = unidad_base_presentacion.equivalenciaUnidadBase or 1

                costo_ingrediente = (
                    (insumo.precioActual * cantidad * unidad_receta.equivalenciaUnidadBase) /
                    (presentacion.equivalenciaUnidadBase * conversion)
                )

                costo_produccion += costo_ingrediente
                insumos_utilizados.append(f"{insumo.nombre} ({cantidad} {unidad_receta.abreviatura})")

                ingrediente = IngredienteReceta.query.filter_by(idReceta=receta.idReceta, idInsumo=idInsumo).first()
                if ingrediente:
                    ingrediente.cantidad = cantidad
                    ingrediente.idUnidadMedida = idUnidad
                else:
                    db.session.add(IngredienteReceta(
                        idReceta=receta.idReceta,
                        idInsumo=idInsumo,
                        cantidad=cantidad,
                        idUnidadMedida=idUnidad
                    ))

            tiempo_coccion_horas = form.tiempoCoccion.data / 60
            costo_mano_obra = tiempo_coccion_horas * 50
            costo_energia = 5

            costo_produccion += costo_mano_obra + costo_energia

            costo_por_galleta = costo_produccion / receta.galletasProducidas if receta.galletasProducidas > 0 else 0

            tipo_galleta.costo_produccion = round(costo_produccion, 2)
            tipo_galleta.costo_unitario = round(costo_por_galleta, 2)
            tipo_galleta.descripcionInsumos = ", ".join(insumos_utilizados)

            db.session.commit()
            flash("Receta modificada con éxito", "success")
            return redirect(url_for('receta.buscar_receta'))

        except Exception as e:
            db.session.rollback()
            print("Ocurrió un error al modificar la receta:")
            print(str(e))
            import traceback
            traceback.print_exc()
            flash(f"Error: {str(e)}", "danger")

    else:
        
        print("Errores en el formulario:")
        print(form.errors)

    return render_template('modificarRec2.html', form=form, receta=receta, tipo_galleta=tipo_galleta)



@receta_bp.route('/imagen/<int:idReceta>')
@login_required
def imagen_receta(idReceta):
    receta = Receta.query.get_or_404(idReceta)
    
    if not receta.imagen:
        return make_response('Imagen no encontrada', 404)
    
    try:
        img_data = None
        mimetype = None

        
        if isinstance(receta.imagen, (str, bytes)):
       
            if isinstance(receta.imagen, bytes) and receta.imagen.startswith(b'data:image/'):
                img_str = receta.imagen.decode('utf-8')
                header, data = img_str.split(',', 1)
                mimetype = header.split(';')[0].split(':')[1]
                img_data = base64.b64decode(data)
            
           
            elif isinstance(receta.imagen, str) and receta.imagen.startswith('data:image/'):
                header, data = receta.imagen.split(',', 1)
                mimetype = header.split(';')[0].split(':')[1]
                img_data = base64.b64decode(data)
            
        
            elif isinstance(receta.imagen, str) and receta.imagen.startswith('/9j/'):
                mimetype = 'image/jpeg'
                img_data = base64.b64decode(receta.imagen)

        
        if img_data is None:
            
            if isinstance(receta.imagen, str):
                img_data = receta.imagen.encode('latin-1')  
            else:
                img_data = receta.imagen

           
            detected_type = imghdr.what(None, h=img_data)
            mimetype = f'image/{detected_type}' if detected_type else 'image/jpeg' 

       
        extension = mimetype.split('/')[1]
        if extension == 'jpeg':
            extension = 'jpg'

        return send_file(
            BytesIO(img_data),
            mimetype=mimetype,
            as_attachment=False,
            download_name=f'{receta.nombre}.{extension}'
        )
    
    except Exception as e:
        return make_response(f'Error al procesar la imagen: {str(e)}', 500)
    


@receta_bp.route('/buscar_receta')
@login_required
def buscar_receta():
    
    recetas = Receta.query.filter_by(estatus='ACTIVO').all()
    
   
    for receta in recetas:
        
        ingredientes = IngredienteReceta.query.filter_by(idReceta=receta.idReceta).all()
        
       
        for ingrediente in ingredientes:
            ingrediente.insumo = Insumo.query.get(ingrediente.idInsumo)  
            ingrediente.unidad = UnidadMedida.query.get(ingrediente.idUnidadMedida) 
            
     
        receta.ingredientes_procesados = ingredientes
    

    return render_template('vistaRec.html', recetas=recetas)


@receta_bp.route('/eliminar_receta/<int:idReceta>', methods=['POST'])
@login_required
def eliminar_receta(idReceta):
    form = EliminarRecetaForm()
   
    if form.validate_on_submit():
        receta = Receta.query.get_or_404(idReceta)
        
        try:
           
            receta.estatus = 'INACTIVO'
            
           
            if receta.tipo_galleta:
                receta.tipo_galleta.estatus = 'INACTIVO'
            
            db.session.commit()
            flash('Receta y tipo de galleta desactivados correctamente', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al desactivar: {str(e)}', 'danger')
    
    return redirect(url_for('receta.buscar_receta'))




@receta_bp.route('/consultarReceta/<int:idReceta>', methods=['GET'])
@login_required
def consultarReceta(idReceta):
   
    receta = Receta.query.get_or_404(idReceta)
    tipo_galleta = TipoGalleta.query.filter_by(idReceta=receta.idReceta).first()
    
    
    ingredientes = IngredienteReceta.query.filter_by(idReceta=receta.idReceta).all()
    
    
    detalles_ingredientes = []
    for ingrediente in ingredientes:
        insumo = Insumo.query.get(ingrediente.idInsumo)
        unidad_medida = UnidadMedida.query.get(ingrediente.idUnidadMedida)
        detalles_ingredientes.append({
            'insumo': insumo.nombre,
            'cantidad': ingrediente.cantidad,
            'unidad': unidad_medida.nombre
        })
    
 
    return render_template('consultarReceta.html', receta=receta, tipo_galleta=tipo_galleta, ingredientes=detalles_ingredientes)


def validate_galletasProducidas(self, field):
        if field.data > 100:
            raise ValidationError("No se pueden producir más de 100 galletas.")