"""Exercise the actual packaged EXE without a browser or external bank requests."""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / 'dist' / 'ExchangeStudio' / 'ExchangeStudio.exe'
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def request(url, body=None):
    req = urllib.request.Request(url, data=None if body is None else json.dumps(body).encode(), headers={'Content-Type':'application/json'})
    with opener.open(req, timeout=5) as response:
        return response.read()


def wait_ready(folder, process):
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise AssertionError(f'EXE exited early: {process.returncode}')
        try:
            state = json.loads((folder / 'instance.json').read_text())
            url = f"http://127.0.0.1:{state['port']}"
            health = json.loads(request(url + '/api/health'))
            if health['token'] == state['token']:
                return url, state
        except (OSError, ValueError):
            pass
        time.sleep(.1)
    raise AssertionError('EXE did not start')


def main():
    processes = []
    with tempfile.TemporaryDirectory(prefix='exchange-smoke-') as temporary:
        folder = Path(temporary)
        occupied = socket.socket()
        occupied.bind(('127.0.0.1', 0)); occupied.listen()
        port = occupied.getsockname()[1]
        # Exercise frozen default LOCALAPPDATA behavior without touching real user records.
        env = dict(os.environ, LOCALAPPDATA=str(folder))
        data = folder / 'ExchangeStudio'
        command = [str(EXE), '--no-browser', '--port', str(port)]
        try:
            first = subprocess.Popen(command, env=env); processes.append(first)
            url, state = wait_ready(data, first)
            assert state['port'] != port, 'Port fallback failed'
            assert b'Exchange Studio' in request(url + '/')
            assert b'setupShutdown' in request(url + '/app.js')
            assert request(url + '/style.css')
            if '--live' in sys.argv:
                day = datetime.now(timezone(timedelta(hours=9))).date().isoformat()
                rates = json.loads(request(url + '/api/rates?date=' + day))
                assert {r['code'] for r in rates['rates']} == {'USD', 'JPY', 'CNY'}
                print('EXE live Hana rates PASS:', rates['baseDate'], rates['sequence'])
            request(url + '/api/settings', {'USD':81, 'JPY':72, 'CNY':43})
            assert request(url + '/api/export').startswith(b'PK')
            second = subprocess.Popen(command, env=env); processes.append(second)
            assert second.wait(timeout=10) == 0, 'Duplicate instance failed'
            assert first.poll() is None
            try:
                request(url + '/api/shutdown', {'token':'wrong'})
                raise AssertionError('Invalid shutdown token accepted')
            except urllib.error.HTTPError as error:
                assert error.code == 403
            request(url + '/api/shutdown', {'token':state['token']})
            assert first.wait(timeout=10) == 0
            assert not (data / 'instance.json').exists()
            third = subprocess.Popen(command, env=env); processes.append(third)
            url, state = wait_ready(data, third)
            assert json.loads(request(url + '/api/settings'))['USD'] == '81'
            request(url + '/api/shutdown', {'token':state['token']})
            assert third.wait(timeout=10) == 0
            assert (data / 'exchange.sqlite3').is_file()
            print('EXE PASS: assets, isolated user data, occupied port, duplicate launch, export, shutdown token, restart persistence.')
        finally:
            occupied.close()
            for process in processes:
                if process.poll() is None:
                    process.terminate(); process.wait(timeout=10)


if __name__ == '__main__':
    main()
