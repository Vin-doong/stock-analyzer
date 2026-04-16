"""종목 필터링"""
import pandas as pd


def filter_by_market_cap(df: pd.DataFrame, min_cap: float = 0, max_cap: float = float("inf")) -> pd.DataFrame:
    """시가총액 필터"""
    if "market_cap" not in df.columns:
        return df
    mask = (df["market_cap"] >= min_cap)
    if max_cap < float("inf"):
        mask = mask & (df["market_cap"] <= max_cap)
    return df[mask]


def filter_by_name(df: pd.DataFrame, keyword: str) -> pd.DataFrame:
    """종목명 검색"""
    if not keyword or "name" not in df.columns:
        return df
    return df[df["name"].str.contains(keyword, case=False, na=False)]


def apply_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """여러 필터 적용"""
    result = df.copy()

    if "min_cap" in filters or "max_cap" in filters:
        result = filter_by_market_cap(
            result,
            min_cap=filters.get("min_cap", 0),
            max_cap=filters.get("max_cap", float("inf")),
        )

    if "keyword" in filters and filters["keyword"]:
        result = filter_by_name(result, filters["keyword"])

    return result
