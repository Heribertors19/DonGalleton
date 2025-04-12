from sqlalchemy import ForeignKey, Integer, String

from .. import db, Mapped, mapped_column, relationship


class Categoria(db.Model):
    __tablename__ = "categoria"
    idCategoria: Mapped[int] = mapped_column(primary_key=True)
    nombreCategoria: Mapped[str] = mapped_column(String, nullable=False)
    idUnidadBase: Mapped[int] = mapped_column(ForeignKey("catunidad.idUnidad"))

    UnidadBase = relationship("CatUnidad")
