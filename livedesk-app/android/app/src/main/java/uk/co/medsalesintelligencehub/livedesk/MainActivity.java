package uk.co.medsalesintelligencehub.livedesk;

import android.content.Intent;
import android.content.pm.ApplicationInfo;
import android.os.Bundle;

import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(HubViewPlugin.class);
        super.onCreate(savedInstanceState);
        openHubFromLaunch(getIntent());
    }

    // Test builds only: `adb shell am start ... --es hubUrl <url>` opens the Hub view straight away.
    private void openHubFromLaunch(Intent intent) {
        boolean debuggable = (getApplicationInfo().flags & ApplicationInfo.FLAG_DEBUGGABLE) != 0;
        String url = intent == null ? null : intent.getStringExtra("hubUrl");
        if (!debuggable || url == null) return;
        Intent i = new Intent(this, HubWebActivity.class);
        i.putExtra(HubWebActivity.EXTRA_URL, url);
        i.putExtra(HubWebActivity.EXTRA_PROBE, true);
        startActivity(i);
    }
}
