import datetime
import uuid
from typing import List

from sqlalchemy import UUID, DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from application.extensions import db


class Extract(db.Model):
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime.date] = mapped_column(
        DateTime, default=datetime.datetime.today, nullable=False
    )
    items: Mapped[List["ExtractItem"]] = relationship(
        back_populates="extract", order_by="ExtractItem.index"
    )


class ExtractItem(db.Model):
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    index: Mapped[int] = mapped_column(Integer, nullable=False)
    data: Mapped[str] = mapped_column(Text, nullable=False)
    extract_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), db.ForeignKey("extract.id"), nullable=False
    )
    extract: Mapped["Extract"] = relationship(back_populates="items")
