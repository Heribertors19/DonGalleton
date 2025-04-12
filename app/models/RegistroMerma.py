from sqlalchemy import Date, Float, Integer, String
from .. import db, Mapped, mapped_column


class RegistroMerma(db.Model):
    __tablename__ = "registromerma"
    idRegistroMerma: Mapped[int] = mapped_column(primary_key=True)
    categoria: Mapped[str] = mapped_column(String, nullable=False)
    tipoMerma: Mapped[str] = mapped_column(String, nullable=False)
    fecha: Mapped[Date] = mapped_column(Date, nullable=False)
    cantidad: Mapped[int]
