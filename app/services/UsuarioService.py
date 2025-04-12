from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import SQLAlchemyError
from app.models import Usuario, Rol
from app import db


class UsuarioService:

    @staticmethod
    def crearUsuario(
        nombreUsuario,
        contrasenia,
        confirmContrasenia,
        nombre,
        apellidoPaterno,
        apellidoMaterno,
        idRol,
        estatus,
        estatus_bloqueo,
        email
    ):
        if contrasenia != confirmContrasenia:
            raise ValueError("Las contraseñas no coinciden")

        nuevoUsuario = Usuario(
            nombreUsuario=nombreUsuario,
            nombre=nombre,
            apellidoPaterno=apellidoPaterno,
            apellidoMaterno=apellidoMaterno,
            idRol=idRol,
            estatus=estatus,
            estatus_bloqueo=estatus_bloqueo,
            email=email
        )

        nuevoUsuario.contrasenia = UsuarioService._crearContrasenia(contrasenia)

        db.session.add(nuevoUsuario)
        db.session.commit()

        return nuevoUsuario

    @staticmethod
    def verificarContrasenia(usuario, contrasenia):
        return check_password_hash(usuario.contrasenia, contrasenia)

    @staticmethod
    def obtenerUsuarioPorNombre(nombreUsuario):
        return Usuario.query.filter_by(nombreUsuario=nombreUsuario).first()

    @staticmethod
    def obtenerRolPorNombreUsuario(nombreUsuario):
        try:
            usuario = Usuario.query.filter_by(nombreUsuario=nombreUsuario).first()
            if usuario:
                return usuario.idRol  # Asumiendo que tienes una relación entre Usuario y Rol
            return None
        except Exception as e:
            raise e

    @staticmethod
    def _crearContrasenia(contrasenia):
        return generate_password_hash(contrasenia)

    @staticmethod
    def modificarUsuario(usuario):
        try:
            existing_user = Usuario.query.filter_by(nombreUsuario=usuario.nombreUsuario).first()

            if not existing_user:
                raise ValueError(f"Usuario con nombre {usuario.nombreUsuario} no encontrado.")

            existing_user.nombre = usuario.nombre
            existing_user.apellidoPaterno = usuario.apellidoPaterno
            existing_user.apellidoMaterno = usuario.apellidoMaterno
            existing_user.contrasenia = usuario.contrasenia
            existing_user.email = usuario.email

            # Obtener el ID del rol
            rol = Rol.query.filter_by(nombre=usuario.idRol).first()
            if rol:
                existing_user.idRol = rol.id
            else:
                raise ValueError(f"Rol {usuario.idRol} no encontrado.")

            existing_user.estatus = usuario.estatus
            existing_user.estatus_bloqueo = usuario.estatus_bloqueo

            db.session.commit()

        except Exception as e:
            db.session.rollback()
            raise ValueError(f"Error al modificar el usuario: {str(e)}")

    @staticmethod
    def obtenerRoles():
        try:
            roles = Rol.query.all()
            return roles
        except SQLAlchemyError as e:
            print(f"Error al obtener roles: {str(e)}")
            return []

    @staticmethod
    def desactivarUsuario(nombreUsuario):
        try:
            usuario = UsuarioService.obtenerUsuarioPorNombre(nombreUsuario)
            if usuario:
                usuario.estatus = "INACTIVO"
                db.session.commit()
                return True
            return False
        except Exception as e:
            db.session.rollback()
            raise e


    