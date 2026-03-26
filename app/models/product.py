from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Boolean, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import ActiveSoftDeleteMixin, Base, TimestampMixin


class Product(Base, TimestampMixin, ActiveSoftDeleteMixin):
    __tablename__ = "products"
    __table_args__ = (
        Index("ix_products_barcode", "barcode", unique=True),
        Index("ix_products_internal_code", "internal_code", unique=True),
        Index("ix_products_name_pinyin", "name_pinyin"),
        Index("ix_products_quick_match", "barcode", "internal_code", "name_pinyin"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    name_pinyin: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    barcode: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    internal_code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    is_available_for_sale: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_pos_visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
