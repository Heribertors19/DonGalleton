from sqlalchemy import Float, ForeignKey, Integer, String
from .. import db, Mapped, mapped_column, relationship
from typing import List



class TipoGalleta(db.Model):
    __tablename__ = "tipogalleta"
    idTipoGalleta: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String, nullable=False)
    idReceta: Mapped[int] = mapped_column(ForeignKey("receta.idReceta"))
    costo: Mapped[float] = mapped_column(Float, nullable=False)
    costo_produccion: Mapped[float] = mapped_column(Float, nullable=False)
    costo_unitario: Mapped[float] = mapped_column(Float, nullable=False)
    stock_minimo: Mapped[int] = mapped_column(nullable=False)
    receta = db.relationship('Receta', backref='tipo_galleta')
    estatus = db.Column(db.String(10), default='ACTIVO', nullable=False)

   # Relaciones
    receta = relationship("Receta", back_populates="tipo_galleta")
    estatus = db.Column(db.String(10), default='ACTIVO', nullable=False)
    lotes: Mapped[List["LoteGalleta"]] = relationship(back_populates="tipo_galleta")
    # Relación inversa con DetalleVenta
    detalles_venta: Mapped[list["DetalleVenta"]] = db.relationship("DetalleVenta", back_populates="tipo_galleta")