"""Local Hana exchange calculator. Python 3.9+, no third-party dependencies."""
import argparse
import io
import json
import os
import re
import shutil
import sqlite3
import subprocess
import threading
import time
import uuid
import zipfile
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent
DB = ROOT / 'data' / 'exchange.sqlite3'
KST = timezone(timedelta(hours=9))
SOURCE = 'https://www.kebhana.com/cms/rate/wpfxd651_01i.do'
ENDPOINT = 'https://www.kebhana.com/cms/rate/wpfxd651_01i_01.do'
CURRENCIES = {'USD': ('미국 달러', 1, 90), 'JPY': ('일본 엔', 100, 90), 'CNY': ('중국 위안', 1, 50)}
CACHE = {}
LOCK = threading.Lock()


def database():
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    con.execute('CREATE TABLE IF NOT EXISTS history (id TEXT PRIMARY KEY, created TEXT, payload TEXT)')
    con.execute('CREATE TABLE IF NOT EXISTS settings (code TEXT PRIMARY KEY, discount TEXT)')
    return con


def number(value, low=Decimal('0'), high=Decimal('1000000000000')):
    try:
        n = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError('숫자를 정확하게 입력해 주세요.')
    if not n.is_finite() or not low <= n <= high:
        raise ValueError(f'입력값은 {low} ~ {high} 범위여야 합니다.')
    return n


def rounded(n, places='0.01'):
    return str(n.quantize(Decimal(places), rounding=ROUND_HALF_UP))


class RateParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows, self.row, self.cell, self.text = [], [], None, []

    def handle_starttag(self, tag, attrs):
        if tag == 'tr':
            self.row = []
        if tag == 'td':
            self.cell = []

    def handle_data(self, data):
        self.text.append(data)
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag == 'td' and self.cell is not None:
            self.row.append(' '.join(''.join(self.cell).split()))
            self.cell = None
        if tag == 'tr' and self.row:
            self.rows.append(self.row)


def parse_rates(html, requested):
    parser = RateParser()
    parser.feed(html)
    text = ' '.join(' '.join(parser.text).split())
    stamp = re.search(r'고시일시\s*:\s*(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일\s*(\d{1,2})시\s*(\d{1,2})분\s*(\d{1,2})초\s*\((\d+)회차\)', text)
    if not stamp:
        raise ValueError('하나은행 고시 정보를 확인하지 못했습니다. 조회 날짜를 확인해 주세요.')
    y, m, d, hh, mm, ss, seq = map(int, stamp.groups())
    actual = datetime(y, m, d, hh, mm, ss, tzinfo=KST)
    base_match = re.search(r'기준일\s*:\s*(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일', text)
    if not base_match:
        raise ValueError('은행 기준일을 확인하지 못했습니다.')
    base_date = date(*map(int, base_match.groups()))
    if base_date > date.fromisoformat(requested):
        raise ValueError('요청 날짜와 은행 고시 날짜가 일치하지 않습니다.')
    rates = []
    for row in parser.rows:
        for code, (name, unit, default) in CURRENCIES.items():
            if not re.search(r'\b' + code + r'\b', row[0]):
                continue
            if len(row) != 11 or (code == 'JPY' and '(100)' not in row[0]):
                raise ValueError('하나은행 환율 표 구조가 변경되었습니다.')
            cash, remittance, base = [number(row[i].replace(',', ''), Decimal('0.01')) for i in (1, 5, 8)]
            if cash < base or remittance < base:
                raise ValueError('은행 매입 환율 데이터가 올바르지 않습니다.')
            rates.append(dict(code=code, name=name, unit=unit, cash=str(cash), remittance=str(remittance), base=str(base), defaultDiscount=default))
    if len(rates) != 3:
        raise ValueError('해당 날짜의 USD·JPY·CNY 환율을 모두 조회할 수 없습니다.')
    return dict(requestedDate=requested, baseDate=base_date.isoformat(), publishedAt=actual.isoformat(), sequence=seq, rates=rates, source=SOURCE, fetchedAt=datetime.now(KST).isoformat())


def get_rates(day):
    try:
        selected = date.fromisoformat(day)
    except ValueError:
        raise ValueError('조회 날짜 형식은 YYYY-MM-DD입니다.')
    if not date(1986, 1, 27) <= selected <= datetime.now(KST).date():
        raise ValueError('1986-01-27부터 오늘까지 조회할 수 있습니다.')
    with LOCK:
        if day in CACHE and time.monotonic() - CACHE[day][0] < 60:
            return CACHE[day][1]
        form = urlencode(dict(ajax='true', curCd='', tmpInqStrDt=day, inqStrDt=day.replace('-', ''), pbldDvCd='3' if selected == datetime.now(KST).date() else '0', pbldSqn='', inqKindCd='1', requestTarget='searchContentDiv'))
        # curl uses the OS certificate store on Windows; certificate verification stays enabled.
        try:
            curl = shutil.which('curl.exe' if os.name == 'nt' else 'curl')
            if not curl:
                raise OSError('curl not found')
            result = subprocess.run([curl, '--silent', '--show-error', '--fail', '--max-time', '20', '--max-filesize', '1000000', '--referer', SOURCE, '--data', form, ENDPOINT], capture_output=True, timeout=25, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError('환율 서버 연결에 실패했습니다. curl 설치와 인터넷 연결을 확인해 주세요.') from exc
        if result.returncode:
            raise RuntimeError('하나은행 환율 조회에 실패했습니다. 잠시 후 다시 조회해 주세요.')
        snapshot = parse_rates(result.stdout.decode('utf-8'), day)
        CACHE.clear() if len(CACHE) > 100 else None
        CACHE[day] = (time.monotonic(), snapshot)
        return snapshot


def calculate(snapshot, body):
    code, mode = body.get('currency'), body.get('mode')
    if code not in CURRENCIES or mode not in ('cash', 'remittance'):
        raise ValueError('통화 또는 거래 유형이 올바르지 않습니다.')
    amount = number(body.get('amount'), Decimal('0.01'), Decimal('1000000000'))
    discount = number(body.get('discount'), high=Decimal('100'))
    rate = next(r for r in snapshot['rates'] if r['code'] == code)
    base, before = Decimal(rate['base']), Decimal(rate[mode])
    spread = before - base
    after_spread = (spread * (1 - discount / 100)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    final = base + after_spread
    total = (final * amount / rate['unit']).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    original = (before * amount / rate['unit']).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    return dict(currency=code, mode=mode, amount=str(amount), discount=str(discount), unit=rate['unit'], base=str(base), before=str(before), spread=str(spread), afterSpread=str(after_spread), finalRate=str(final), total=str(total), originalTotal=str(original), savings=str(original-total), requestedDate=snapshot['requestedDate'], baseDate=snapshot.get('baseDate', snapshot['requestedDate']), publishedAt=snapshot['publishedAt'], sequence=snapshot['sequence'], source=snapshot['source'])


def history():
    with database() as con:
        return [dict(id=i, created=c, **json.loads(p)) for i, c, p in con.execute('SELECT id,created,payload FROM history ORDER BY created DESC')]


def workbook(records):
    columns = [('created','저장 시각'),('requestedDate','조회일'),('publishedAt','고시일시'),('sequence','고시회차'),('currency','통화'),('mode','거래유형'),('unit','기준 단위'),('amount','외화 금액'),('discount','우대율(%)'),('base','매매기준율'),('before','우대 전 환율'),('spread','스프레드'),('afterSpread','우대 후 스프레드'),('finalRate','최종 구매환율'),('originalTotal','우대 전 원화'),('total','필요 원화'),('savings','절약 원화'),('source','출처')]
    columns.append(('baseDate', '은행 기준일'))
    numeric = {k for k, _ in columns[6:17]}
    rows = [[label for _, label in columns]] + [[r.get(k, '') for k, _ in columns] for r in records]
    xmlrows = []
    for index, row in enumerate(rows, 1):
        cells = []
        for col, value in enumerate(row):
            ref = f'{chr(65+col)}{index}'
            if index > 1 and columns[col][0] in numeric:
                cells.append(f'<c r="{ref}"><v>{escape(str(value))}</v></c>')
            else:
                cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{escape(str(value))}</t></is></c>')
        xmlrows.append(f'<row r="{index}">{"".join(cells)}</row>')
    ns = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>')
        z.writestr('_rels/.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr('xl/workbook.xml', f'<workbook xmlns="{ns}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="환전 계산 기록" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr('xl/worksheets/sheet1.xml', f'<worksheet xmlns="{ns}"><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" state="frozen"/></sheetView></sheetViews><cols><col min="1" max="19" width="22" customWidth="1"/></cols><sheetData>{"".join(xmlrows)}</sheetData><autoFilter ref="A1:S{len(rows)}"/></worksheet>')
    return out.getvalue()


class Handler(BaseHTTPRequestHandler):
    def send(self, data, status=200, mime='application/json; charset=utf-8'):
        payload = json.dumps(data, ensure_ascii=False).encode() if not isinstance(data, bytes) else data
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        if mime.startswith('application/vnd.'):
            self.send_header('Content-Disposition', 'attachment; filename="exchange-history.xlsx"')
        self.end_headers()
        self.wfile.write(payload)

    def dispatch(self):
        url = urlsplit(self.path)
        if self.headers.get('Host') not in (f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'):
            return self.send({'error': '허용되지 않은 호스트입니다.'}, 403)
        if self.command == 'POST':
            origin = self.headers.get('Origin')
            if origin and origin not in (f'http://localhost:{self.server.server_port}', f'http://127.0.0.1:{self.server.server_port}'):
                return self.send({'error':'허용되지 않은 요청입니다.'}, 403)
            if not self.headers.get('Content-Type', '').startswith('application/json'):
                raise ValueError('JSON 요청이 필요합니다.')
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 10000:
                raise ValueError('요청 크기가 올바르지 않습니다.')
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError('JSON 객체가 필요합니다.')
            if url.path == '/api/shutdown':
                token = getattr(self.server, 'instance_token', None)
                if not token or body.get('token') != token:
                    return self.send({'error':'종료 요청을 확인할 수 없습니다.'}, 403)
                self.send({'stopped': True})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return
            if url.path == '/api/settings':
                values = [(c, str(number(body[c], high=Decimal('100')))) for c in CURRENCIES]
                with database() as con:
                    con.executemany('INSERT OR REPLACE INTO settings VALUES (?,?)', values)
                return self.send({'saved': True})
            if url.path in ('/api/calculate', '/api/history'):
                result = calculate(get_rates(body.get('date', '')), body)
                if url.path == '/api/history':
                    with database() as con:
                        con.execute('INSERT INTO history VALUES (?,?,?)', (str(uuid.uuid4()), datetime.now(KST).isoformat(), json.dumps(result)))
                return self.send(result)
        elif self.command == 'GET':
            if url.path == '/api/health':
                return self.send({'app':'ExchangeStudio', 'token':getattr(self.server, 'instance_token', None)})
            if url.path == '/api/rates':
                return self.send(get_rates(parse_qs(url.query).get('date', [datetime.now(KST).date().isoformat()])[0]))
            if url.path == '/api/settings':
                with database() as con:
                    saved = dict(con.execute('SELECT code,discount FROM settings'))
                return self.send({c: saved.get(c, v[2]) for c, v in CURRENCIES.items()})
            if url.path == '/api/history':
                return self.send(history())
            if url.path == '/api/export':
                return self.send(workbook(history()), mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            files = {'/': ('index.html','text/html; charset=utf-8'), '/app.js': ('app.js','text/javascript; charset=utf-8'), '/style.css': ('style.css','text/css; charset=utf-8')}
            if url.path in files:
                name, mime = files[url.path]
                return self.send((ROOT / 'static' / name).read_bytes(), mime=mime)
        self.send({'error':'찾을 수 없습니다.'}, 404)

    def handle_request(self):
        try:
            self.dispatch()
        except ValueError as exc:
            self.send({'error':str(exc)}, 400)
        except (KeyError, TypeError, InvalidOperation):
            self.send({'error':'입력값 또는 환율 데이터를 확인해 주세요. 날짜·금액·우대율이 유효해야 합니다.'}, 400)
        except RuntimeError as exc:
            self.send({'error':str(exc)}, 502)
        except Exception:
            self.send({'error':'서버 처리 중 오류가 발생했습니다.'}, 500)

    do_GET = handle_request
    do_POST = handle_request


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8080)
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    print(f'Exchange Studio: http://localhost:{args.port}', flush=True)
    server.serve_forever()
