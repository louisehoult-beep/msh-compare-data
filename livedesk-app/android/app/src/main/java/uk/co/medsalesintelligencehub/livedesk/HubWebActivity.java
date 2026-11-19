package uk.co.medsalesintelligencehub.livedesk;

import android.annotation.SuppressLint;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.content.pm.ApplicationInfo;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.Message;
import android.util.Log;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.ViewGroup;
import android.webkit.CookieManager;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;

import androidx.activity.OnBackPressedCallback;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.graphics.Insets;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowInsetsCompat;

import org.json.JSONArray;

/**
 * The Hub inside the Live Desk app (plan step A spike, 19/11/2026).
 * - One WebView, the app's persistent CookieManager store: a Hub login stays.
 * - User agent ends with "MSHLiveDeskApp/android" (the Hub's in-app mode keys on it).
 * - Hub links stay here; other sites, target=_blank and window.open go to the
 *   phone's browser; mailto:/tel: go to their apps.
 * - Probe (debuggable builds, or when asked): logs MSH_GATE and data-gate-reads
 *   under the tag "MSHHubProbe" and shows them in a strip at the bottom.
 */
public class HubWebActivity extends AppCompatActivity {
    public static final String HUB_HOST = "medsalesintelligencehub.co.uk";
    public static final String LOGIN_URL = "https://" + HUB_HOST + "/login/";
    public static final String EXTRA_URL = "url";
    public static final String EXTRA_PROBE = "probe";
    public static final String UA_TOKEN = "MSHLiveDeskApp/android";
    static final String TAG = "MSHHubProbe";

    static final String REMEMBER_JS =
        "(function(){document.querySelectorAll('input[name=rememberme],input[name=pms_login_remember],input[type=checkbox][id*=remember]')"
        + ".forEach(function(c){c.checked=true;});})();";
    static final String PROBE_JS =
        "(function(){var g=window.MSH_GATE,b=document.body;return JSON.stringify({url:location.href,title:document.title,"
        + "ua:navigator.userAgent,gate:!!(g&&g.nonce),gateRoot:g&&g.root||null,reads:document.documentElement.getAttribute('data-gate-reads'),"
        + "loggedIn:!!(b&&b.classList.contains('logged-in'))});})()";

    private WebView web;
    private TextView probeView;
    private boolean probe;
    private final Handler handler = new Handler(Looper.getMainLooper());

    static boolean isHub(Uri u) {
        if (u == null || u.getHost() == null) return false;
        String s = u.getScheme();
        if (!"https".equals(s) && !"http".equals(s)) return false;
        String h = u.getHost().toLowerCase();
        return h.equals(HUB_HOST) || h.equals("www." + HUB_HOST);
    }

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle saved) {
        super.onCreate(saved);
        boolean debuggable = (getApplicationInfo().flags & ApplicationInfo.FLAG_DEBUGGABLE) != 0;
        probe = getIntent().getBooleanExtra(EXTRA_PROBE, false) || debuggable;
        if (debuggable) WebView.setWebContentsDebuggingEnabled(true);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(Color.parseColor("#0B1C33"));

        LinearLayout bar = new LinearLayout(this);
        bar.setOrientation(LinearLayout.HORIZONTAL);
        bar.setGravity(Gravity.CENTER_VERTICAL);
        bar.setPadding(dp(8), dp(4), dp(8), dp(4));
        Button close = new Button(this);
        close.setText("Done");
        close.setOnClickListener(v -> finish());
        Button back = new Button(this);
        back.setText("Back");
        back.setOnClickListener(v -> { if (web.canGoBack()) web.goBack(); });
        TextView title = new TextView(this);
        title.setText("The Hub");
        title.setTextColor(Color.parseColor("#E0BE8E"));
        title.setTextSize(TypedValue.COMPLEX_UNIT_SP, 17);
        title.setPadding(dp(12), 0, 0, 0);
        bar.addView(close);
        bar.addView(back);
        bar.addView(title);
        root.addView(bar);

        web = new WebView(this);
        root.addView(web, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));

        probeView = new TextView(this);
        probeView.setTextColor(Color.WHITE);
        probeView.setTextSize(TypedValue.COMPLEX_UNIT_SP, 11);
        probeView.setPadding(dp(8), dp(4), dp(8), dp(4));
        probeView.setBackgroundColor(Color.parseColor("#132238"));
        if (probe) root.addView(probeView);
        setContentView(root);
        ViewCompat.setOnApplyWindowInsetsListener(root, (v, insets) -> {
            Insets b = insets.getInsets(WindowInsetsCompat.Type.systemBars());
            v.setPadding(b.left, b.top, b.right, b.bottom);
            return insets;
        });

        CookieManager cm = CookieManager.getInstance();
        cm.setAcceptCookie(true);
        cm.setAcceptThirdPartyCookies(web, true);

        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setSupportMultipleWindows(true);
        s.setJavaScriptCanOpenWindowsAutomatically(true);
        s.setUserAgentString(s.getUserAgentString() + " " + UA_TOKEN);

        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest req) {
                if (!req.isForMainFrame()) return false;
                Uri u = req.getUrl();
                if (isHub(u)) return false;
                String sc = u.getScheme() == null ? "" : u.getScheme();
                if (sc.equals("about") || sc.equals("data") || sc.equals("blob")) return false;
                openOutside(u);
                return true;
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                view.evaluateJavascript(REMEMBER_JS, null);
                CookieManager.getInstance().flush();
                if (probe) {
                    runProbe("load");
                    handler.postDelayed(() -> runProbe("6s"), 6000);
                    handler.postDelayed(() -> runProbe("15s"), 15000);
                }
            }
        });
        web.setWebChromeClient(new WebChromeClient() {
            // target=_blank and window.open: hand the address to the phone's browser.
            @Override
            public boolean onCreateWindow(WebView view, boolean isDialog, boolean isUserGesture, Message resultMsg) {
                WebView temp = new WebView(HubWebActivity.this);
                temp.setWebViewClient(new WebViewClient() {
                    @Override
                    public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest req) {
                        openOutside(req.getUrl());
                        v.destroy();
                        return true;
                    }
                });
                ((WebView.WebViewTransport) resultMsg.obj).setWebView(temp);
                resultMsg.sendToTarget();
                return true;
            }
        });

        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
            @Override
            public void handleOnBackPressed() {
                if (web.canGoBack()) web.goBack(); else finish();
            }
        });

        String url = getIntent().getStringExtra(EXTRA_URL);
        web.loadUrl(url != null && isHub(Uri.parse(url)) ? url : LOGIN_URL);
    }

    private void runProbe(String when) {
        if (web == null) return;
        web.evaluateJavascript(PROBE_JS, result -> {
            String json = result;
            try { json = new JSONArray("[" + result + "]").getString(0); } catch (Exception ignored) { }
            Log.i(TAG, when + " " + json);
            probeView.setText("probe " + when + ": " + json);
        });
    }

    private void openOutside(Uri u) {
        Log.i(TAG, "outside " + u);
        try {
            startActivity(new Intent(Intent.ACTION_VIEW, u).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
        } catch (ActivityNotFoundException e) {
            Log.w(TAG, "no app for " + u);
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        CookieManager.getInstance().flush();
    }

    @Override
    protected void onDestroy() {
        handler.removeCallbacksAndMessages(null);
        if (web != null) web.destroy();
        super.onDestroy();
    }

    private int dp(int v) {
        return Math.round(v * getResources().getDisplayMetrics().density);
    }
}
