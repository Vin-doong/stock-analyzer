"""Claude Advisor CLI 진입점

사용법:
  python -m advisor status                    # 현재 포트폴리오 상태
  python -m advisor check 005930               # 종목 분석
  python -m advisor can-buy 005930 --qty 10 --price 25000
  python -m advisor log buy 005930 --qty 10 --price 25000 --reason "..."
  python -m advisor journal                    # 최근 매매 일지
  python -m advisor briefing                   # 일일 브리핑
  python -m advisor risk --stop 24000 --cash 500000 --risk-pct 2
  python -m advisor sectors                    # 섹터 회전 분석
  python -m advisor performance                # 누적 성과
"""
import sys
import argparse
from datetime import datetime


def cmd_status(args):
    from advisor.portfolio import load_state, days_held
    from advisor.analysis import fetch_stock_price

    state = load_state()
    print("=" * 60)
    print(f"  포트폴리오 현황  [{datetime.now().strftime('%Y-%m-%d %H:%M')}]")
    print("=" * 60)

    # 스윙 계좌 (청산 종목 제외)
    swing = state.get("swing", {})
    print(f"\n[스윙 계좌 - {swing.get('account', '')}]")
    holdings = [h for h in swing.get("holdings", [])
                if h.get("qty", 0) > 0 and h.get("status") != "closed"]
    total_value = 0
    for h in holdings:
        try:
            data = fetch_stock_price(h["ticker"], days=10)
            current = data.get("current", h["avg_price"])
        except Exception:
            current = h["avg_price"]

        qty = h["qty"]
        avg = h["avg_price"]
        cost = qty * avg
        value = qty * current
        pnl = value - cost
        pnl_pct = (current / avg - 1) * 100
        total_value += value

        d = days_held(h.get("entry_date", ""))
        max_d = state.get("rules", {}).get("swing", {}).get("max_holding_days", 14)

        print(f"  {h['name']} ({h['ticker']})")
        print(f"    {qty}주 @ {avg:,}원 → 현재 {current:,.0f}원")
        print(f"    평가: {value:,.0f}원 | 손익: {pnl:+,.0f}원 ({pnl_pct:+.2f}%)")
        print(f"    손절: {h.get('stop_loss', 0):,}원 | 보유: {d}일차 (상한 {max_d}일)")

        targets = h.get("targets", [])
        if targets:
            tgt_strs = []
            for t in targets:
                status = "✓" if t.get("hit") else " "
                tgt_strs.append(f"{status}{t['price']:,}")
            print(f"    목표: {' / '.join(tgt_strs)}")
        print()

    cash = swing.get("cash", 0)
    total = total_value + cash
    print(f"  예수금: {cash:,}원")
    print(f"  스윙 계좌 총액: {total:,.0f}원")

    # 규칙 요약
    rules = state.get("rules", {}).get("swing", {})
    print(f"\n[스윙 규칙 v2]")
    pr = rules.get("price_range", [0, 0])
    print(f"  가격: {pr[0]:,}~{pr[1]:,}원 | 최대 {rules.get('max_positions', 2)}종목")
    print(f"  손절: {rules.get('stop_loss_pct', -4)}% | 상한 보유: {rules.get('max_holding_days', 14)}일")
    print("=" * 60)


def cmd_check(args):
    from advisor.analysis import fetch_stock_price
    from advisor.portfolio import get_swing_holdings

    ticker = args.ticker
    data = fetch_stock_price(ticker)
    if not data:
        print(f"[오류] {ticker} 데이터 조회 실패")
        return

    print("=" * 60)
    print(f"  종목 체크: {ticker}")
    print("=" * 60)
    print(f"현재가: {data['current']:,.0f}원 ({data['day_change_pct']:+.2f}%)")
    print(f"시/고/저: {data['open']:,.0f} / {data['high']:,.0f} / {data['low']:,.0f}")
    print(f"거래량: {data['volume']:,}주 (평소 대비 {data.get('volume_ratio', 0):.2f}x)")
    print()
    print(f"기술적 지표:")
    print(f"  RSI: {data.get('rsi', 0):.1f} | MACD Hist: {data.get('macd_hist', 0):.2f}")
    print(f"  볼린저 %B: {(data.get('bb_pctb', 0) or 0)*100:.1f}% | ADX: {data.get('adx', 0):.1f}")
    if data.get('ma20'):
        above = "↑ (강세)" if data.get('above_ma20') else "↓ (약세)"
        print(f"  MA20: {data['ma20']:,.0f} {above}")

    # 보유 중 여부
    held = next((h for h in get_swing_holdings() if h["ticker"] == ticker), None)
    if held:
        c = data["current"]
        avg = held["avg_price"]
        pnl_pct = (c / avg - 1) * 100
        print(f"\n[본인 포지션]")
        print(f"  {held['qty']}주 @ {avg:,}원")
        print(f"  손익: {(c-avg)*held['qty']:+,.0f}원 ({pnl_pct:+.2f}%)")
        print(f"  손절선 {held.get('stop_loss', 0):,}원까지: {c - held.get('stop_loss', 0):+,.0f}원")


def cmd_can_buy(args):
    from advisor.rules import BuyValidator, format_check_result
    from advisor.analysis import fetch_stock_price

    ticker = args.ticker
    qty = args.qty
    data = fetch_stock_price(ticker)
    if not data:
        print(f"[오류] {ticker} 데이터 조회 실패")
        return

    price = args.price if args.price else int(data["current"])
    name = args.name or ticker

    validator = BuyValidator(
        ticker=ticker, name=name, price=price, qty=qty,
        style=args.style,
        volume_ratio=data.get("volume_ratio"),
        daily_change_pct=data.get("day_change_pct"),
        rsi=data.get("rsi"),
        macd_hist=data.get("macd_hist"),
        above_ma20=data.get("above_ma20"),
        bb_pctb=data.get("bb_pctb"),
        adx=data.get("adx"),
        ret_60d=data.get("ret_60d"),
        ret_90d=data.get("ret_90d"),
        market_cap=data.get("market_cap"),
        trading_value=data.get("trading_value"),
    )
    checks = validator.validate_all()

    print("=" * 60)
    print(f"  매수 가능 여부: {name} ({ticker})")
    print(f"  {qty}주 × {price:,}원 = {qty*price:,}원")
    print("=" * 60)
    print(format_check_result(checks, style=args.style))


def cmd_log(args):
    from advisor.journal import log_trade
    from advisor.portfolio import load_state, save_state

    entry = log_trade(
        action=args.action,
        ticker=args.ticker,
        name=args.name or args.ticker,
        qty=args.qty,
        price=args.price,
        reason=args.reason,
        emotion=args.emotion,
        notes=args.notes,
    )
    print(f"✅ 매매 기록 저장 (id={entry['id']})")
    print(f"   {args.action} {args.ticker} {args.qty}주 @ {args.price:,}원")
    print(f"   이유: {args.reason}")
    if args.emotion:
        print(f"   감정: {args.emotion}")


def cmd_journal(args):
    from advisor.journal import get_recent, analyze_patterns

    entries = get_recent(args.n or 10)
    print("=" * 60)
    print(f"  최근 매매 일지 ({len(entries)}건)")
    print("=" * 60)
    for e in entries:
        ts = e["timestamp"][:16].replace("T", " ")
        print(f"[{ts}] {e['action']:8} {e['name']} {e['qty']}주 @ {e['price']:,}원")
        print(f"  이유: {e['reason']}")
        if e.get("emotion"):
            print(f"  감정: {e['emotion']}")
        print()

    # 패턴 분석
    patterns = analyze_patterns()
    print("=" * 60)
    print(f"매매 통계:")
    print(f"  총 거래: {patterns['total_trades']}건")
    print(f"  행동별: {patterns['by_action']}")
    if patterns.get("emotional_ratio", 0) > 0:
        print(f"  감정 매매 비율: {patterns['emotional_ratio']:.1f}%")


def cmd_briefing(args):
    from advisor.analysis import fetch_market_overview, fetch_sector_leaders
    from advisor.portfolio import load_state, days_held
    from advisor.analysis import fetch_stock_price

    print("=" * 60)
    print(f"  일일 브리핑  [{datetime.now().strftime('%Y-%m-%d %H:%M')}]")
    print("=" * 60)

    # 시장 개요
    print("\n[시장]")
    mkt = fetch_market_overview()
    for key, label in [("kospi", "KOSPI"), ("kosdaq", "KOSDAQ"),
                        ("sp500", "S&P500"), ("nasdaq", "NASDAQ")]:
        if key in mkt:
            d = mkt[key]
            extra = ""
            if "ret_5d" in d:
                extra = f" | 5일 {d['ret_5d']:+.2f}% | 20일 {d['ret_20d']:+.2f}%"
            print(f"  {label}: {d['value']:,.2f} ({d['day_change']:+.2f}%){extra}")

    # 섹터
    print("\n[섹터 평균]")
    sectors = fetch_sector_leaders()
    for sector, d in sorted(sectors.items(), key=lambda x: -x[1]["avg_change"]):
        emoji = "🔥" if d["avg_change"] > 3 else ("🟢" if d["avg_change"] > 1 else ("🟡" if d["avg_change"] > -1 else "🔴"))
        print(f"  {emoji} {sector:8}: {d['avg_change']:+.2f}%")

    # 내 포지션 (청산 종목 제외)
    print("\n[내 스윙 포지션]")
    state = load_state()
    active = [h for h in state.get("swing", {}).get("holdings", [])
              if h.get("qty", 0) > 0 and h.get("status") != "closed"]
    if not active:
        print("  (보유 종목 없음)")
    for h in active:
        try:
            data = fetch_stock_price(h["ticker"], days=5)
            c = data.get("current", h["avg_price"])
        except Exception:
            c = h["avg_price"]
        pnl_pct = (c / h["avg_price"] - 1) * 100
        d = days_held(h.get("entry_date", ""))
        max_d = state["rules"]["swing"]["max_holding_days"]
        print(f"  {h['name']}: {c:,.0f}원 ({pnl_pct:+.2f}%) | D+{d}/{max_d}")


def cmd_risk(args):
    stop = args.stop
    cash = args.cash
    risk_pct = args.risk_pct or 2

    max_loss = cash * risk_pct / 100
    max_shares_rough = int(max_loss / (abs(args.buy - stop) if args.buy else stop * 0.04))

    print("=" * 60)
    print("  리스크 계산기")
    print("=" * 60)
    print(f"예수금: {cash:,}원")
    print(f"최대 허용 손실: {risk_pct}% = {max_loss:,.0f}원")
    print(f"손절선: {stop:,}원")
    if args.buy:
        loss_per_share = args.buy - stop
        print(f"매수 예정가: {args.buy:,}원")
        print(f"주당 손실: {loss_per_share:,}원")
        print(f"최대 매수 수량: {max_shares_rough}주")
        print(f"최대 투입 금액: {max_shares_rough * args.buy:,}원")
    else:
        print("매수 예정가 (-b) 옵션 필요")


def cmd_sectors(args):
    from advisor.sector import analyze_sectors
    from advisor.portfolio import get_rules
    sectors = analyze_sectors()

    # 가격 필터 기본값은 스윙 룰의 가격대
    rules = get_rules()
    default_lo, default_hi = rules.get("price_range", [3000, 50000])
    price_max = args.price_max if args.price_max is not None else default_hi
    price_min = args.price_min if args.price_min is not None else default_lo

    print("=" * 60)
    print(f"  섹터 회전 분석  [{datetime.now().strftime('%Y-%m-%d %H:%M')}]")
    if args.price_max is not None or args.price_min is not None:
        print(f"  (가격 필터: {price_min:,}~{price_max:,}원)")
    print("=" * 60)
    print(f"{'섹터':<16}{'오늘':>10}{'5일':>10}{'종목수':>8}  상태")
    print("-" * 60)

    ranked = sorted(sectors.items(), key=lambda x: -x[1]["avg_today"])
    for name, d in ranked:
        today = d["avg_today"]
        five = d["avg_5d"]
        count = d["count"]
        if today > 2 and five > 3:
            status = "🔥 HOT"
        elif today > 1 and five > 0:
            status = "🟢 강세"
        elif today < -1 and five < -2:
            status = "🔴 약세"
        elif today < -0.5:
            status = "🟠 약보합"
        else:
            status = "🟡 중립"
        print(f"{name:<16}{today:+9.2f}%{five:+9.2f}%{count:>8}  {status}")

    print()
    # Top sector details: 가격대 내 종목만
    if ranked:
        top_name, top_data = ranked[0]
        eligible = [m for m in top_data["members"]
                    if price_min <= m["price"] <= price_max]
        print(f"[오늘 최강 섹터: {top_name}]")
        if eligible:
            for m in eligible[:5]:
                print(f"  {m['name']:<14} {m['price']:>9,.0f}원 ({m['change_pct']:+.2f}%) | 5일 {m['ret_5d']:+.2f}%")
        else:
            print(f"  (가격 {price_min:,}~{price_max:,}원 범위 내 종목 없음)")
            # 가격 초과 참고용 표시
            others = top_data["members"][:3]
            if others:
                print(f"\n  참고 — 가격 초과 종목:")
                for m in others:
                    print(f"    {m['name']:<14} {m['price']:>9,.0f}원 ({m['change_pct']:+.2f}%)")


def cmd_us_status(args):
    from advisor.us_stocks import evaluate_us_portfolio
    from advisor.portfolio import load_state

    state = load_state()
    us_holdings = state.get("us_stocks", {}).get("holdings", [])
    if not us_holdings:
        print("미국 주식 포트폴리오가 비어있습니다.")
        return

    result = evaluate_us_portfolio(us_holdings)

    print("=" * 68)
    print(f"  미국 주식 포트폴리오  [{datetime.now().strftime('%Y-%m-%d %H:%M')}]")
    print(f"  환율: {result['usd_krw_rate']:.2f}원/USD")
    print("=" * 68)
    print(f"{'종목':<10}{'수량':>10}{'현재가':>12}{'평가액':>16}{'전일':>10}")
    print("-" * 68)

    for item in result["items"]:
        if "error" in item:
            print(f"  {item['symbol']:<8} (조회 실패)")
            continue
        print(f"  {item['symbol']:<8}"
              f"{item['qty']:>10.4f}"
              f"{item['price_usd']:>10.2f}USD"
              f"{item['value_krw']:>13,.0f}원"
              f"{item['change_pct']:>+9.2f}%")

    print("-" * 68)
    print(f"  총 평가: ${result['total_value_usd']:,.2f} "
          f"(₩{result['total_value_krw']:,.0f})")

    # 상세 지표
    print()
    print("[종목별 상세]")
    for item in result["items"]:
        if "error" in item:
            continue
        div = item.get('dividend_yield')
        # div는 이미 percentage (us_stocks.py에서 정규화됨)
        div_str = f"{div:.2f}%" if div else "-"
        pe = item.get('pe')
        pe_str = f"{pe:.1f}" if pe else "-"

        ma50 = item.get('fifty_day_avg')
        ma200 = item.get('two_hundred_day_avg')
        trend = ""
        if ma50 and ma200:
            if item['price_usd'] > ma50 > ma200:
                trend = "📈 강세 (정배열)"
            elif item['price_usd'] < ma50 < ma200:
                trend = "📉 약세 (역배열)"
            else:
                trend = "🟡 혼조"

        print(f"  {item['symbol']:<8} PER:{pe_str:<8} 배당:{div_str:<8} {trend}")


def cmd_us_alternatives(args):
    from advisor.us_stocks import evaluate_alternatives, ALTERNATIVE_CANDIDATES

    print("=" * 68)
    print(f"  미국 주식 대안 후보 분석")
    print("=" * 68)
    print(f"{'종목':<8}{'가격':>10}{'전일':>8}{'PER':>8}{'배당':>8}  추세/점수")
    print("-" * 68)

    results = evaluate_alternatives()
    for r in results:
        pe = f"{r['pe']:.1f}" if r.get('pe') else "-"
        div_raw = r.get('dividend_yield')
        div = f"{div_raw:.2f}%" if div_raw else "-"
        off_high = r.get('off_52w_high', 0)
        score = r['health_score']
        icon = "🔥" if score >= 80 else ("🟢" if score >= 70 else ("🟡" if score >= 55 else "🔴"))
        print(f"  {r['symbol']:<6}"
              f"{r['price']:>8.2f}"
              f"{r['change_pct']:>+7.2f}%"
              f"{pe:>8}"
              f"{div:>8}"
              f"  {icon} {score}점 ({off_high:+.1f}% vs 52w 고점)")

    print()
    print("[대안 카테고리]")
    for symbol, desc in ALTERNATIVE_CANDIDATES.items():
        print(f"  {symbol:<8} {desc}")


def cmd_performance(args):
    from advisor.performance import calculate_performance, monthly_summary
    perf = calculate_performance()

    print("=" * 60)
    print(f"  성과 통계")
    print("=" * 60)
    print(f"총 매매 기록: {perf['total_trades']}건")
    print(f"청산 완료: {perf.get('closed_trades', 0)}건")
    print(f"오픈 포지션: {perf.get('open_positions', 0)}개")

    if perf.get("closed_trades", 0) > 0:
        print()
        print(f"승률: {perf['win_rate']:.1f}% ({perf['wins']}승 {perf['losses']}패)")
        print(f"총 손익: {perf['total_pnl']:+,.0f}원")
        print(f"평균 수익: {perf['avg_win']:+,.0f}원")
        print(f"평균 손실: {perf['avg_loss']:+,.0f}원")
        pf = perf['profit_factor']
        pf_str = f"{pf:.2f}" if pf != float('inf') else "∞"
        print(f"손익비(PF): {pf_str}")

        if perf.get("best_trade"):
            bt = perf["best_trade"]
            print(f"\n최고 수익: {bt['name']} {bt['pnl']:+,.0f}원 ({bt['pnl_pct']:+.2f}%)")
        if perf.get("worst_trade"):
            wt = perf["worst_trade"]
            print(f"최대 손실: {wt['name']} {wt['pnl']:+,.0f}원 ({wt['pnl_pct']:+.2f}%)")

    print()
    print(f"감정 매매 비율: {perf.get('emotional_ratio', 0):.1f}% ({perf.get('emotional_trades', 0)}건)")

    # 월별
    monthly = monthly_summary()
    if monthly:
        print()
        print("[월별 성과]")
        for month, d in monthly.items():
            print(f"  {month}: {d['trades']}건 / 승률 {d['win_rate']:.0f}% / 손익 {d['pnl']:+,.0f}원")


def main():
    parser = argparse.ArgumentParser(prog="advisor", description="Claude Advisor")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="포트폴리오 현황")

    p_check = sub.add_parser("check", help="종목 체크")
    p_check.add_argument("ticker")

    p_buy = sub.add_parser("can-buy", help="매수 가능 여부 검증")
    p_buy.add_argument("ticker")
    p_buy.add_argument("--qty", type=int, required=True)
    p_buy.add_argument("--price", type=int)
    p_buy.add_argument("--name", type=str)
    p_buy.add_argument("--style", type=str, default="swing",
                       choices=["swing", "day", "long"],
                       help="투자 스타일 (swing/day/long). 기본: swing")

    p_log = sub.add_parser("log", help="매매 기록")
    p_log.add_argument("action", choices=["buy", "sell", "stop_loss", "target_hit"])
    p_log.add_argument("ticker")
    p_log.add_argument("--qty", type=int, required=True)
    p_log.add_argument("--price", type=int, required=True)
    p_log.add_argument("--reason", type=str, required=True)
    p_log.add_argument("--emotion", choices=["calm", "fomo", "fear", "greed", "revenge"])
    p_log.add_argument("--name", type=str)
    p_log.add_argument("--notes", type=str)

    p_journal = sub.add_parser("journal", help="매매 일지")
    p_journal.add_argument("--n", type=int, default=10)

    sub.add_parser("briefing", help="일일 브리핑")

    p_risk = sub.add_parser("risk", help="리스크 계산")
    p_risk.add_argument("--stop", type=int, required=True)
    p_risk.add_argument("--cash", type=int, required=True)
    p_risk.add_argument("--buy", type=int)
    p_risk.add_argument("--risk-pct", type=float, default=2)

    p_sectors = sub.add_parser("sectors", help="섹터 회전 분석")
    p_sectors.add_argument("--price-max", type=int, dest="price_max",
                           help="최강 섹터 종목 가격 상한 (기본: 룰 상한)")
    p_sectors.add_argument("--price-min", type=int, dest="price_min",
                           help="최강 섹터 종목 가격 하한 (기본: 룰 하한)")
    sub.add_parser("performance", help="누적 성과 통계")
    sub.add_parser("us-status", help="미국 주식 포트폴리오 현황")
    sub.add_parser("us-alternatives", help="미국 주식 대안 후보 분석")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    dispatch = {
        "status": cmd_status,
        "check": cmd_check,
        "can-buy": cmd_can_buy,
        "log": cmd_log,
        "journal": cmd_journal,
        "briefing": cmd_briefing,
        "risk": cmd_risk,
        "sectors": cmd_sectors,
        "performance": cmd_performance,
        "us-status": cmd_us_status,
        "us-alternatives": cmd_us_alternatives,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
