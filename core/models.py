"""SQLAlchemy Base model and shared database utilities.

Provides the declarative base for all DAWO.ECO database models.
Uses SQLAlchemy 2.0 style with mapped_column and Mapped types.

Usage:
    from core.models import Base

    class MyModel(Base):
        __tablename__ = "my_table"
        id: Mapped[UUID] = mapped_column(primary_key=True)
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all DAWO.ECO models.

    All models should inherit from this base class to ensure
    consistent metadata and configuration across the application.
    """

    pass
