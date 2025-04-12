from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from .. import db


class Menu(db.Model):
    __tablename__ = "menu"
    idMenu: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(45), nullable=False)
    idRol: Mapped[int] = mapped_column(ForeignKey("rol.idRol"), nullable=False)
