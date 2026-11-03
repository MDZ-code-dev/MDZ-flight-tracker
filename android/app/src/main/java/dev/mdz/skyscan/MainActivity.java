package dev.mdz.skyscan;

import android.app.Activity;
import android.os.Bundle;
import android.webkit.JavascriptInterface;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import org.json.JSONArray;
import org.json.JSONObject;
import javax.net.ssl.HttpsURLConnection;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Offline UI and private settings, with live ADS-B requests over verified HTTPS. */
public class MainActivity extends Activity {
    private WebView web;
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private static final String ORIGIN = "https://appassets.androidplatform.net/";
    private static final double MAX_CONTACT_AGE_SECONDS = 90;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        web = new WebView(this);
        web.setOnApplyWindowInsetsListener((view, insets) -> {
            view.setPadding(insets.getSystemWindowInsetLeft(), insets.getSystemWindowInsetTop(),
                insets.getSystemWindowInsetRight(), insets.getSystemWindowInsetBottom());
            return insets;
        });
        web.getSettings().setJavaScriptEnabled(true);
        web.getSettings().setAllowFileAccess(false);
        web.getSettings().setAllowContentAccess(false);
        web.addJavascriptInterface(new Backend(), "MDZAndroid");
        web.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest req) {
                return !req.getUrl().toString().startsWith(ORIGIN);
            }
            @Override public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest req) {
                String url = req.getUrl().toString();
                if (url.startsWith(ORIGIN)) {
                    String path = req.getUrl().getPath();
                    if ("/".equals(path)) path = "/index.html";
                    if (path != null && path.matches("/[a-zA-Z0-9_.-]+") && !path.contains("..")) {
                        try {
                            String mime = path.endsWith(".js") ? "application/javascript" :
                                path.endsWith(".css") ? "text/css" :
                                path.endsWith(".ttf") ? "font/ttf" : "text/html";
                            return new WebResourceResponse(mime, path.endsWith(".ttf") ? null : "UTF-8", getAssets().open("web" + path));
                        } catch (Exception ignored) { }
                    }
                }
                return new WebResourceResponse("text/plain", "UTF-8", 404, "Not Found", null,
                    new ByteArrayInputStream(new byte[0]));
            }
        });
        setContentView(web);
        web.loadUrl(ORIGIN);
    }

    private JSONObject config() throws Exception {
        String saved = getPreferences(MODE_PRIVATE).getString("config", "{}");
        JSONObject cfg = new JSONObject(saved);
        if (!cfg.has("lat")) cfg.put("lat", JSONObject.NULL);
        if (!cfg.has("lon")) cfg.put("lon", JSONObject.NULL);
        if (!cfg.has("radius_nm")) cfg.put("radius_nm", 80);
        if (!cfg.has("refresh_seconds")) cfg.put("refresh_seconds", 5);
        return cfg;
    }

    private double number(JSONObject data, String key, double fallback) throws Exception {
        double n = data.has(key) ? Double.parseDouble(data.getString(key)) : fallback;
        if (Double.isNaN(n) || Double.isInfinite(n)) throw new IllegalArgumentException("Invalid " + key);
        return n;
    }

    private JSONObject save(String body) throws Exception {
        JSONObject data = new JSONObject(body), cfg = config();
        for (String key : new String[]{"lat", "lon"}) {
            if (!data.has(key)) continue;
            if (data.isNull(key) || data.optString(key).isEmpty()) cfg.put(key, JSONObject.NULL);
            else {
                double value = number(data, key, 0), limit = key.equals("lat") ? 90 : 180;
                if (Math.abs(value) > limit) throw new IllegalArgumentException("Invalid " + key);
                cfg.put(key, value);
            }
        }
        cfg.put("radius_nm", Math.max(1, Math.min(250, number(data, "radius_nm", cfg.getDouble("radius_nm")))));
        cfg.put("refresh_seconds", Math.max(3, Math.min(60, number(data, "refresh_seconds", cfg.getDouble("refresh_seconds")))));
        if (!getPreferences(MODE_PRIVATE).edit().putString("config", cfg.toString()).commit())
            throw new IllegalStateException("Unable to save settings");
        return new JSONObject().put("ok", true).put("config", cfg);
    }

    private String text(JSONObject ac, String key, String fallback) {
        String value = ac.isNull(key) ? "" : ac.optString(key, "").trim();
        return value.isEmpty() ? fallback : value;
    }
    private String direction(double degrees) {
        degrees = heading(degrees);
        return new String[]{"N","NE","E","SE","S","SW","W","NW"}[(int)((degrees + 22.5) / 45) % 8];
    }
    private double heading(double degrees) { return (degrees % 360 + 360) % 360; }
    private Double finiteNumber(Object value) {
        if (!(value instanceof Number)) return null;
        double number = ((Number)value).doubleValue();
        return Double.isNaN(number) || Double.isInfinite(number) ? null : number;
    }
    private Object jsonNumber(Double value) { return value == null ? JSONObject.NULL : value; }
    private String rounded(double value) { return String.format(Locale.US, "%.0f", value); }

    private JSONObject planes() throws Exception {
        JSONObject cfg = config();
        if (cfg.isNull("lat") || cfg.isNull("lon")) return new JSONObject().put("ok", false)
            .put("needs_location", true).put("error", "Set a location first").put("config", cfg).put("planes", new JSONArray());
        double lat = cfg.getDouble("lat"), lon = cfg.getDouble("lon"), radius = cfg.getDouble("radius_nm");
        URL url = new URL("https://api.adsb.lol/v2/point/" + lat + "/" + lon + "/" + radius);
        HttpsURLConnection connection = (HttpsURLConnection) url.openConnection();
        connection.setConnectTimeout(8000);
        connection.setReadTimeout(8000);
        connection.setInstanceFollowRedirects(false);
        connection.setRequestProperty("User-Agent", "MDZ-SkyScan-Android/1.0");
        connection.setRequestProperty("Accept", "application/json");
        JSONObject payload;
        try {
            if (connection.getResponseCode() != 200)
                throw new IllegalStateException("ADS-B API HTTP " + connection.getResponseCode());
            try (InputStream input = connection.getInputStream(); ByteArrayOutputStream output = new ByteArrayOutputStream()) {
                byte[] buffer = new byte[8192]; int count;
                while ((count = input.read(buffer)) != -1) {
                    if (output.size() + count > 16 * 1024 * 1024) throw new IllegalStateException("ADS-B response too large");
                    output.write(buffer, 0, count);
                }
                payload = new JSONObject(new String(output.toByteArray(), StandardCharsets.UTF_8));
            }
        } finally { connection.disconnect(); }
        JSONArray contacts = payload.optJSONArray("ac");
        List<JSONObject> sorted = new ArrayList<>();
        if (contacts != null) for (int i = 0; i < contacts.length(); i++) {
            JSONObject ac = contacts.optJSONObject(i);
            if (ac == null) continue;
            double alat = ac.optDouble("lat", Double.NaN), alon = ac.optDouble("lon", Double.NaN);
            if (Double.isNaN(alat) || Double.isInfinite(alat) || Math.abs(alat) > 90 ||
                Double.isNaN(alon) || Double.isInfinite(alon) || Math.abs(alon) > 180) continue;
            // Unknown ages are retained; only a numeric age establishes staleness.
            Double seen = finiteNumber(ac.opt("seen")), seenPos = finiteNumber(ac.opt("seen_pos"));
            if ((seen != null && seen > MAX_CONTACT_AGE_SECONDS) ||
                (seenPos != null && seenPos > MAX_CONTACT_AGE_SECONDS)) continue;
            double p1 = Math.toRadians(lat), p2 = Math.toRadians(alat), dl = Math.toRadians(alon - lon);
            double a = Math.pow(Math.sin((p2-p1)/2),2) + Math.cos(p1)*Math.cos(p2)*Math.pow(Math.sin(dl/2),2);
            double dist = 6371.0088 * 2 * Math.asin(Math.sqrt(Math.max(0,Math.min(1,a)))) / 1.852;
            if (dist > radius) continue;
            double bearing = (Math.toDegrees(Math.atan2(Math.sin(dl)*Math.cos(p2),
                Math.cos(p1)*Math.sin(p2)-Math.sin(p1)*Math.cos(p2)*Math.cos(dl))) + 360) % 360;
            Object altValue = ac.has("alt_baro") ? ac.opt("alt_baro") : ac.opt("alt_geom");
            boolean onGround = altValue instanceof String && "ground".equalsIgnoreCase(((String)altValue).trim());
            Double alt = finiteNumber(altValue), speed = finiteNumber(ac.opt("gs")), track = finiteNumber(ac.opt("track"));
            Double rate = finiteNumber(ac.has("baro_rate") ? ac.opt("baro_rate") : ac.opt("geom_rate"));
            if (track != null) track = heading(track);
            String altitude = onGround ? "GROUND" : alt != null ? String.format(Locale.US,"%,.0f FT",alt) : "---";
            String vertical = "---";
            if (rate != null) {
                double v = rate;
                vertical = v > 100 ? "▲ " + rounded(v) + " FPM" : v < -100 ? "▼ " + rounded(-v) + " FPM" : "LEVEL";
            }
            double flags = ac.optDouble("dbFlags", 0);
            boolean military = !Double.isNaN(flags) && !Double.isInfinite(flags) && (ac.optInt("dbFlags",0)&1)!=0;
            sorted.add(new JSONObject().put("hex",text(ac,"hex","---"))
                .put("callsign",text(ac,"flight","NO CALLSIGN")).put("registration",text(ac,"r","---"))
                .put("type",text(ac,"t","---")).put("description",text(ac,"desc","---"))
                .put("altitude",altitude).put("altitude_raw",onGround ? altValue : jsonNumber(alt))
                .put("speed",speed != null ? rounded(speed) + " KT" : "---")
                .put("speed_raw",jsonNumber(speed)).put("vertical",vertical)
                .put("track",jsonNumber(track)).put("track_direction",track != null ? direction(track) : "---")
                .put("lat",alat).put("lon",alon).put("distance_nm",dist)
                .put("bearing",Math.round(bearing*10)/10.0).put("bearing_direction",direction(bearing))
                .put("squawk",text(ac,"squawk","---")).put("military",military)
                .put("category",text(ac,"category","---")).put("seen",jsonNumber(seen)).put("seen_pos",jsonNumber(seenPos)));
        }
        sorted.sort(Comparator.comparingDouble(p -> p.optDouble("distance_nm")));
        for (JSONObject plane : sorted) plane.put("distance_nm",Math.round(plane.getDouble("distance_nm")*100)/100.0);
        return new JSONObject().put("ok",true).put("needs_location",false).put("config",cfg)
            .put("updated",System.currentTimeMillis()/1000).put("source_now",jsonNumber(finiteNumber(payload.opt("now"))))
            .put("total",sorted.size()).put("planes",new JSONArray(sorted))
            .put("nearest",sorted.isEmpty() ? JSONObject.NULL : sorted.get(0));
    }

    public class Backend {
        @JavascriptInterface public void request(int id, String path, String method, String body) {
            worker.execute(() -> {
                JSONObject result;
                try {
                    if ("/api/config".equals(path) && "POST".equals(method)) result = save(body);
                    else if ("/api/config".equals(path) && "GET".equals(method)) result = config();
                    else if ("/api/planes".equals(path) && "GET".equals(method)) result = planes();
                    else throw new IllegalArgumentException("Unknown request");
                } catch (Exception error) {
                    result = new JSONObject();
                    try { result.put("ok",false).put("error",error.getMessage() == null ? "Request failed" : error.getMessage()); }
                    catch (Exception ignored) { }
                }
                final String script = "window.MDZNativeResult(" + id + "," + result.toString() + ")";
                runOnUiThread(() -> { if (web != null) web.evaluateJavascript(script, null); });
            });
        }
    }

    @Override protected void onDestroy() {
        worker.shutdownNow();
        if (web != null) { web.removeJavascriptInterface("MDZAndroid"); web.destroy(); web = null; }
        super.onDestroy();
    }
}
