from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column
from .. import db


class MermaGalleta(db.Model):
    __tablename__ = "mermagalleta"
    idMermaInsumo: Mapped[int] = mapped_column(primary_key=True)
    idRegistroMerma: Mapped[int] = mapped_column(
        ForeignKey("registromerma.idRegistroMerma"), nullable=False
    )
    idTipoGalleta: Mapped[int] = mapped_column(
        ForeignKey("tipogalleta.idTipoGalleta"), nullable=False
    )
