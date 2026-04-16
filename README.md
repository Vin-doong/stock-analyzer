# Stock Analyzer — 주식 분석 & 투자 조언 시스템

규칙 기반 스윙 트레이딩 보조 도구입니다.

1. **Claude Advisor CLI** (`advisor/`) — 터미널에서 실시간 시세/분석, 매수 검증, 매매 일지
2. **Streamlit 대시보드** (`app.py`) — 브라우저 기반 종목 스크리닝/차트/백테스트

---

## 빠른 시작 (Windows)

```batch
git clone https://github.com/Vin-doong/stock-analyzer.git
cd stock-analyzer
install.bat
```

### 실행

```batch
:: Streamlit 대시보드 (브라우저)
run.bat

:: Advisor CLI (터미널)
.venv\Scripts\python.exe -m advisor status
```

### 환경변수 (선택)

AI 추천 기능을 사용하려면:

```batch
copy .env.example .env
```

`.env`에서 provider 선택 후 API 키 입력:
```
# Claude 사용 시
AI_PROVIDER=claude
ANTHROPIC_API_KEY=sk-ant-api03-...

# GPT 사용 시
AI_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

둘 중 하나만 설정하면 됩니다. 기본값은 `claude`.

---

## Advisor CLI 명령어

```batch
.venv\Scripts\python.exe -m advisor <명령어>
```

| 명령어 | 용도 | 예시 |
|---|---|---|
| `status` | 포트폴리오 현황 | `advisor status` |
| `check` | 종목 기술적 분석 | `advisor check 005930` |
| `can-buy` | 매수 규칙 검증 | `advisor can-buy 005930 --qty 10 --price 25000` |
| `log` | 매매 기록 | `advisor log buy 005930 --qty 10 --price 25000 --reason "..." --emotion calm` |
| `journal` | 매매 일지 조회 | `advisor journal --n 10` |
| `briefing` | 시장 브리핑 | `advisor briefing` |
| `risk` | 리스크 계산기 | `advisor risk --stop 24000 --cash 500000 --buy 25000` |
| `sectors` | 섹터 회전 분석 | `advisor sectors` |
| `performance` | 누적 성과 | `advisor performance` |
| `us-status` | 미국 주식 현황 | `advisor us-status` |
| `us-alternatives` | 미국 대안 분석 | `advisor us-alternatives` |

> `--emotion` 옵션: `calm` / `fomo` / `fear` / `greed` / `revenge` — 감정 매매 추적용

---

## 기술적 지표 해석

| 지표 | 의미 | 매수 적합 | 주의 |
|---|---|---|---|
| **RSI** | 모멘텀 강도 (0~100) | 40~70 | >70 과매수 / <30 과매도 |
| **MACD Hist** | 추세 가속도 | 양수(+) | 음전환 → 약세 |
| **볼린저 %B** | 밴드 내 위치 (0~100%) | 20~80% | >100% 추격 금지 |
| **ADX** | 추세 강도 (0~100) | >20 추세 형성 | <15 횡보 |
| **MA20** | 20일 이동평균선 | 현재가 > MA20 | 이탈 시 매도 고려 |
| **거래량 비율** | 20일 평균 대비 | >1.0x | >2.0x 급변 신호 |

---

## 데이터 소스

| API | 용도 | 비용 |
|---|---|---|
| Naver Finance | 한국 주식 실시간 | 무료 |
| Daum Finance | 백업 (Naver 실패 시) | 무료 |
| FinanceDataReader | 과거 OHLCV | 무료 |
| yfinance | 미국 주식 펀더멘털 | 무료 |
| Anthropic API | AI 추천 - Claude (선택) | 유료 |
| OpenAI API | AI 추천 - GPT (선택) | 유료 |

실시간 시세는 **Naver → Daum → FDR 3단계 폴백**으로 동작합니다.

---

## 프로젝트 구조

```
├── advisor/           # CLI 도구 (핵심)
│   ├── __main__.py    # CLI 진입점
│   ├── portfolio.py   # 포트폴리오 (state.json)
│   ├── rules.py       # 매매 규칙 엔진
│   ├── journal.py     # 매매 일지
│   ├── analysis.py    # 기술적 지표 통합
│   ├── realtime.py    # 실시간 시세 (3단계 폴백)
│   ├── sector.py      # 섹터 분석
│   └── us_stocks.py   # 미국 주식
├── app.py             # Streamlit 대시보드
├── ai/                # AI 분석 (Claude / GPT 선택)
├── analysis/          # 기술적 지표 계산
├── data/              # 데이터 조회
├── pages/             # Streamlit 페이지
├── install.bat        # 설치
├── run.bat            # 실행
└── requirements.txt   # 의존성
```

### git 제외 (개인 데이터)
- `advisor/state.json` — 포트폴리오
- `advisor/journal.json` — 매매 일지
- `.env` — API 키

---

## 라이선스

MIT License — 자유롭게 사용 가능. 단, **투자 판단과 손익은 본인 책임입니다.**
