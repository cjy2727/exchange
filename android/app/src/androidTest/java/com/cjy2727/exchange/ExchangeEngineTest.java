package com.cjy2727.exchange;

import android.test.InstrumentationTestCase;
import org.json.JSONObject;
import org.json.JSONArray;
import java.io.InputStream;
import java.io.ByteArrayOutputStream;
import java.io.ByteArrayInputStream;
import java.nio.charset.StandardCharsets;
import java.util.zip.ZipInputStream;
import java.util.zip.ZipEntry;

public class ExchangeEngineTest extends InstrumentationTestCase {
    private ExchangeEngine engine;
    @Override protected void setUp() throws Exception {
        super.setUp();
        // Instrumentation uses an isolated test database via RenamingDelegatingContext.
        engine = new ExchangeEngine(new android.test.RenamingDelegatingContext(getInstrumentation().getTargetContext(), "test_") {
            @Override public android.content.Context getApplicationContext() { return this; }
        });
    }
    private JSONObject sample() throws Exception {
        return new JSONObject("{\"requestedDate\":\"2026-10-22\",\"baseDate\":\"2026-10-22\",\"publishedAt\":\"2026-10-22T12:00:00+09:00\",\"sequence\":1,\"rates\":[{\"code\":\"USD\",\"base\":\"1326.8\",\"cash\":\"1350.1\",\"remittance\":\"1339.8\",\"unit\":1},{\"code\":\"JPY\",\"base\":\"838.66\",\"cash\":\"853.33\",\"remittance\":\"847.00\",\"unit\":100},{\"code\":\"CNY\",\"base\":\"198.68\",\"cash\":\"208.61\",\"remittance\":\"200.66\",\"unit\":1}]}");
    }
    private JSONObject body(String code, String discount, String amount) throws Exception {
        return new JSONObject().put("currency", code).put("discount", discount).put("amount", amount).put("mode", "cash");
    }
    public void testExcelExamplesAndYenUnit() throws Exception {
        JSONObject usd = ExchangeEngine.calculate(sample(), body("USD", "90", "1000"));
        assertEquals("1329.13", usd.getString("finalRate")); assertEquals("1329130", usd.getString("total")); assertEquals("20970", usd.getString("savings"));
        JSONObject jpy = ExchangeEngine.calculate(sample(), body("JPY", "90", "100000"));
        assertEquals("840.13", jpy.getString("finalRate")); assertEquals("840130", jpy.getString("total"));
        assertEquals("203.65", ExchangeEngine.calculate(sample(), body("CNY", "50", "1000")).getString("finalRate"));
    }
    public void testRemittanceAndInvalidInput() throws Exception {
        assertEquals("1328.10", ExchangeEngine.calculate(sample(), body("USD", "90", "1000").put("mode", "remittance")).getString("finalRate"));
        for (String bad : new String[]{"NaN", "Infinity", "-1", "101"}) {
            try { ExchangeEngine.calculate(sample(), body("USD", bad, "1000")); fail("Accepted " + bad); }
            catch (IllegalArgumentException expected) { }
        }
    }
    public void testSaveAndExport() throws Exception {
        engine.settings(new JSONObject().put("USD", "80").put("JPY", "70").put("CNY", "40"));
        assertEquals("70", engine.settings(null).getString("JPY"));
        int before = engine.history().length();
        engine.save(ExchangeEngine.calculate(sample(), body("USD", "90", "1000")));
        assertEquals(before + 1, engine.history().length());
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        ExchangeEngine.workbook(engine.history(), output);
        boolean found = false;
        try (ZipInputStream zip = new ZipInputStream(new ByteArrayInputStream(output.toByteArray()))) {
            ZipEntry entry;
            while ((entry = zip.getNextEntry()) != null) {
                if (entry.getName().equals("xl/worksheets/sheet1.xml")) {
                    String xml = new String(ExchangeEngine.readLimited(zip, 1000000), StandardCharsets.UTF_8);
                    assertTrue(xml.contains("1329130")); found = true;
                }
            }
        }
        assertTrue(found);
    }
    public void testBankFixturesAndHolidayDate() throws Exception {
        String current, historical;
        try (InputStream input = getInstrumentation().getContext().getAssets().open("hana-fixture.html")) {
            current = new String(ExchangeEngine.readLimited(input, 1000000), StandardCharsets.UTF_8);
        }
        try (InputStream input = getInstrumentation().getContext().getAssets().open("hana-history-fixture.html")) {
            historical = new String(ExchangeEngine.readLimited(input, 1000000), StandardCharsets.UTF_8);
        }
        JSONObject latest = ExchangeEngine.parseRates(current, "2026-10-22");
        assertEquals(400, latest.getInt("sequence"));
        assertEquals("1323.20", latest.getJSONArray("rates").getJSONObject(0).getString("base"));
        JSONObject past = ExchangeEngine.parseRates(historical, "2026-10-18");
        assertEquals("2026-10-16", past.getString("baseDate"));
        assertTrue(past.getString("publishedAt").startsWith("2026-10-19"));
        try { ExchangeEngine.parseRates("<html>점검 중</html>", "2026-10-22"); fail("Accepted invalid page"); }
        catch (IllegalArgumentException expected) { }
    }

    public void testParseRatesWithFallbackCharset() throws Exception {
        String html;
        try (InputStream input = getInstrumentation().getContext().getAssets().open("hana-fixture.html")) {
            html = new String(ExchangeEngine.readLimited(input, 1000000), StandardCharsets.UTF_8);
        }
        byte[] cp949 = html.getBytes("MS949");
        JSONObject parsed = ExchangeEngine.parseRatesWithFallback(cp949, "2026-10-22", "text/html; charset=MS949");
        assertEquals(400, parsed.getInt("sequence"));
    }
}
