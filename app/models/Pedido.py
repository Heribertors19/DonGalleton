from sqlalchemy import ForeignKey, Integer, Date, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from .. import db


class Pedido(db.Model):
    __tablename__ = "pedido"
    idPedido: Mapped[int] = mapped_column(primary_key=True)
    fechaEntrega: Mapped[Date] = mapped_column(Date, nullable=False)
    fechaCreacion: Mapped[Date] = mapped_column(Date, nullable=False)
    estatus: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    idVenta: Mapped[int] = mapped_column(ForeignKey("venta.idVenta"))
    nombreUsuario: Mapped[str] = mapped_column(ForeignKey("usuario.nombreUsuario"))
