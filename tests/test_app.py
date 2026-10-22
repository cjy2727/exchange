import io
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree

import app


def sample():
    return dict(requestedDate='2026-10-22', publishedAt='2026-10-22T12:00:00+09:00', sequence=1, source=app.SOURCE, rates=[
        dict(code='USD', base='1326.8', cash='1350.1', remittance='1339.8', unit=1),
        dict(code='JPY', base='838.66', cash='853.33', remittance='847.00', unit=100),
        dict(code='CNY', base='198.68', cash='208.61', remittance='200.66', unit=1)])


class CalculationTests(unittest.TestCase):
    def request(self, code='USD', discount='90', amount='1000', mode='cash'):
        return dict(currency=code, discount=discount, amount=amount, mode=mode, date='2026-10-22')

    def test_excel_examples(self):
        for code, discount, expected in [('USD','90','1329.13'), ('JPY','90','840.13'), ('CNY','50','203.65')]:
            self.assertEqual(app.calculate(sample(), self.request(code, discount))['finalRate'], expected)

    def test_dollar_cost_and_savings(self):
        r = app.calculate(sample(), self.request())
        self.assertEqual((r['total'], r['savings']), ('1329130','20970'))

    def test_yen_unit(self):
        r = app.calculate(sample(), self.request('JPY', amount='100000'))
        self.assertEqual(r['total'], '840130')

    def test_remittance_and_extremes(self):
        self.assertEqual(app.calculate(sample(), self.request(mode='remittance'))['finalRate'], '1328.10')
        self.assertEqual(app.calculate(sample(), self.request(discount='100'))['finalRate'], '1326.80')
        self.assertEqual(app.calculate(sample(), self.request(discount='0'))['finalRate'], '1350.10')

    def test_invalid_numbers(self):
        for value in ['NaN', 'Infinity', '-1', '101', 'hello']:
            with self.assertRaises(ValueError): app.calculate(sample(), self.request(discount=value))
        with self.assertRaises(ValueError): app.calculate(sample(), self.request(amount='0'))

    def test_real_bank_fixture(self):
        html = (Path(__file__).parent / 'hana-fixture.html').read_text(encoding='utf-8')
        result = app.parse_rates(html, '2026-10-22')
        self.assertEqual(result['sequence'], 400)
        self.assertEqual(result['rates'][0]['base'], '1323.20')
        self.assertEqual(result['rates'][1]['unit'], 100)
        self.assertEqual(result['rates'][2]['remittance'], '200.27')
        with self.assertRaises(ValueError): app.parse_rates('<html>점검 중</html>', '2026-10-22')
        with self.assertRaises(ValueError): app.parse_rates(html, '2026-10-21')

    def test_historical_base_date_differs_from_publication(self):
        html = (Path(__file__).parent / 'hana-history-fixture.html').read_text(encoding='utf-8')
        result = app.parse_rates(html, '2026-10-16')
        self.assertEqual(result['baseDate'], '2026-10-16')
        self.assertTrue(result['publishedAt'].startswith('2026-10-19'))
        self.assertEqual(app.parse_rates(html, '2026-10-18')['baseDate'], '2026-10-16')

    def test_xlsx(self):
        data = app.workbook([app.calculate(sample(), self.request())])
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            self.assertIsNone(z.testzip())
            for name in z.namelist(): ElementTree.fromstring(z.read(name))
            self.assertIn('1329130', z.read('xl/worksheets/sheet1.xml').decode())


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = patch.object(app, 'DB', Path(self.temp.name)/'test.sqlite3'); self.db.start()
        self.rates = patch.object(app, 'get_rates', return_value=sample()); self.rates.start()
        self.server = app.ThreadingHTTPServer(('127.0.0.1', 0), app.Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True); self.thread.start()
        self.url = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join()
        self.rates.stop(); self.db.stop(); self.temp.cleanup()

    def call(self, path, body=None, origin=None):
        headers = {'Content-Type':'application/json'}
        if origin: headers['Origin'] = origin
        req = urllib.request.Request(self.url+path, data=json.dumps(body).encode() if body is not None else None, headers=headers)
        return urllib.request.urlopen(req)

    def test_round_trip(self):
        body = dict(currency='USD', discount=90, amount=1000, mode='cash', date='2026-10-22')
        with self.call('/api/history', body) as r: self.assertEqual(json.load(r)['total'], '1329130')
        with self.call('/api/history') as r: self.assertEqual(len(json.load(r)), 1)
        with self.call('/api/settings', dict(USD=80, JPY=70, CNY=40)) as r: self.assertEqual(r.status, 200)
        with self.call('/api/settings') as r: self.assertEqual(json.load(r)['JPY'], '70')
        with self.call('/api/export') as r: self.assertTrue(r.read().startswith(b'PK'))
        with self.call('/') as r: self.assertIn(b'Exchange Studio', r.read())

    def test_reject_cross_origin_and_bad_inputs(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx: self.call('/api/settings', {}, 'https://example.com')
        self.assertEqual(ctx.exception.code, 403)
        with self.assertRaises(urllib.error.HTTPError) as ctx: self.call('/api/calculate', {})
        self.assertEqual(ctx.exception.code, 400)


if __name__ == '__main__': unittest.main()
