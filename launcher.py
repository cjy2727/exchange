"""Desktop entry point: one instance per data folder, browser launch, clean shutdown."""
import argparse
import ctypes
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import secrets
import sys
import time
import urllib.request
import webbrowser

import app


def data_directory():
    if getattr(sys, 'frozen', False):
        return Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local')) / 'ExchangeStudio'
    return app.ROOT / 'data'


class InstanceLock:
    def __init__(self, path):
        self.path = path
        self.file = None

    def acquire(self):
        self.file = self.path.open('a+b')
        self.file.seek(0, 2)
        if self.file.tell() == 0:
            self.file.write(b'0'); self.file.flush()
        self.file.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except OSError:
            self.file.close(); self.file = None
            return False

    def close(self):
        if self.file:
            self.file.close(); self.file = None


def existing_url(state_path):
    try:
        state = json.loads(state_path.read_text(encoding='utf-8'))
        port = int(state['port'])
        if not 1 <= port <= 65535:
            return None
        url = f'http://127.0.0.1:{port}'
        # Local requests must not go through system HTTP proxies.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(url + '/api/health', timeout=1) as response:
            health = json.load(response)
        if health.get('app') == 'ExchangeStudio' and health.get('token') == state['token']:
            return url
    except (OSError, ValueError, KeyError):
        pass
    return None


def open_browser(url):
    if not webbrowser.open(url):
        show_error(f'브라우저에서 다음 주소를 열어 주세요.\n{url}')


def show_error(message):
    if os.name == 'nt':
        ctypes.windll.user32.MessageBoxW(None, message, 'Exchange Studio', 0x40)
    else:
        print(message, file=sys.stderr)


class DesktopHandler(app.Handler):
    def log_message(self, fmt, *args):
        logging.info(fmt, *args)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8080)
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--data-dir', type=Path, help='Override data folder (testing/portable use)')
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error('port must be 0..65535')
    folder = (args.data_dir or data_directory()).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    state_path = folder / 'instance.json'
    lock = InstanceLock(folder / 'instance.lock')
    if not lock.acquire():
        for _ in range(30):
            url = existing_url(state_path)
            if url:
                if not args.no_browser:
                    open_browser(url)
                return 0
            time.sleep(.1)
        raise RuntimeError('기존 프로그램이 시작 또는 종료 중입니다. 잠시 후 다시 실행해 주세요.')
    server = None
    try:
        logging.basicConfig(level=logging.INFO, handlers=[RotatingFileHandler(folder / 'app.log', maxBytes=1000000, backupCount=2, encoding='utf-8')])
        app.DB = folder / 'exchange.sqlite3'
        with app.database():
            pass
        try:
            server = app.ThreadingHTTPServer(('127.0.0.1', args.port), DesktopHandler)
        except OSError:
            server = app.ThreadingHTTPServer(('127.0.0.1', 0), DesktopHandler)
        server.instance_token = secrets.token_urlsafe(32)
        state = {'port':server.server_port, 'token':server.instance_token}
        temporary = folder / 'instance.json.tmp'
        temporary.write_text(json.dumps(state), encoding='utf-8')
        temporary.replace(state_path)
        url = f'http://127.0.0.1:{server.server_port}'
        logging.info('Started %s', url)
        if not args.no_browser:
            # Socket is already listening; browser requests wait until serve_forever starts.
            open_browser(url)
        server.serve_forever(poll_interval=.2)
        return 0
    finally:
        if server:
            server.server_close()
            state_path.unlink(missing_ok=True)
        lock.close()
        logging.shutdown()


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        logging.exception('Launcher failed')
        show_error(f'프로그램을 시작하지 못했습니다.\n{exc}')
        sys.exit(1)
