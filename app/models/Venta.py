from datetime import date
from sqlalchemy import Date, Double, Float, ForeignKey, Integer, String
from .. import db, Mapped, mapped_column


class Venta(db.Model):
    __tablename__ = "venta"
    idVenta: Mapped[int] = mapped_column(primary_key=True)
    fechaVenta: Mapped[Date] = mapped_column(Date, nullable=False, default=date.today)
    precioTotal: Mapped[Float] = mapped_column(Float, nullable=False)
    estado = db.Column(db.String(20), default='en_proceso')  # Asegúrate que este campo existe
    
    # Relación con DetalleVenta
    detalles = db.relationship('DetalleVenta', backref='venta', lazy=True)