<?php
/*
 * WPCode snippet: "Live Desk app - store membership bridge" (PHP, run everywhere).
 * Plan step D2, 19/11/2026. DRAFT: not installed. Installing it is publishing
 * and needs Lou's word in chat (publish skill).
 *
 * Hub membership bought in the Live Desk app (App Store / Google Play, through
 * RevenueCat) reaches WordPress here. The Supabase webhook livedesk-revenuecat
 * posts a signed JSON body to POST /wp-json/msh/v1/livedesk-store:
 *
 *   {v:1, action:"grant",  email, plan_id, expires_at, app_user, product, store, event_id}
 *       find or create the WordPress user by email, then start or extend their
 *       Paid Member Subscriptions plan to expires_at.
 *   {v:1, action:"revoke", email, plan_id, expires_at, app_user, ...}
 *       end the app-bought subscription now (store expiry or refund). Website-
 *       bought subscriptions are never touched.
 *   {v:1, action:"login_link", wp_user_id, app_user}
 *       only for accounts this bridge created (the store email is unverified,
 *       so an existing website account is never signed in this way): a one-time, five-minute link that signs the member in to the Hub inside
 *       the app's web view (remember-me cookie), then lands on My Hub.
 *
 * Signature: header X-MSH-Bridge: t=<unix>,s=<base64url(HMAC-SHA256(secret, t.body))>,
 * the same as supabase/functions/livedesk/hub_bridge.ts. Refused outside
 * MSH_LDB_WINDOW seconds. Secret: constant MSH_LIVEDESK_BRIDGE_SECRET (wp-config)
 * or option msh_livedesk_bridge_secret; same value as Supabase HUB_BRIDGE_SECRET.
 *
 * App-bought subscriptions carry subscription meta msh_store_source = "app",
 * payment gateway "manual" and billing amount 0 (the store took the money).
 *
 * The pure functions (msh_ldb_*) have no WordPress calls and are tested by
 * test_livedesk_store_bridge.py with php -r.
 */

if ( ! defined( 'MSH_LDB_WINDOW' ) ) {
	define( 'MSH_LDB_WINDOW', 300 );
}
if ( ! defined( 'MSH_LDB_LOGIN_TTL' ) ) {
	define( 'MSH_LDB_LOGIN_TTL', 300 );
}
if ( ! defined( 'MSH_LDB_MY_HUB' ) ) {
	define( 'MSH_LDB_MY_HUB', 4404 );
}

if ( ! function_exists( 'msh_ldb_hub_plans' ) ) {
	/* Plans the app may grant. Same list as msh_myhub_is_hub_member() minus the
	   withdrawn trial (954). Hub Employer (5167) stays out until it is sold in the app. */
	function msh_ldb_hub_plans() {
		return array( 690, 691, 692, 694, 930 );
	}
}

if ( ! function_exists( 'msh_ldb_b64url' ) ) {
	function msh_ldb_b64url( $bin ) {
		return rtrim( strtr( base64_encode( $bin ), '+/', '-_' ), '=' );
	}
}

if ( ! function_exists( 'msh_ldb_verify_sig' ) ) {
	/* true when the X-MSH-Bridge header signs this exact body inside the window. */
	function msh_ldb_verify_sig( $secret, $header, $body, $now ) {
		if ( ! is_string( $secret ) || strlen( $secret ) < 32 || ! is_string( $header ) || ! is_string( $body ) ) {
			return false;
		}
		if ( ! preg_match( '/^t=(\d{9,11}),s=([A-Za-z0-9_-]{43})$/', trim( $header ), $m ) ) {
			return false;
		}
		$t = (int) $m[1];
		if ( abs( $now - $t ) > MSH_LDB_WINDOW ) {
			return false;
		}
		$want = msh_ldb_b64url( hash_hmac( 'sha256', $m[1] . '.' . $body, $secret, true ) );
		return hash_equals( $want, $m[2] );
	}
}

if ( ! function_exists( 'msh_ldb_parse' ) ) {
	/* The checked request, or a short reason string. */
	function msh_ldb_parse( $body ) {
		$d = json_decode( (string) $body, true );
		if ( ! is_array( $d ) || ( isset( $d['v'] ) ? $d['v'] : 0 ) !== 1 ) {
			return 'json';
		}
		$action = isset( $d['action'] ) ? $d['action'] : '';
		$app    = isset( $d['app_user'] ) ? $d['app_user'] : '';
		if ( ! is_string( $app ) || ! preg_match( '/^[0-9a-f-]{36}$/i', $app ) ) {
			return 'app_user';
		}
		if ( 'login_link' === $action ) {
			$wp = isset( $d['wp_user_id'] ) ? $d['wp_user_id'] : 0;
			if ( ! is_int( $wp ) || $wp <= 0 ) {
				return 'wp_user_id';
			}
			return array( 'action' => 'login_link', 'wp_user_id' => $wp, 'app_user' => strtolower( $app ) );
		}
		if ( 'grant' !== $action && 'revoke' !== $action ) {
			return 'action';
		}
		$email = isset( $d['email'] ) && is_string( $d['email'] ) ? strtolower( trim( $d['email'] ) ) : '';
		if ( '' === $email || strlen( $email ) > 254 || ! preg_match( '/^[^\s@<>"]+@[^\s@<>"]+\.[a-z]{2,63}$/i', $email ) ) {
			return 'email';
		}
		$plan = isset( $d['plan_id'] ) ? $d['plan_id'] : 0;
		if ( ! is_int( $plan ) || ! in_array( $plan, msh_ldb_hub_plans(), true ) ) {
			return 'plan';
		}
		$exp = isset( $d['expires_at'] ) && is_string( $d['expires_at'] ) ? strtotime( $d['expires_at'] ) : false;
		if ( false === $exp || $exp <= 0 ) {
			return 'expires_at';
		}
		return array(
			'action'   => $action,
			'email'    => $email,
			'plan_id'  => $plan,
			'expires'  => $exp,
			'app_user' => strtolower( $app ),
			'product'  => isset( $d['product'] ) && is_string( $d['product'] ) ? substr( $d['product'], 0, 120 ) : '',
			'store'    => isset( $d['store'] ) && is_string( $d['store'] ) ? substr( $d['store'], 0, 40 ) : '',
			'event_id' => isset( $d['event_id'] ) && is_string( $d['event_id'] ) ? substr( $d['event_id'], 0, 120 ) : '',
		);
	}
}

if ( ! function_exists( 'msh_ldb_live' ) ) {
	/* A subscription that opens the Hub now (as pms_is_member() reads it). */
	function msh_ldb_live( $s, $now ) {
		$s = (object) $s;
		if ( ! in_array( (string) $s->status, array( 'active', 'canceled', 'cancelled' ), true ) ) {
			return false;
		}
		$e = isset( $s->expiration_date ) ? (string) $s->expiration_date : '';
		return '' === $e || '0000-00-00' === substr( $e, 0, 10 ) || strtotime( $e ) >= $now;
	}
}

if ( ! function_exists( 'msh_ldb_decide' ) ) {
	/*
	 * What to do with the member's subscriptions. $subs: list of objects/arrays
	 * with id, subscription_plan_id, status, expiration_date, and app (bool: our
	 * meta msh_store_source = "app"). Hub plans only are considered.
	 * Returns array( 'op' => insert|update|none, 'id' => <sub id or 0>, 'why' => ... ).
	 */
	function msh_ldb_decide( $req, $subs, $now ) {
		$hub  = msh_ldb_hub_plans();
		$mine = null;
		$web_live = null;
		$spare    = null;
		foreach ( (array) $subs as $s ) {
			$s = (object) $s;
			if ( ! in_array( (int) $s->subscription_plan_id, $hub, true ) ) {
				continue;
			}
			if ( ! empty( $s->app ) ) {
				if ( null === $mine ) {
					$mine = $s;
				}
			} elseif ( msh_ldb_live( $s, $now ) ) {
				$web_live = $s;
			} elseif ( null === $spare ) {
				$spare = $s;
			}
		}
		if ( 'revoke' === $req['action'] ) {
			if ( $mine && 'expired' !== (string) $mine->status ) {
				return array( 'op' => 'update', 'id' => (int) $mine->id, 'why' => 'end app subscription' );
			}
			return array( 'op' => 'none', 'id' => 0, 'why' => 'nothing bought in the app' );
		}
		if ( $mine ) {
			return array( 'op' => 'update', 'id' => (int) $mine->id, 'why' => 'extend app subscription' );
		}
		if ( $web_live ) {
			/* Already a member through the website: no second record. The store
			   purchase still opens the Live Desk; support can refund one of them. */
			return array( 'op' => 'none', 'id' => (int) $web_live->id, 'why' => 'website membership live' );
		}
		if ( $spare ) {
			/* PMS keeps one subscription per plan group: reuse the lapsed one. */
			return array( 'op' => 'update', 'id' => (int) $spare->id, 'why' => 'reuse lapsed subscription' );
		}
		return array( 'op' => 'insert', 'id' => 0, 'why' => 'new app subscription' );
	}
}

if ( ! function_exists( 'msh_ldb_may_link' ) ) {
	/* May the app sign this account in with a one-time link? Only accounts the
	   bridge created (user meta msh_created_by = livedesk-app), never admins. */
	function msh_ldb_may_link( $created_by, $is_admin ) {
		return ! $is_admin && 'livedesk-app' === $created_by;
	}
}

if ( ! function_exists( 'msh_ldb_login_name' ) ) {
	/* A user_login from the email's local part; $taken( $name ) says if it is used. */
	function msh_ldb_login_name( $email, $taken ) {
		$base = strtolower( preg_replace( '/[^a-z0-9]+/i', '', strstr( $email, '@', true ) ) );
		if ( strlen( $base ) < 3 ) {
			$base = 'member' . $base;
		}
		$base = substr( $base, 0, 40 );
		$name = $base;
		for ( $i = 2; $taken( $name ) && $i < 1000; $i++ ) {
			$name = $base . $i;
		}
		return $name;
	}
}

/* ---------------------------------------------------------------- WordPress */

if ( function_exists( 'add_action' ) ) {

	add_action( 'rest_api_init', function () {
		register_rest_route( 'msh/v1', '/livedesk-store', array(
			'methods'             => 'POST',
			'permission_callback' => '__return_true', /* signature checked below */
			'callback'            => 'msh_ldb_handle',
		) );
	} );

	if ( ! function_exists( 'msh_ldb_secret' ) ) {
		function msh_ldb_secret() {
			if ( defined( 'MSH_LIVEDESK_BRIDGE_SECRET' ) ) {
				return (string) MSH_LIVEDESK_BRIDGE_SECRET;
			}
			return (string) get_option( 'msh_livedesk_bridge_secret', '' );
		}
	}

	if ( ! function_exists( 'msh_ldb_handle' ) ) {
		function msh_ldb_handle( WP_REST_Request $request ) {
			$body = $request->get_body();
			if ( ! msh_ldb_verify_sig( msh_ldb_secret(), (string) $request->get_header( 'x_msh_bridge' ), $body, time() ) ) {
				return new WP_REST_Response( array( 'ok' => false, 'why' => 'signature' ), 401 );
			}
			$req = msh_ldb_parse( $body );
			if ( ! is_array( $req ) ) {
				return new WP_REST_Response( array( 'ok' => false, 'why' => $req ), 400 );
			}
			if ( 'login_link' === $req['action'] ) {
				return msh_ldb_login_link( $req );
			}
			if ( ! function_exists( 'pms_get_member_subscriptions' ) || ! class_exists( 'PMS_Member_Subscription' ) ) {
				return new WP_REST_Response( array( 'ok' => false, 'why' => 'pms' ), 500 );
			}
			/* A replayed event (RevenueCat retries) does nothing twice. */
			if ( '' !== $req['event_id'] ) {
				$key = 'msh_ldb_ev_' . md5( $req['event_id'] . '|' . $req['action'] );
				if ( get_transient( $key ) ) {
					$u = get_user_by( 'email', $req['email'] );
					return new WP_REST_Response( array( 'ok' => true, 'dup' => true, 'wp_user_id' => $u ? (int) $u->ID : null ), 200 );
				}
			}

			$user = get_user_by( 'email', $req['email'] );
			if ( ! $user ) {
				if ( 'revoke' === $req['action'] ) {
					return new WP_REST_Response( array( 'ok' => true, 'op' => 'none', 'wp_user_id' => null ), 200 );
				}
				$uid = wp_insert_user( array(
					'user_login' => msh_ldb_login_name( $req['email'], 'username_exists' ),
					'user_email' => $req['email'],
					'user_pass'  => wp_generate_password( 32, true, true ),
					'role'       => 'subscriber',
				) );
				if ( is_wp_error( $uid ) ) {
					return new WP_REST_Response( array( 'ok' => false, 'why' => 'user' ), 500 );
				}
				update_user_meta( $uid, 'msh_created_by', 'livedesk-app' );
			} else {
				$uid = (int) $user->ID;
			}
			/* The store email is not proven to belong to the buyer. So the app may
			   only ever sign in to accounts this bridge created; an existing
			   website account gets the membership but its owner signs in with
			   their own password or emailed code (msh_ldb_may_link). */
			if ( msh_ldb_may_link( get_user_meta( $uid, 'msh_created_by', true ), user_can( $uid, 'manage_options' ) ) ) {
				update_user_meta( $uid, 'msh_livedesk_app_user', $req['app_user'] );
			}

			$subs = array();
			foreach ( (array) pms_get_member_subscriptions( array( 'user_id' => $uid ) ) as $s ) {
				$o      = (object) ( is_object( $s ) ? get_object_vars( $s ) : $s );
				$o->app = 'app' === pms_get_member_subscription_meta( (int) $o->id, 'msh_store_source', true );
				$subs[] = $o;
			}
			$now  = time();
			$plan = msh_ldb_decide( $req, $subs, $now );
			$date = gmdate( 'Y-m-d H:i:s', 'revoke' === $req['action'] ? $now : $req['expires'] );
			$data = array(
				'subscription_plan_id' => $req['plan_id'],
				'expiration_date'      => $date,
				'status'               => 'revoke' === $req['action'] ? 'expired' : 'active',
				'payment_gateway'      => 'manual',
				'billing_amount'       => 0,
			);
			if ( 'revoke' === $req['action'] ) {
				unset( $data['subscription_plan_id'] );
			}
			$sub_id = $plan['id'];
			if ( 'insert' === $plan['op'] ) {
				$sub = new PMS_Member_Subscription();
				$ok  = $sub->insert( array_merge( $data, array( 'user_id' => $uid, 'start_date' => gmdate( 'Y-m-d H:i:s', $now ) ) ) );
				$sub_id = $ok ? (int) $sub->id : 0;
				if ( ! $sub_id ) {
					return new WP_REST_Response( array( 'ok' => false, 'why' => 'pms insert' ), 500 );
				}
			} elseif ( 'update' === $plan['op'] ) {
				$sub = new PMS_Member_Subscription( $sub_id );
				if ( ! $sub->update( $data ) ) {
					return new WP_REST_Response( array( 'ok' => false, 'why' => 'pms update' ), 500 );
				}
			}
			if ( $sub_id && 'none' !== $plan['op'] ) {
				pms_update_member_subscription_meta( $sub_id, 'msh_store_source', 'app' );
				pms_update_member_subscription_meta( $sub_id, 'msh_store_product', $req['product'] );
				pms_update_member_subscription_meta( $sub_id, 'msh_store_platform', $req['store'] );
			}
			if ( '' !== $req['event_id'] ) {
				set_transient( 'msh_ldb_ev_' . md5( $req['event_id'] . '|' . $req['action'] ), 1, 7 * DAY_IN_SECONDS );
			}
			return new WP_REST_Response( array( 'ok' => true, 'op' => $plan['op'], 'why' => $plan['why'], 'wp_user_id' => $uid ), 200 );
		}
	}

	if ( ! function_exists( 'msh_ldb_login_link' ) ) {
		function msh_ldb_login_link( $req ) {
			$user = get_userdata( $req['wp_user_id'] );
			if ( ! $user || ! msh_ldb_may_link( get_user_meta( $user->ID, 'msh_created_by', true ), user_can( $user, 'manage_options' ) ) ) {
				/* Only accounts this bridge created; never an administrator. */
				return new WP_REST_Response( array( 'ok' => false, 'why' => 'user' ), 403 );
			}
			if ( get_user_meta( $user->ID, 'msh_livedesk_app_user', true ) !== $req['app_user'] ) {
				return new WP_REST_Response( array( 'ok' => false, 'why' => 'app_user' ), 403 );
			}
			$token = msh_ldb_b64url( random_bytes( 32 ) );
			set_transient( 'msh_ldb_login_' . hash( 'sha256', $token ), (int) $user->ID, MSH_LDB_LOGIN_TTL );
			return new WP_REST_Response( array( 'ok' => true, 'url' => add_query_arg( 'msh_app_login', $token, home_url( '/' ) ) ), 200 );
		}
	}

	/* The one-time link: single use, then a remember-me sign-in and My Hub. */
	add_action( 'init', function () {
		if ( empty( $_GET['msh_app_login'] ) || ! is_string( $_GET['msh_app_login'] ) ) {
			return;
		}
		$token = preg_replace( '/[^A-Za-z0-9_-]/', '', wp_unslash( $_GET['msh_app_login'] ) );
		$key   = 'msh_ldb_login_' . hash( 'sha256', $token );
		$uid   = (int) get_transient( $key );
		delete_transient( $key );
		nocache_headers();
		if ( $uid > 0 && msh_ldb_may_link( get_user_meta( $uid, 'msh_created_by', true ), user_can( $uid, 'manage_options' ) ) ) {
			wp_set_current_user( $uid );
			wp_set_auth_cookie( $uid, true, is_ssl() );
			wp_safe_redirect( get_permalink( MSH_LDB_MY_HUB ) ?: home_url( '/' ) );
			exit;
		}
		wp_safe_redirect( home_url( '/' ) );
		exit;
	}, 1 );
}
