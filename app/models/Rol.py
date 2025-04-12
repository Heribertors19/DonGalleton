from sqlalchemy import Integer
from .. import db, Mapped, mapped_column


class Rol(db.Model):
    __tablename__ = "rol"
    idRol: Mapped[int] = mapped_column(primary_key=True)
    descripcion: Mapped[str] = mapped_column(Integer, nullable=False)
