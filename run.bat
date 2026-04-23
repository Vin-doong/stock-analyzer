@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] .venv not found. Run install.bat first.
    pause
    exit /b 1
)

set "PY=.venv\Scripts\python.exe"

:menu
cls
echo.
echo  ============================================================
echo    Stock Analyzer  ^|  Claude Advisor CLI
echo  ============================================================
echo    [A] 포트폴리오 현황         (status)
echo    [B] 전종목 스캔 (스윙)      (scan swing)
echo    [C] 전종목 스캔 (단타)      (scan day)
echo    [D] 전종목 스캔 (장기)      (scan long)
echo    [E] 종목 체크              (check ticker)
echo    [F] 매수 검증              (can-buy ticker --qty N)
echo    [G] 매매 일지              (journal)
echo    [H] 누적 성과              (performance)
echo    [I] 시장 브리핑            (briefing)
echo    [J] 섹터 회전 분석         (sectors)
echo    [K] 리스크 계산기          (risk)
echo    [L] 미국 주식 현황         (us-status)
echo  ------------------------------------------------------------
echo    [D1] Streamlit 대시보드 (브라우저)
echo    [D2] Advisor 셸 (수동 입력)
echo  ------------------------------------------------------------
echo    [Q] 종료
echo  ============================================================
set "CHOICE="
set /p CHOICE=  선택:

if not defined CHOICE goto menu
if /i "%CHOICE%"=="A" goto status
if /i "%CHOICE%"=="B" goto scan_swing
if /i "%CHOICE%"=="C" goto scan_day
if /i "%CHOICE%"=="D" goto scan_long
if /i "%CHOICE%"=="E" goto check
if /i "%CHOICE%"=="F" goto canbuy
if /i "%CHOICE%"=="G" goto journal
if /i "%CHOICE%"=="H" goto performance
if /i "%CHOICE%"=="I" goto briefing
if /i "%CHOICE%"=="J" goto sectors
if /i "%CHOICE%"=="K" goto risk
if /i "%CHOICE%"=="L" goto us_status
if /i "%CHOICE%"=="D1" goto dashboard
if /i "%CHOICE%"=="D2" goto shell
if /i "%CHOICE%"=="Q" goto end

echo.
echo   잘못된 입력입니다.
timeout /t 1 >nul
goto menu

:status
cls
"%PY%" -m advisor status
goto after_cmd

:scan_swing
cls
set "TOPN="
set /p TOPN=  정밀 분석 개수 (기본 10, 엔터=기본):
if "%TOPN%"=="" set "TOPN=10"
"%PY%" -m advisor scan --style swing --top %TOPN%
goto after_cmd

:scan_day
cls
set "TOPN="
set /p TOPN=  정밀 분석 개수 (기본 10, 엔터=기본):
if "%TOPN%"=="" set "TOPN=10"
"%PY%" -m advisor scan --style day --top %TOPN%
goto after_cmd

:scan_long
cls
set "TOPN="
set /p TOPN=  정밀 분석 개수 (기본 10, 엔터=기본):
if "%TOPN%"=="" set "TOPN=10"
"%PY%" -m advisor scan --style long --top %TOPN%
goto after_cmd

:check
cls
set "TICKER="
set /p TICKER=  종목코드 (예: 005930):
if "%TICKER%"=="" goto menu
"%PY%" -m advisor check %TICKER%
goto after_cmd

:canbuy
cls
set "TICKER="
set "QTY="
set "STYLE="
set /p TICKER=  종목코드:
if "%TICKER%"=="" goto menu
set /p QTY=  수량:
if "%QTY%"=="" goto menu
set /p STYLE=  스타일 (swing/day/long, 엔터=swing):
if "%STYLE%"=="" set "STYLE=swing"
"%PY%" -m advisor can-buy %TICKER% --qty %QTY% --style %STYLE%
goto after_cmd

:journal
cls
set "N="
set /p N=  표시할 건수 (기본 10, 엔터=기본):
if "%N%"=="" set "N=10"
"%PY%" -m advisor journal --n %N%
goto after_cmd

:performance
cls
"%PY%" -m advisor performance
goto after_cmd

:briefing
cls
"%PY%" -m advisor briefing
goto after_cmd

:sectors
cls
"%PY%" -m advisor sectors
goto after_cmd

:risk
cls
set "STOP="
set "CASH="
set "BUY="
set /p STOP=  손절가:
set /p CASH=  투입 자본:
set /p BUY=  매수 희망가:
if "%STOP%"=="" goto menu
if "%CASH%"=="" goto menu
if "%BUY%"=="" goto menu
"%PY%" -m advisor risk --stop %STOP% --cash %CASH% --buy %BUY%
goto after_cmd

:us_status
cls
"%PY%" -m advisor us-status
goto after_cmd

:after_cmd
echo.
echo  ------------------------------------------------------------
echo   [엔터] 메뉴로 돌아가기   [Q] 종료
set "NEXT="
set /p NEXT=  :
if /i "%NEXT%"=="Q" goto end
goto menu

:dashboard
cls
echo  Streamlit 대시보드 시작 중... (브라우저가 자동으로 열립니다)
echo  종료하려면 이 창에서 Ctrl+C
echo.
call ".venv\Scripts\activate.bat"
streamlit run app.py
goto end

:shell
cls
call ".venv\Scripts\activate.bat"
echo.
echo  Advisor 셸이 활성화되었습니다.
echo  사용법: python -m advisor ^<command^>
echo    예: python -m advisor check 005930
echo        python -m advisor scan --top 20
echo  종료: exit
echo.
cmd /k
goto end

:end
endlocal
exit /b 0
