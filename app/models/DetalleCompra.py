from sqlalchemy import ForeignKey, Integer, Float, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .. import db


class DetalleCompra(db.Model):
    __tablename__ = "detallecompra"
    idDetalleCompra: Mapped[int] = mapped_column(primary_key=True)
    idCompra: Mapped[int] = mapped_column(ForeignKey("compra.idCompra"))
    idInsumo: Mapped[int] = mapped_column(ForeignKey("insumo.idInsumo"), nullable=False)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    cantidadDisponible: Mapped[int] = mapped_column(Integer, nullable=False)
    precioUnitario: Mapped[float] = mapped_column(Float, nullable=False)
    fechaCaducidadInsumo: Mapped[Date] = mapped_column(Date, nullable=False)

    compra = relationship("Compra", back_populates="detalles")

