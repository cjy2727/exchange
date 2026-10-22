Exchange Studio — Windows 10/11 x64

1. ZIP 파일의 압축을 모두 풀어 주세요.
2. ExchangeStudio.exe를 실행하세요. _internal 폴더도 함께 있어야 합니다.
3. 기본 브라우저에서 환율 계산기가 자동으로 열립니다.
4. 사용 후 화면 위쪽의 '프로그램 종료'를 누르세요.
   브라우저 탭만 닫으면 프로그램은 계속 실행됩니다.
   다시 EXE를 실행하면 실행 중인 화면이 열립니다.

Python 설치나 관리자 권한은 필요하지 않습니다.
환율 조회에는 인터넷과 Windows 기본 curl.exe가 필요합니다.
8080 포트 사용 중에는 사용 가능한 다른 포트를 자동으로 선택합니다.

기록과 설정: %LOCALAPPDATA%\ExchangeStudio\exchange.sqlite3
진단 로그: %LOCALAPPDATA%\ExchangeStudio\app.log
백업: 프로그램 종료 후 exchange.sqlite3를 복사하세요.
업데이트: 프로그램 종료 후 새 ZIP을 별도 폴더에 풀어 실행하세요.
기록은 프로그램 폴더 외부에 보관되므로 그대로 유지됩니다.
제거: 프로그램 종료 후 압축 해제한 폴더를 삭제하세요.
저장 기록까지 지우려면 위 데이터 폴더도 별도로 삭제하세요.

기존 소스 버전 기록 가져오기:
두 프로그램을 모두 종료하고 기존 data\exchange.sqlite3를 위 데이터 폴더로
복사하세요. 기존 배포판 기록이 있다면 먼저 백업하세요. 병합은 지원하지 않습니다.

이 배포판은 코드 서명되지 않았습니다. Windows 보안 확인이 표시될 수 있습니다.
다운로드 출처와 함께 제공된 SHA256SUMS.txt를 확인하세요.
출처: https://github.com/cjy2727/exchange/releases

하나은행 공식 프로그램이 아닌 개인용 계산 도구입니다.
실제 환전 및 송금은 실행하지 않습니다.
