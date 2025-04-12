from datetime import date
from sqlalchemy import Float, ForeignKey, Date
from .. import db, Mapped, mapped_column, relationship


class Compra(db.Model):
    __tablename__ = "compra"
    idCompra: Mapped[int] = mapped_column(primary_key=True)
    idProveedor: Mapped[int] = mapped_column(ForeignKey("proveedor.idProveedor"))
    fechaCompra: Mapped[Date] = mapped_column(Date, nullable=False, default=date.today)
    costoTotal: Mapped[float] = mapped_column(Float, nullable=True)

    proveedor = relationship("Proveedor")
    detalles = relationship("DetalleCompra", back_populates="compra")
