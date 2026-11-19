import UIKit
import WebKit
import Capacitor

// The Hub inside the Live Desk app (plan step A spike, 19/11/2026).
// - WKWebView on the default (persistent) website data store: a Hub login stays.
// - User agent ends with "MSHLiveDeskApp/ios" (the Hub's in-app mode keys on it).
// - Hub links stay here; other sites, target=_blank and window.open go to the
//   phone's browser; mailto:/tel: go to their apps.
// - Probe (DEBUG builds, or when asked): logs MSH_GATE and data-gate-reads as
//   "MSHHubProbe ..." and shows them in a strip at the bottom.

enum Hub {
    static let host = "medsalesintelligencehub.co.uk"
    static let loginURL = URL(string: "https://\(host)/login/")!
    static let uaToken = "MSHLiveDeskApp/ios"

    static func isHub(_ url: URL?) -> Bool {
        guard let u = url, let scheme = u.scheme?.lowercased(), scheme == "https" || scheme == "http",
              let h = u.host?.lowercased() else { return false }
        return h == host || h == "www." + host
    }
}

class MainViewController: CAPBridgeViewController {
    override open func capacitorDidLoad() {
        bridge?.registerPluginInstance(HubViewPlugin())
    }

    // Test builds only: `simctl launch ... -hubUrl <url>` opens the Hub view straight away.
    override func viewDidAppear(_ animated: Bool) {
        super.viewDidAppear(animated)
        #if DEBUG
        if let s = UserDefaults.standard.string(forKey: "hubUrl"), let u = URL(string: s), presentedViewController == nil {
            UserDefaults.standard.removeObject(forKey: "hubUrl")
            HubWebViewController.present(from: self, url: u, probe: true)
        }
        #endif
    }
}

@objc(HubViewPlugin)
public class HubViewPlugin: CAPPlugin, CAPBridgedPlugin {
    public let identifier = "HubViewPlugin"
    public let jsName = "HubView"
    public let pluginMethods: [CAPPluginMethod] = [
        CAPPluginMethod(name: "open", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "signOut", returnType: CAPPluginReturnPromise),
    ]

    @objc func open(_ call: CAPPluginCall) {
        let url = call.getString("url").flatMap(URL.init(string:)) ?? Hub.loginURL
        let probe = call.getBool("probe") ?? false
        DispatchQueue.main.async {
            guard let vc = self.bridge?.viewController else { call.reject("no view"); return }
            HubWebViewController.present(from: vc, url: url, probe: probe)
            call.resolve()
        }
    }

    @objc func signOut(_ call: CAPPluginCall) {
        DispatchQueue.main.async {
            let store = WKWebsiteDataStore.default()
            store.fetchDataRecords(ofTypes: WKWebsiteDataStore.allWebsiteDataTypes()) { records in
                let hub = records.filter { $0.displayName.lowercased().contains(Hub.host) }
                store.removeData(ofTypes: WKWebsiteDataStore.allWebsiteDataTypes(), for: hub) { call.resolve() }
            }
        }
    }
}

final class HubWebViewController: UIViewController, WKNavigationDelegate, WKUIDelegate {
    private var web: WKWebView!
    private let probeLabel = UILabel()
    private var startURL: URL = Hub.loginURL
    private var probe = false

    static let rememberJS = """
    (function(){var f=function(){document.querySelectorAll('input[name=rememberme],input[name=pms_login_remember],input[type=checkbox][id*=remember]').forEach(function(c){c.checked=true;});};f();setTimeout(f,800);})();
    """
    static let probeJS = """
    (function(){var g=window.MSH_GATE,b=document.body;return JSON.stringify({url:location.href,title:document.title,ua:navigator.userAgent,gate:!!(g&&g.nonce),gateRoot:g&&g.root||null,reads:document.documentElement.getAttribute('data-gate-reads'),loggedIn:!!(b&&b.classList.contains('logged-in'))});})()
    """

    static func present(from vc: UIViewController, url: URL, probe: Bool) {
        let hub = HubWebViewController()
        hub.startURL = Hub.isHub(url) ? url : Hub.loginURL
        #if DEBUG
        hub.probe = true
        #else
        hub.probe = probe
        #endif
        let nav = UINavigationController(rootViewController: hub)
        nav.modalPresentationStyle = .fullScreen
        vc.present(nav, animated: true)
    }

    override func viewDidLoad() {
        super.viewDidLoad()
        title = "The Hub"
        view.backgroundColor = UIColor(red: 0.043, green: 0.11, blue: 0.2, alpha: 1)
        navigationItem.leftBarButtonItem = UIBarButtonItem(barButtonSystemItem: .done, target: self, action: #selector(done))
        navigationItem.rightBarButtonItem = UIBarButtonItem(title: "Back", style: .plain, target: self, action: #selector(back))

        let config = WKWebViewConfiguration()
        config.websiteDataStore = .default()
        config.applicationNameForUserAgent = "Mobile/15E148 " + Hub.uaToken
        config.userContentController.addUserScript(
            WKUserScript(source: Self.rememberJS, injectionTime: .atDocumentEnd, forMainFrameOnly: true))
        web = WKWebView(frame: .zero, configuration: config)
        web.navigationDelegate = self
        web.uiDelegate = self
        web.allowsBackForwardNavigationGestures = true
        #if DEBUG
        if #available(iOS 16.4, *) { web.isInspectable = true }
        #endif

        let stack = UIStackView(arrangedSubviews: [web])
        stack.axis = .vertical
        if probe {
            probeLabel.numberOfLines = 3
            probeLabel.font = .monospacedSystemFont(ofSize: 10, weight: .regular)
            probeLabel.textColor = .white
            probeLabel.backgroundColor = UIColor(red: 0.075, green: 0.133, blue: 0.22, alpha: 1)
            probeLabel.text = "probe: waiting"
            stack.addArrangedSubview(probeLabel)
        }
        stack.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(stack)
        NSLayoutConstraint.activate([
            stack.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor),
            stack.bottomAnchor.constraint(equalTo: view.safeAreaLayoutGuide.bottomAnchor),
            stack.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            stack.trailingAnchor.constraint(equalTo: view.trailingAnchor),
        ])
        web.load(URLRequest(url: startURL))
    }

    @objc private func done() { dismiss(animated: true) }
    @objc private func back() { if web.canGoBack { web.goBack() } }

    // MARK: links
    func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction,
                 decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        guard let url = action.request.url else { decisionHandler(.cancel); return }
        let scheme = url.scheme?.lowercased() ?? ""
        if action.targetFrame == nil {           // target=_blank, window.open
            openOutside(url); decisionHandler(.cancel); return
        }
        if action.targetFrame?.isMainFrame == false { decisionHandler(.allow); return }   // embeds
        if Hub.isHub(url) || ["about", "data", "blob"].contains(scheme) { decisionHandler(.allow); return }
        openOutside(url); decisionHandler(.cancel)
    }

    func webView(_ webView: WKWebView, createWebViewWith configuration: WKWebViewConfiguration,
                 for action: WKNavigationAction, windowFeatures: WKWindowFeatures) -> WKWebView? {
        if let url = action.request.url { openOutside(url) }
        return nil
    }

    private func openOutside(_ url: URL) {
        NSLog("MSHHubProbe outside %@", url.absoluteString)
        UIApplication.shared.open(url)
    }

    // MARK: probe
    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        guard probe else { return }
        runProbe("load")
        DispatchQueue.main.asyncAfter(deadline: .now() + 6) { [weak self] in self?.runProbe("6s") }
        DispatchQueue.main.asyncAfter(deadline: .now() + 15) { [weak self] in self?.runProbe("15s") }
    }

    private func runProbe(_ when: String) {
        web?.evaluateJavaScript(Self.probeJS) { [weak self] result, _ in
            let json = (result as? String) ?? "null"
            NSLog("MSHHubProbe %@ %@", when, json)
            self?.probeLabel.text = "probe \(when): \(json)"
        }
    }
}
