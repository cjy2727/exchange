package com.cjy2727.exchange;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.webkit.JavascriptInterface;
import android.webkit.JsResult;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;
import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import org.json.JSONObject;

public final class MainActivity extends Activity {
    private static final String ORIGIN = "https://appassets.androidplatform.net";
    private static final int EXPORT = 10;
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private WebView web;
    private ExchangeEngine engine;
    private boolean exporting;
    private volatile boolean destroyed;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        engine = new ExchangeEngine(this);
        web = new WebView(this);
        web.setBackgroundColor(0xfff3f6f3);
        web.getSettings().setJavaScriptEnabled(true);
        web.getSettings().setAllowFileAccess(false);
        web.getSettings().setAllowContentAccess(false);
        web.getSettings().setMixedContentMode(android.webkit.WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        web.getSettings().setJavaScriptCanOpenWindowsAutomatically(false);
        web.addJavascriptInterface(new Bridge(), "ExchangeAndroid");
        web.setWebChromeClient(new WebChromeClient() {
            @Override public boolean onJsConfirm(WebView view, String url, String message, JsResult result) {
                new AlertDialog.Builder(MainActivity.this).setMessage(message)
                        .setPositiveButton("확인", (dialog, which) -> result.confirm())
                        .setNegativeButton("취소", (dialog, which) -> result.cancel())
                        .setOnCancelListener(dialog -> result.cancel()).show();
                return true;
            }
        });
        web.setWebViewClient(new WebViewClient() {
            @Override public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                if (!local(uri)) return blocked();
                String path = uri.getPath();
                String name, mime;
                if ("/".equals(path) || "/index.html".equals(path)) { name = "index.html"; mime = "text/html"; }
                else if ("/app.js".equals(path) || "/android.js".equals(path)) { name = path.substring(1); mime = "text/javascript"; }
                else if ("/style.css".equals(path)) { name = "style.css"; mime = "text/css"; }
                else return blocked();
                try (InputStream input = getAssets().open(name)) {
                    String content = new String(ExchangeEngine.readLimited(input, 2000000), StandardCharsets.UTF_8);
                    if (name.equals("index.html")) {
                        content = content.replace("<script src=\"/app.js\"", "<script src=\"/android.js\" defer></script><script src=\"/app.js\"")
                                .replace("LOCAL WORKSPACE", "ANDROID")
                                .replace("개인용 계산 도구입니다.", "개인용 계산 도구입니다. PC와 휴대폰의 기록은 서로 동기화되지 않습니다.");
                    }
                    if (name.equals("style.css")) content = content.replaceAll("(?m)^@import[^;]+;", "");
                    Map<String,String> headers = new HashMap<>();
                    headers.put("Cache-Control", "no-store");
                    headers.put("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'none'; frame-src 'none'; object-src 'none'; base-uri 'none'");
                    return new WebResourceResponse(mime, "UTF-8", 200, "OK", headers, new ByteArrayInputStream(content.getBytes(StandardCharsets.UTF_8)));
                } catch (Exception e) { return blocked(); }
            }
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                if (local(request.getUrl())) return false;
                if (request.isForMainFrame() && "https".equals(request.getUrl().getScheme())) {
                    try { startActivity(new Intent(Intent.ACTION_VIEW, request.getUrl())); }
                    catch (Exception e) { toast("링크를 열 수 있는 브라우저가 없습니다."); }
                }
                return true;
            }
        });
        web.setOnApplyWindowInsetsListener((view, insets) -> {
            view.setPadding(insets.getSystemWindowInsetLeft(), insets.getSystemWindowInsetTop(), insets.getSystemWindowInsetRight(), insets.getSystemWindowInsetBottom());
            return insets.consumeSystemWindowInsets();
        });
        setContentView(web);
        web.loadUrl(ORIGIN + "/index.html");
    }

    private static boolean local(Uri uri) {
        return "https".equals(uri.getScheme()) && "appassets.androidplatform.net".equals(uri.getHost()) && uri.getPort() == -1;
    }
    private static WebResourceResponse blocked() {
        return new WebResourceResponse("text/plain", "UTF-8", 404, "Not Found", new HashMap<>(), new ByteArrayInputStream(new byte[0]));
    }
    private void toast(String message) { runOnUiThread(() -> { if (!destroyed) Toast.makeText(this, message, Toast.LENGTH_LONG).show(); }); }
    private void reply(String id, Object value, String error) {
        runOnUiThread(() -> {
            if (destroyed) return;
            String data = value == null ? "null" : value.toString();
            web.evaluateJavascript("window.exchangeReply(" + JSONObject.quote(id) + "," + data + "," + (error == null ? "null" : JSONObject.quote(error)) + ")", null);
        });
    }

    private final class Bridge {
        @JavascriptInterface public void request(String id, String path, String bodyText) {
            if (destroyed || !id.matches("[0-9]{1,12}") || path.length() > 200 || bodyText.length() > 10000) return;
            worker.execute(() -> {
                try {
                    JSONObject body = bodyText.equals("null") ? null : new JSONObject(bodyText);
                    Uri uri = Uri.parse(path);
                    if (uri.getScheme() != null || uri.getHost() != null) throw new IllegalArgumentException("지원하지 않는 요청입니다.");
                    Object result;
                    switch (uri.getPath()) {
                        case "/api/rates": result = engine.rates(uri.getQueryParameter("date")); break;
                        case "/api/settings": result = engine.settings(body); break;
                        case "/api/history":
                            result = body == null ? engine.history() : engine.save(ExchangeEngine.calculate(engine.rates(body.getString("date")), body)); break;
                        case "/api/calculate":
                            if (body == null) throw new IllegalArgumentException("계산 값을 입력해 주세요.");
                            result = ExchangeEngine.calculate(engine.rates(body.getString("date")), body); break;
                        case "/api/health": result = new JSONObject().put("app", "ExchangeStudioAndroid").put("token", "android-local"); break;
                        case "/api/shutdown":
                            result = new JSONObject().put("stopped", true);
                            runOnUiThread(() -> { if (!destroyed) finishAndRemoveTask(); }); break;
                        case "/api/export":
                            runOnUiThread(() -> chooseExport());
                            result = new JSONObject().put("opened", true); break;
                        default: throw new IllegalArgumentException("지원하지 않는 요청입니다.");
                    }
                    reply(id, result, null);
                } catch (Exception e) {
                    String error = e instanceof IllegalArgumentException || e instanceof java.io.IOException ? e.getMessage() : "처리 중 오류가 발생했습니다. 다시 시도해 주세요.";
                    reply(id, null, error == null ? "요청을 처리하지 못했습니다." : error);
                }
            });
        }
    }

    private void chooseExport() {
        if (destroyed || exporting) return;
        Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE)
                .setType("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                .putExtra(Intent.EXTRA_TITLE, "exchange-history.xlsx");
        try { exporting = true; startActivityForResult(intent, EXPORT); }
        catch (Exception e) { exporting = false; toast("파일 저장 화면을 열 수 없습니다."); }
    }
    @Override protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != EXPORT) return;
        exporting = false;
        if (resultCode != RESULT_OK || data == null || data.getData() == null) return;
        Uri target = data.getData();
        worker.execute(() -> {
            try (OutputStream output = getContentResolver().openOutputStream(target)) {
                if (output == null) throw new java.io.IOException();
                ExchangeEngine.workbook(engine.history(), output);
                toast("엑셀 파일을 저장했습니다.");
            } catch (Exception e) { toast("파일을 저장하지 못했습니다. 저장 위치와 여유 공간을 확인해 주세요."); }
        });
    }
    @Override public void onBackPressed() {
        new AlertDialog.Builder(this).setMessage("환율 계산기를 종료할까요?")
                .setPositiveButton("종료", (dialog, which) -> finishAndRemoveTask()).setNegativeButton("취소", null).show();
    }
    @Override protected void onDestroy() {
        destroyed = true;
        worker.shutdown();
        if (web != null) { web.removeJavascriptInterface("ExchangeAndroid"); web.destroy(); }
        super.onDestroy();
    }
}
