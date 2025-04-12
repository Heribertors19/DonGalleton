from sqlalchemy import ForeignKey, Integer, String, Float
from sqlalchemy.orm import Mapped, mapped_column
from .. import db

class Insumo(db.Model):
    __tablename__ = "insumo"
    
    idInsumo: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(45), nullable=False)
    precioActual: Mapped[float] = mapped_column(Float, nullable=False)
    idProveedor: Mapped[int] = mapped_column(
        ForeignKey("proveedor.idProveedor"), nullable=False
    )
    idPresentacion: Mapped[int] = mapped_column(
        ForeignKey("presentacioninsumo.idPresentacionInsumo"), nullable=False
    )
    idCategoria: Mapped[int] = mapped_column(
        ForeignKey("categoria.idCategoria"), nullable=False
    )
    estatus: Mapped[str] = mapped_column(db.String(10), default='ACTIVO', nullable=False)

    # Relaciones
    proveedor = db.relationship('Proveedor', backref='insumos')
    presentacionInsumo = db.relationship('PresentacionInsumo', backref='insumos_presentacion', lazy=True)  # Renamed backref
    detalleCompra = db.relationship('DetalleCompra', backref='insumos')
