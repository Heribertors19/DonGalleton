from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column
from .. import db


class MermaInsumo(db.Model):
    __tablename__ = "mermainsumo"
    idMermaInsumo: Mapped[int] = mapped_column(primary_key=True)
    idRegistroMerma: Mapped[int] = mapped_column(
        ForeignKey("registromerma.idRegistroMerma"), nullable=False
    )
    idInsumo: Mapped[int] = mapped_column(ForeignKey("insumo.idInsumo"), nullable=False)
