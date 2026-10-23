/* Association for Industry Professional Nurses: automatic free Hub access.
   Added 23/10/2026. Design decision (Lou, 23/10/2026): free Hub access is
   automatic once someone has confirmed their email with the association, not
   a tick box fulfilled by hand.

   WPCode snippet, type "PHP Snippet", location "Run Everywhere", on
   medsalesintelligencehub.co.uk only. Paste from the line below this comment
   (WPCode adds the opening PHP tag itself).

   Source of truth: hub/wpcode/association-free-hub-access.php in
   louisehoult-beep/msh-compare-data. Edit it there, then paste it here again
   and confirm the stored code by SHA-256.

   HOW IT WORKS (same mechanism as the NHS clinician and care worker routes:
   Process flows for all brands/nhs-clinician-free-access.md "Why no new plan")
   1. A nurse joins on the association landing page. MailerLite double opt-in
      asks them to confirm their address.
   2. MailerLite calls the webhook below (REST, secret key in the URL).
      Only a subscriber who is ACTIVE (confirmed) and who came through the
      association form gets anything.
   3. WordPress emails them a signed link (HMAC of their address plus an
      expiry, 14 days) to the free sign-up page (shortcode
      [msh_assoc_register]).
   4. On that page the link sets a cookie and redirects to the bare URL. While
      the cookie is valid, plan 690 (Hub Member, Annual, the plan every Hub
      page already ticks) costs 0 for that request, but ONLY when the form
      posts plan 690 and the same email the link was sent to. Each link works
      for one registration.
   NO new PMS plan, NO codes. Members carry user meta msh_assoc_member and an
   Association column on the Users screen, so revenue counts can exclude them.
   Renewal: the plan is not recurring. 14 days before it ends a fresh link is
   emailed; opening it while signed in extends the plan by one term. The
   term is never shown to members.

   No secret is stored in this file, only the SHA-256 of the webhook key. The
   key itself lives in the MailerLite webhook URL (?k=...). */

if ( ! defined( 'MSH_ASSOC_PLAN_ID' ) ) {
	define( 'MSH_ASSOC_PLAN_ID', 690 );
	define( 'MSH_ASSOC_GROUP_ID', '202112609174946953' );
	define( 'MSH_ASSOC_PAGE_PATH', '/association-free-hub-access/' );
	define( 'MSH_ASSOC_LINK_DAYS', 14 );
	define( 'MSH_ASSOC_COOKIE', 'msh_assoc' );
	define( 'MSH_ASSOC_HOOK_HASH', '9f2fa14d7cd621b1e7946902ad8898cd40b89f33c0333613b9c7847bda3bd8fe' ); // SHA-256 of the webhook key; the key is only in the MailerLite webhook URL
}

/* ---------- helpers ---------- */

function msh_assoc_b64( $s ) {
	return rtrim( strtr( base64_encode( $s ), '+/', '-_' ), '=' );
}

function msh_assoc_unb64( $s ) {
	return base64_decode( strtr( (string) $s, '-_', '+/' ) );
}

function msh_assoc_sig( $email, $exp ) {
	return hash_hmac( 'sha256', strtolower( $email ) . '|' . (int) $exp, wp_salt( 'auth' ) . 'msh-assoc' );
}

/** A triple (email, expiry, signature) is valid when signed, in date and unused. */
function msh_assoc_valid( $email, $exp, $sig ) {
	$email = strtolower( trim( (string) $email ) );
	if ( ! is_email( $email ) || (int) $exp < time() || ! $sig ) {
		return false;
	}
	if ( ! hash_equals( msh_assoc_sig( $email, $exp ), (string) $sig ) ) {
		return false;
	}
	if ( get_transient( 'msh_assoc_used_' . substr( $sig, 0, 32 ) ) ) {
		return false;
	}
	return true;
}

function msh_assoc_make_link( $email ) {
	$exp = time() + MSH_ASSOC_LINK_DAYS * DAY_IN_SECONDS;
	return add_query_arg(
		array(
			'aie' => msh_assoc_b64( strtolower( $email ) ),
			'aix' => $exp,
			'ais' => msh_assoc_sig( $email, $exp ),
		),
		home_url( MSH_ASSOC_PAGE_PATH )
	);
}

function msh_assoc_mail( $to, $subject, $lines ) {
	$plain = function () { return 'text/plain'; };
	add_filter( 'wp_mail_content_type', $plain );
	$sent = wp_mail( $to, $subject, implode( "\n", $lines ), array( 'Reply-To: louisehoult@elevateandthrive.uk' ) );
	remove_filter( 'wp_mail_content_type', $plain );
	return $sent;
}

/** The cookie triple for THIS request, validated, or false. */
function msh_assoc_cookie() {
	static $c = null;
	if ( $c !== null ) {
		return $c;
	}
	$c = false;
	if ( empty( $_COOKIE[ MSH_ASSOC_COOKIE ] ) ) {
		return $c;
	}
	$parts = explode( '.', sanitize_text_field( wp_unslash( $_COOKIE[ MSH_ASSOC_COOKIE ] ) ) );
	if ( count( $parts ) !== 3 ) {
		return $c;
	}
	$email = strtolower( (string) msh_assoc_unb64( $parts[0] ) );
	if ( msh_assoc_valid( $email, $parts[1], $parts[2] ) ) {
		$c = array( 'email' => $email, 'exp' => (int) $parts[1], 'sig' => $parts[2] );
	}
	return $c;
}

/* ---------- 1. MailerLite webhook ---------- */

add_action( 'rest_api_init', function () {
	register_rest_route( 'msh-assoc/v1', '/ml', array(
		'methods'             => 'POST',
		'permission_callback' => '__return_true',
		'callback'            => 'msh_assoc_webhook',
	) );
} );

function msh_assoc_find_subscribers( $node, &$out ) {
	if ( ! is_array( $node ) ) {
		return;
	}
	if ( isset( $node['email'] ) && is_string( $node['email'] ) && isset( $node['status'] ) ) {
		$out[] = $node;
	}
	foreach ( $node as $child ) {
		msh_assoc_find_subscribers( $child, $out );
	}
}

function msh_assoc_webhook( WP_REST_Request $req ) {

	$given = (string) $req->get_param( 'k' );
	if ( ! hash_equals( MSH_ASSOC_HOOK_HASH, hash( 'sha256', $given ) ) ) {
		return new WP_REST_Response( array( 'ok' => false ), 403 );
	}

	$raw  = $req->get_body();
	$json = json_decode( $raw, true );
	if ( ! is_array( $json ) ) {
		return new WP_REST_Response( array( 'ok' => false ), 400 );
	}

	// Keep the last few payload shapes (no personal data) so the format can be checked.
	$log   = get_option( 'msh_assoc_hook_log', array() );
	$log[] = gmdate( 'c' ) . ' ' . substr( preg_replace( '/[\w.+-]+@[\w.-]+/', '[email]', $raw ), 0, 1200 );
	update_option( 'msh_assoc_hook_log', array_slice( $log, -5 ), false );

	$from_assoc = strpos( $raw, MSH_ASSOC_GROUP_ID ) !== false || stripos( $raw, 'signup_source' ) !== false;
	if ( ! $from_assoc ) {
		return new WP_REST_Response( array( 'ok' => true, 'skipped' => 'other group' ), 200 );
	}

	$subs = array();
	msh_assoc_find_subscribers( $json, $subs );
	$sent = 0;

	foreach ( $subs as $s ) {
		if ( strtolower( (string) $s['status'] ) !== 'active' ) {
			continue; // unconfirmed: no link until the address is confirmed
		}
		$email = strtolower( trim( $s['email'] ) );
		if ( ! is_email( $email ) ) {
			continue;
		}
		$flag = 'msh_assoc_sent_' . md5( $email );
		if ( get_transient( $flag ) ) {
			continue;
		}
		set_transient( $flag, 1, DAY_IN_SECONDS );

		if ( get_user_by( 'email', $email ) ) {
			msh_assoc_mail( $email, 'Your Association for Industry Professional Nurses membership', array(
				'Thank you for confirming your address.',
				'',
				'You already have an account on the Medical Sales Intelligence Hub with this email address, so there is nothing more to set up. Sign in here:',
				home_url( '/login/' ),
				'',
				'If something does not work, reply to this email.',
				'',
				'Elevate and Thrive Ltd',
			) );
			$sent++;
			continue;
		}

		msh_assoc_mail( $email, 'Your free Medical Sales Hub access', array(
			'Thank you for confirming your address and joining the Association for Industry Professional Nurses.',
			'',
			'Your free access to the Medical Sales Hub is ready. Use this link to set up your account:',
			'',
			msh_assoc_make_link( $email ),
			'',
			'The link is for you only and works once. Please register with this same email address.',
			'If you cannot see this email later, check your junk folder. If the link will not open, reply to this email and we will help.',
			'',
			'Elevate and Thrive Ltd',
		) );
		$sent++;
	}

	return new WP_REST_Response( array( 'ok' => true, 'sent' => $sent ), 200 );
}

/* ---------- 2. The sign-up page: link -> cookie -> bare URL ---------- */

add_action( 'template_redirect', function () {

	// The page differs per visitor (cookie), so it must never sit in the edge cache.
	$path = isset( $_SERVER['REQUEST_URI'] ) ? wp_parse_url( wp_unslash( $_SERVER['REQUEST_URI'] ), PHP_URL_PATH ) : '';
	if ( rtrim( (string) $path, '/' ) === rtrim( MSH_ASSOC_PAGE_PATH, '/' ) ) {
		if ( ! defined( 'DONOTCACHEPAGE' ) ) {
			define( 'DONOTCACHEPAGE', true );
		}
		nocache_headers();
	}

	if ( empty( $_GET['aie'] ) || empty( $_GET['aix'] ) || empty( $_GET['ais'] ) ) {
		return;
	}
	$email = strtolower( (string) msh_assoc_unb64( sanitize_text_field( wp_unslash( $_GET['aie'] ) ) ) );
	$exp   = (int) $_GET['aix'];
	$sig   = sanitize_text_field( wp_unslash( $_GET['ais'] ) );

	$target = home_url( MSH_ASSOC_PAGE_PATH );

	if ( ! msh_assoc_valid( $email, $exp, $sig ) ) {
		wp_safe_redirect( add_query_arg( 'ai', 'invalid', $target ) );
		exit;
	}

	setcookie(
		MSH_ASSOC_COOKIE,
		msh_assoc_b64( $email ) . '.' . $exp . '.' . $sig,
		array(
			'expires'  => $exp,
			'path'     => '/',
			'secure'   => true,
			'httponly' => true,
			'samesite' => 'Lax',
		)
	);
	wp_safe_redirect( $target );
	exit;
}, 1 );

add_shortcode( 'msh_assoc_register', function () {

	$GLOBALS['msh_assoc_page'] = true;
	$c = msh_assoc_cookie();

	if ( ! $c ) {
		return '<div class="msh-assoc-note"><p><strong>This link has already been used or has expired.</strong></p>'
			. '<p>Join the association on <a href="' . esc_url( home_url( '/association-for-industry-professional-nurses/' ) ) . '">its sign-up page</a> and we will email you a new link once you have confirmed your address. If you think this is a mistake, email <a href="mailto:louisehoult@elevateandthrive.uk">louisehoult@elevateandthrive.uk</a>.</p></div>';
	}

	// Signed in already: this is a renewal (reminder link), not a new account.
	if ( is_user_logged_in() ) {
		$user = wp_get_current_user();
		if ( strtolower( $user->user_email ) !== $c['email'] || ! get_user_meta( $user->ID, 'msh_assoc_member', true ) ) {
			return '<div class="msh-assoc-note"><p>You are already signed in to the Hub. Nothing more is needed.</p></div>';
		}
		return '<div class="msh-assoc-note"><h2>Keep your free Hub access</h2><form method="post" action="' . esc_url( admin_url( 'admin-post.php' ) ) . '">'
			. '<input type="hidden" name="action" value="msh_assoc_renew">' . wp_nonce_field( 'msh_assoc_renew', '_wpnonce', true, false )
			. '<p>Confirm you are still a member of the Association for Industry Professional Nurses.</p><button type="submit" class="msh-assoc-btn">Keep my free access</button></form></div>';
	}

	$email = esc_attr( $c['email'] );
	$form  = do_shortcode( '[pms-register subscription_plans="' . (int) MSH_ASSOC_PLAN_ID . '" selected="' . (int) MSH_ASSOC_PLAN_ID . '"]' );

	return '<div class="msh-assoc-form">' . $form . '</div>'
		. '<script>(function(){var e=document.querySelector(".msh-assoc-form input[name=user_email]");if(e&&!e.value){e.value="' . $email . '";}})();</script>';
} );

/* ---------- 3. Plan 690 at 0, only for a valid link on a matching sign-up ---------- */

function msh_assoc_request_ok() {

	static $ok = null;
	if ( $ok !== null ) {
		return $ok;
	}
	$ok = false;

	if ( is_admin() && ! wp_doing_ajax() ) {
		return $ok;
	}
	if ( defined( 'DOING_CRON' ) && DOING_CRON ) {
		return $ok;
	}
	$c = msh_assoc_cookie();
	if ( ! $c ) {
		return $ok;
	}

	if ( isset( $_SERVER['REQUEST_METHOD'] ) && $_SERVER['REQUEST_METHOD'] === 'POST' ) {
		$plans = isset( $_POST['subscription_plans'] ) ? wp_unslash( $_POST['subscription_plans'] ) : '';
		$plans = is_array( $plans ) ? array_map( 'absint', $plans ) : array( absint( $plans ) );
		if ( ! in_array( (int) MSH_ASSOC_PLAN_ID, $plans, true ) ) {
			return $ok;
		}
		$posted = isset( $_POST['user_email'] ) ? strtolower( sanitize_email( wp_unslash( $_POST['user_email'] ) ) ) : '';
		if ( ! is_user_logged_in() && $posted !== $c['email'] ) {
			return $ok;
		}
		$ok = $c;
		return $ok;
	}

	// Display only, and only on the association page itself.
	if ( ! empty( $GLOBALS['msh_assoc_page'] ) ) {
		$ok = $c;
	}
	return $ok;
}

add_filter( 'pms_get_subscription_plan', function ( $plan ) {
	if ( ! is_object( $plan ) || ! isset( $plan->id ) || (int) $plan->id !== (int) MSH_ASSOC_PLAN_ID ) {
		return $plan;
	}
	if ( ! msh_assoc_request_ok() ) {
		return $plan;
	}
	$plan->price = 0;
	if ( isset( $plan->sign_up_fee ) ) {
		$plan->sign_up_fee = 0;
	}
	return $plan;
}, 10, 2 );

add_action( 'pms_register_form_validation', function () {
	if ( empty( $_COOKIE[ MSH_ASSOC_COOKIE ] ) || empty( $_POST['subscription_plans'] ) ) {
		return;
	}
	$c = msh_assoc_cookie();
	if ( ! $c ) {
		return; // an ordinary registration; the cookie is stale
	}
	$posted = isset( $_POST['user_email'] ) ? strtolower( sanitize_email( wp_unslash( $_POST['user_email'] ) ) ) : '';
	if ( $posted !== $c['email'] ) {
		pms_errors()->add( 'msh_assoc_email', 'Please register with the same email address we sent your link to.' );
	}
} );

add_action( 'pms_register_form_after_create_user', function ( $user_data ) {
	$user_id = isset( $user_data['user_id'] ) ? (int) $user_data['user_id'] : 0;
	$c       = msh_assoc_request_ok();
	if ( ! $user_id || ! $c ) {
		return;
	}
	update_user_meta( $user_id, 'msh_assoc_member', 1 );
	update_user_meta( $user_id, 'msh_assoc_joined', current_time( 'mysql' ) );
	set_transient( 'msh_assoc_used_' . substr( $c['sig'], 0, 32 ), 1, 30 * DAY_IN_SECONDS ); // one registration per link
} );

/* ---------- 4. Renewal ---------- */

add_action( 'admin_post_msh_assoc_renew', function () {

	$back = home_url( MSH_ASSOC_PAGE_PATH );
	if ( ! is_user_logged_in() || ! wp_verify_nonce( isset( $_POST['_wpnonce'] ) ? $_POST['_wpnonce'] : '', 'msh_assoc_renew' ) ) {
		wp_safe_redirect( $back );
		exit;
	}
	$c    = msh_assoc_cookie();
	$user = wp_get_current_user();
	if ( ! $c || strtolower( $user->user_email ) !== $c['email'] || ! get_user_meta( $user->ID, 'msh_assoc_member', true ) ) {
		wp_safe_redirect( $back );
		exit;
	}
	$subs = function_exists( 'pms_get_member_subscriptions' )
		? pms_get_member_subscriptions( array( 'user_id' => $user->ID, 'subscription_plan_id' => (int) MSH_ASSOC_PLAN_ID ) )
		: array();
	if ( $subs ) {
		$sub  = $subs[0];
		$base = max( time(), strtotime( $sub->expiration_date ) );
		$sub->update( array(
			'status'          => 'active',
			'expiration_date' => gmdate( 'Y-m-d 00:00:00', strtotime( '+1 year', $base ) ),
		) );
		set_transient( 'msh_assoc_used_' . substr( $c['sig'], 0, 32 ), 1, 30 * DAY_IN_SECONDS );
	}
	wp_safe_redirect( home_url( '/account/' ) );
	exit;
} );

add_action( 'init', function () {
	if ( ! wp_next_scheduled( 'msh_assoc_reminder_sweep' ) ) {
		wp_schedule_event( time() + 3 * HOUR_IN_SECONDS, 'daily', 'msh_assoc_reminder_sweep' );
	}
} );

add_action( 'msh_assoc_reminder_sweep', function () {
	if ( ! function_exists( 'pms_get_member_subscriptions' ) ) {
		return;
	}
	$subs = pms_get_member_subscriptions( array(
		'subscription_plan_id'   => (int) MSH_ASSOC_PLAN_ID,
		'status'                 => 'active',
		'expiration_date_before' => gmdate( 'Y-m-d', strtotime( '+14 days' ) ),
	) );
	foreach ( (array) $subs as $sub ) {
		$uid = (int) $sub->user_id;
		if ( ! get_user_meta( $uid, 'msh_assoc_member', true ) ) {
			continue; // paying members, NHS clinicians and care workers are on 690 too
		}
		$last = get_user_meta( $uid, 'msh_assoc_reminded_on', true );
		if ( $last && strtotime( $last ) > strtotime( '-14 days' ) ) {
			continue;
		}
		$user = get_userdata( $uid );
		if ( ! $user ) {
			continue;
		}
		msh_assoc_mail( $user->user_email, 'Keep your free Medical Sales Hub access', array(
			'Your free Hub access through the Association for Industry Professional Nurses is due to be renewed.',
			'',
			'Open this link and confirm you are still a member:',
			'',
			msh_assoc_make_link( $user->user_email ),
			'',
			'If you no longer want it, you do not need to do anything.',
			'',
			'Elevate and Thrive Ltd',
		) );
		update_user_meta( $uid, 'msh_assoc_reminded_on', current_time( 'mysql' ) );
	}
} );

/* ---------- 5. Users screen column ---------- */

add_filter( 'manage_users_columns', function ( $cols ) {
	$cols['msh_assoc'] = 'Association';
	return $cols;
} );

add_filter( 'manage_users_custom_column', function ( $val, $col, $user_id ) {
	if ( $col === 'msh_assoc' ) {
		return get_user_meta( $user_id, 'msh_assoc_member', true ) ? 'Free (association)' : '';
	}
	return $val;
}, 10, 3 );
