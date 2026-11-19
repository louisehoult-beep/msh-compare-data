<?php
/* Colleague Day Pass (Lou, 02/11/2026: "Yes, build it").

   A paying Hub member gets a personal code (HUB-NAME-XXXX) and shares it, or
   the link /colleague-pass/?code=XXXX, with a colleague. The colleague registers
   on the Hub page "Colleague Day Pass" (shortcode [msh_colleague_pass]) with
   that code and gets the full Hub free until the end of the following day
   (UK time). When it ends they are gated again and see the join link.

   HOW IT GRANTS ACCESS (the load-bearing decision)
   No new Paid Member Subscriptions (PMS) plan. Hub pages name their permitted
   plans one by one, so a new plan would grant access to nothing (see
   Process flows for all brands/nhs-clinician-free-access.md, "Why no new plan").
   The pass grants the EXISTING plan 690 "Hub Member — Annual" at £0 for one
   validated request, exactly as the NHS clinician route (snippet 4310) does,
   then sets that subscription's expiration_date to the end of tomorrow.

   Limits: 3 redemptions per code per calendar month; one pass per colleague
   email address ever; the colleague must not already have an account; a code
   stops working when its owner's membership is no longer active. Codes belong
   to members with an active subscription on plan 690, 691, 692 or 694 who are
   not NHS free-access clinicians and not pass holders themselves.

   Never call this a trial. The one-week trial (plan 954) was withdrawn on
   23/09/2026. This is one day, by a member's invitation only.

   CAPTURE (Lou, 04/11/2026): every redeemed pass is added to the MailerLite
   group MSH_CPASS_ML_GROUP for follow-up, and Lou's notification email
   carries the lines for the CRM. A MailerLite failure never blocks the pass;
   the email says NOT ADDED so it can be added by hand.

   Process: 02-Elevate-and-Thrive/Process flows for all brands/hub-colleague-day-pass.md */

if ( ! defined( 'MSH_CPASS_PLAN_ID' ) ) {
	define( 'MSH_CPASS_PLAN_ID', 690 ); // Hub Member — Annual: the plan every Hub page already permits
}
if ( ! defined( 'MSH_CPASS_PAGE_SLUG' ) ) {
	define( 'MSH_CPASS_PAGE_SLUG', 'colleague-pass' );
}
if ( ! defined( 'MSH_CPASS_USES_PER_MONTH' ) ) {
	define( 'MSH_CPASS_USES_PER_MONTH', 3 );
}
if ( ! defined( 'MSH_CPASS_ATTEMPTS_PER_HOUR' ) ) {
	define( 'MSH_CPASS_ATTEMPTS_PER_HOUR', 5 );
}
if ( ! defined( 'MSH_CPASS_JOIN_URL' ) ) {
	define( 'MSH_CPASS_JOIN_URL', 'https://medsalesintelligencehub.co.uk/join-the-hub/' );
}
if ( ! defined( 'MSH_CPASS_FROM' ) ) {
	define( 'MSH_CPASS_FROM', 'louisehoult@elevateandthrive.uk' );
}
/* Lou's own code, fixed so it can go in an email before she has opened the
   page (Lou, 04/11/2026). It resolves to the administrator whose email is
   MSH_CPASS_FROM, or else the first administrator. Admin codes have no cap. */
if ( ! defined( 'MSH_CPASS_ADMIN_CODE' ) ) {
	define( 'MSH_CPASS_ADMIN_CODE', 'HUB-LOUISE-TEGU' );
}
/* Every redeemed pass goes into this MailerLite group for follow-up
   (Lou, 04/11/2026: "capture the email for CRM and follow up in MailerLite").
   Group "Hub - Colleague Day Pass (auto from WordPress)", made 04/11/2026.
   Uses the key the MailerLite WooCommerce plugin already holds, as the
   Medical Sales Register snippet does. No key is stored here. */
if ( ! defined( 'MSH_CPASS_ML_GROUP' ) ) {
	define( 'MSH_CPASS_ML_GROUP', '203233407060149528' );
}
/* Plans whose active members may hold a code. 690 annual, 691 monthly, 692 programme member, 694 Clinical Interview Playbook. */
if ( ! defined( 'MSH_CPASS_REFERRER_PLANS' ) ) {
	define( 'MSH_CPASS_REFERRER_PLANS', '690,691,692,694' );
}
/* Code alphabet: no 0, O, 1 or I, so a code read out loud or copied by hand cannot be misread. */
if ( ! defined( 'MSH_CPASS_ALPHABET' ) ) {
	define( 'MSH_CPASS_ALPHABET', 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789' );
}

// -----------------------------------------------------------------------------
// Small helpers
// -----------------------------------------------------------------------------

function msh_cpass_normalise_code( $code ) {
	$code = strtoupper( trim( (string) $code ) );
	$code = preg_replace( '/[^A-Z0-9-]/', '', $code );
	return $code;
}

function msh_cpass_code_valid_format( $code ) {
	return (bool) preg_match( '/^HUB-[A-Z]{2,10}-[' . MSH_CPASS_ALPHABET . ']{4}$/', $code );
}

function msh_cpass_random_suffix() {
	$alphabet = MSH_CPASS_ALPHABET;
	$out      = '';
	$max      = strlen( $alphabet ) - 1;
	for ( $i = 0; $i < 4; $i++ ) {
		$out .= $alphabet[ wp_rand( 0, $max ) ];
	}
	return $out;
}

function msh_cpass_name_part( $user ) {
	$first = '';
	if ( is_object( $user ) ) {
		$first = $user->first_name ? $user->first_name : $user->display_name;
	}
	$first = strtoupper( preg_replace( '/[^A-Za-z]/', '', remove_accents( (string) $first ) ) );
	if ( strlen( $first ) < 2 ) {
		$first = 'HUB';
	}
	return substr( $first, 0, 10 );
}

function msh_cpass_email_hash( $email ) {
	return hash( 'sha256', 'msh_cpass|' . strtolower( trim( (string) $email ) ) );
}

function msh_cpass_client_ip() {
	$ip = isset( $_SERVER['REMOTE_ADDR'] ) ? sanitize_text_field( wp_unslash( $_SERVER['REMOTE_ADDR'] ) ) : '';
	return $ip ? $ip : 'unknown';
}

function msh_cpass_month_key( $ts = null ) {
	return wp_date( 'Y-m', $ts ? $ts : current_time( 'timestamp' ) );
}

/** End of tomorrow, site time (UK), as a mysql datetime. */
function msh_cpass_expiry_from( $ts = null ) {
	$ts  = $ts ? $ts : current_time( 'timestamp' );
	$day = wp_date( 'Y-m-d', $ts + DAY_IN_SECONDS );
	return $day . ' 23:59:59';
}

function msh_cpass_mail( $to, $subject, $body ) {
	$headers = array(
		'Content-Type: text/plain; charset=UTF-8',
		'From: Louise Hoult <' . MSH_CPASS_FROM . '>',
		'Reply-To: Louise Hoult <' . MSH_CPASS_FROM . '>',
	);
	return wp_mail( $to, $subject, $body, $headers );
}

// -----------------------------------------------------------------------------
// Who may hold a code, who holds a pass
// -----------------------------------------------------------------------------

function msh_cpass_referrer_plans() {
	return array_map( 'absint', explode( ',', MSH_CPASS_REFERRER_PLANS ) );
}

/** Site administrators (Lou) hold a code too, so she can give a prospect a day herself; no monthly cap for them. */
function msh_cpass_is_admin_referrer( $user_id ) {
	return (bool) ( $user_id && function_exists( 'user_can' ) && user_can( (int) $user_id, 'manage_options' ) );
}

/** Active, paid-for membership: a subscription on one of the referrer plans with status active. Or an administrator. */
function msh_cpass_is_eligible_referrer( $user_id ) {
	$user_id = (int) $user_id;
	if ( ! $user_id ) {
		return false;
	}
	if ( msh_cpass_is_admin_referrer( $user_id ) ) {
		return true;
	}
	if ( ! function_exists( 'pms_get_member_subscriptions' ) ) {
		return false;
	}
	if ( get_user_meta( $user_id, 'msh_nhs_email', true ) ) {
		return false; // NHS free access: not a paying member
	}
	if ( get_user_meta( $user_id, 'msh_cpass_from', true ) ) {
		return false; // a pass holder cannot pass it on
	}
	$plans = msh_cpass_referrer_plans();
	foreach ( (array) pms_get_member_subscriptions( array( 'user_id' => $user_id ) ) as $sub ) {
		if ( isset( $sub->status, $sub->subscription_plan_id ) && $sub->status === 'active'
			&& in_array( (int) $sub->subscription_plan_id, $plans, true ) ) {
			return true;
		}
	}
	return false;
}

function msh_cpass_is_pass_holder( $user_id ) {
	return (bool) get_user_meta( (int) $user_id, 'msh_cpass_from', true );
}

function msh_cpass_find_user_by_code( $code ) {
	$code = msh_cpass_normalise_code( $code );
	if ( ! msh_cpass_code_valid_format( $code ) ) {
		return 0;
	}
	$users = get_users( array(
		'meta_key'   => 'msh_cpass_code',
		'meta_value' => $code,
		'number'     => 1,
		'fields'     => 'ID',
	) );
	if ( $users ) {
		return (int) $users[0];
	}
	if ( MSH_CPASS_ADMIN_CODE && $code === MSH_CPASS_ADMIN_CODE ) {
		return msh_cpass_admin_user_id();
	}
	return 0;
}

/** The administrator who owns MSH_CPASS_ADMIN_CODE: the one whose email is MSH_CPASS_FROM, else the first administrator. */
function msh_cpass_admin_user_id() {
	$u = function_exists( 'get_user_by' ) ? get_user_by( 'email', MSH_CPASS_FROM ) : false;
	if ( $u && msh_cpass_is_admin_referrer( $u->ID ) ) {
		return (int) $u->ID;
	}
	$admins = get_users( array( 'role' => 'administrator', 'number' => 1, 'orderby' => 'ID', 'order' => 'ASC', 'fields' => 'ID' ) );
	return $admins ? (int) $admins[0] : 0;
}

/** The member's code, made on first request. A code is never changed once given. */
function msh_cpass_code_for( $user_id ) {
	$user_id = (int) $user_id;
	if ( MSH_CPASS_ADMIN_CODE && $user_id && $user_id === msh_cpass_admin_user_id() ) {
		return MSH_CPASS_ADMIN_CODE;
	}
	$code    = get_user_meta( $user_id, 'msh_cpass_code', true );
	if ( $code ) {
		return $code;
	}
	$user = get_userdata( $user_id );
	$name = msh_cpass_name_part( $user );
	for ( $i = 0; $i < 20; $i++ ) {
		$try = 'HUB-' . $name . '-' . msh_cpass_random_suffix();
		if ( ! msh_cpass_find_user_by_code( $try ) ) {
			update_user_meta( $user_id, 'msh_cpass_code', $try );
			update_user_meta( $user_id, 'msh_cpass_code_made', current_time( 'mysql' ) );
			return $try;
		}
	}
	return '';
}

function msh_cpass_uses( $user_id ) {
	$uses = get_user_meta( (int) $user_id, 'msh_cpass_uses', true );
	return is_array( $uses ) ? $uses : array();
}

function msh_cpass_uses_this_month( $user_id, $month = null ) {
	$month = $month ? $month : msh_cpass_month_key();
	$n     = 0;
	foreach ( msh_cpass_uses( $user_id ) as $u ) {
		if ( isset( $u['month'] ) && $u['month'] === $month ) {
			$n++;
		}
	}
	return $n;
}

function msh_cpass_email_already_used( $email ) {
	$used = get_option( 'msh_cpass_redeemed', array() );
	return is_array( $used ) && isset( $used[ msh_cpass_email_hash( $email ) ] );
}

/**
 * Check a code against a colleague's address. Returns array('ok'=>true,'referrer'=>id)
 * or array('ok'=>false,'message'=>plain English reason).
 */
function msh_cpass_check( $code, $email, $own_user_id = 0 ) {
	$code  = msh_cpass_normalise_code( $code );
	$email = strtolower( trim( sanitize_email( (string) $email ) ) );

	if ( $code === '' ) {
		return array( 'ok' => false, 'message' => 'Please enter the colleague code you were given.' );
	}
	if ( ! msh_cpass_code_valid_format( $code ) ) {
		return array( 'ok' => false, 'message' => 'That code is not in the right form. It looks like HUB-NAME-XXXX.' );
	}
	$referrer = msh_cpass_find_user_by_code( $code );
	if ( ! $referrer ) {
		return array( 'ok' => false, 'message' => 'We do not recognise that code. Check it with the colleague who shared it.' );
	}
	if ( ! msh_cpass_is_eligible_referrer( $referrer ) ) {
		return array( 'ok' => false, 'message' => 'That code is no longer active. Ask your colleague for a current one, or join the Hub directly.' );
	}
	if ( ! msh_cpass_is_admin_referrer( $referrer ) && msh_cpass_uses_this_month( $referrer ) >= MSH_CPASS_USES_PER_MONTH ) {
		return array( 'ok' => false, 'message' => 'That code has been used the most times it can this month. Ask your colleague again next month, or join the Hub directly.' );
	}
	if ( $email === '' || ! is_email( $email ) ) {
		return array( 'ok' => false, 'message' => 'Please enter the email address you will log in with.' );
	}
	if ( msh_cpass_email_already_used( $email ) ) {
		return array( 'ok' => false, 'message' => 'This email address has already had a colleague day. You are welcome to join the Hub directly.' );
	}
	$existing = email_exists( $email );
	if ( $existing && (int) $existing !== (int) $own_user_id ) {
		return array( 'ok' => false, 'message' => 'There is already a Hub account for this email address. Please log in instead.' );
	}
	return array( 'ok' => true, 'referrer' => $referrer );
}

// -----------------------------------------------------------------------------
// The registration request: was a valid code submitted with this POST?
// -----------------------------------------------------------------------------

function msh_cpass_plan_submitted() {
	$plans = isset( $_POST['subscription_plans'] ) ? wp_unslash( $_POST['subscription_plans'] ) : '';
	$plans = is_array( $plans ) ? array_map( 'absint', $plans ) : array( absint( $plans ) );
	return in_array( (int) MSH_CPASS_PLAN_ID, $plans, true );
}

/**
 * Memoised per request. False, or array('referrer'=>id,'code'=>code,'email'=>email).
 * $own_user_id: after the account exists, re-check allowing that account's own address.
 */
function msh_cpass_request( $own_user_id = 0 ) {
	static $cached = null;
	if ( $cached !== null && ( $cached || ! $own_user_id ) ) {
		return $cached;
	}
	$cached = false;
	if ( ( is_admin() && ! wp_doing_ajax() ) || ( defined( 'DOING_CRON' ) && DOING_CRON ) ) {
		return $cached;
	}
	if ( empty( $_POST['msh_cpass_choice'] ) || empty( $_POST['msh_cpass_code'] ) ) {
		return $cached;
	}
	if ( ! empty( $_POST['msh_cpass_website'] ) ) {
		return $cached; // honeypot
	}
	if ( ! msh_cpass_plan_submitted() ) {
		return $cached;
	}
	$code  = msh_cpass_normalise_code( wp_unslash( $_POST['msh_cpass_code'] ) );
	$email = isset( $_POST['user_email'] ) ? strtolower( trim( sanitize_email( wp_unslash( $_POST['user_email'] ) ) ) ) : '';
	$check = msh_cpass_check( $code, $email, $own_user_id );
	if ( empty( $check['ok'] ) ) {
		return $cached;
	}
	$cached = array( 'referrer' => (int) $check['referrer'], 'code' => $code, 'email' => $email );
	return $cached;
}

/** Plan 690 costs nothing for a request carrying a valid code. */
add_filter( 'pms_get_subscription_plan', 'msh_cpass_filter_plan_price', 11, 2 );

function msh_cpass_filter_plan_price( $plan, $id_or_post ) {
	if ( ! is_object( $plan ) || ! isset( $plan->id ) || (int) $plan->id !== (int) MSH_CPASS_PLAN_ID ) {
		return $plan;
	}
	if ( ! msh_cpass_request() ) {
		return $plan;
	}
	$plan->price = 0;
	if ( isset( $plan->sign_up_fee ) ) {
		$plan->sign_up_fee = 0;
	}
	return $plan;
}

/**
 * The invoicing add-on requires billing name, email, address, city and country even
 * when the plan costs nothing, and prints its errors inside fields the pass page hides.
 * For a valid pass request fill them from the account fields before PMS validates.
 * (This is also why no registration through the NHS free route was ever completed.)
 */
add_action( 'pms_register_form_validation', 'msh_cpass_fill_billing', 1 );

function msh_cpass_fill_billing() {
	if ( empty( $_POST['msh_cpass_choice'] ) || ! msh_cpass_request() ) {
		return;
	}
	$first = isset( $_POST['first_name'] ) ? sanitize_text_field( wp_unslash( $_POST['first_name'] ) ) : '';
	$last  = isset( $_POST['last_name'] ) ? sanitize_text_field( wp_unslash( $_POST['last_name'] ) ) : '';
	$email = isset( $_POST['user_email'] ) ? sanitize_email( wp_unslash( $_POST['user_email'] ) ) : '';
	/* Username is the email address (Lou, 04/11/2026), so a pass holder logs in
	   with the one thing they know. The page's script copies it in as they type;
	   this keeps it right if the script did not run. */
	if ( $email !== '' ) {
		$_POST['user_login'] = $email;
	}
	$fill  = array(
		'pms_billing_first_name' => $first !== '' ? $first : 'Colleague',
		'pms_billing_last_name'  => $last !== '' ? $last : 'Day Pass',
		'pms_billing_email'      => $email,
		'pms_billing_address'    => 'Colleague day pass (no charge, no invoice)',
		'pms_billing_city'       => 'Not applicable',
		'pms_billing_zip'        => '',
		'pms_billing_country'    => 'GB',
		'pms_billing_state'      => '',
	);
	foreach ( $fill as $k => $v ) {
		if ( ! isset( $_POST[ $k ] ) || trim( (string) $_POST[ $k ] ) === '' ) {
			$_POST[ $k ] = $v;
		}
	}
}

/** Plain-English errors on the form, and a per-address attempt limit on bad codes. */
add_action( 'pms_register_form_validation', 'msh_cpass_validate_registration' );

function msh_cpass_validate_registration() {
	if ( empty( $_POST['msh_cpass_choice'] ) ) {
		return; // an ordinary registration elsewhere on the site
	}
	if ( ! function_exists( 'pms_errors' ) ) {
		return;
	}
	if ( ! empty( $_POST['msh_cpass_website'] ) ) {
		pms_errors()->add( 'msh_cpass_code', 'Something went wrong. Please reload the page and try again.' );
		return;
	}
	$key   = 'msh_cpass_ip_' . md5( msh_cpass_client_ip() );
	$tries = (int) get_transient( $key );
	if ( $tries >= MSH_CPASS_ATTEMPTS_PER_HOUR ) {
		pms_errors()->add( 'msh_cpass_code', 'Too many attempts. Please try again in an hour.' );
		return;
	}
	if ( msh_cpass_request() ) {
		return;
	}
	set_transient( $key, $tries + 1, HOUR_IN_SECONDS );
	$code  = isset( $_POST['msh_cpass_code'] ) ? wp_unslash( $_POST['msh_cpass_code'] ) : '';
	$email = isset( $_POST['user_email'] ) ? wp_unslash( $_POST['user_email'] ) : '';
	$check = msh_cpass_check( $code, $email );
	$why   = empty( $check['ok'] ) ? $check['message'] : 'Please choose the Hub Member plan to use your colleague code.';
	pms_errors()->add( 'msh_cpass_code', $why );
}

// -----------------------------------------------------------------------------
// After the account is made: record the pass, email both sides
// -----------------------------------------------------------------------------

add_action( 'pms_register_form_after_create_user', 'msh_cpass_after_create_user' );

function msh_cpass_after_create_user( $user_data ) {
	$user_id = isset( $user_data['user_id'] ) ? (int) $user_data['user_id'] : 0;
	$req     = $user_id ? msh_cpass_request( $user_id ) : false;
	if ( ! $user_id || ! $req ) {
		return;
	}
	$now     = current_time( 'timestamp' );
	$expires = msh_cpass_expiry_from( $now );

	update_user_meta( $user_id, 'msh_cpass_from', $req['referrer'] );
	update_user_meta( $user_id, 'msh_cpass_code_used', $req['code'] );
	update_user_meta( $user_id, 'msh_cpass_granted', wp_date( 'Y-m-d H:i:s', $now ) );
	update_user_meta( $user_id, 'msh_cpass_expires', $expires );

	$uses   = msh_cpass_uses( $req['referrer'] );
	$uses[] = array( 'month' => msh_cpass_month_key( $now ), 'on' => wp_date( 'Y-m-d', $now ), 'hash' => msh_cpass_email_hash( $req['email'] ), 'user' => $user_id );
	update_user_meta( $req['referrer'], 'msh_cpass_uses', $uses );

	$used = get_option( 'msh_cpass_redeemed', array() );
	$used = is_array( $used ) ? $used : array();
	$used[ msh_cpass_email_hash( $req['email'] ) ] = wp_date( 'Y-m-d', $now );
	update_option( 'msh_cpass_redeemed', $used, false );

	$user     = get_userdata( $user_id );
	$referrer = get_userdata( $req['referrer'] );
	$name     = $user && $user->first_name ? $user->first_name : 'there';
	$ref_name = $referrer ? $referrer->display_name : 'a colleague';
	$until    = wp_date( 'l j F', strtotime( $expires ) ) . ' at midnight';

	msh_cpass_mail(
		$req['email'],
		'Your colleague day on the Medical Sales Intelligence Hub',
		"Hello $name,\n\n"
		. "$ref_name has given you a day on the Medical Sales Intelligence Hub. You have full access until $until (UK time).\n\n"
		. "Log in: " . wp_login_url() . "\n"
		. "Start here: https://medsalesintelligencehub.co.uk/medical-sales-hub/\n\n"
		. "Make the most of it: open the Rep's Briefing, the framework expiry tracker and the supplier pages for the accounts you sell into. Everything you see is live NHS market intelligence, updated every day.\n\n"
		. "When your day ends, your login stays and you can keep going from the join page: " . MSH_CPASS_JOIN_URL . "\n\n"
		. "Any questions, reply to this email.\n\n"
		. "Louise Hoult\nElevate & Thrive\n"
	);

	$ml = msh_cpass_to_mailerlite( $req['email'], $user, $req['code'], $ref_name, $expires );

	msh_cpass_mail(
		MSH_CPASS_FROM,
		'Colleague day pass used: ' . ( $user ? $user->display_name : $req['email'] ),
		"A colleague day pass was redeemed.\n\n"
		. "Colleague: " . ( $user ? $user->display_name : '' ) . " <" . $req['email'] . ">\n"
		. "Referred by: $ref_name (code " . $req['code'] . ", " . msh_cpass_uses_this_month( $req['referrer'] ) . " of " . MSH_CPASS_USES_PER_MONTH . " this month)\n"
		. "Access until: $expires\n\n"
		. "Users list: " . admin_url( 'users.php?s=' . rawurlencode( $req['email'] ) ) . "\n"
		. "MailerLite: " . $ml . "\n\n"
		. "FOR THE CRM (add or update this contact, source Colleague Day Pass):\n"
		. "Name: " . ( $user ? trim( $user->first_name . ' ' . $user->last_name ) : '' ) . "\n"
		. "Email: " . $req['email'] . "\n"
		. "Email domain: " . substr( strrchr( $req['email'], '@' ), 1 ) . "\n"
		. "Source: Colleague Day Pass, code " . $req['code'] . ", referred by $ref_name\n"
		. "Pass granted: " . wp_date( 'Y-m-d', $now ) . ", ends $expires\n"
		. "Next step: follow up the day after the pass ends\n"
	);
}

/** Add the pass holder to the Colleague Day Pass group in MailerLite. Returns a short
    status line for Lou's email. Never blocks the registration: a failure is reported, not thrown. */
function msh_cpass_to_mailerlite( $email, $user, $code, $ref_name, $expires ) {
	if ( ! MSH_CPASS_ML_GROUP ) {
		return 'not sent (no group set)';
	}
	$key = defined( 'MSH_ML_API_KEY' ) && MSH_ML_API_KEY ? MSH_ML_API_KEY : '';
	if ( ! $key ) {
		$o   = get_option( 'woo_mailerlite_options', array() );
		$key = ( is_array( $o ) && ! empty( $o['apiKey'] ) ) ? $o['apiKey'] : '';
	}
	if ( ! $key ) {
		return 'NOT ADDED: no MailerLite key on this site. Add them by hand.';
	}
	$payload = array(
		'email'  => $email,
		'fields' => array(
			'name'          => $user ? $user->first_name : '',
			'last_name'     => $user ? $user->last_name : '',
			'signup_source' => 'Colleague Day Pass ' . $code . ' from ' . $ref_name . ', ends ' . substr( $expires, 0, 10 ),
		),
		'groups' => array( (string) MSH_CPASS_ML_GROUP ),
	);
	$r = wp_remote_post( 'https://connect.mailerlite.com/api/subscribers', array(
		'timeout' => 15,
		'headers' => array( 'Authorization' => 'Bearer ' . $key, 'Content-Type' => 'application/json', 'Accept' => 'application/json' ),
		'body'    => wp_json_encode( $payload ),
	) );
	if ( is_wp_error( $r ) ) {
		return 'NOT ADDED: ' . $r->get_error_message() . '. Add them by hand.';
	}
	$http = (int) wp_remote_retrieve_response_code( $r );
	return ( $http === 200 || $http === 201 ) ? 'added to the Colleague Day Pass group' : 'NOT ADDED: MailerLite answered HTTP ' . $http . '. Add them by hand.';
}

/** Deleting a pass holder's account (wp-admin, Users) frees their address and gives the referrer the use back. */
add_action( 'delete_user', 'msh_cpass_on_delete_user' );

function msh_cpass_on_delete_user( $user_id ) {
	$user_id = (int) $user_id;
	$from    = (int) get_user_meta( $user_id, 'msh_cpass_from', true );
	if ( ! $from ) {
		return;
	}
	$user = get_userdata( $user_id );
	$used = get_option( 'msh_cpass_redeemed', array() );
	if ( $user && is_array( $used ) ) {
		unset( $used[ msh_cpass_email_hash( $user->user_email ) ] );
		update_option( 'msh_cpass_redeemed', $used, false );
	}
	$kept = array();
	foreach ( msh_cpass_uses( $from ) as $u ) {
		if ( ! isset( $u['user'] ) || (int) $u['user'] !== $user_id ) {
			$kept[] = $u;
		}
	}
	update_user_meta( $from, 'msh_cpass_uses', $kept );
}

// -----------------------------------------------------------------------------
// The subscription itself: one day, not one year
// -----------------------------------------------------------------------------

/** Set the pass holder's plan-690 subscription to end at msh_cpass_expires. Returns true when it is right. */
function msh_cpass_apply_expiry( $user_id ) {
	$user_id = (int) $user_id;
	$expires = get_user_meta( $user_id, 'msh_cpass_expires', true );
	if ( ! $expires || ! function_exists( 'pms_get_member_subscriptions' ) ) {
		return false;
	}
	$subs = pms_get_member_subscriptions( array( 'user_id' => $user_id, 'subscription_plan_id' => (int) MSH_CPASS_PLAN_ID ) );
	if ( empty( $subs ) ) {
		return false;
	}
	$sub    = $subs[0];
	$ok     = true;
	$update = array();
	$cur    = isset( $sub->expiration_date ) ? $sub->expiration_date : '';
	if ( $cur !== $expires ) {
		$update['expiration_date'] = $expires;
	}
	if ( isset( $sub->billing_amount ) && (float) $sub->billing_amount > 0 ) {
		$update['billing_amount'] = 0;
	}
	$past   = strtotime( $expires ) < current_time( 'timestamp' );
	$status = isset( $sub->status ) ? $sub->status : '';
	if ( $past && $status === 'active' ) {
		$update['status'] = 'expired';
	} elseif ( ! $past && $status === 'pending' ) {
		$update['status'] = 'active'; // the manual gateway leaves a £0 sign-up "pending" (awaiting offline payment); nothing is owed
	}
	if ( $update && method_exists( $sub, 'update' ) ) {
		$ok = (bool) $sub->update( $update );
	}
	return $ok;
}

add_action( 'pms_member_subscription_insert', 'msh_cpass_on_subscription_change', 10, 2 );
add_action( 'pms_member_subscription_update', 'msh_cpass_on_subscription_change', 10, 2 );

function msh_cpass_on_subscription_change( $subscription_id, $data ) {
	static $busy = false;
	if ( $busy ) {
		return; // our own update() call
	}
	$user_id = isset( $data['user_id'] ) ? (int) $data['user_id'] : 0;
	if ( ! $user_id && function_exists( 'pms_get_member_subscription' ) ) {
		$sub     = pms_get_member_subscription( (int) $subscription_id );
		$user_id = $sub && isset( $sub->user_id ) ? (int) $sub->user_id : 0;
	}
	if ( ! $user_id || ! msh_cpass_is_pass_holder( $user_id ) ) {
		return;
	}
	$busy = true;
	msh_cpass_apply_expiry( $user_id );
	$busy = false;
}

/** Belt and braces: every page load by a pass holder re-checks the expiry, so a pass never outlives its day. */
add_action( 'init', 'msh_cpass_enforce_on_load', 20 );

function msh_cpass_enforce_on_load() {
	if ( ! is_user_logged_in() ) {
		return;
	}
	$user_id = get_current_user_id();
	if ( ! msh_cpass_is_pass_holder( $user_id ) ) {
		return;
	}
	msh_cpass_apply_expiry( $user_id );
}

// -----------------------------------------------------------------------------
// The page: shortcode [msh_colleague_pass]
// -----------------------------------------------------------------------------

add_shortcode( 'msh_colleague_pass', 'msh_cpass_shortcode' );

function msh_cpass_shortcode() {
	if ( is_user_logged_in() ) {
		$user_id = get_current_user_id();
		if ( msh_cpass_is_pass_holder( $user_id ) ) {
			return msh_cpass_render_holder( $user_id );
		}
		if ( msh_cpass_is_eligible_referrer( $user_id ) ) {
			return msh_cpass_render_referrer( $user_id );
		}
		return '<div class="msh-cpass-card"><p>Colleague codes belong to paying Hub members. '
			. '<a href="' . esc_url( MSH_CPASS_JOIN_URL ) . '">Join the Hub</a> and your code appears here.</p></div>';
	}
	$form  = function_exists( 'do_shortcode' ) ? do_shortcode( '[pms-register subscription_plans="' . (int) MSH_CPASS_PLAN_ID . '"]' ) : '';
	$error = '';
	if ( function_exists( 'pms_errors' ) && method_exists( pms_errors(), 'get_error_message' ) ) {
		$msg = pms_errors()->get_error_message( 'msh_cpass_code' );
		if ( $msg ) {
			$error = '<div class="msh-cpass-error" role="alert">' . esc_html( $msg ) . '</div>';
		}
	}
	return '<div class="msh-cpass-register" id="msh-cpass-register">' . $error . $form . '</div>';
}

function msh_cpass_render_referrer( $user_id ) {
	$code  = msh_cpass_code_for( $user_id );
	$link  = home_url( '/' . MSH_CPASS_PAGE_SLUG . '/?code=' . rawurlencode( $code ) );
	$used  = msh_cpass_uses_this_month( $user_id );
	$total = count( msh_cpass_uses( $user_id ) );
	$left  = max( 0, MSH_CPASS_USES_PER_MONTH - $used );
	$meta  = msh_cpass_is_admin_referrer( $user_id )
		? 'Used ' . (int) $used . ' this month, ' . (int) $total . ' in total. No monthly limit on your code. '
		: 'Used ' . (int) $used . ' of ' . (int) MSH_CPASS_USES_PER_MONTH . ' this month (' . (int) $left . ' left), ' . (int) $total . ' in total. ';
	return '<div class="msh-cpass-card msh-cpass-mine">'
		. '<p class="msh-cpass-eyebrow">Your colleague code</p>'
		. '<p class="msh-cpass-code" id="msh-cpass-code">' . esc_html( $code ) . '</p>'
		. '<p>Share this link. Your colleague registers with their own email address and gets the whole Hub until the end of the next day.</p>'
		. '<p class="msh-cpass-link"><input type="text" readonly id="msh-cpass-link" value="' . esc_attr( $link ) . '"> '
		. '<button type="button" class="msh-cpass-copy" data-copy="#msh-cpass-link">Copy link</button></p>'
		. '<p class="msh-cpass-meta">' . $meta
		. 'Each colleague can have one day, once. The code works while your membership is active.</p>'
		. '</div>';
}

function msh_cpass_render_holder( $user_id ) {
	$expires = get_user_meta( $user_id, 'msh_cpass_expires', true );
	$ts      = $expires ? strtotime( $expires ) : 0;
	$now     = current_time( 'timestamp' );
	if ( $ts && $ts > $now ) {
		$hours = max( 1, (int) ceil( ( $ts - $now ) / HOUR_IN_SECONDS ) );
		return '<div class="msh-cpass-card"><p class="msh-cpass-eyebrow">Your colleague day</p>'
			. '<p>You have full Hub access for about ' . $hours . ' more hour' . ( $hours === 1 ? '' : 's' ) . ', until ' . esc_html( wp_date( 'l j F', $ts ) ) . ' at midnight. '
			. '<a href="' . esc_url( home_url( '/medical-sales-hub/' ) ) . '">Go to the Hub</a>.</p>'
			. '<p>Want to keep it? <a href="' . esc_url( MSH_CPASS_JOIN_URL ) . '">Join the Hub</a> and your login carries on.</p></div>';
	}
	return '<div class="msh-cpass-card"><p class="msh-cpass-eyebrow">Your colleague day has ended</p>'
		. '<p>Thank you for taking a look. Your login is still here: <a href="' . esc_url( MSH_CPASS_JOIN_URL ) . '">join the Hub</a> to keep the live intelligence, the tools and the weekly Rep&rsquo;s Briefing.</p></div>';
}

/** A small reminder bar for pass holders on every page, with the join link once the day has ended. */
add_action( 'wp_footer', 'msh_cpass_holder_bar', 5 );

function msh_cpass_holder_bar() {
	if ( ! is_user_logged_in() ) {
		return;
	}
	$user_id = get_current_user_id();
	if ( ! msh_cpass_is_pass_holder( $user_id ) ) {
		return;
	}
	$expires = get_user_meta( $user_id, 'msh_cpass_expires', true );
	$ts      = $expires ? strtotime( $expires ) : 0;
	$live    = $ts && $ts > current_time( 'timestamp' );
	$text    = $live
		? 'Your colleague day runs until ' . esc_html( wp_date( 'l', $ts ) ) . ' at midnight.'
		: 'Your colleague day has ended.';
	echo '<div id="msh-cpass-bar" style="position:fixed;left:0;right:0;bottom:0;z-index:99999;background:#0B1C33;color:#F5F1E8;font:500 15px/1.4 Jost,Inter,system-ui,sans-serif;padding:12px 20px;text-align:center;box-shadow:0 -2px 10px rgba(0,0,0,.25)">'
		. $text . ' <a href="' . esc_url( MSH_CPASS_JOIN_URL ) . '" style="color:#E0BE8E;font-weight:600;text-decoration:underline;margin-left:8px">Join the Hub</a></div>';
}

// -----------------------------------------------------------------------------
// Front-end: the form on the pass page (code field, free mode, prefill from ?code=)
// -----------------------------------------------------------------------------

add_action( 'wp_footer', 'msh_cpass_page_assets', 20 );

function msh_cpass_page_assets() {
	if ( ! is_page( MSH_CPASS_PAGE_SLUG ) ) {
		return;
	}
	$html = <<<'MSHCPASS'
<style id="msh-cpass-css">
body .wp-site-blocks .msh-cpass-card{max-width:720px;margin:0 auto;background:#FFFFFF;border:1px solid #DBE3EE;border-top:4px solid #A8842C;border-radius:12px;padding:28px 28px 22px;color:#1D2733;font-family:Jost,Inter,system-ui,sans-serif}
body .wp-site-blocks .msh-cpass-card p{color:#1D2733;margin:0 0 12px;font-size:17px;line-height:1.55}
body .wp-site-blocks .msh-cpass-card a{color:#0B1C33;font-weight:600;text-decoration:underline}
body .wp-site-blocks .msh-cpass-eyebrow{font-size:14px!important;letter-spacing:.08em;text-transform:uppercase;color:#14304F!important;font-weight:600}
body .wp-site-blocks .msh-cpass-code{font-size:38px!important;font-weight:700;letter-spacing:.06em;color:#0B1C33!important;margin:4px 0 14px!important}
body .wp-site-blocks .msh-cpass-link input{width:100%;max-width:520px;padding:10px 12px;border:1px solid #DBE3EE;border-radius:8px;font:400 15px Jost,Inter,system-ui,sans-serif;color:#1D2733;background:#F7F9FC}
body .wp-site-blocks .msh-cpass-copy{margin-top:8px;background:#0B1C33;color:#FFFFFF;border:0;border-radius:8px;padding:10px 18px;font:600 15px Jost,Inter,system-ui,sans-serif;cursor:pointer}
body .wp-site-blocks .msh-cpass-meta{font-size:15px!important;color:#26364B!important}
.msh-cpass-register .pms-form .pms-subscription-plans-list,
.msh-cpass-register .pms-form .pms-field-subscriptions,
.msh-cpass-register .pms-form .pms-paygates-holder,
.msh-cpass-register .pms-form .pms-billing-details,
.msh-cpass-register .pms-form .pms-section-billing-details,
.msh-cpass-register .pms-form .pms-paygate-extra-fields,
.msh-cpass-register .pms-form #pms-subscription-plans-discount,
.msh-cpass-register .pms-form #pms-subscription-plans-discount-messages-wrapper,
.msh-cpass-register .pms-form .pms-invite-code-field,
.msh-cpass-register .pms-form .msh-cpass-honey{display:none!important}
.msh-cpass-register .msh-cpass-error{max-width:640px;margin:0 auto 14px;background:#FFFFFF;border-left:4px solid #8A1C1C;border-radius:8px;padding:12px 16px;color:#8A1C1C;font:600 16px/1.4 Jost,Inter,system-ui,sans-serif}
.msh-cpass-register .pms-form{max-width:640px;margin:0 auto;background:#FFFFFF;border:1px solid #DBE3EE;border-top:4px solid #A8842C;border-radius:12px;padding:26px 28px}
.msh-cpass-register .pms-form label{font-family:Jost,Inter,system-ui,sans-serif;color:#26364B}
.msh-cpass-register .pms-form input[type=text],.msh-cpass-register .pms-form input[type=email],.msh-cpass-register .pms-form input[type=password]{width:100%;padding:11px 12px;border:1px solid #CBD5E1;border-radius:8px;font:400 16px Jost,Inter,system-ui,sans-serif;color:#1D2733}
.msh-cpass-register .pms-form .pms-form-submit input,.msh-cpass-register .pms-form input[type=submit]{background:#0B1C33;color:#FFFFFF;border:0;border-radius:8px;padding:13px 22px;font:600 16px Jost,Inter,system-ui,sans-serif;cursor:pointer}
.msh-cpass-register .msh-cpass-plan{background:#F7F9FC;border:1px solid #DBE3EE;border-radius:10px;padding:14px 16px;margin:0 0 18px;font-family:Jost,Inter,system-ui,sans-serif;color:#1D2733}
.msh-cpass-register .msh-cpass-plan strong{color:#0B1C33}
.msh-cpass-register .msh-cpass-plan .msh-cpass-free{float:right;color:#14304F;font-weight:700}
</style>
<script id="msh-cpass-js">
(function(){
	var wrap = document.getElementById('msh-cpass-register');
	document.querySelectorAll('.msh-cpass-copy').forEach(function(b){
		b.addEventListener('click', function(){
			var i = document.querySelector(b.getAttribute('data-copy'));
			if (!i) { return; }
			i.select();
			try { navigator.clipboard.writeText(i.value); } catch (e) { document.execCommand('copy'); }
			b.textContent = 'Copied';
			setTimeout(function(){ b.textContent = 'Copy link'; }, 2000);
		});
	});
	if (!wrap) { return; }
	var form = wrap.querySelector('.pms-form');
	if (!form) { return; }
	var planId = __PLAN_ID__;
	form.querySelectorAll('input[name="subscription_plans"]').forEach(function(r){
		if (parseInt(r.value, 10) === planId) { r.checked = true; }
	});
	function hidden(name, value){
		var e = form.querySelector('input[type="hidden"][name="' + name + '"]');
		if (!e) { e = document.createElement('input'); e.type = 'hidden'; e.name = name; form.appendChild(e); }
		e.value = value;
	}
	hidden('msh_cpass_choice', '1');
	var params = new URLSearchParams(window.location.search);
	var pre = (params.get('code') || '').toUpperCase().replace(/[^A-Z0-9-]/g, '');
	var sent = form.querySelector('input[name="msh_cpass_code"]');
	var li = document.createElement('li');
	li.className = 'pms-field pms-field-text msh-cpass-code-field';
	li.innerHTML = '<div class="msh-cpass-plan"><span class="msh-cpass-free">Free for a day</span><strong>Hub Member</strong><br>Full Hub access until the end of tomorrow, on your colleague\'s code.</div>'
		+ '<label for="msh-cpass-code-input">Colleague code</label>'
		+ '<input type="text" id="msh-cpass-code-input" name="msh_cpass_code" autocomplete="off" placeholder="HUB-NAME-XXXX" required value="' + (sent ? sent.value : pre) + '">'
		+ '<input type="text" class="msh-cpass-honey" name="msh_cpass_website" tabindex="-1" autocomplete="off" aria-hidden="true">';
	if (sent) { sent.remove(); }
	/* PMS nests its <li> fields inside a <div> within the <ul>, so insert beside the first field's real parent. */
	var list = form.querySelector('ul.pms-form-fields-wrapper') || form.querySelector('ul');
	var first = form.querySelector('li.pms-field');
	try {
		if (first && first.parentNode) { first.parentNode.insertBefore(li, first); } else if (list) { list.appendChild(li); } else { form.insertBefore(li, form.firstChild); }
	} catch (e) { form.insertBefore(li, form.firstChild); }
	/* Username = email address (Lou, 04/11/2026): hide the username field and copy the email into it. */
	var login = form.querySelector('input[name="user_login"]');
	var mail = form.querySelector('input[name="user_email"]');
	if (login && mail) {
		var row = login.closest('li') || login.parentNode;
		if (row) { row.style.display = 'none'; }
		login.removeAttribute('required');
		var sync = function(){ login.value = mail.value.trim(); };
		mail.addEventListener('input', sync);
		mail.addEventListener('change', sync);
		form.addEventListener('submit', sync);
		sync();
	}
	var code = li.querySelector('#msh-cpass-code-input');
	code.addEventListener('input', function(){ code.value = code.value.toUpperCase().replace(/[^A-Z0-9-]/g, ''); });
})();
</script>
MSHCPASS;
	echo str_replace( '__PLAN_ID__', (string) (int) MSH_CPASS_PLAN_ID, $html );
}

/** Invitation only: keep the page out of search results (a public "free day" result is not the offer). */
add_filter( 'wp_robots', 'msh_cpass_robots' );

function msh_cpass_robots( $robots ) {
	if ( function_exists( 'is_page' ) && is_page( MSH_CPASS_PAGE_SLUG ) ) {
		$robots['noindex'] = true;
		$robots['follow']  = true;
		unset( $robots['index'] );
	}
	return $robots;
}

// -----------------------------------------------------------------------------
// wp-admin: a Users column so Lou can see passes and codes at a glance
// -----------------------------------------------------------------------------

add_filter( 'manage_users_columns', 'msh_cpass_user_column' );

function msh_cpass_user_column( $columns ) {
	$columns['msh_cpass'] = 'Colleague pass';
	return $columns;
}

add_filter( 'manage_users_custom_column', 'msh_cpass_user_column_value', 10, 3 );

function msh_cpass_user_column_value( $value, $column, $user_id ) {
	if ( $column !== 'msh_cpass' ) {
		return $value;
	}
	$from = get_user_meta( $user_id, 'msh_cpass_from', true );
	if ( $from ) {
		$ref = get_userdata( (int) $from );
		return esc_html( 'Pass from ' . ( $ref ? $ref->display_name : '#' . $from ) . ', until ' . get_user_meta( $user_id, 'msh_cpass_expires', true ) );
	}
	$code = get_user_meta( $user_id, 'msh_cpass_code', true );
	if ( ! $code && msh_cpass_is_eligible_referrer( $user_id ) ) {
		$code = msh_cpass_code_for( $user_id ); // listing the Users screen gives every paying member a code, so it can go in an email before they open the page
	}
	if ( $code ) {
		return esc_html( $code . ' (' . count( msh_cpass_uses( $user_id ) ) . ' used)' );
	}
	return '';
}
