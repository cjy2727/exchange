"""Build a signed personal APK; keys stay in the ignored .android-signing folder."""
import argparse
import hashlib
import os
from pathlib import Path
import secrets
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--java-home', type=Path)
    parser.add_argument('--sdk', type=Path)
    parser.add_argument('--gradle', help='Gradle executable; defaults to project wrapper')
    parser.add_argument('--version-code', type=int, default=1)
    parser.add_argument('--version-name', default='0.1.0')
    args = parser.parse_args()
    env = dict(os.environ)
    env.setdefault('GRADLE_USER_HOME', str(ROOT / '.gradle-user-home'))
    if args.java_home: env['JAVA_HOME'] = str(args.java_home.resolve())
    if args.sdk: env['ANDROID_HOME'] = str(args.sdk.resolve())
    java_home = Path(env.get('JAVA_HOME', ''))
    suffix = '.exe' if os.name == 'nt' else ''
    keytool = java_home / 'bin' / ('keytool' + suffix)
    if not keytool.is_file(): raise SystemExit('Set --java-home or JAVA_HOME to JDK 17.')
    if args.version_code < 1: raise SystemExit('Version code must be positive.')
    signing = ROOT / '.android-signing'
    signing.mkdir(exist_ok=True)
    keystore = signing / 'exchange-release.jks'
    password_file = signing / 'password.txt'
    if keystore.exists() and not password_file.exists():
        raise SystemExit('Signing password is missing. Restore it from backup; do not replace the existing key.')
    if not password_file.exists(): password_file.write_text(secrets.token_urlsafe(36), encoding='utf-8')
    env['EXCHANGE_STORE_PASSWORD'] = password_file.read_text(encoding='utf-8').strip()
    env['EXCHANGE_KEYSTORE'] = str(keystore)
    if not keystore.exists():
        subprocess.run([str(keytool), '-genkeypair', '-keystore', str(keystore), '-storetype', 'JKS', '-alias', 'exchange',
                        '-keyalg', 'RSA', '-keysize', '3072', '-validity', '10000', '-dname', 'CN=Exchange Studio',
                        '-storepass:env', 'EXCHANGE_STORE_PASSWORD', '-keypass:env', 'EXCHANGE_STORE_PASSWORD', '-noprompt'], env=env, check=True)
    env['ANDROID_VERSION_CODE'] = str(args.version_code)
    env['ANDROID_VERSION_NAME'] = args.version_name
    gradle = args.gradle or str(ROOT / 'android' / ('gradlew.bat' if os.name == 'nt' else 'gradlew'))
    subprocess.run([gradle, '--no-daemon', 'assembleRelease', 'assembleDebug', 'assembleDebugAndroidTest'], cwd=ROOT / 'android', env=env, check=True)
    dist = ROOT / 'dist'; dist.mkdir(exist_ok=True)
    apk = dist / 'ExchangeStudio-Android.apk'
    shutil.copyfile(ROOT / 'android/app/build/outputs/apk/release/app-release.apk', apk)
    digest = hashlib.sha256(apk.read_bytes()).hexdigest()
    (dist / 'ANDROID-SHA256SUMS.txt').write_text(f'{digest}  {apk.name}\n', encoding='ascii')
    print(f'Signed APK: {apk}')
    print('Back up .android-signing privately. The same key is required for future updates.')


if __name__ == '__main__': main()
