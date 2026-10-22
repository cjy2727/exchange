# Exchange Studio

하나은행 환율 조회와 엑셀 우대율 계산을 연결한 로컬 웹 프로젝트입니다.

## 처음 사용하시나요? 여기서 시작하세요

별도 설치 과정 없이 다운로드해서 실행할 수 있습니다. **Windows 10·11의 64비트(x64) PC**에서 사용할 수 있으며, 환율 조회에는 인터넷 연결이 필요합니다.

### ① 프로그램 다운로드

**[여기를 눌러 최신 버전 다운로드 페이지를 여세요](https://github.com/cjy2727/exchange/releases/latest).**

페이지 아래쪽의 **Assets**를 눌러 펼친 뒤, **`ExchangeStudio-Windows.zip`**을 클릭하세요.

| 보이는 파일 | 선택 방법 |
| --- | --- |
| **ExchangeStudio-Windows.zip** | **이 파일을 다운로드하세요.** |
| SHA256SUMS.txt | 파일 확인용입니다. 실행할 때는 필요하지 않습니다. |
| Source code (zip) / Source code (tar.gz) | 개발용 소스입니다. 실행파일이 들어 있지 않습니다. |

저장소 위쪽의 **Code → Download ZIP**도 소스코드를 받는 메뉴입니다. 위 다운로드 링크를 이용하세요. 실행파일 ZIP이 없거나 페이지가 열리지 않으면 [전체 배포 목록](https://github.com/cjy2727/exchange/releases)을 확인하세요. 실행파일이 첨부된 버전이 없다면 아직 배포 준비 중입니다.

### ② 압축 풀기

다운로드 폴더에서 `ExchangeStudio-Windows.zip`을 찾아 마우스 오른쪽 버튼으로 클릭하고 **모두 압축 풀기 → 압축 풀기**를 누르세요.

압축파일 안에서 바로 실행하지 말고, 먼저 압축을 풀어 주세요.

### ③ 프로그램 실행

압축을 푼 폴더 안의 **ExchangeStudio** 폴더를 열고 **`ExchangeStudio.exe`**를 더블클릭하세요. 확장자가 숨겨져 있으면 **ExchangeStudio**로 보일 수 있습니다.

인터넷 브라우저가 열리면서 환율 계산기 화면이 나타납니다.

```text
ExchangeStudio
├─ ExchangeStudio.exe   ← 이 파일을 더블클릭하세요.
├─ _internal           ← 실행에 필요한 폴더입니다. 함께 보관하세요.
└─ README.txt          ← 사용 방법 안내입니다.
```

EXE만 다른 곳으로 옮기거나 `_internal` 폴더를 삭제하면 실행되지 않을 수 있습니다. 옮길 때는 **ExchangeStudio 폴더 전체**를 옮기세요.

### ④ 환율 계산하기

1. 조회할 날짜를 선택하고 **환율 조회**를 누릅니다.
2. 통화·거래 유형·외화 금액·우대율을 입력합니다.
3. **원화 비용 계산하기**를 누릅니다.
4. 결과를 보관하려면 **계산 기록 저장**을 누릅니다.
5. 저장한 기록을 엑셀로 받으려면 **엑셀 다운로드**를 누릅니다.

### ⑤ 프로그램 종료

화면 위쪽의 **프로그램 종료**를 누르고 확인을 선택하세요. 종료 안내가 나오면 브라우저 탭을 닫으세요.

브라우저 창만 닫으면 프로그램은 계속 실행됩니다. 화면을 다시 열려면 **ExchangeStudio.exe**를 다시 실행하세요.

### 새 버전으로 바꾸기

프로그램을 종료한 뒤 새 ZIP을 다운로드하고 **새 폴더에 압축을 풀어 실행**하세요. 같은 Windows 사용자 계정에서는 저장한 기록과 설정이 유지됩니다.

### 실행이 잘 안 될 때

- **EXE가 없고 `app.py` 같은 파일만 보여요:** 소스코드를 받은 상태입니다. 위 다운로드 페이지에서 `ExchangeStudio-Windows.zip`을 받으세요.
- **화면을 닫았는데 다시 열고 싶어요:** `ExchangeStudio.exe`를 다시 더블클릭하세요.
- **환율 조회가 안 돼요:** 인터넷 연결을 확인하고 잠시 후 다시 시도하세요. 계속 실패하면 화면의 오류 문구를 담당자에게 알려 주세요.
- **Windows 보안 확인이 나와요:** 이 배포판은 코드 서명되지 않았습니다. 이 저장소의 Releases에서 받은 파일인지 확인하고, 판단이 어려우면 경고 화면을 담당자에게 보여 주세요.

기록 백업·삭제 방법은 [자세한 사용 안내](docs/WINDOWS-README.txt)를 참고하세요.

## 개발자 안내

지원 환경: Windows 10/11 x64, 인터넷 연결, Windows 기본 `curl.exe`. 관리자 권한이나 Python 설치는 필요하지 않습니다. 배포판은 코드 서명되지 않았으므로 Windows 보안 확인이 나타날 수 있습니다.

기록·설정은 `%LOCALAPPDATA%\ExchangeStudio\exchange.sqlite3`, 로그는 같은 폴더의 `app.log`에 저장합니다. 업데이트할 때는 프로그램을 종료하고 새 ZIP을 풀어 실행하면 기존 기록을 계속 사용합니다. 소스 버전의 `data` 폴더는 자동 이동하지 않습니다. 기록을 가져오는 방법은 [Windows 안내](docs/WINDOWS-README.txt)를 참고하세요.

프로그램을 중복 실행하면 기존 화면을 다시 엽니다. 8080 포트를 다른 프로그램이 사용하면 빈 포트를 자동으로 선택합니다. 브라우저 탭을 닫는 것만으로 프로그램이 종료되지는 않습니다.

## 실행

Python 3.9 이상과 curl이 필요합니다. Windows 10/11 기본 curl을 사용하며 별도 Python 패키지는 필요하지 않습니다.

```powershell
cd D:\exchange
python launcher.py
```

기본 브라우저가 자동으로 열립니다. `start.bat`으로도 실행할 수 있습니다. 포트 변경: `python launcher.py --port 8081`. 자동 열기 없이 실행: `python launcher.py --no-browser`. 종료: 화면의 프로그램 종료 또는 Ctrl+C. `python app.py`는 브라우저 자동 열기·중복 실행 관리 없는 기존 서버 실행 방식입니다.

## 기능

- USD, JPY, CNY의 최신 및 과거 날짜 환율 조회
- 현찰 살 때 / 송금 보낼 때 선택
- 통화별 기본 우대율 저장 (USD 90%, JPY 90%, CNY 50%)
- 외화 금액별 최종 구매환율, 필요 원화, 절약 금액 계산
- 실제 고시일시·회차와 요청 날짜 구분
- 은행 기준일 별도 보관 (고시일시는 기준일 이후일 수도 있음)
- 계산 기록 SQLite 저장 및 실제 .xlsx 다운로드
- 조회 실패 안내, 입력 검증, 60초 환율 캐시
- 반응형 한국어 UI

## 계산 정책

스프레드 = 선택한 거래 환율 − 매매기준율.
우대 후 스프레드 = 스프레드 × (1 − 우대율/100).
우대 후 스프레드를 소수 둘째 자리로 반올림(ROUND_HALF_UP)한 다음 매매기준율을 더합니다. 제공된 엑셀 화면의 USD 1329.13 / JPY 840.13 / CNY 203.65 결과를 재현하는 정책입니다. 원본 엑셀 수식은 제공되지 않았으므로 숨은 소수점 유지 여부는 확인되지 않았습니다.

필요 원화 = 최종 구매환율 × 외화 금액 ÷ 기준 단위. JPY는 100, 나머지는 1입니다. 원화는 정수로 반올림하며 우대 전 원화와 차이를 절약액으로 표시합니다. 서버는 Decimal을 사용합니다.

우대율은 사용자 가정값이며 실제 은행 제공 조건을 의미하지 않습니다. 송금 수수료 등 별도 비용은 제외합니다. 저장 시 서버가 환율을 다시 확인하므로 고시가 갱신되었다면 저장 결과가 앞선 계산과 달라질 수 있으며 화면에 저장된 결과를 표시합니다.

## 데이터 연동

출처: https://www.kebhana.com/cms/rate/wpfxd651_01i.do

공개 조회 페이지가 사용하는 `wpfxd651_01i_01.do`에 날짜와 현재(`pbldDvCd=3`)/과거 최종 고시(`pbldDvCd=0`) 조건으로 POST합니다. 공식 조회 스크립트의 날짜별 고시 구분을 따릅니다. 계약형 공식 API를 사용하는 구조는 아닙니다. 은행 페이지 변경·접속 제한 시 연동 수정이 필요할 수 있습니다. 실패를 샘플 환율로 대체하지 않습니다. 휴일에는 이전 영업일 고시가 반환될 수 있고 일부 과거 날짜에는 지원 통화 데이터가 없을 수 있습니다.

소스 실행 시 `data/exchange.sqlite3`, Windows 실행파일 사용 시 `%LOCALAPPDATA%\ExchangeStudio\exchange.sqlite3`에 기록과 기본 우대율이 저장됩니다. 백업하려면 프로그램 종료 후 해당 파일을 복사하세요. 로컬 단일 사용자용으로 127.0.0.1에만 바인딩합니다. 여러 사용자가 접속하는 운영 배포에는 인증·권한·배포 구성을 추가해야 합니다.

## 검증

```powershell
python -m unittest discover -s tests -v
node --check static/app.js
```

`app.py`: API, 하나은행 어댑터, 계산, 저장, XLSX 생성.
`static/`: 화면. `tests/`: 엑셀 예제·엔 단위·입력 검증·은행 파서·저장·내보내기 검증.

## Windows 배포 파일 만들기

Windows x64 Python 환경에서 실행합니다. 빌드 도구는 사용자 실행 시 필요하지 않습니다.

```powershell
python -m venv .venv-build
.\.venv-build\Scripts\python.exe -m pip install -r requirements-build.txt
powershell -ExecutionPolicy Bypass -File scripts\build.ps1 -Python .\.venv-build\Scripts\python.exe
.\.venv-build\Scripts\python.exe scripts\smoke_exe.py
```

결과: `dist/ExchangeStudio-Windows.zip`, `dist/SHA256SUMS.txt`. ZIP에는 실행에 필요한 파일만 포함되며 개발자의 `data` 폴더는 포함하지 않습니다. 실제 EXE 검증은 별도의 임시 사용자 데이터 폴더에서 실행합니다.

## GitHub Releases 자동 배포

`.github/workflows/release.yml`은 `v*` 태그가 GitHub에 올라오면 테스트 → Windows 빌드 → 실제 EXE 검증 → Releases 업로드를 진행합니다. 일반 브랜치 push에는 릴리스를 만들지 않습니다. Actions에서 수동 실행하면 다운로드 가능한 빌드 아티팩트만 만들고 릴리스는 게시하지 않습니다.

변경 내용을 커밋하고 원격에 반영한 뒤, 게시할 버전을 선택해 태그를 올립니다. 예시:

```powershell
git tag v0.1.0
git push origin v0.1.0
```

이미 사용한 버전 태그를 재사용하지 마세요. GitHub Actions 실행 및 실제 릴리스 게시 여부는 저장소 Actions/Releases에서 확인합니다.

새 릴리스 설명에는 `docs/RELEASE-NOTES.md`의 사용자 안내와 자동 생성한 변경 내역이 함께 들어갑니다. 이미 게시한 릴리스의 설명은 자동으로 바뀌지 않으므로 GitHub에서 별도로 편집해야 합니다. `docs/WINDOWS-README.txt`는 빌드 시 ZIP 안의 `README.txt`로 복사됩니다.
