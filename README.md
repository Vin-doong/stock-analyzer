# Stock Analyzer — 주식 분석 & 투자 조언 시스템

규칙 기반 스윙 트레이딩 보조 도구입니다.

1. **Claude Advisor CLI** (`advisor/`) — 터미널에서 실시간 시세/분석, 매수 검증, 매매 일지, 전종목 스캔
2. **Streamlit 대시보드** (`app.py`) — 브라우저 기반 종목 스크리닝/차트/백테스트

---

## 빠른 시작 (Windows)

```batch
git clone https://github.com/Vin-doong/stock-analyzer.git
cd stock-analyzer
install.bat
```

### 실행 방법

가장 간단한 방법 — **`run.bat` 더블클릭**해서 메뉴에서 선택:

```
  [A] 포트폴리오 현황         (status)
  [B] 전종목 스캔 (스윙)      (scan swing)
  [C] 전종목 스캔 (단타)      (scan day)
  [D] 전종목 스캔 (장기)      (scan long)
  [E] 종목 체크              (check ticker)
  [F] 매수 검증              (can-buy ticker --qty N)
  [G] 매매 일지              (journal)
  [H] 누적 성과              (performance)
  [I] 시장 브리핑            (briefing)
  [J] 섹터 회전 분석         (sectors)
  [K] 리스크 계산기          (risk)
  [L] 미국 주식 현황         (us-status)
  [D1] Streamlit 대시보드 (브라우저)
  [D2] Advisor 셸 (수동 입력)
  [Q] 종료
```

- 각 메뉴는 필요한 값(종목코드, 수량, 스타일 등)을 대화형으로 입력받음
- 실행 후 엔터로 메뉴 복귀, Q로 종료
- UTF-8 코드페이지(`chcp 65001`) 자동 설정 — 한글 깨짐 없음

명령어를 직접 실행하려면 `advisor.bat` 래퍼 사용:

```batch
advisor status
advisor scan --style swing --top 10
advisor check 005930
advisor can-buy 005930 --qty 10
```

> `advisor.bat`은 자동으로 `.venv`를 찾아 실행하므로 venv 활성화가 필요 없습니다.

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
advisor <명령어>
```

| 명령어 | 용도 | 예시 |
|---|---|---|
| `status` | 포트폴리오 현황 | `advisor status` |
| `check` | 종목 기술적 분석 | `advisor check 005930` |
| `can-buy` | 매수 규칙 검증 (점수화) | `advisor can-buy 005930 --qty 10` |
| `scan` | **전종목 스캔 (KOSPI+KOSDAQ)** | `advisor scan --style swing --top 10` |
| `log` | 매매 기록 | `advisor log buy 005930 --qty 10 --price 25000 --reason "..." --emotion calm` |
| `journal` | 매매 일지 조회 | `advisor journal --n 10` |
| `briefing` | 시장 브리핑 | `advisor briefing` |
| `risk` | 리스크 계산기 | `advisor risk --stop 24000 --cash 500000 --buy 25000` |
| `sectors` | 섹터 회전 분석 | `advisor sectors` |
| `performance` | 누적 성과 | `advisor performance` |
| `us-status` | 미국 주식 현황 | `advisor us-status` |
| `us-alternatives` | 미국 대안 분석 | `advisor us-alternatives` |

> `--emotion` 옵션: `calm` / `fomo` / `fear` / `greed` / `revenge` — 감정 매매 추적용

### `scan` 옵션

| 옵션 | 기본값 | 설명 |
|---|---|---|
| `--style` | `swing` | `swing` / `day` / `long` 중 선택. 스타일별 하드 필터 + 가중치 적용 |
| `--top` | `10` | 정밀 분석할 상위 N개 |
| `--no-precise` | off | 1차 필터만 (빠른 체크) |
| `--include-held` | off | 보유 종목도 결과에 포함 |

**예시**:
```batch
advisor scan                              # 스윙 스타일, 상위 10개
advisor scan --style day --top 5          # 단타 상위 5개
advisor scan --style long --top 15        # 장기 상위 15개
advisor scan --no-precise --top 50        # 1차 필터만 (빠름)
```

스캔 흐름:
1. KOSPI + KOSDAQ 전종목 스냅샷 (FinanceDataReader)
2. 스타일별 하드 필터 적용 (가격/등락/거래대금/시총)
3. 거래대금 내림차순 정렬 → 상위 N개 추출
4. 정밀 분석 (BuyValidator + 점수화) — 병렬 처리

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
| **60일 모멘텀** | 중기 추세 | 10~50% | >70% 과열 페널티 |

---

## 매수 점수 등급

`can-buy` / `scan` 결과의 점수는 다음 기준으로 해석합니다:

| 점수 | 권장 | 진입 비중 |
|---|---|---|
| 80~100 | 🟢 풀 진입 | 계획량의 80~100% |
| 60~79 | 🟡 반 진입 | 계획량의 50% |
| 40~59 | 🟠 정찰 | 계획량의 20~30% |
| 0~39 | 🔴 관망 | 진입 금지 |

하드 블록(`hard_block`) 걸린 종목은 점수와 무관하게 진입 금지.

---

## 데이터 소스

| API | 용도 | 비용 |
|---|---|---|
| Naver Finance | 한국 주식 실시간 | 무료 |
| Daum Finance | 백업 (Naver 실패 시) | 무료 |
| FinanceDataReader | 과거 OHLCV + 전종목 리스팅 | 무료 |
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
│   ├── rules.py       # 매매 규칙 엔진 (스타일별 가중치)
│   ├── journal.py     # 매매 일지
│   ├── analysis.py    # 기술적 지표 통합
│   ├── realtime.py    # 실시간 시세 (3단계 폴백)
│   ├── scan.py        # 전종목 스캔
│   ├── sector.py      # 섹터 분석
│   └── us_stocks.py   # 미국 주식
├── app.py             # Streamlit 대시보드
├── ai/                # AI 분석 (Claude / GPT 선택)
├── analysis/          # 기술적 지표 계산
├── data/              # 데이터 조회
├── pages/             # Streamlit 페이지
├── install.bat        # 설치
├── run.bat            # 실행 메뉴 (대시보드 / Advisor)
├── advisor.bat        # Advisor CLI 래퍼
└── requirements.txt   # 의존성
```

### git 제외 (개인 데이터)
- `advisor/state.json` — 포트폴리오
- `advisor/journal.json` — 매매 일지
- `.env` — API 키

---

## 라이선스

MIT License — 자유롭게 사용 가능. 단, **투자 판단과 손익은 본인 책임입니다.**
