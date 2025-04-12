from sqlalchemy import ForeignKey, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column
from .. import db
from sqlalchemy.orm import relationship


class IngredienteReceta(db.Model):
    __tablename__ = "ingredientereceta"
    idIngredienteReceta: Mapped[int] = mapped_column(primary_key=True)
    idReceta: Mapped[int] = mapped_column(ForeignKey("receta.idReceta"), nullable=False)
    idInsumo: Mapped[int] = mapped_column(ForeignKey("insumo.idInsumo"), nullable=False)
    cantidad: Mapped[float] = mapped_column(Float, nullable=False)
    idUnidadMedida: Mapped[int] = mapped_column(
        ForeignKey("unidadmedida.idUnidadMedida"), nullable=False)
    
    receta = relationship('Receta', back_populates='ingredientes')
