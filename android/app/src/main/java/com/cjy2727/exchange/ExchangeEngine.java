package com.cjy2727.exchange;

import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.Charset;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

public final class ExchangeEngine {
    public static final String SOURCE = "https://www.kebhana.com/cms/rate/wpfxd651_01i.do";
    private static final String ENDPOINT = "https://www.kebhana.com/cms/rate/wpfxd651_01i_01.do";
    private static final ZoneOffset KST = ZoneOffset.ofHours(9);
    private static final String[] CODES = {"USD", "JPY", "CNY"};
    private final Context context;
    private JSONObject cached;
    private long cachedAt;

    public ExchangeEngine(Context context) { this.context = context.getApplicationContext(); }

    static String clean(String html) {
        return html.replaceAll("(?s)<[^>]*>", " ").replace("&nbsp;", " ")
                .replace("&#160;", " ").replaceAll("\\s+", " ").trim();
    }

    static JSONObject parseRatesWithFallback(byte[] payload, String requested, String contentType) throws Exception {
        List<String> candidates = new ArrayList<>();
        if (contentType != null) {
            Matcher charset = Pattern.compile("(?i)charset=([A-Za-z0-9._-]+)").matcher(contentType);
            if (charset.find()) candidates.add(charset.group(1));
        }
        candidates.add("UTF-8");
        candidates.add("EUC-KR");
        candidates.add("CP949");

        IllegalArgumentException last = null;
        for (String name : candidates) {
            try {
                String html = new String(payload, Charset.forName(name));
                return parseRates(html, requested);
            } catch (IllegalArgumentException e) {
                last = e;
            } catch (Exception ignored) {
                // Unsupported charset or decoding failure; try next candidate.
            }
        }
        if (last != null) throw last;
        throw new IllegalArgumentException("은행 고시 정보를 확인하지 못했습니다.");
    }

    public static JSONObject parseRates(String html, String requested) throws Exception {
        String text = clean(html);
        Matcher stamp = Pattern.compile("고시일시\\s*:\\s*(\\d{4})년\\s*(\\d{1,2})월\\s*(\\d{1,2})일\\s*(\\d{1,2})시\\s*(\\d{1,2})분\\s*(\\d{1,2})초\\s*\\((\\d+)회차\\)").matcher(text);
        Matcher base = Pattern.compile("기준일\\s*:\\s*(\\d{4})년\\s*(\\d{1,2})월\\s*(\\d{1,2})일").matcher(text);
        if (!stamp.find() || !base.find()) throw new IllegalArgumentException("은행 고시 정보를 확인하지 못했습니다.");
        LocalDate baseDate = LocalDate.of(Integer.parseInt(base.group(1)), Integer.parseInt(base.group(2)), Integer.parseInt(base.group(3)));
        if (baseDate.isAfter(LocalDate.parse(requested))) throw new IllegalArgumentException("은행 기준일이 요청 날짜와 맞지 않습니다.");
        OffsetDateTime published = OffsetDateTime.of(Integer.parseInt(stamp.group(1)), Integer.parseInt(stamp.group(2)), Integer.parseInt(stamp.group(3)), Integer.parseInt(stamp.group(4)), Integer.parseInt(stamp.group(5)), Integer.parseInt(stamp.group(6)), 0, KST);
        JSONArray rates = new JSONArray();
        Matcher rows = Pattern.compile("(?is)<tr\\b[^>]*>(.*?)</tr>").matcher(html);
        while (rows.find()) {
            List<String> cells = new ArrayList<>();
            Matcher cell = Pattern.compile("(?is)<td\\b[^>]*>(.*?)</td>").matcher(rows.group(1));
            while (cell.find()) cells.add(clean(cell.group(1)));
            if (cells.isEmpty()) continue;
            for (String code : CODES) {
                if (!Pattern.compile("\\b" + code + "\\b").matcher(cells.get(0)).find()) continue;
                if (cells.size() != 11 || (code.equals("JPY") && !cells.get(0).contains("(100)")))
                    throw new IllegalArgumentException("은행 환율 표 구조가 변경되었습니다.");
                BigDecimal cash = numeric(cells.get(1).replace(",", ""), "0.01", "1000000000000");
                BigDecimal remittance = numeric(cells.get(5).replace(",", ""), "0.01", "1000000000000");
                BigDecimal mid = numeric(cells.get(8).replace(",", ""), "0.01", "1000000000000");
                if (cash.compareTo(mid) < 0 || remittance.compareTo(mid) < 0) throw new IllegalArgumentException("은행 환율 데이터가 올바르지 않습니다.");
                rates.put(new JSONObject().put("code", code).put("name", code.equals("USD") ? "미국 달러" : code.equals("JPY") ? "일본 엔" : "중국 위안")
                        .put("unit", code.equals("JPY") ? 100 : 1).put("base", mid.toPlainString()).put("cash", cash.toPlainString())
                        .put("remittance", remittance.toPlainString()).put("defaultDiscount", code.equals("CNY") ? 50 : 90));
            }
        }
        if (rates.length() != 3) throw new IllegalArgumentException("USD·JPY·CNY 환율을 모두 확인하지 못했습니다.");
        for (String code : CODES) {
            int count = 0;
            for (int i = 0; i < rates.length(); i++) if (rates.getJSONObject(i).getString("code").equals(code)) count++;
            if (count != 1) throw new IllegalArgumentException("통화 데이터가 중복되거나 누락되었습니다.");
        }
        return new JSONObject().put("requestedDate", requested).put("baseDate", baseDate.toString())
                .put("publishedAt", published.format(java.time.format.DateTimeFormatter.ISO_OFFSET_DATE_TIME))
                .put("sequence", Integer.parseInt(stamp.group(7))).put("rates", rates).put("source", SOURCE)
                .put("fetchedAt", OffsetDateTime.now(KST).toString());
    }

    public synchronized JSONObject rates(String day) throws Exception {
        LocalDate selected;
        try { selected = LocalDate.parse(day); } catch (Exception e) { throw new IllegalArgumentException("조회 날짜를 확인해 주세요."); }
        LocalDate today = LocalDate.now(KST);
        if (selected.isBefore(LocalDate.of(1986, 1, 27)) || selected.isAfter(today)) throw new IllegalArgumentException("오늘 또는 과거 날짜를 선택해 주세요.");
        long now = android.os.SystemClock.elapsedRealtime();
        if (cached != null && cached.getString("requestedDate").equals(day) && now - cachedAt < 60000) return cached;
        HttpURLConnection connection = (HttpURLConnection) new URL(ENDPOINT).openConnection();
        connection.setConnectTimeout(15000); connection.setReadTimeout(20000);
        connection.setInstanceFollowRedirects(false);
        connection.setRequestMethod("POST"); connection.setDoOutput(true);
        connection.setRequestProperty("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8");
        connection.setRequestProperty("Referer", SOURCE);
        connection.setRequestProperty("Accept", "text/html, */*;q=0.8");
        connection.setRequestProperty("Accept-Language", "ko-KR,ko;q=0.9,en-US;q=0.7,en;q=0.6");
        connection.setRequestProperty("Origin", "https://www.kebhana.com");
        connection.setRequestProperty("User-Agent", "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Mobile Safari/537.36");
        connection.setRequestProperty("X-Requested-With", "XMLHttpRequest");
        String form = "ajax=true&curCd=&tmpInqStrDt=" + day + "&inqStrDt=" + day.replace("-", "")
                + "&pbldDvCd=" + (selected.equals(today) ? "3" : "0") + "&pbldSqn=&inqKindCd=1&requestTarget=searchContentDiv";
        try {
            try (OutputStream output = connection.getOutputStream()) { output.write(form.getBytes(StandardCharsets.UTF_8)); }
            if (connection.getResponseCode() != 200) throw new java.io.IOException("은행 응답 오류");
            try (InputStream input = connection.getInputStream()) {
            byte[] payload = readLimited(input, 1000000);
            cached = parseRatesWithFallback(payload, day, connection.getContentType());
                cachedAt = android.os.SystemClock.elapsedRealtime();
                return cached;
            }
        } catch (java.io.IOException e) {
            throw new java.io.IOException("환율 조회에 실패했습니다. 인터넷 연결을 확인하고 다시 시도해 주세요.", e);
        } finally { connection.disconnect(); }
    }

    public static byte[] readLimited(InputStream input, int limit) throws java.io.IOException {
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        byte[] buffer = new byte[8192]; int count;
        while ((count = input.read(buffer)) != -1) {
            if (output.size() + count > limit) throw new java.io.IOException("응답 크기가 너무 큽니다.");
            output.write(buffer, 0, count);
        }
        return output.toByteArray();
    }

    static BigDecimal numeric(String value, String low, String high) {
        try {
            if (value.length() > 40 || !value.matches("[0-9]+(?:\\.[0-9]+)?")) throw new NumberFormatException();
            BigDecimal number = new BigDecimal(value);
            if (number.compareTo(new BigDecimal(low)) < 0 || number.compareTo(new BigDecimal(high)) > 0) throw new NumberFormatException();
            return number;
        } catch (NumberFormatException e) { throw new IllegalArgumentException("금액과 우대율의 입력 범위를 확인해 주세요."); }
    }

    public static JSONObject calculate(JSONObject snapshot, JSONObject body) throws Exception {
        String code = body.getString("currency"), mode = body.getString("mode");
        if (!mode.equals("cash") && !mode.equals("remittance")) throw new IllegalArgumentException("거래 유형을 확인해 주세요.");
        JSONObject rate = null;
        JSONArray rates = snapshot.getJSONArray("rates");
        for (int i = 0; i < rates.length(); i++) if (rates.getJSONObject(i).getString("code").equals(code)) rate = rates.getJSONObject(i);
        if (rate == null) throw new IllegalArgumentException("통화를 확인해 주세요.");
        BigDecimal amount = numeric(body.getString("amount"), "0.01", "1000000000");
        BigDecimal discount = numeric(body.getString("discount"), "0", "100");
        BigDecimal mid = new BigDecimal(rate.getString("base")), before = new BigDecimal(rate.getString(mode));
        BigDecimal spread = before.subtract(mid);
        BigDecimal afterSpread = spread.multiply(BigDecimal.ONE.subtract(discount.movePointLeft(2))).setScale(2, RoundingMode.HALF_UP);
        BigDecimal finalRate = mid.add(afterSpread), unit = new BigDecimal(rate.getInt("unit"));
        BigDecimal total = finalRate.multiply(amount).divide(unit).setScale(0, RoundingMode.HALF_UP);
        BigDecimal original = before.multiply(amount).divide(unit).setScale(0, RoundingMode.HALF_UP);
        return new JSONObject().put("currency", code).put("mode", mode).put("amount", amount.toPlainString()).put("discount", discount.toPlainString())
                .put("unit", rate.getInt("unit")).put("base", mid.toPlainString()).put("before", before.toPlainString())
                .put("spread", spread.toPlainString()).put("afterSpread", afterSpread.toPlainString()).put("finalRate", finalRate.toPlainString())
                .put("total", total.toPlainString()).put("originalTotal", original.toPlainString()).put("savings", original.subtract(total).toPlainString())
                .put("requestedDate", snapshot.getString("requestedDate")).put("baseDate", snapshot.getString("baseDate"))
                .put("publishedAt", snapshot.getString("publishedAt")).put("sequence", snapshot.getInt("sequence")).put("source", SOURCE);
    }

    private SQLiteDatabase database() {
        SQLiteDatabase db = context.openOrCreateDatabase("exchange.sqlite3", Context.MODE_PRIVATE, null);
        try {
            db.execSQL("CREATE TABLE IF NOT EXISTS history (id TEXT PRIMARY KEY, created TEXT, payload TEXT)");
            db.execSQL("CREATE TABLE IF NOT EXISTS settings (code TEXT PRIMARY KEY, discount TEXT)");
            return db;
        } catch (RuntimeException e) { db.close(); throw e; }
    }

    public JSONObject settings(JSONObject body) throws Exception {
        if (body != null) for (String code : CODES) numeric(body.getString(code), "0", "100");
        try (SQLiteDatabase db = database()) {
            if (body != null) {
                db.beginTransaction();
                try {
                    for (String code : CODES) {
                        ContentValues values = new ContentValues(); values.put("code", code); values.put("discount", body.getString(code));
                        db.insertWithOnConflict("settings", null, values, SQLiteDatabase.CONFLICT_REPLACE);
                    }
                    db.setTransactionSuccessful();
                } finally { db.endTransaction(); }
                return new JSONObject().put("saved", true);
            }
            JSONObject result = new JSONObject().put("USD", 90).put("JPY", 90).put("CNY", 50);
            try (Cursor cursor = db.rawQuery("SELECT code,discount FROM settings", null)) {
                while (cursor.moveToNext()) result.put(cursor.getString(0), cursor.getString(1));
            }
            return result;
        }
    }

    public JSONObject save(JSONObject result) throws Exception {
        try (SQLiteDatabase db = database()) {
            ContentValues values = new ContentValues(); values.put("id", UUID.randomUUID().toString());
            values.put("created", OffsetDateTime.now(KST).toString()); values.put("payload", result.toString());
            db.insertOrThrow("history", null, values);
        }
        return result;
    }

    public JSONArray history() throws Exception {
        JSONArray records = new JSONArray();
        try (SQLiteDatabase db = database(); Cursor cursor = db.rawQuery("SELECT id,created,payload FROM history ORDER BY created DESC", null)) {
            while (cursor.moveToNext()) records.put(new JSONObject(cursor.getString(2)).put("id", cursor.getString(0)).put("created", cursor.getString(1)));
        }
        return records;
    }

    private static String xml(String value) {
        return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\"", "&quot;");
    }
    private static void entry(ZipOutputStream zip, String name, String content) throws Exception {
        zip.putNextEntry(new ZipEntry(name)); zip.write(content.getBytes(StandardCharsets.UTF_8)); zip.closeEntry();
    }
    public static void workbook(JSONArray records, OutputStream output) throws Exception {
        String[] keys = {"created","requestedDate","publishedAt","sequence","currency","mode","unit","amount","discount","base","before","spread","afterSpread","finalRate","originalTotal","total","savings","source","baseDate"};
        String[] labels = {"저장 시각","조회일","고시일시","고시회차","통화","거래유형","기준 단위","외화 금액","우대율(%)","매매기준율","우대 전 환율","스프레드","우대 후 스프레드","최종 구매환율","우대 전 원화","필요 원화","절약 원화","출처","은행 기준일"};
        String ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main";
        StringBuilder sheet = new StringBuilder("<worksheet xmlns=\"" + ns + "\"><sheetViews><sheetView workbookViewId=\"0\"><pane ySplit=\"1\" topLeftCell=\"A2\" state=\"frozen\"/></sheetView></sheetViews><cols><col min=\"1\" max=\"19\" width=\"22\" customWidth=\"1\"/></cols><sheetData>");
        for (int row = 0; row <= records.length(); row++) {
            sheet.append("<row r=\"").append(row + 1).append("\">");
            for (int col = 0; col < keys.length; col++) {
                String value = row == 0 ? labels[col] : records.getJSONObject(row - 1).optString(keys[col]);
                sheet.append("<c r=\"").append((char)('A' + col)).append(row + 1).append("\"");
                if (row > 0 && col >= 6 && col <= 16) sheet.append("><v>").append(xml(value)).append("</v></c>");
                else sheet.append(" t=\"inlineStr\"><is><t>").append(xml(value)).append("</t></is></c>");
            }
            sheet.append("</row>");
        }
        sheet.append("</sheetData><autoFilter ref=\"A1:S").append(records.length() + 1).append("\"/></worksheet>");
        try (ZipOutputStream zip = new ZipOutputStream(output)) {
            entry(zip, "[Content_Types].xml", "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\"><Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/><Default Extension=\"xml\" ContentType=\"application/xml\"/><Override PartName=\"/xl/workbook.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml\"/><Override PartName=\"/xl/worksheets/sheet1.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml\"/></Types>");
            entry(zip, "_rels/.rels", "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\"><Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"xl/workbook.xml\"/></Relationships>");
            entry(zip, "xl/workbook.xml", "<workbook xmlns=\"" + ns + "\" xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\"><sheets><sheet name=\"환전 계산 기록\" sheetId=\"1\" r:id=\"rId1\"/></sheets></workbook>");
            entry(zip, "xl/_rels/workbook.xml.rels", "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\"><Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet\" Target=\"worksheets/sheet1.xml\"/></Relationships>");
            entry(zip, "xl/worksheets/sheet1.xml", sheet.toString());
        }
    }
}
