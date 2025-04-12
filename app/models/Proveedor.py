from sqlalchemy import Integer, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column,relationship
from .. import db


class Proveedor(db.Model):
    __tablename__ = "proveedor"
    idProveedor: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    telefono: Mapped[str] = mapped_column(String(20), nullable=True)
    direccion: Mapped[str] = mapped_column(String(250), nullable=True)
    email: Mapped[str] = mapped_column(String(100), nullable=True)
    estatus = db.Column(db.Integer, default=1)  # 1 = activo, 2 = inactivo

    #insumos = relationship("Insumo", backref="proveedor")