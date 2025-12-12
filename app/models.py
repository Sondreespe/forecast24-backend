# app/models.py
from sqlalchemy import Column, Integer, String, Date, Float, DateTime, UniqueConstraint, Index
from .db import Base

class SpotPrice(Base):
    __tablename__ = "spot_prices"

    id = Column(Integer, primary_key=True)
    area = Column(String(3), nullable=False)          # NO1..NO5
    date = Column(Date, nullable=False)               # YYYY-MM-DD (dato for time_start)
    time_start = Column(DateTime(timezone=True), nullable=False)
    time_end = Column(DateTime(timezone=True), nullable=False)

    nok_per_kwh = Column(Float, nullable=True)
    eur_per_kwh = Column(Float, nullable=True)
    exr = Column(Float, nullable=True)

    __table_args__ = (
        UniqueConstraint("area", "time_start", name="uq_area_time_start"),
        Index("ix_spot_prices_area_date", "area", "date"),
    )