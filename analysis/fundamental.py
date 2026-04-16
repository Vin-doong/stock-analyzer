"""재무 분석"""


def evaluate_value(fund: dict) -> dict:
    """밸류에이션 점수"""
    scores = {}

    per = fund.get("per")
    if per is not None and per > 0:
        if per < 5:
            scores["per"] = 95
        elif per < 10:
            scores["per"] = 80
        elif per < 15:
            scores["per"] = 65
        elif per < 20:
            scores["per"] = 50
        elif per < 30:
            scores["per"] = 35
        elif per < 50:
            scores["per"] = 20
        else:
            scores["per"] = 10
    else:
        scores["per"] = 50  # 데이터 없음

    pbr = fund.get("pbr")
    if pbr is not None and pbr > 0:
        if pbr < 0.5:
            scores["pbr"] = 95
        elif pbr < 1.0:
            scores["pbr"] = 80
        elif pbr < 1.5:
            scores["pbr"] = 65
        elif pbr < 2.0:
            scores["pbr"] = 50
        elif pbr < 3.0:
            scores["pbr"] = 35
        else:
            scores["pbr"] = 15
    else:
        scores["pbr"] = 50

    # PER/PBR 종합
    scores["value"] = (scores["per"] + scores["pbr"]) / 2
    return scores


def evaluate_growth(fund: dict) -> dict:
    """성장성 점수"""
    scores = {}

    roe = fund.get("roe")
    if roe is not None:
        roe_pct = roe * 100 if abs(roe) < 1 else roe  # 0.15 → 15%
        if roe_pct > 25:
            scores["roe"] = 95
        elif roe_pct > 20:
            scores["roe"] = 80
        elif roe_pct > 15:
            scores["roe"] = 65
        elif roe_pct > 10:
            scores["roe"] = 50
        elif roe_pct > 5:
            scores["roe"] = 35
        else:
            scores["roe"] = 15
    else:
        scores["roe"] = 50

    rev_growth = fund.get("revenue_growth")
    if rev_growth is not None:
        rg_pct = rev_growth * 100 if abs(rev_growth) < 5 else rev_growth
        if rg_pct > 30:
            scores["revenue_growth"] = 95
        elif rg_pct > 20:
            scores["revenue_growth"] = 80
        elif rg_pct > 10:
            scores["revenue_growth"] = 65
        elif rg_pct > 0:
            scores["revenue_growth"] = 50
        elif rg_pct > -10:
            scores["revenue_growth"] = 30
        else:
            scores["revenue_growth"] = 10
    else:
        scores["revenue_growth"] = 50

    scores["growth"] = (scores["roe"] + scores["revenue_growth"]) / 2
    return scores


def evaluate_profitability(fund: dict) -> dict:
    """수익성 점수"""
    scores = {}

    margin = fund.get("operating_margin")
    if margin is not None:
        mg_pct = margin * 100 if abs(margin) < 1 else margin
        if mg_pct > 25:
            scores["operating_margin"] = 90
        elif mg_pct > 15:
            scores["operating_margin"] = 70
        elif mg_pct > 10:
            scores["operating_margin"] = 55
        elif mg_pct > 5:
            scores["operating_margin"] = 40
        elif mg_pct > 0:
            scores["operating_margin"] = 25
        else:
            scores["operating_margin"] = 10
    else:
        scores["operating_margin"] = 50

    return scores


def get_fundamental_scores(fund: dict) -> dict:
    """종합 재무 점수"""
    value = evaluate_value(fund)
    growth = evaluate_growth(fund)
    profit = evaluate_profitability(fund)

    return {
        "per_pbr": value.get("value", 50),
        "roe_growth": growth.get("growth", 50),
        "revenue": growth.get("revenue_growth", 50),
        "operating_margin": profit.get("operating_margin", 50),
        "details": {**value, **growth, **profit},
    }
