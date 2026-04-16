"""본인 스윙 규칙 v2 검증 엔진

핵심 역할: 감정 매매 방지.
매수/매도 전에 이 검증을 돌려서 규칙 위반 여부를 자동 체크한다.
"""
from dataclasses import dataclass
from typing import Optional
from advisor.portfolio import get_rules, get_swing_holdings, get_swing_cash


@dataclass
class RuleCheck:
    passed: bool
    name: str
    message: str
    severity: str  # "pass", "warn", "fail"


class BuyValidator:
    """매수 전 규칙 검증"""

    def __init__(self, ticker: str, name: str, price: int, qty: int,
                 volume_ratio: Optional[float] = None,
                 daily_change_pct: Optional[float] = None,
                 rsi: Optional[float] = None,
                 macd_hist: Optional[float] = None,
                 above_ma20: Optional[bool] = None,
                 market_cap: Optional[int] = None):
        self.ticker = ticker
        self.name = name
        self.price = price
        self.qty = qty
        self.volume_ratio = volume_ratio
        self.daily_change_pct = daily_change_pct
        self.rsi = rsi
        self.macd_hist = macd_hist
        self.above_ma20 = above_ma20
        self.market_cap = market_cap
        self.rules = get_rules()

    def validate_all(self) -> list[RuleCheck]:
        checks = []
        checks.append(self._check_price_range())
        checks.append(self._check_position_count())
        checks.append(self._check_already_held())
        checks.append(self._check_cash_sufficient())
        if self.volume_ratio is not None:
            checks.append(self._check_volume())
        if self.daily_change_pct is not None:
            checks.append(self._check_daily_change())
        if self.rsi is not None:
            checks.append(self._check_rsi())
        if self.macd_hist is not None:
            checks.append(self._check_macd())
        if self.above_ma20 is not None:
            checks.append(self._check_ma20())
        return checks

    def _check_price_range(self) -> RuleCheck:
        lo, hi = self.rules.get("price_range", [0, float("inf")])
        if lo <= self.price <= hi:
            return RuleCheck(True, "가격 범위",
                             f"{self.price:,}원 (범위 {lo:,}~{hi:,})", "pass")
        return RuleCheck(False, "가격 범위",
                         f"{self.price:,}원 (허용 {lo:,}~{hi:,} 초과)", "fail")

    def _check_position_count(self) -> RuleCheck:
        max_pos = self.rules.get("max_positions", 2)
        held = get_swing_holdings()
        held_tickers = {h["ticker"] for h in held}
        if self.ticker in held_tickers:
            return RuleCheck(True, "보유 종목 수",
                             f"{len(held)}/{max_pos} (기존 종목 추가매수)", "pass")
        if len(held) >= max_pos:
            return RuleCheck(False, "보유 종목 수",
                             f"이미 {len(held)}개 보유 중 (상한 {max_pos}개)", "fail")
        return RuleCheck(True, "보유 종목 수",
                         f"{len(held)}/{max_pos}", "pass")

    def _check_already_held(self) -> RuleCheck:
        for h in get_swing_holdings():
            if h["ticker"] == self.ticker:
                return RuleCheck(True, "기존 보유",
                                 f"평단 {h['avg_price']:,}원으로 {h['qty']}주 보유 중 (추가매수 가능)",
                                 "warn")
        return RuleCheck(True, "신규 종목", "기존 보유 없음", "pass")

    def _check_cash_sufficient(self) -> RuleCheck:
        needed = self.price * self.qty
        cash = get_swing_cash()
        if cash >= needed:
            return RuleCheck(True, "예수금 충분",
                             f"{needed:,}원 필요 / {cash:,}원 보유 (잔액 {cash-needed:,}원)",
                             "pass")
        return RuleCheck(False, "예수금 부족",
                         f"{needed:,}원 필요 / {cash:,}원 보유 ({needed-cash:,}원 부족)",
                         "fail")

    def _check_volume(self) -> RuleCheck:
        min_vr = self.rules.get("min_volume_ratio", 0.5)
        if self.volume_ratio >= min_vr:
            return RuleCheck(True, "거래량",
                             f"{self.volume_ratio:.1f}x (최소 {min_vr}x)", "pass")
        return RuleCheck(False, "거래량 부족",
                         f"{self.volume_ratio:.1f}x (최소 {min_vr}x 미만)", "warn")

    def _check_daily_change(self) -> RuleCheck:
        max_chg = self.rules.get("max_daily_change", 5)
        if abs(self.daily_change_pct) <= max_chg:
            return RuleCheck(True, "당일 등락률",
                             f"{self.daily_change_pct:+.2f}% (허용 ±{max_chg}%)", "pass")
        return RuleCheck(False, "당일 등락률 초과",
                         f"{self.daily_change_pct:+.2f}% (허용 ±{max_chg}%)", "warn")

    def _check_rsi(self) -> RuleCheck:
        lo, hi = self.rules.get("rsi_range", [40, 70])
        if lo <= self.rsi <= hi:
            return RuleCheck(True, "RSI",
                             f"{self.rsi:.1f} (범위 {lo}~{hi})", "pass")
        return RuleCheck(False, "RSI 범위 벗어남",
                         f"{self.rsi:.1f} (권장 {lo}~{hi})", "warn")

    def _check_macd(self) -> RuleCheck:
        if self.rules.get("require_macd_positive", True):
            if self.macd_hist > 0:
                return RuleCheck(True, "MACD",
                                 f"히스토그램 {self.macd_hist:+.2f} (양수)", "pass")
            return RuleCheck(False, "MACD 음수",
                             f"히스토그램 {self.macd_hist:+.2f} (양수 조건 미충족)",
                             "warn")
        return RuleCheck(True, "MACD", "체크 건너뜀", "pass")

    def _check_ma20(self) -> RuleCheck:
        if self.rules.get("require_above_ma20", True):
            if self.above_ma20:
                return RuleCheck(True, "20일선 위치", "주가가 MA20 위 (상승 추세)",
                                 "pass")
            return RuleCheck(False, "20일선 미달",
                             "주가가 MA20 아래 (추세 약함)", "warn")
        return RuleCheck(True, "20일선", "체크 건너뜀", "pass")


class SellAdvisor:
    """매도 타이밍 조언"""

    def __init__(self, ticker: str, current_price: int, days_held: int):
        self.ticker = ticker
        self.current_price = current_price
        self.days_held = days_held
        self.rules = get_rules()
        self.holding = next(
            (h for h in get_swing_holdings() if h["ticker"] == ticker), None
        )

    def advise(self) -> list[str]:
        """매도 권장 이유 리스트 반환"""
        if not self.holding:
            return ["보유 종목이 아님"]

        advice = []
        avg = self.holding["avg_price"]
        pnl_pct = (self.current_price / avg - 1) * 100

        # 손절선 체크
        stop = self.holding.get("stop_loss", 0)
        if stop and self.current_price <= stop:
            advice.append(f"🚨 손절선 {stop:,}원 이탈 → 즉시 매도 (재협상 금지)")

        # 목표가 체크
        targets = self.holding.get("targets", [])
        for t in targets:
            if not t.get("hit") and self.current_price >= t["price"]:
                advice.append(
                    f"🎯 {t['price']:,}원 도달 → {t['qty']}주 분할 매도"
                )

        # 시간 체크
        max_days = self.rules.get("max_holding_days", 14)
        alert_days = self.rules.get("alert_holding_days", 7)
        if self.days_held >= max_days:
            advice.append(
                f"⏰ 보유 {self.days_held}일차 (상한 {max_days}일 초과) → 전량 매도"
            )
        elif self.days_held >= alert_days:
            if pnl_pct < 5:
                advice.append(
                    f"⏰ 보유 {self.days_held}일차 (주의 {alert_days}일), "
                    f"목표 미달성 → 50% 매도 고려"
                )

        if not advice:
            advice.append("✅ 보유 유지 (손절/목표/시간 조건 미충족)")

        return advice


def format_check_result(checks: list[RuleCheck]) -> str:
    """검증 결과 포맷팅"""
    lines = []
    failed = [c for c in checks if not c.passed or c.severity == "fail"]
    warned = [c for c in checks if c.severity == "warn"]
    passed = [c for c in checks if c.passed and c.severity == "pass"]

    for c in checks:
        icon = {"pass": "✅", "warn": "⚠️ ", "fail": "❌"}.get(c.severity, "❓")
        lines.append(f"  {icon} {c.name}: {c.message}")

    lines.append("")
    hard_fail = any(c.severity == "fail" for c in checks)
    if hard_fail:
        lines.append("🚫 판정: 매수 불가 (규칙 위반)")
    elif warned:
        lines.append(f"⚠️  판정: 매수 가능하나 주의 필요 ({len(warned)}개 경고)")
    else:
        lines.append("✅ 판정: 매수 조건 모두 충족")

    return "\n".join(lines)
