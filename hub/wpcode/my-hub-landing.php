/* My Hub landing: a returning Hub member who opens the Live Desk from outside
   the Hub lands on My Hub instead, at most once a day.
   WPCode snippet, type "PHP Snippet", location "Run Everywhere", on
   medsalesintelligencehub.co.uk only. Paste from the line below this comment
   (WPCode adds the opening PHP tag itself).

   Source of truth: hub/wpcode/my-hub-landing.php in louisehoult-beep/msh-compare-data.
   The decision is the pure function msh_myhub_landing_decide(), tested by
   test_my_hub_landing.py; edit both together.

   Lou, 01/10/2026 (option A): logins already go to Choose your profile, but
   sessions last 30 days, so returning members arrive on /medical-sales-hub/
   (the Live Desk, page 675) from bookmarks and emails. Rule:
     * a logged-in member on one of the Hub plans listed in snippet 3902,
     * requesting page 675 with a GET,
     * with no Hub address as the referrer (bookmark, email, new tab),
     * who has not already been sent today (cookie msh_myhub_day),
   gets a 302 to /medical-sales-hub/my-hub/. A Live Desk link clicked inside
   the Hub carries a Hub referrer and still opens the Live Desk.
   Escape hatch: /medical-sales-hub/?desk=1 always opens the Live Desk.

   Must stay a 302 with nocache_headers(): the answer depends on who is asking
   (the same reason snippet 3902 is a 302). Never "tidy" it to a 301.
   Fires only on page 675, only for logged-in users, never for admin, AJAX,
   REST, cron, feeds or browser prefetches. The PMS plan check runs last, so
   a request that is going nowhere costs nothing. To undo: deactivate. */

if ( ! function_exists( 'msh_myhub_landing_decide' ) ) {
	/* $r: is_live_desk, method, skip_context, prefetch, logged_in, escape,
	   referer, hub_hosts (list), cookie_day, today (Y-m-d), member (bool or a
	   callable returning bool, called only when everything else says go).
	   Returns array( bool go, string why ). */
	function msh_myhub_landing_decide( $r ) {
		if ( empty( $r['is_live_desk'] ) ) {
			return array( false, 'not-live-desk' );
		}
		if ( ! isset( $r['method'] ) || 'GET' !== $r['method'] ) {
			return array( false, 'not-get' );
		}
		if ( ! empty( $r['skip_context'] ) ) {
			return array( false, 'admin-ajax-rest-cron-feed' );
		}
		if ( ! empty( $r['prefetch'] ) ) {
			return array( false, 'prefetch' );
		}
		if ( empty( $r['logged_in'] ) ) {
			return array( false, 'logged-out' );
		}
		if ( ! empty( $r['escape'] ) ) {
			return array( false, 'escape-param' );
		}
		$host = strtolower( (string) parse_url( isset( $r['referer'] ) ? (string) $r['referer'] : '', PHP_URL_HOST ) );
		if ( '' !== $host && in_array( $host, (array) $r['hub_hosts'], true ) ) {
			return array( false, 'came-from-hub' );
		}
		if ( isset( $r['cookie_day'], $r['today'] ) && '' !== (string) $r['today'] && (string) $r['cookie_day'] === (string) $r['today'] ) {
			return array( false, 'already-today' );
		}
		$member = isset( $r['member'] ) ? $r['member'] : false;
		if ( is_callable( $member ) ) {
			$member = call_user_func( $member );
		}
		if ( true !== $member ) {
			return array( false, 'not-member' );
		}
		return array( true, 'send-to-my-hub' );
	}
}

if ( ! function_exists( 'msh_myhub_is_hub_member' ) ) {
	/* The same test as snippet 3902: an active subscription, or a cancelled
	   one paid up to a future date, on one of the Hub plans. PMS returns
	   objects on this install, not arrays; read both. */
	function msh_myhub_is_hub_member( $user_id ) {
		if ( ! function_exists( 'pms_get_member_subscriptions' ) ) {
			return false;
		}
		/* Identical to snippet 3902 (hub-subscriber-home-redirect.php). 954 (Hub
		   Trial) is withdrawn and gone; kept only so the two lists stay the same.
		   Hub Employer 5167 is deliberately not here, as in 3902. */
		$hub_plans = array( 690, 691, 692, 694, 930, 954 );
		$subs      = pms_get_member_subscriptions( array( 'user_id' => $user_id ) );
		if ( ! is_array( $subs ) ) {
			return false;
		}
		foreach ( $subs as $sub ) {
			if ( is_object( $sub ) ) {
				$plan_id = isset( $sub->subscription_plan_id ) ? (int) $sub->subscription_plan_id : 0;
				$status  = isset( $sub->status ) ? (string) $sub->status : '';
				$expires = isset( $sub->expiration_date ) ? (string) $sub->expiration_date : '';
			} elseif ( is_array( $sub ) ) {
				$plan_id = isset( $sub['subscription_plan_id'] ) ? (int) $sub['subscription_plan_id'] : 0;
				$status  = isset( $sub['status'] ) ? (string) $sub['status'] : '';
				$expires = isset( $sub['expiration_date'] ) ? (string) $sub['expiration_date'] : '';
			} else {
				continue;
			}
			if ( ! in_array( $plan_id, $hub_plans, true ) ) {
				continue;
			}
			if ( 'active' === $status ) {
				return true;
			}
			if ( in_array( $status, array( 'canceled', 'cancelled' ), true ) ) {
				if ( '' === $expires || '0000-00-00' === substr( $expires, 0, 10 ) || strtotime( $expires ) > current_time( 'timestamp' ) ) {
					return true;
				}
			}
		}
		return false;
	}
}

add_action( 'template_redirect', function () {
	$purpose = '';
	if ( isset( $_SERVER['HTTP_SEC_PURPOSE'] ) ) {
		$purpose .= (string) $_SERVER['HTTP_SEC_PURPOSE'];
	}
	if ( isset( $_SERVER['HTTP_PURPOSE'] ) ) {
		$purpose .= (string) $_SERVER['HTTP_PURPOSE'];
	}
	$req = array(
		'is_live_desk' => is_page( 675 ),
		'method'       => isset( $_SERVER['REQUEST_METHOD'] ) ? strtoupper( (string) $_SERVER['REQUEST_METHOD'] ) : '',
		'skip_context' => is_admin() || wp_doing_ajax() || wp_doing_cron() || is_feed() || ( defined( 'REST_REQUEST' ) && REST_REQUEST ),
		'prefetch'     => false !== stripos( $purpose, 'prefetch' ),
		'logged_in'    => is_user_logged_in(),
		'escape'       => isset( $_GET['desk'] ),
		'referer'      => isset( $_SERVER['HTTP_REFERER'] ) ? (string) $_SERVER['HTTP_REFERER'] : '',
		'hub_hosts'    => array( 'medsalesintelligencehub.co.uk', 'www.medsalesintelligencehub.co.uk' ),
		'cookie_day'   => isset( $_COOKIE['msh_myhub_day'] ) ? (string) $_COOKIE['msh_myhub_day'] : '',
		'today'        => wp_date( 'Y-m-d' ),
		'member'       => function () { return msh_myhub_is_hub_member( get_current_user_id() ); },
	);
	$d = msh_myhub_landing_decide( $req );
	if ( ! $d[0] ) {
		return;
	}
	setcookie( 'msh_myhub_day', $req['today'], array(
		'expires'  => time() + 2 * DAY_IN_SECONDS,
		'path'     => '/',
		'secure'   => true,
		'httponly' => true,
		'samesite' => 'Lax',
	) );
	nocache_headers();
	wp_safe_redirect( home_url( '/medical-sales-hub/my-hub/' ), 302 );
	exit;
}, 2 );
