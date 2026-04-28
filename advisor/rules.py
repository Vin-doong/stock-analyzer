"""본인 스윙/단타/장투 규칙 v3 검증 엔진 (스타일별 가중치 시스템)

투자 스타일별 지표 우선순위:
- SWING (3~14일): 거래대금 + MACD + 추세 + 중장기 모멘텀
- DAY (당일): 거래대금 + 거래량 배수 + 볼밴 변동성 + 회전율
- LONG (장기): 중장기 모멘텀 + MA20 추세 + 유동성

판정 기준 (공통)
  80점 이상 : 풀 진입 (계획량 100%)
  60 ~ 80점 : 반 진입 (계획량 50%)
  40 ~ 60점 : 정찰 진입 (계획량 20~30%)
  40점 미만 : 관망
"""
from dataclasses import dataclass
from typing import Optional
from advisor.portfolio import get_rules, get_swing_holdings, get_swing_cash


# 스타일별 가중치 (합계 100)
WEIGHTS_BY_STYLE = {
    "swing": {
        "trading_value": 10,     # 거래대금 (유동성)
        "volume_ratio": 10,      # 거래량 배수
        "macd": 12,
        "ma20": 10,
        "rsi": 10,
        "bb_pctb": 10,
        "adx": 8,
        "momentum_60d": 15,
        "momentum_90d": 5,
        "price_range": 3,
        "daily_change": 3,
        "market_cap": 4,
    },
    "day": {
        "trading_value": 20,     # 단타 최우선
        "volume_ratio": 20,      # 단타 최우선
        "macd": 5,
        "ma20": 5,
        "rsi": 10,
        "bb_pctb": 15,           # 변동성 지표 단타에 중요
        "adx": 10,
        "momentum_60d": 3,
        "momentum_90d": 2,
        "price_range": 3,
        "daily_change": 5,
        "market_cap": 2,
    },
    "long": {
        "trading_value": 5,
        "volume_ratio": 5,
        "macd": 5,
        "ma20": 15,              # 장기 추세 핵심
        "rsi": 5,
        "bb_pctb": 5,
        "adx": 5,
        "momentum_60d": 15,
        "momentum_90d": 20,      # 장기 추세 핵심
        "price_range": 3,
        "daily_change": 2,
        "market_cap": 15,        # 안전성
    },
}


@dataclass
class RuleCheck:
    passed: bool
    name: str
    message: str
    severity: str
    weight: int = 0
    score: int = 0
    hard_block: bool = False


class BuyValidator:
    """스타일별 매수 전 규칙 검증 + 가중치 점수화"""

    def __init__(self, ticker: str, name: str, price: int, qty: int,
                 style: str = "swing",
                 volume_ratio: Optional[float] = None,
                 daily_change_pct: Optional[float] = None,
                 rsi: Optional[float] = None,
                 macd_hist: Optional[float] = None,
                 above_ma20: Optional[bool] = None,
                 market_cap: Optional[int] = None,
                 bb_pctb: Optional[float] = None,
                 adx: Optional[float] = None,
                 ret_60d: Optional[float] = None,
                 ret_90d: Optional[float] = None,
                 trading_value: Optional[int] = None,
                 turnover_rate: Optional[float] = None):
        self.ticker = ticker
        self.name = name
        self.price = price
        self.qty = qty
        self.style = style if style in WEIGHTS_BY_STYLE else "swing"
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
        self.trading_value = trading_value
        self.turnover_rate = turnover_rate
        self.rules = get_rules(self.style)
        self.weights = WEIGHTS_BY_STYLE[self.style]

    def validate_all(self) -> list[RuleCheck]:
        checks = []
        # 하드 제약
        checks.append(self._check_position_count())
        checks.append(self._check_already_held())
        checks.append(self._check_cash_sufficient())

        # 가중치 지표
        checks.append(self._check_price_range())
        checks.append(self._check_daily_change())
        if self.market_cap is not None:
            checks.append(self._check_market_cap())
        if self.trading_value is not None:
            checks.append(self._check_trading_value())
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

    # ---- 하드 제약 ----

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
        w = self.weights["price_range"]
        if lo <= self.price <= hi:
            return RuleCheck(True, "가격 범위",
                             f"{self.price:,}원 (범위 {lo:,}~{hi:,})",
                             "pass", weight=w, score=w)
        return RuleCheck(False, "가격 범위",
                         f"{self.price:,}원 (허용 {lo:,}~{hi:,} 초과)",
                         "fail", weight=w, score=0, hard_block=True)

    def _check_market_cap(self) -> RuleCheck:
        min_cap = self.rules.get("min_market_cap", 0)
        w = self.weights["market_cap"]
        if min_cap == 0:
            return RuleCheck(True, "시총", "체크 건너뜀", "pass", weight=w, score=w)
        cap_e = self.market_cap / 1e8
        min_e = min_cap / 1e8
        if self.market_cap >= min_cap:
            if self.market_cap >= min_cap * 3:
                s = w
            elif self.market_cap >= min_cap * 1.5:
                s = int(w * 0.8)
            else:
                s = int(w * 0.6)
            return RuleCheck(True, "시총",
                             f"{cap_e:,.0f}억 (최소 {min_e:,.0f}억)",
                             "pass", weight=w, score=s)
        return RuleCheck(False, "시총 미달",
                         f"{cap_e:,.0f}억 (최소 {min_e:,.0f}억 미만)",
                         "warn", weight=w, score=0)

    def _check_trading_value(self) -> RuleCheck:
        """거래대금 = 실질 유동성 지표 (단타/스윙 핵심)"""
        min_val = self.rules.get("min_trading_value", 3_000_000_000)
        w = self.weights["trading_value"]
        tv_e = self.trading_value / 1e8
        min_e = min_val / 1e8
        if self.trading_value >= min_val:
            # 거래대금 규모별 점수
            if self.trading_value >= min_val * 3:
                s = w
            elif self.trading_value >= min_val * 1.5:
                s = int(w * 0.8)
            else:
                s = int(w * 0.6)
            return RuleCheck(True, "거래대금",
                             f"{tv_e:,.0f}억 (최소 {min_e:,.0f}억)",
                             "pass", weight=w, score=s)
        return RuleCheck(False, "거래대금 부족",
                         f"{tv_e:,.0f}억 (최소 {min_e:,.0f}억 미만 — 유동성 부족)",
                         "warn", weight=w, score=0)

    def _check_volume(self) -> RuleCheck:
        min_vr = self.rules.get("min_volume_ratio", 0.5)
        w = self.weights["volume_ratio"]
        if self.volume_ratio >= min_vr:
            if self.volume_ratio >= 1.5:
                s = w  # 평소 1.5배 이상 = 관심 집중 만점
            elif self.volume_ratio >= 1.0:
                s = int(w * 0.85)
            elif self.volume_ratio >= 0.7:
                s = int(w * 0.65)
            else:
                s = int(w * 0.4)
            return RuleCheck(True, "거래량 배수",
                             f"{self.volume_ratio:.1f}x (최소 {min_vr}x)",
                             "pass", weight=w, score=s)
        return RuleCheck(False, "거래량 부족",
                         f"{self.volume_ratio:.1f}x (최소 {min_vr}x 미만)",
                         "warn", weight=w, score=0)

    def _check_daily_change(self) -> RuleCheck:
        max_chg = self.rules.get("max_daily_change", 5)
        w = self.weights["daily_change"]
        if abs(self.daily_change_pct) <= max_chg:
            return RuleCheck(True, "당일 등락률",
                             f"{self.daily_change_pct:+.2f}% (허용 ±{max_chg}%)",
                             "pass", weight=w, score=w)
        return RuleCheck(False, "당일 등락률 초과",
                         f"{self.daily_change_pct:+.2f}% (허용 ±{max_chg}%)",
                         "warn", weight=w, score=0)

    def _check_rsi(self) -> RuleCheck:
        """RSI 단계 점수화 (이분법 X).
        - 범위 안: 중앙 가까울수록 만점
        - 범위 위쪽 초과: 5 단위로 점진 차감 (강세장 대장주 수용)
        - 범위 아래쪽 초과: 약세 종목이라 더 빠르게 감점
        """
        lo, hi = self.rules.get("rsi_range", [40, 70])
        w = self.weights["rsi"]
        if lo <= self.rsi <= hi:
            mid = (lo + hi) / 2
            dist = abs(self.rsi - mid) / ((hi - lo) / 2)
            s = int(w * (1 - dist * 0.3))
            return RuleCheck(True, "RSI",
                             f"{self.rsi:.1f} (범위 {lo}~{hi})",
                             "pass", weight=w, score=s)
        if self.rsi > hi:
            # 과매수 단계: hi+5까지 70%, hi+10까지 40%, hi+15까지 15%, 그 이상 0
            over = self.rsi - hi
            if over <= 5:
                s = int(w * 0.7)
            elif over <= 10:
                s = int(w * 0.4)
            elif over <= 15:
                s = int(w * 0.15)
            else:
                s = 0
            return RuleCheck(s > 0, "RSI 과매수권",
                             f"{self.rsi:.1f} (권장 {lo}~{hi}, 상한 {over:.0f} 초과)",
                             "warn", weight=w, score=s)
        # 과매도: 약세 신호이므로 더 보수적 (lo-5까지 50%, lo-10까지 20%, 그 이상 0)
        under = lo - self.rsi
        if under <= 5:
            s = int(w * 0.5)
        elif under <= 10:
            s = int(w * 0.2)
        else:
            s = 0
        return RuleCheck(s > 0, "RSI 과매도권",
                         f"{self.rsi:.1f} (권장 {lo}~{hi}, 하한 {under:.0f} 미달)",
                         "warn", weight=w, score=s)

    def _check_macd(self) -> RuleCheck:
        w = self.weights["macd"]
        if self.rules.get("require_macd_positive", True):
            if self.macd_hist > 0:
                return RuleCheck(True, "MACD",
                                 f"히스토그램 {self.macd_hist:+.2f} (양수)",
                                 "pass", weight=w, score=w)
            return RuleCheck(False, "MACD 음수",
                             f"히스토그램 {self.macd_hist:+.2f} (양수 조건 미충족)",
                             "warn", weight=w, score=0)
        if self.macd_hist > 0:
            return RuleCheck(True, "MACD", f"히스토그램 {self.macd_hist:+.2f}",
                             "pass", weight=w, score=w)
        return RuleCheck(True, "MACD", f"히스토그램 {self.macd_hist:+.2f} (스타일상 비필수)",
                         "pass", weight=w, score=int(w * 0.5))

    def _check_ma20(self) -> RuleCheck:
        w = self.weights["ma20"]
        if self.rules.get("require_above_ma20", True):
            if self.above_ma20:
                return RuleCheck(True, "20일선 위치", "주가가 MA20 위 (상승 추세)",
                                 "pass", weight=w, score=w)
            return RuleCheck(False, "20일선 미달",
                             "주가가 MA20 아래 (추세 약함)",
                             "warn", weight=w, score=0)
        if self.above_ma20:
            return RuleCheck(True, "20일선", "MA20 위", "pass", weight=w, score=w)
        return RuleCheck(True, "20일선", "MA20 아래 (단타 스타일상 비필수)",
                         "pass", weight=w, score=int(w * 0.5))

    def _check_bollinger_pctb(self) -> RuleCheck:
        """볼린저 %B 단계 점수화 (이분법 X).
        - 적정 구간 (0.4~0.7): 만점
        - 정상 구간 안: 70%
        - 상단 돌파: 0.05 단위로 점진 차감 (강세 종목이 밴드 상단 타고 가는 패턴 수용)
        - 하단 근접: 약세 신호이므로 더 빠르게 감점
        """
        lo = self.rules.get("bb_pctb_min", 0.2)
        hi = self.rules.get("bb_pctb_max", 0.95)
        w = self.weights["bb_pctb"]
        pct = self.bb_pctb * 100
        if self.bb_pctb > hi:
            # 상단 돌파 단계: hi+0.05까지 60%, hi+0.10까지 30%, hi+0.20까지 10%, 그 이상 0
            over = self.bb_pctb - hi
            if over <= 0.05:
                s = int(w * 0.6)
            elif over <= 0.10:
                s = int(w * 0.3)
            elif over <= 0.20:
                s = int(w * 0.1)
            else:
                s = 0
            return RuleCheck(s > 0, "볼린저 %B 상단 돌파",
                             f"{pct:.1f}% (상한 {hi*100:.0f}% 초과 — 과열)",
                             "warn", weight=w, score=s)
        if self.bb_pctb < lo:
            # 하단 근접 단계: lo-0.05까지 40%, lo-0.10까지 15%, 그 이상 0
            under = lo - self.bb_pctb
            if under <= 0.05:
                s = int(w * 0.4)
            elif under <= 0.10:
                s = int(w * 0.15)
            else:
                s = 0
            return RuleCheck(s > 0, "볼린저 %B 하단 근접",
                             f"{pct:.1f}% (하한 {lo*100:.0f}% 미만 — 하락 추세)",
                             "warn", weight=w, score=s)
        if 0.4 <= self.bb_pctb <= 0.7:
            s = w
        else:
            s = int(w * 0.7)
        return RuleCheck(True, "볼린저 %B",
                         f"{pct:.1f}% (적정 구간)",
                         "pass", weight=w, score=s)

    def _check_adx(self) -> RuleCheck:
        w = self.weights["adx"]
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
                         f"{self.adx:.1f} (20 미만 — 박스권)",
                         "warn", weight=w, score=0)

    def _check_momentum_60d(self) -> RuleCheck:
        w = self.weights["momentum_60d"]
        r = self.ret_60d
        if r >= 60:
            return RuleCheck(False, "60일 모멘텀 과열",
                             f"{r:+.1f}% (이미 급등 — 고점 추격 리스크)",
                             "warn", weight=w, score=int(w * 0.3))
        if r >= 30:
            return RuleCheck(True, "60일 모멘텀",
                             f"{r:+.1f}% (강력 상승 — 적정)",
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
                             f"{r:+.1f}% (단기 조정)",
                             "warn", weight=w, score=0)
        return RuleCheck(False, "60일 모멘텀 급락",
                         f"{r:+.1f}% (-10% 이하 하락)",
                         "fail", weight=w, score=0)

    def _check_momentum_90d(self) -> RuleCheck:
        w = self.weights["momentum_90d"]
        r = self.ret_90d
        if r >= 100:
            return RuleCheck(False, "90일 과열",
                             f"{r:+.1f}% (3개월 2배↑ — 조정 임박)",
                             "warn", weight=w, score=int(w * 0.2))
        if r >= 50:
            return RuleCheck(True, "90일 추세",
                             f"{r:+.1f}% (장기 강세)",
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
    """매도 타이밍 조언 (스윙 기준).

    매도 결정을 정형화해 사용자 직관 의존을 제거한다.
    5가지 룰 트리거 + 5가지 매도 신호 + 시장 상황 동적 조정 + 트레일링 스탑.

    트리거 종류:
      [룰] 손절선 / 목표가 / 시간 상한 / 시간 알람 / 트레일링 스탑
      [신호] 거래량 매도세 / 고점 반납 / 추세 약화 / 섹터 동조 / 시장 약세
    """

    def __init__(self, ticker: str, current_price: int, days_held: int,
                 high_today: Optional[int] = None,
                 prev_close: Optional[int] = None,
                 volume_ratio: Optional[float] = None,
                 rsi: Optional[float] = None,
                 adx: Optional[float] = None,
                 adx_prev: Optional[float] = None,
                 sector_change_pct: Optional[float] = None,
                 market_change_pct: Optional[float] = None,
                 market_regime: Optional[str] = None):
        self.ticker = ticker
        self.current_price = current_price
        self.days_held = days_held
        self.high_today = high_today
        self.prev_close = prev_close
        self.volume_ratio = volume_ratio
        self.rsi = rsi
        self.adx = adx
        self.adx_prev = adx_prev
        self.sector_change_pct = sector_change_pct
        self.market_change_pct = market_change_pct
        self.market_regime = market_regime  # "강세" / "중립" / "약세"
        self.rules = get_rules("swing")
        self.holding = next(
            (h for h in get_swing_holdings() if h["ticker"] == ticker), None
        )

    def _adjusted_thresholds(self) -> dict:
        """시장 상황 기반 동적 임계 조정.

        강세장: 손절 완화 (-5%), 시간 알람 늦춤 (D+10), 시간 상한 D+14
        중립장: 기본값 (-4%, D+7, D+14)
        약세장: 손절 강화 (-3%), 시간 알람 빠르게 (D+5), 시간 상한 D+10
        """
        base_stop = abs(self.rules.get("stop_loss_pct", -4))  # 4
        base_alert = self.rules.get("alert_holding_days", 7)
        base_max = self.rules.get("max_holding_days", 14)

        if self.market_regime == "강세":
            return {"stop_pct": -5, "alert_days": 10, "max_days": 14, "context": "강세"}
        if self.market_regime == "약세":
            return {"stop_pct": -3, "alert_days": 5, "max_days": 10, "context": "약세"}
        return {"stop_pct": -base_stop, "alert_days": base_alert,
                "max_days": base_max, "context": "중립"}

    def _trailing_stop(self) -> Optional[int]:
        """1차/2차 매도 후 트레일링 스탑 가격 계산.

        1차 hit: 손절선을 평단으로 끌어올림 (본전 보전)
        2차 hit: 손절선을 1차 매도가로 끌어올림 (1차 수익 보전)
        """
        if not self.holding:
            return None
        targets = self.holding.get("targets", [])
        avg = self.holding["avg_price"]
        original_stop = self.holding.get("stop_loss", 0)

        first_hit = targets and targets[0].get("hit")
        second_hit = len(targets) >= 2 and targets[1].get("hit")

        if second_hit:
            sold_at = targets[0].get("sold_at") or targets[0].get("price")
            return max(original_stop, sold_at)
        if first_hit:
            return max(original_stop, avg)
        return None

    def advise(self) -> dict:
        """매도 조언. dict 반환 (구조화된 출력)."""
        if not self.holding:
            return {"status": "not_held", "messages": ["보유 종목이 아님"]}

        avg = self.holding["avg_price"]
        pnl_pct = (self.current_price / avg - 1) * 100
        thr = self._adjusted_thresholds()

        rule_triggers: list[str] = []
        signals: list[str] = []
        info: list[str] = []

        # ===== 룰 트리거 (명시적, 정형화) =====

        # 1. 손절선
        stop = self.holding.get("stop_loss", 0)
        if stop and self.current_price <= stop:
            rule_triggers.append(
                f"🚨 손절선 {stop:,}원 이탈 → 즉시 전량 매도 (재협상 금지)"
            )

        # 2. 트레일링 스탑 (1차/2차 매도 후)
        trail = self._trailing_stop()
        if trail and self.current_price <= trail:
            rule_triggers.append(
                f"🚨 트레일링 스탑 {trail:,}원 이탈 → 잔여 전량 매도 (1차/2차 수익 보전)"
            )

        # 3. 시장 상황 보정 손절 (사용자 평단 대비)
        adj_stop_price = int(avg * (1 + thr["stop_pct"] / 100))
        if self.current_price <= adj_stop_price and self.current_price > (stop or 0):
            rule_triggers.append(
                f"🚨 {thr['context']} 보정 손절 {adj_stop_price:,}원 도달 "
                f"({thr['stop_pct']}% / 평단 {avg:,}) → 전량 매도 검토"
            )

        # 4. 목표가 분할 매도
        targets = self.holding.get("targets", [])
        for t in targets:
            if not t.get("hit") and self.current_price >= t["price"]:
                rule_triggers.append(
                    f"🎯 {t['price']:,}원 도달 → {t['qty']}주 분할 매도"
                )

        # 5. 시간 상한
        if self.days_held >= thr["max_days"]:
            rule_triggers.append(
                f"⏰ 보유 {self.days_held}일차 ({thr['context']} 상한 "
                f"{thr['max_days']}일 초과) → 전량 매도"
            )
        elif self.days_held >= thr["alert_days"]:
            if pnl_pct < 5:
                rule_triggers.append(
                    f"⏰ 보유 {self.days_held}일차 ({thr['context']} 알람 "
                    f"{thr['alert_days']}일), 목표 미달성 → 50% 매도 고려"
                )

        # ===== 매도 신호 (감정 의존 대체용) =====

        # SIGNAL 1: 거래량 매도세 (평소 2배+ + 당일 음봉)
        if (self.volume_ratio is not None and self.volume_ratio >= 2.0
                and self.prev_close is not None
                and self.current_price < self.prev_close):
            signals.append(
                f"📉 거래량 매도세: {self.volume_ratio:.1f}x 폭증 + 음봉 "
                f"→ 50% 매도 신호"
            )

        # SIGNAL 2: 고점 반납 (당일 고점 대비 -5% 이상)
        if self.high_today and self.current_price > 0:
            reverted = (self.high_today - self.current_price) / self.high_today * 100
            if reverted >= 5:
                signals.append(
                    f"📉 고점 반납 -{reverted:.1f}% (고점 {self.high_today:,} "
                    f"→ 현재 {self.current_price:,}) → 추세 정점 가능성"
                )

        # SIGNAL 3: 추세 약화 (RSI 70+ AND ADX 하락)
        if (self.rsi is not None and self.rsi >= 70
                and self.adx is not None and self.adx_prev is not None
                and self.adx < self.adx_prev):
            signals.append(
                f"📉 추세 약화: RSI {self.rsi:.0f} 과매수 + ADX 하락 "
                f"({self.adx_prev:.1f}→{self.adx:.1f}) → 30% 매도 검토"
            )

        # SIGNAL 4: 섹터 약세 동조 (섹터 -2% + 종목 -1.5%)
        if (self.sector_change_pct is not None and self.sector_change_pct <= -2
                and self.prev_close is not None and self.current_price > 0):
            stock_chg = (self.current_price / self.prev_close - 1) * 100
            if stock_chg <= -1.5:
                signals.append(
                    f"📉 섹터 약세 동조: 섹터 {self.sector_change_pct:+.1f}% + "
                    f"종목 {stock_chg:+.1f}% → 구조적 약세 가능성"
                )

        # SIGNAL 5: 시장 약세 전환 (KOSPI/KOSDAQ -2%+)
        if (self.market_change_pct is not None
                and self.market_change_pct <= -2):
            signals.append(
                f"📉 시장 약세 전환: 지수 {self.market_change_pct:+.1f}% "
                f"→ 시스템 보호 50% 매도 검토"
            )

        # ===== 정보 출력 =====
        info.append(
            f"📊 평단 {avg:,} / 현재 {self.current_price:,} "
            f"({pnl_pct:+.2f}%) / D+{self.days_held} / 시장 {thr['context']}"
        )
        if trail:
            info.append(f"🛡️ 트레일링 스탑: {trail:,}원")

        # 종합 판정
        if rule_triggers:
            status = "rule_action"
        elif signals:
            status = "signal_warn"
        else:
            status = "hold"
            info.append("✅ 보유 유지 (룰 트리거·매도 신호 모두 미발동)")

        return {
            "status": status,
            "rule_triggers": rule_triggers,
            "signals": signals,
            "info": info,
            "thresholds": thr,
            "trailing_stop": trail,
        }


def format_sell_advice(advice: dict) -> str:
    """SellAdvisor.advise() 결과를 사람이 읽을 수 있게 포맷."""
    if advice["status"] == "not_held":
        return "보유 종목이 아님"
    lines = []
    for line in advice.get("info", []):
        lines.append(f"  {line}")
    if advice.get("rule_triggers"):
        lines.append("")
        lines.append("  [룰 트리거]")
        for t in advice["rule_triggers"]:
            lines.append(f"  {t}")
    if advice.get("signals"):
        lines.append("")
        lines.append("  [매도 신호]")
        for s in advice["signals"]:
            lines.append(f"  {s}")
    if advice["status"] == "hold":
        pass  # info에 이미 포함
    return "\n".join(lines)


def check_market_warnings(
    current_price: int,
    high_today: Optional[int] = None,
    prev_close: Optional[int] = None,
    volume_ratio: Optional[float] = None,
    rsi: Optional[float] = None,
    adx: Optional[float] = None,
    adx_prev: Optional[float] = None,
    sector_change_pct: Optional[float] = None,
    market_change_pct: Optional[float] = None,
    ret_60d: Optional[float] = None,
) -> list[str]:
    """매수/매도 공통 시장 신호 체크 (선행 신호).

    SellAdvisor의 매도 신호 5종을 BuyValidator에서도 사용해
    점수가 후행적인 한계를 시장 신호로 보완.

    Returns: 발동된 신호의 사람 읽기용 한 줄 설명 리스트
    """
    warnings = []

    # 거래량 매도세 (2x+ 음봉)
    if (volume_ratio is not None and volume_ratio >= 2.0
            and prev_close is not None and current_price < prev_close):
        warnings.append(f"거래량 매도세 ({volume_ratio:.1f}x + 음봉)")

    # 고점 반납 (-5% 이상)
    if high_today and current_price > 0:
        reverted = (high_today - current_price) / high_today * 100
        if reverted >= 5:
            warnings.append(f"고점 -{reverted:.1f}% 반납")
        elif reverted >= 3:
            warnings.append(f"고점 -{reverted:.1f}% 반납 임박")

    # 추세 약화 (RSI 70+ + ADX 하락)
    if (rsi is not None and rsi >= 70
            and adx is not None and adx_prev is not None
            and adx < adx_prev):
        warnings.append(
            f"추세 약화 (RSI {rsi:.0f} + ADX {adx_prev:.0f}→{adx:.0f})"
        )

    # 섹터 약세 동조 (섹터 -2% + 종목 -1.5%)
    if (sector_change_pct is not None and sector_change_pct <= -2
            and prev_close is not None and current_price > 0):
        stock_chg = (current_price / prev_close - 1) * 100
        if stock_chg <= -1.5:
            warnings.append(
                f"섹터 약세 동조 (섹터 {sector_change_pct:+.1f}%/종목 {stock_chg:+.1f}%)"
            )

    # 시장 약세 전환 (지수 -2%+)
    if market_change_pct is not None and market_change_pct <= -2:
        warnings.append(f"시장 약세 ({market_change_pct:+.1f}%)")

    # 60일 모멘텀 과열 (+100% 초과 = 1개월 1.5배 폭등)
    # 점수 시스템(_check_momentum_60d)이 +60% 이상 모두 동일 처리하는 한계 보완
    if ret_60d is not None:
        if ret_60d >= 200:
            warnings.append(f"60일 모멘텀 극과열 (+{ret_60d:.0f}%, 단기 조정 임박)")
        elif ret_60d >= 100:
            warnings.append(f"60일 모멘텀 과열 (+{ret_60d:.0f}%, 1개월 1.5배 이상)")

    return warnings


def calculate_score(checks: list[RuleCheck]) -> tuple[int, int]:
    total_weight = sum(c.weight for c in checks)
    total_score = sum(c.score for c in checks)
    return total_score, total_weight


def score_to_action(score: int, total: int = 100) -> tuple[str, str]:
    pct = (score / total * 100) if total > 0 else 0
    if pct >= 80:
        return ("🟢 풀 진입", "계획량의 80~100%")
    if pct >= 60:
        return ("🟡 반 진입", "계획량의 50%")
    if pct >= 40:
        return ("🟠 정찰 진입", "계획량의 20~30%")
    return ("🔴 관망", "진입 보류")


def format_check_result(checks: list[RuleCheck], style: str = "swing") -> str:
    lines = []
    hard_block = any(c.hard_block for c in checks)

    # 하드 제약: hard_block이거나 가중치 없는 사전 검증 (보유 종목 수 등)
    hard_checks = [c for c in checks if c.hard_block or c.weight == 0]
    # 점수 지표: 가중치 있고 hard_block 아닌 것만
    scored_checks = [c for c in checks if c.weight > 0 and not c.hard_block]

    lines.append(f"  [투자 스타일: {style.upper()}]")
    lines.append("")
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
