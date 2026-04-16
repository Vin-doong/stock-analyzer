"""데이터 모델 정의"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class StockInfo(BaseModel):
    ticker: str
    name: str
    market: str
    sector: Optional[str] = None
    market_cap: Optional[float] = None


class Fundamentals(BaseModel):
    ticker: str
    per: Optional[float] = None
    pbr: Optional[float] = None
    roe: Optional[float] = None
    eps: Optional[float] = None
    revenue: Optional[float] = None
    revenue_growth: Optional[float] = None
    operating_margin: Optional[float] = None


class ScoreResult(BaseModel):
    ticker: str
    name: str
    style: str
    composite_score: float
    category_scores: dict[str, float]
    signal: str
    confidence: float
    timestamp: datetime = Field(default_factory=datetime.now)


class AnalysisResult(BaseModel):
    ticker: str
    name: str
    style: str
    technical_summary: dict
    fundamental_summary: Optional[dict] = None
    composite_score: float
    signal: str
    ai_summary: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
