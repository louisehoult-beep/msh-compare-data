/* Live Desk app: "in-app mode" for Hub pages opened inside the app's Hub tab.
   DRAFT (19/11/2026), step C of Cowork-OS/02-Elevate-and-Thrive/Hub/
   live-desk-app-hub-section-PLAN-2026-11-19.md. Not installed. Goes live only
   with Lou's yes, through the publish skill.
   WPCode snippet, type "PHP Snippet", location "Run Everywhere", on
   medsalesintelligencehub.co.uk only. Paste from the line below this comment
   (WPCode adds the opening PHP tag itself).

   Source of truth: hub/wpcode/livedesk-in-app-mode.php in
   louisehoult-beep/msh-compare-data. Tested by test_livedesk_in_app_mode.py.

   The app's web view sends a user agent ending "MSHLiveDeskApp/ios" or
   "MSHLiveDeskApp/android". In that view, and only there:
     1. Server side, logged-in GET requests for the hidden pages get a 302 to
        the Hub home (page 675). Hidden: Register 685, Join 1174, Account 687,
        My account 167, Checkout 166, Cart 165 (buying and account flows: App
        Store 3.1.1, no steering to buy outside the app) and 4802, 4463, 4504
        (pages about the app itself).
     2. In the browser, a small static script adds the class msh-in-app to
        <html>, hides links to the hidden pages and Join / pricing / Upgrade /
        Print controls, and sends any click on such a link to the Hub home.
   The script is the same for every visitor and does nothing unless the user
   agent carries the token, so edge-cached pages stay correct. The server-side
   302 runs only for logged-in requests, which WordPress.com does not cache;
   it is a 302 with nocache_headers() because the answer depends on who asks.
   To undo: deactivate. */

if ( ! function_exists( 'msh_inapp_hidden_ids' ) ) {
	function msh_inapp_hidden_ids() {
		return array( 685, 1174, 687, 167, 166, 165, 4802, 4463, 4504 );
	}
}

if ( ! function_exists( 'msh_inapp_platform' ) ) {
	/* 'ios' | 'android' | '' from a user agent. The token must be its own word. */
	function msh_inapp_platform( $ua ) {
		if ( preg_match( '~(?:^|[\s;(])MSHLiveDeskApp/(ios|android)(?=$|[\s;)])~', (string) $ua, $m ) ) {
			return $m[1];
		}
		return '';
	}
}

if ( ! function_exists( 'msh_inapp_decide' ) ) {
	/* $r: ua, method, skip_context, logged_in, page_id.
	   Returns array( bool redirect, string why ). */
	function msh_inapp_decide( $r ) {
		if ( '' === msh_inapp_platform( isset( $r['ua'] ) ? $r['ua'] : '' ) ) {
			return array( false, 'not-app' );
		}
		if ( ! empty( $r['skip_context'] ) ) {
			return array( false, 'admin-ajax-rest-cron-feed' );
		}
		if ( ! isset( $r['method'] ) || 'GET' !== $r['method'] ) {
			return array( false, 'not-get' );
		}
		if ( empty( $r['logged_in'] ) ) {
			return array( false, 'logged-out' );
		}
		if ( ! in_array( (int) ( isset( $r['page_id'] ) ? $r['page_id'] : 0 ), msh_inapp_hidden_ids(), true ) ) {
			return array( false, 'not-hidden' );
		}
		return array( true, 'hidden-in-app' );
	}
}

if ( function_exists( 'add_action' ) ) {
	add_action( 'template_redirect', function () {
		$d = msh_inapp_decide( array(
			'ua'           => isset( $_SERVER['HTTP_USER_AGENT'] ) ? (string) $_SERVER['HTTP_USER_AGENT'] : '',
			'method'       => isset( $_SERVER['REQUEST_METHOD'] ) ? strtoupper( (string) $_SERVER['REQUEST_METHOD'] ) : '',
			'skip_context' => is_admin() || wp_doing_ajax() || wp_doing_cron() || is_feed() || ( defined( 'REST_REQUEST' ) && REST_REQUEST ),
			'logged_in'    => is_user_logged_in(),
			'page_id'      => is_page() ? (int) get_queried_object_id() : 0,
		) );
		if ( $d[0] ) {
			nocache_headers();
			wp_safe_redirect( get_permalink( 675 ), 302 );
			exit;
		}
	}, 5 );

	add_action( 'wp_head', function () {
		$paths = array();
		foreach ( msh_inapp_hidden_ids() as $id ) {
			$u = get_permalink( $id );
			if ( $u ) {
				$p = (string) wp_parse_url( $u, PHP_URL_PATH );
				if ( '' !== $p ) {
					$paths[] = rtrim( strtolower( $p ), '/' ) . '/';
				}
			}
		}
		$home = (string) wp_parse_url( (string) get_permalink( 675 ), PHP_URL_PATH );
		?>
<style id="msh-in-app-css">html.msh-in-app .msh-inapp-hide{display:none!important}</style>
<script id="msh-in-app-js">
(function () {
  if (!/(?:^|[\s;(])MSHLiveDeskApp\/(?:ios|android)(?=$|[\s;)])/.test(navigator.userAgent)) return;
  var HIDDEN = <?php echo wp_json_encode( array_values( array_unique( $paths ) ) ); ?>;
  var HOME = <?php echo wp_json_encode( $home ? $home : '/medical-sales-hub/' ); ?>;
  var WORDS = /^\s*(join( the hub)?( now| today)?|register|sign up|upgrade( now)?|see (the )?(plans|pricing)|pricing|view plans|buy( now)?|checkout|basket|cart|print( this page)?)\s*$/i;
  var HOSTS = /^(www\.)?medsalesintelligencehub\.co\.uk$/i;
  document.documentElement.className += ' msh-in-app';
  function hiddenPath(href) {
    try {
      var u = new URL(href, location.href);
      if (!HOSTS.test(u.hostname)) return false;
      var p = u.pathname.toLowerCase().replace(/\/?$/, '/');
      for (var i = 0; i < HIDDEN.length; i++) if (p === HIDDEN[i]) return true;
      return /\/(join-the-hub|register|checkout|cart|account|my-account)\//.test(p);
    } catch (e) { return false; }
  }
  function sweep(root) {
    var els = (root || document).querySelectorAll('a[href], button, input[type=button], input[type=submit], [onclick]');
    for (var i = 0; i < els.length; i++) {
      var el = els[i];
      var text = (el.innerText || el.value || '').replace(/\s+/g, ' ');
      var click = el.getAttribute('onclick') || '';
      if ((el.href && hiddenPath(el.getAttribute('href'))) || WORDS.test(text) || /print\s*\(/.test(click)) {
        el.classList.add('msh-inapp-hide');
        var li = el.closest('li.menu-item, li.wp-block-navigation-item, .wp-block-button');
        if (li) li.classList.add('msh-inapp-hide');
      }
    }
  }
  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('a[href]');
    if (a && hiddenPath(a.getAttribute('href'))) { e.preventDefault(); location.href = HOME; }
  }, true);
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function () { sweep(); });
  else sweep();
  new MutationObserver(function (ms) {
    for (var i = 0; i < ms.length; i++) for (var j = 0; j < ms[i].addedNodes.length; j++) {
      var n = ms[i].addedNodes[j];
      if (n.nodeType === 1) sweep(n.parentNode || n);
    }
  }).observe(document.documentElement, { childList: true, subtree: true });
})();
</script>
		<?php
	}, 1 );
}
