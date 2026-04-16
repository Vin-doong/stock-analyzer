"""숫자 포맷팅"""


def format_krw(value) -> str:
    """한국 원화 포맷"""
    if value is None:
        return "-"
    value = float(value)
    if abs(value) >= 1e12:
        return f"{value / 1e12:.1f}조"
    elif abs(value) >= 1e8:
        return f"{value / 1e8:.0f}억"
    elif abs(value) >= 1e4:
        return f"{value / 1e4:.0f}만"
    else:
        return f"{value:,.0f}원"


def format_usd(value) -> str:
    """미국 달러 포맷"""
    if value is None:
        return "-"
    value = float(value)
    if abs(value) >= 1e12:
        return f"${value / 1e12:.1f}T"
    elif abs(value) >= 1e9:
        return f"${value / 1e9:.1f}B"
    elif abs(value) >= 1e6:
        return f"${value / 1e6:.1f}M"
    else:
        return f"${value:,.2f}"


def format_percent(value) -> str:
    """퍼센트 포맷"""
    if value is None:
        return "-"
    value = float(value)
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}%"


def format_number(value) -> str:
    """일반 숫자 포맷"""
    if value is None:
        return "-"
    value = float(value)
    if abs(value) >= 1e6:
        return f"{value / 1e6:.1f}M"
    elif abs(value) >= 1e3:
        return f"{value / 1e3:.1f}K"
    else:
        return f"{value:,.1f}"


def format_price(value, market: str = "KR") -> str:
    """시장에 따른 가격 포맷"""
    if value is None:
        return "-"
    if market in ("KOSPI", "KOSDAQ", "KR"):
        return f"{float(value):,.0f}원"
    else:
        return f"${float(value):,.2f}"
