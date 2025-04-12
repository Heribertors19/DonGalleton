from sqlalchemy import String
from .. import db, Mapped, mapped_column


class CatUnidad(db.Model):
    __tablename__ = "catunidad"
    idUnidad: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String, nullable=False)
    abreviatura: Mapped[str] = mapped_column(String, nullable=False)
