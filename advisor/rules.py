"""본인 스윙 규칙 v3 검증 엔진 (가중치 점수 시스템)

핵심 역할: 감정 매매 방지 + 시그널 강도 정량화.
각 지표에 가중치를 부여해 0~100점으로 매수 타당성을 점수화한다.

가중치 구성 (총 100점)
  MACD 히스토그램 양수  : 20
  MA20 위              : 15
  RSI 범위             : 15
  볼린저 %B 구간        : 15
  거래량 비율          : 15
  ADX 추세 강도         : 10
  가격 범위            : 5
  당일 등락률 ±5%       : 5

판정 기준
  80점 이상 : 풀 진입 (계획량 100%)
  60 ~ 80점 : 반 진입 (계획량 50%)
  40 ~ 60점 : 정찰 진입 (계획량 20~30%)
  40점 미만 : 관망
"""
from dataclasses import dataclass, field
from typing import Optional
from advisor.portfolio import get_rules, get_swing_holdings, get_swing_cash


# 지표별 가중치 (합계 100)
# 단기 지표 75 + 중장기 모멘텀 20 + 메타(가격/일등락) 5
WEIGHTS = {
    "macd": 15,
    "ma20": 12,
    "rsi": 10,
    "bb_pctb": 12,
    "volume": 12,
    "adx": 8,
    "momentum_60d": 15,
    "momentum_90d": 5,
    "price_range": 4,
    "daily_change": 7,
}


@dataclass
class RuleCheck:
    passed: bool
    name: str
    message: str
    severity: str  # "pass", "warn", "fail"
    weight: int = 0
    score: int = 0
    hard_block: bool = False  # True면 점수와 무관하게 매수 차단


class BuyValidator:
    """매수 전 규칙 검증 + 가중치 점수화"""

    def __init__(self, ticker: str, name: str, price: int, qty: int,
                 volume_ratio: Optional[float] = None,
                 daily_change_pct: Optional[float] = None,
                 rsi: Optional[float] = None,
                 macd_hist: Optional[float] = None,
                 above_ma20: Optional[bool] = None,
                 market_cap: Optional[int] = None,
                 bb_pctb: Optional[float] = None,
                 adx: Optional[float] = None,
                 ret_60d: Optional[float] = None,
                 ret_90d: Optional[float] = None):
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
        self.bb_pctb = bb_pctb
        self.adx = adx
        self.ret_60d = ret_60d
        self.ret_90d = ret_90d
        self.rules = get_rules()

    def validate_all(self) -> list[RuleCheck]:
        checks = []
        # 하드 제약 (점수 계산 제외, 위반 시 차단)
        checks.append(self._check_position_count())
        checks.append(self._check_already_held())
        checks.append(self._check_cash_sufficient())

        # 가중치 지표
        checks.append(self._check_price_range())
        checks.append(self._check_daily_change())
        if self.volume_ratio is not None:
            checks.append(self._check_volume())
        if self.rsi is not None:
            checks.append(self._check_rsi())
        if self.macd_hist is not None:
            checks.append(self._check_macd())
        if self.above_ma20 is not None:
            checks.append(self._check_ma20())
        if self.bb_pctb is not None:
            checks.append(self._check_bollinger_pctb())
        if self.adx is not None:
            checks.append(self._check_adx())
        if self.ret_60d is not None:
            checks.append(self._check_momentum_60d())
        if self.ret_90d is not None:
            checks.append(self._check_momentum_90d())
        return checks

    # ---- 하드 제약 (통과 필수, 점수 계산 제외) ----

    def _check_position_count(self) -> RuleCheck:
        max_pos = self.rules.get("max_positions", 2)
        held = get_swing_holdings()
        held_tickers = {h["ticker"] for h in held}
        if self.ticker in held_tickers:
            return RuleCheck(True, "보유 종목 수",
                             f"{len(held)}/{max_pos} (기존 종목 추가매수)", "pass")
        if len(held) >= max_pos:
            return RuleCheck(False, "보유 종목 수",
                             f"이미 {len(held)}개 보유 중 (상한 {max_pos}개)",
                             "fail", hard_block=True)
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
                         "fail", hard_block=True)

    # ---- 가중치 지표 ----

    def _check_price_range(self) -> RuleCheck:
        lo, hi = self.rules.get("price_range", [0, float("inf")])
        w = WEIGHTS["price_range"]
        if lo <= self.price <= hi:
            return RuleCheck(True, "가격 범위",
                             f"{self.price:,}원 (범위 {lo:,}~{hi:,})", "pass",
                             weight=w, score=w)
        return RuleCheck(False, "가격 범위",
                         f"{self.price:,}원 (허용 {lo:,}~{hi:,} 초과)",
                         "fail", weight=w, score=0, hard_block=True)

    def _check_volume(self) -> RuleCheck:
        min_vr = self.rules.get("min_volume_ratio", 0.5)
        w = WEIGHTS["volume"]
        if self.volume_ratio >= min_vr:
            # 거래량 비율에 따른 단계별 점수
            if self.volume_ratio >= 1.0:
                s = w  # 평소 이상 = 만점
            elif self.volume_ratio >= 0.7:
                s = int(w * 0.8)
            else:
                s = int(w * 0.5)
            return RuleCheck(True, "거래량",
                             f"{self.volume_ratio:.1f}x (최소 {min_vr}x)",
                             "pass", weight=w, score=s)
        return RuleCheck(False, "거래량 부족",
                         f"{self.volume_ratio:.1f}x (최소 {min_vr}x 미만)",
                         "warn", weight=w, score=0)

    def _check_daily_change(self) -> RuleCheck:
        max_chg = self.rules.get("max_daily_change", 5)
        w = WEIGHTS["daily_change"]
        if abs(self.daily_change_pct) <= max_chg:
            return RuleCheck(True, "당일 등락률",
                             f"{self.daily_change_pct:+.2f}% (허용 ±{max_chg}%)",
                             "pass", weight=w, score=w)
        return RuleCheck(False, "당일 등락률 초과",
                         f"{self.daily_change_pct:+.2f}% (허용 ±{max_chg}%)",
                         "warn", weight=w, score=0)

    def _check_rsi(self) -> RuleCheck:
        lo, hi = self.rules.get("rsi_range", [40, 70])
        w = WEIGHTS["rsi"]
        if lo <= self.rsi <= hi:
            # 50 근처 = 중립 가장 안전, 양 끝으로 갈수록 감점
            mid = (lo + hi) / 2
            dist = abs(self.rsi - mid) / ((hi - lo) / 2)  # 0~1
            s = int(w * (1 - dist * 0.3))  # 최대 30% 감점
            return RuleCheck(True, "RSI",
                             f"{self.rsi:.1f} (범위 {lo}~{hi})",
                             "pass", weight=w, score=s)
        return RuleCheck(False, "RSI 범위 벗어남",
                         f"{self.rsi:.1f} (권장 {lo}~{hi})",
                         "warn", weight=w, score=0)

    def _check_macd(self) -> RuleCheck:
        w = WEIGHTS["macd"]
        if self.rules.get("require_macd_positive", True):
            if self.macd_hist > 0:
                return RuleCheck(True, "MACD",
                                 f"히스토그램 {self.macd_hist:+.2f} (양수)",
                                 "pass", weight=w, score=w)
            return RuleCheck(False, "MACD 음수",
                             f"히스토그램 {self.macd_hist:+.2f} (양수 조건 미충족)",
                             "warn", weight=w, score=0)
        return RuleCheck(True, "MACD", "체크 건너뜀", "pass", weight=w, score=w)

    def _check_ma20(self) -> RuleCheck:
        w = WEIGHTS["ma20"]
        if self.rules.get("require_above_ma20", True):
            if self.above_ma20:
                return RuleCheck(True, "20일선 위치", "주가가 MA20 위 (상승 추세)",
                                 "pass", weight=w, score=w)
            return RuleCheck(False, "20일선 미달",
                             "주가가 MA20 아래 (추세 약함)",
                             "warn", weight=w, score=0)
        return RuleCheck(True, "20일선", "체크 건너뜀", "pass", weight=w, score=w)

    def _check_bollinger_pctb(self) -> RuleCheck:
        lo = self.rules.get("bb_pctb_min", 0.2)
        hi = self.rules.get("bb_pctb_max", 0.95)
        w = WEIGHTS["bb_pctb"]
        pct = self.bb_pctb * 100
        if self.bb_pctb > hi:
            return RuleCheck(False, "볼린저 %B 상단 돌파",
                             f"{pct:.1f}% (상한 {hi*100:.0f}% 초과 — 과열, 추격 금지)",
                             "warn", weight=w, score=0)
        if self.bb_pctb < lo:
            return RuleCheck(False, "볼린저 %B 하단 근접",
                             f"{pct:.1f}% (하한 {lo*100:.0f}% 미만 — 하락 추세 가능)",
                             "warn", weight=w, score=0)
        # 0.4~0.7 구간이 가장 안정적 (만점)
        # 0.2~0.4 또는 0.7~0.95는 70% 점수
        if 0.4 <= self.bb_pctb <= 0.7:
            s = w
        else:
            s = int(w * 0.7)
        return RuleCheck(True, "볼린저 %B",
                         f"{pct:.1f}% (적정 구간)",
                         "pass", weight=w, score=s)

    def _check_adx(self) -> RuleCheck:
        """ADX 추세 강도. 25 이상 = 추세 있음, 20 이하 = 횡보."""
        w = WEIGHTS["adx"]
        if self.adx >= 40:
            return RuleCheck(True, "ADX 추세 강도",
                             f"{self.adx:.1f} (강한 추세)",
                             "pass", weight=w, score=w)
        if self.adx >= 25:
            return RuleCheck(True, "ADX 추세 강도",
                             f"{self.adx:.1f} (추세 형성)",
                             "pass", weight=w, score=int(w * 0.8))
        if self.adx >= 20:
            return RuleCheck(True, "ADX 추세 강도",
                             f"{self.adx:.1f} (약한 추세)",
                             "pass", weight=w, score=int(w * 0.5))
        return RuleCheck(False, "ADX 횡보",
                         f"{self.adx:.1f} (20 미만 — 박스권, 돌파 매매 부적합)",
                         "warn", weight=w, score=0)

    def _check_momentum_60d(self) -> RuleCheck:
        """60일 중장기 모멘텀 + 과열 필터.
        너무 많이 오른 종목(+60% 이상)은 감점해서 "상투 잡기" 방지.
        """
        w = WEIGHTS["momentum_60d"]
        r = self.ret_60d
        if r >= 60:
            return RuleCheck(False, "60일 모멘텀 과열",
                             f"{r:+.1f}% (이미 급등 — 고점 추격 리스크)",
                             "warn", weight=w, score=int(w * 0.3))
        if r >= 30:
            return RuleCheck(True, "60일 모멘텀",
                             f"{r:+.1f}% (강력 상승 — 적정 구간)",
                             "pass", weight=w, score=w)
        if r >= 10:
            return RuleCheck(True, "60일 모멘텀",
                             f"{r:+.1f}% (견조한 상승)",
                             "pass", weight=w, score=int(w * 0.8))
        if r >= 0:
            return RuleCheck(True, "60일 모멘텀",
                             f"{r:+.1f}% (약한 상승/횡보)",
                             "warn", weight=w, score=int(w * 0.3))
        if r >= -10:
            return RuleCheck(False, "60일 모멘텀 하락",
                             f"{r:+.1f}% (단기 조정 or 하락 초입)",
                             "warn", weight=w, score=0)
        return RuleCheck(False, "60일 모멘텀 급락",
                         f"{r:+.1f}% (-10% 이하 — 하락 추세 명확)",
                         "fail", weight=w, score=0)

    def _check_momentum_90d(self) -> RuleCheck:
        """90일 중장기 추세 + 과열 필터.
        +100% 이상은 "이미 2배 올랐다"는 뜻 → 조정 임박 리스크.
        """
        w = WEIGHTS["momentum_90d"]
        r = self.ret_90d
        if r >= 100:
            return RuleCheck(False, "90일 과열",
                             f"{r:+.1f}% (3개월 2배↑ — 조정 임박 가능)",
                             "warn", weight=w, score=int(w * 0.2))
        if r >= 50:
            return RuleCheck(True, "90일 추세",
                             f"{r:+.1f}% (장기 강세 — 적정)",
                             "pass", weight=w, score=w)
        if r >= 20:
            return RuleCheck(True, "90일 추세",
                             f"{r:+.1f}% (상승 추세)",
                             "pass", weight=w, score=int(w * 0.8))
        if r >= 0:
            return RuleCheck(True, "90일 추세",
                             f"{r:+.1f}% (완만 상승)",
                             "warn", weight=w, score=int(w * 0.4))
        return RuleCheck(False, "90일 추세 하락",
                         f"{r:+.1f}% (장기 하락)",
                         "warn", weight=w, score=0)


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
        if not self.holding:
            return ["보유 종목이 아님"]

        advice = []
        avg = self.holding["avg_price"]
        pnl_pct = (self.current_price / avg - 1) * 100

        stop = self.holding.get("stop_loss", 0)
        if stop and self.current_price <= stop:
            advice.append(f"🚨 손절선 {stop:,}원 이탈 → 즉시 매도 (재협상 금지)")

        targets = self.holding.get("targets", [])
        for t in targets:
            if not t.get("hit") and self.current_price >= t["price"]:
                advice.append(
                    f"🎯 {t['price']:,}원 도달 → {t['qty']}주 분할 매도"
                )

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


def calculate_score(checks: list[RuleCheck]) -> tuple[int, int]:
    """가중치 점수 집계. (획득점수, 총가중치) 반환."""
    total_weight = sum(c.weight for c in checks)
    total_score = sum(c.score for c in checks)
    return total_score, total_weight


def score_to_action(score: int, total: int = 100) -> tuple[str, str]:
    """점수 → 액션 가이드. (아이콘+라벨, 권장배분)"""
    pct = (score / total * 100) if total > 0 else 0
    if pct >= 80:
        return ("🟢 풀 진입", "계획량의 80~100%")
    if pct >= 60:
        return ("🟡 반 진입", "계획량의 50%")
    if pct >= 40:
        return ("🟠 정찰 진입", "계획량의 20~30%")
    return ("🔴 관망", "진입 보류")


def format_check_result(checks: list[RuleCheck]) -> str:
    """검증 결과 포맷팅 (점수 포함)"""
    lines = []

    hard_block = any(c.hard_block for c in checks)

    # 하드 제약 먼저
    hard_checks = [c for c in checks if c.weight == 0]
    scored_checks = [c for c in checks if c.weight > 0]

    lines.append("  [하드 제약]")
    for c in hard_checks:
        icon = {"pass": "✅", "warn": "⚠️ ", "fail": "❌"}.get(c.severity, "❓")
        lines.append(f"  {icon} {c.name}: {c.message}")

    lines.append("")
    lines.append("  [점수 지표]")
    for c in scored_checks:
        icon = {"pass": "✅", "warn": "⚠️ ", "fail": "❌"}.get(c.severity, "❓")
        score_str = f" [{c.score}/{c.weight}]"
        lines.append(f"  {icon} {c.name}: {c.message}{score_str}")

    score, total = calculate_score(scored_checks)
    action, guide = score_to_action(score, total)

    lines.append("")
    lines.append(f"  📊 매수 점수: {score}/{total} ({score/total*100:.0f}%)")

    lines.append("")
    if hard_block:
        lines.append("🚫 판정: 매수 불가 (하드 제약 위반)")
    else:
        lines.append(f"{action}")
        lines.append(f"   권장 배분: {guide}")

    return "\n".join(lines)
