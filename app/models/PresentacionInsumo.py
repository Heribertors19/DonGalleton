
from sqlalchemy import ForeignKey, Integer, String, Float
from sqlalchemy.orm import Mapped, mapped_column
from .. import db
class PresentacionInsumo(db.Model):
    __tablename__ = "presentacioninsumo"
    
    idPresentacionInsumo: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(45), nullable=False)
    abreviatura: Mapped[str] = mapped_column(String(45), nullable=False)
    idUnidadBase: Mapped[int] = mapped_column(
        ForeignKey("catunidad.idUnidad"), nullable=False
    )
    equivalenciaUnidadBase: Mapped[float] = mapped_column(Float, nullable=False)

    #insumos = db.relationship('Insumo', backref='presentacionInsumo', lazy=True)  # Changed backref name to 'presentacionInsumo'