# 안드로이드 환율 계산기

PC를 켜 두지 않아도 휴대폰에서 환율 조회·계산·기록 저장·엑셀 내보내기를 사용할 수 있습니다. Android 8.0 이상이 필요하며 최신 Android System WebView를 권장합니다. 환율 조회에는 인터넷이 필요합니다.

## 설치하기

1. 휴대폰으로 받은 **ExchangeStudio-Android.apk** 파일을 누르세요. GitHub에서 받을 때는 해당 파일이 첨부된 릴리스의 Assets에서 선택합니다. `Source code (zip)`과 Windows용 ZIP은 안드로이드 앱이 아닙니다.
2. 휴대폰이 설치 권한을 물으면, 다운로드에 사용한 브라우저 또는 파일 앱의 **이 출처 허용**을 켜세요. 제조사에 따라 메뉴 이름이 다를 수 있습니다.
3. 설치를 누른 다음 **환율 계산기** 앱을 여세요. 출처가 확실한 APK만 설치하세요.

Play 스토어에 등록된 앱은 아니며 APK를 직접 설치하는 방식입니다.

APK 바로 다운로드: https://github.com/cjy2727/exchange/releases/latest/download/ExchangeStudio-Android.apk

## 사용하기

- 날짜를 선택해 환율을 조회하고 통화·현찰/송금·외화 금액·우대율을 입력하세요.
- **계산 기록 저장**을 누르면 이 휴대폰에 기록이 저장됩니다.
- **엑셀 다운로드**를 누르면 휴대폰의 파일 저장 화면이 열립니다. 저장 위치와 파일 이름을 선택하세요.
- 상단의 **프로그램 종료** 또는 휴대폰의 뒤로 가기로 앱을 닫을 수 있습니다. 별도 PC 서버는 실행하지 않습니다.

**PC와 휴대폰의 기록은 자동으로 공유되지 않습니다.** 앱을 삭제하거나 Android 설정에서 앱 데이터를 지우면 기록과 설정도 삭제됩니다. 필요한 기록은 먼저 엑셀로 내보내세요. 엑셀을 다시 가져오는 기능은 없습니다.

업데이트는 같은 서명으로 만든 더 높은 버전의 APK를 기존 앱 위에 설치하세요. 앱을 먼저 삭제할 필요가 없습니다. 설치가 거부되면 앱을 지우기 전에 APK의 버전과 서명을 확인하세요.

## 구현과 검증 범위

화면은 기존 `static/` 파일을 사용하고, Android 네이티브 코드가 HTTPS 환율 조회·BigDecimal 계산·SQLite 저장·XLSX 생성을 처리합니다. Python·curl·외부 중계 서버가 필요하지 않습니다. 하나은행 홈페이지 내부 조회 주소를 사용하는 점은 PC 버전과 같으며 정식 Open API V1~V3 연동은 아닙니다.

WebView에는 앱에 포함한 화면만 로드합니다. 외부 페이지는 별도 브라우저로 열며, 앱 내부 페이지의 외부 스크립트·프레임·파일 접근은 차단합니다. 광범위한 저장소 접근 권한 없이 Android 파일 선택기로 내보냅니다.

## 개발자: 빌드

JDK 17, Android SDK 35, Gradle 8.7이 필요합니다. `android/`를 Android Studio에서 열 수도 있습니다.

```powershell
python scripts/build_android.py --java-home "JDK17 경로" --sdk "Android SDK 경로" --version-code 1 --version-name 0.1.0
```

결과는 `dist/ExchangeStudio-Android.apk`와 `dist/ANDROID-SHA256SUMS.txt`입니다. 이후 업데이트는 `--version-code`를 반드시 늘리세요. Windows 버전과 Android 버전 번호는 별도입니다.

최초 빌드 시 `.android-signing/exchange-release.jks`와 `.android-signing/password.txt`를 만듭니다. **이 두 파일은 비공개로 함께 백업하세요. GitHub에 커밋하거나 릴리스에 첨부하면 안 됩니다.** 같은 서명 키가 있어야 사용자 기록을 유지하면서 다음 버전으로 업데이트할 수 있습니다. 이 폴더와 로컬 빌드 도구는 `.gitignore`에서 제외합니다.

에뮬레이터 또는 테스트 기기를 연결한 후 다음으로 Android 테스트를 실행합니다.

```powershell
cd android
.\gradlew.bat connectedDebugAndroidTest
```

실제 휴대폰의 제조사별 설치·파일 선택 화면은 다를 수 있습니다.
