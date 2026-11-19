package uk.co.medsalesintelligencehub.livedesk;

import android.content.Intent;
import android.webkit.CookieManager;

import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

/**
 * Hub web view (plan step A spike, 19/11/2026). JS: registerPlugin('HubView').
 *   open({ url, probe })  shows a Hub page in HubWebActivity
 *   signOut()             clears the web view cookies (the Hub login)
 */
@CapacitorPlugin(name = "HubView")
public class HubViewPlugin extends Plugin {

    @PluginMethod
    public void open(PluginCall call) {
        String url = call.getString("url", HubWebActivity.LOGIN_URL);
        Intent i = new Intent(getContext(), HubWebActivity.class);
        i.putExtra(HubWebActivity.EXTRA_URL, url);
        i.putExtra(HubWebActivity.EXTRA_PROBE, call.getBoolean("probe", false));
        getActivity().startActivity(i);
        call.resolve();
    }

    @PluginMethod
    public void signOut(PluginCall call) {
        CookieManager cm = CookieManager.getInstance();
        cm.removeAllCookies(done -> { cm.flush(); call.resolve(); });
    }
}
