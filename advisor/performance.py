"""성과 추적 - 매매 일지 기반 통계 분석"""
from datetime import datetime
from advisor.journal import get_all


def calculate_performance() -> dict:
    """전체 매매 성과 계산"""
    entries = get_all()
    if not entries:
        return {"total_trades": 0}

    # 매매 쌍 (buy-sell) 매칭
    trades_by_ticker = {}
    for e in entries:
        ticker = e["ticker"]
        trades_by_ticker.setdefault(ticker, []).append(e)

    closed_trades = []  # 청산 완료된 거래
    open_positions = {}  # 미청산 포지션 (ticker -> [buys])

    for ticker, events in trades_by_ticker.items():
        events.sort(key=lambda x: x["timestamp"])
        buys = []
        for e in events:
            if e["action"] in ("buy",):
                buys.append(e)
            elif e["action"] in ("sell", "stop_loss", "target_hit"):
                # 평균 매수가 계산
                if not buys:
                    continue
                total_qty = sum(b["qty"] for b in buys)
                total_cost = sum(b["qty"] * b["price"] for b in buys)
                avg_buy_price = total_cost / total_qty if total_qty else 0

                sell_qty = e["qty"]
                sell_price = e["price"]
                realized_pnl = (sell_price - avg_buy_price) * sell_qty
                realized_pct = (sell_price / avg_buy_price - 1) * 100 if avg_buy_price else 0

                closed_trades.append({
                    "ticker": ticker,
                    "name": e.get("name", ticker),
                    "sell_date": e["timestamp"][:10],
                    "avg_buy_price": avg_buy_price,
                    "sell_price": sell_price,
                    "qty": sell_qty,
                    "pnl": realized_pnl,
                    "pnl_pct": realized_pct,
                    "exit_action": e["action"],
                })

                # 매수 차감 (FIFO)
                remaining = sell_qty
                while remaining > 0 and buys:
                    b = buys[0]
                    if b["qty"] <= remaining:
                        remaining -= b["qty"]
                        buys.pop(0)
                    else:
                        b["qty"] -= remaining
                        remaining = 0

        if buys:
            open_positions[ticker] = buys

    # 통계
    total_closed = len(closed_trades)
    if total_closed == 0:
        return {
            "total_trades": len(entries),
            "closed_trades": 0,
            "open_positions": len(open_positions),
        }

    wins = [t for t in closed_trades if t["pnl"] > 0]
    losses = [t for t in closed_trades if t["pnl"] <= 0]
    total_pnl = sum(t["pnl"] for t in closed_trades)

    avg_win = sum(t["pnl"] for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t["pnl"] for t in losses) / len(losses) if losses else 0
    win_rate = len(wins) / total_closed * 100

    # 손익비 (Profit Factor)
    total_profit = sum(t["pnl"] for t in wins) if wins else 0
    total_loss = abs(sum(t["pnl"] for t in losses)) if losses else 0
    profit_factor = total_profit / total_loss if total_loss > 0 else float("inf")

    # 감정 매매 분석
    emotional_count = sum(
        1 for e in entries
        if e.get("emotion") in ("fomo", "fear", "greed", "revenge")
    )

    return {
        "total_trades": len(entries),
        "closed_trades": total_closed,
        "open_positions": len(open_positions),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": win_rate,
        "total_pnl": total_pnl,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "profit_factor": profit_factor,
        "best_trade": max(closed_trades, key=lambda x: x["pnl"]),
        "worst_trade": min(closed_trades, key=lambda x: x["pnl"]),
        "emotional_trades": emotional_count,
        "emotional_ratio": emotional_count / len(entries) * 100 if entries else 0,
        "all_closed": closed_trades,
    }


def monthly_summary() -> dict:
    """월별 성과 요약"""
    perf = calculate_performance()
    closed = perf.get("all_closed", [])

    by_month = {}
    for t in closed:
        month = t["sell_date"][:7]  # YYYY-MM
        by_month.setdefault(month, []).append(t)

    result = {}
    for month, trades in sorted(by_month.items()):
        pnl = sum(t["pnl"] for t in trades)
        wins = len([t for t in trades if t["pnl"] > 0])
        result[month] = {
            "trades": len(trades),
            "wins": wins,
            "win_rate": wins / len(trades) * 100 if trades else 0,
            "pnl": pnl,
        }
    return result
