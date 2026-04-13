from sqlalchemy import Column, String, Float, Integer, ForeignKey
from sqlalchemy.orm import relationship

from backend.db.database import Base


class Asset(Base):
    __tablename__ = "assets"

    id                = Column(String,  primary_key=True)
    type              = Column(String,  nullable=False)
    name              = Column(String,  nullable=False)
    current_value     = Column(Float,   default=0)
    acquisition_date  = Column(String)
    acquisition_price = Column(Float,   default=0)
    disposal_date     = Column(String)
    disposal_price    = Column(Float,   default=0)
    quantity          = Column(Float,   default=0)
    created_at        = Column(String)
    updated_at        = Column(String)

    # 관계
    history      = relationship("AssetHistory",      back_populates="asset", cascade="all, delete-orphan")
    real_estate  = relationship("RealEstateDetail",  back_populates="asset", uselist=False, cascade="all, delete-orphan")
    stock        = relationship("StockDetail",        back_populates="asset", uselist=False, cascade="all, delete-orphan")
    pension      = relationship("PensionDetail",      back_populates="asset", uselist=False, cascade="all, delete-orphan")
    savings      = relationship("SavingsDetail",      back_populates="asset", uselist=False, cascade="all, delete-orphan")


class AssetHistory(Base):
    __tablename__ = "asset_history"

    id       = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(String,  ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    date     = Column(String,  nullable=False)   # YYYY-MM-DD
    value    = Column(Float)                     # 평가액 (KRW, 환율 적용 후)
    price    = Column(Float)                     # 단가 (주식/실물자산용)
    quantity = Column(Float)                     # 수량 (주식/실물자산용)

    asset = relationship("Asset", back_populates="history")


class RealEstateDetail(Base):
    __tablename__ = "real_estate_details"

    asset_id       = Column(String,  ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True)
    is_owned       = Column(Integer, default=1)   # 1=자가, 0=임대
    has_tenant     = Column(Integer, default=0)   # 1=세입자 있음
    tenant_deposit = Column(Float,   default=0)   # 보증금
    address        = Column(String)
    loan_amount    = Column(Float,   default=0)   # 대출금

    asset = relationship("Asset", back_populates="real_estate")


class StockDetail(Base):
    __tablename__ = "stock_details"

    asset_id           = Column(String,  ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True)
    account_name       = Column(String)
    currency           = Column(String,  default="KRW")  # KRW|USD|JPY
    is_pension_like    = Column(Integer, default=0)
    pension_start_year = Column(Integer)
    pension_monthly    = Column(Float)
    ticker             = Column(String)                  # Yahoo Finance ticker

    asset = relationship("Asset", back_populates="stock")


class PensionDetail(Base):
    __tablename__ = "pension_details"

    asset_id                = Column(String,  ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True)
    pension_type            = Column(String)             # 국민연금|퇴직연금|개인연금 등
    expected_start_year     = Column(Integer)
    expected_end_year       = Column(Integer)
    expected_monthly_payout = Column(Float,   default=0) # 예상 월 수령액 (KRW)
    annual_growth_rate      = Column(Float,   default=0) # 연 증가율 (%)

    asset = relationship("Asset", back_populates="pension")


class SavingsDetail(Base):
    __tablename__ = "savings_details"

    asset_id           = Column(String,  ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True)
    is_pension_like    = Column(Integer, default=0)
    pension_start_year = Column(Integer)
    pension_monthly    = Column(Float)

    asset = relationship("Asset", back_populates="savings")
