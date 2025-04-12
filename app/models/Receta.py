from sqlalchemy import Float, Integer, String, LargeBinary, Text
from .. import db, Mapped, mapped_column
from .. import db, Mapped, mapped_column, relationship
from typing import List


class Receta(db.Model):
    __tablename__ = "receta"
    idReceta: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String, nullable=False)
    galletasProducidas: Mapped[int] = mapped_column(String, nullable=False)
    pesoIndividualGalleta: Mapped[float] = mapped_column(Float, nullable=False)
    imagen: Mapped[str] = mapped_column(String(length=2**24), nullable=False)
    #imagen: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    #imagen = db.Column(db.String(200), nullable=True)
    #ingredientes = db.relationship('IngredienteReceta', back_populates='receta')
    instrucciones = mapped_column(Text, nullable=False)
    tiempoCoccion: Mapped[int] = mapped_column(nullable=False)
    estatus = db.Column(db.String(10), default='ACTIVO', nullable=False)
    #ingredientes = db.relationship('IngredienteReceta', back_populates='receta')

     # Relación con TipoGalleta
    tipo_galleta = relationship("TipoGalleta", back_populates="receta", uselist=False)
    
    ingredientes: Mapped[List["IngredienteReceta"]] = relationship("IngredienteReceta", back_populates="receta")