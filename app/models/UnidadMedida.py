from sqlalchemy import Double, Float, ForeignKey, Integer, String
from .. import db, Mapped, mapped_column


class UnidadMedida(db.Model):
    __tablename__ = "unidadmedida"
    idUnidadMedida: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String)
    abreviatura: Mapped[str] = mapped_column(String)
    equivalenciaUnidadBase: Mapped[Double] = mapped_column(Double)
    idUnidadBase: Mapped[int] = mapped_column(ForeignKey("catunidad.idUnidad"))
    idCategoria: Mapped[int] = mapped_column(ForeignKey("categoria.idCategoria"))


    def to_dict(self):
        return {
            'id': self.idUnidadMedida,
            'nombre': self.nombre
        }