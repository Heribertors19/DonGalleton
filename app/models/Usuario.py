from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from .. import db
from datetime import datetime

class Usuario(db.Model, UserMixin):
    __tablename__ = "usuario"
    nombreUsuario: Mapped[str] = mapped_column(primary_key=True)
    contrasenia: Mapped[str] = mapped_column(String(45), nullable=False)
    nombre: Mapped[str] = mapped_column(String(45), nullable=False)
    apellidoPaterno: Mapped[str] = mapped_column(String(45), nullable=False)
    apellidoMaterno: Mapped[str] = mapped_column(String(45), nullable=False)
    idRol: Mapped[int] = mapped_column(Integer, ForeignKey("rol.idRol"), nullable=False)
    ultima_sesion = db.Column(db.DateTime) 
    intentos_fallidos: Mapped[int] = mapped_column(Integer, nullable=False,  default=0)
    estatus = db.Column(db.String(20), default='ACTIVO')
    estatus_bloqueo = db.Column(db.String(20), default='DESACTIVADO')
    fechaUltimoCambio = db.Column(db.DateTime, default=datetime.utcnow)
    email: Mapped[str] = mapped_column(String(40))


    def get_id(self):
        return self.nombreUsuario  # Usamos nombreUsuario como identificador
