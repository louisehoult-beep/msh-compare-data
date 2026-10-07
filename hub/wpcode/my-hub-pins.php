/* My Hub: the pages a member has chosen, and the rest of their My Hub state.
   WPCode snippet id 4503.
   WPCode snippet, type "PHP Snippet", location "Run Everywhere", on
   medsalesintelligencehub.co.uk only. Paste from the line below this comment
   (WPCode adds the opening PHP tag itself).

   Source of truth: hub/wpcode/my-hub-pins.php in louisehoult-beep/msh-compare-data.
   Edit it there, then paste it here again. Read by app/my-hub.js,
   app/hub-account.js and app/hub-chrome.js.

   GET  /wp-json/msh/v1/my-hub
        { saved, pins, stateSaved, state }
   POST /wp-json/msh/v1/my-hub   (any of, in one body)
        pins:   [catalogue id, ...]                  replaces the list
        state:  { wnSeen, tour, tourSeen, briefing, phone, scope, stars }
                                                     merges the keys given
        star:   { u, t, k }                          adds one saved item, newest first
        unstar: "url"                                removes one saved item
        Returns the same shape as GET.

   User meta: msh_hub_pins (list of ids, unchanged since 23/09/2026) and
   msh_hub_state (added 2026-10 for the home screen: What's new entries
   seen, tour finished or skipped, briefing interest, Home Screen step,
   the specialities/everything switch, and starred pages and stories).
   Logged-in members only, each reads and writes their own, nothing else.
   Every value is cleaned by the functions below before it is stored;
   app/hub-account.js applies the same rules in the browser, and
   test_my_hub_state.py proves the two agree. Separate from the existing
   /msh/v1/prefs endpoint, which is left exactly as it is. */

if ( ! function_exists( 'msh_hub_state_blank' ) ) {
	function msh_hub_state_blank() {
		return array(
			'v'        => 1,
			'wnSeen'   => array(),
			'tour'     => false,
			'tourSeen' => false,
			'briefing' => false,
			'phone'    => false,
			'scope'    => 'mine',
			'stars'    => array(),
		);
	}
}

/* A real list, as JSON arrays are in the browser (Array.isArray): keys 0..n-1.
   A JSON object that PHP decodes to an associative array is not one. */
if ( ! function_exists( 'msh_hub_is_list' ) ) {
	function msh_hub_is_list( $x ) {
		return is_array( $x ) && array_values( $x ) === $x;
	}
}

if ( ! function_exists( 'msh_hub_cut' ) ) {
	function msh_hub_cut( $s, $n ) {
		return function_exists( 'mb_substr' ) ? mb_substr( $s, 0, $n ) : substr( $s, 0, $n );
	}
}

/* A Hub address is stored as a path, so the same page saved on www. and
   without it is one item. Anything else must be an https link. */
if ( ! function_exists( 'msh_hub_star_key' ) ) {
	function msh_hub_star_key( $u ) {
		$u = trim( (string) $u );
		$m = preg_replace( '#^https://(www\.)?medsalesintelligencehub\.co\.uk(?=/|$)#', '', $u );
		if ( $m !== $u && '' === $m ) {
			$m = '/';
		}
		return $m;
	}
}

if ( ! function_exists( 'msh_hub_star_clean' ) ) {
	function msh_hub_star_clean( $s ) {
		if ( ! is_array( $s ) ) {
			return null;
		}
		if ( ! isset( $s['u'] ) || ! is_string( $s['u'] ) || ! isset( $s['t'] ) || ! is_string( $s['t'] ) ) {
			return null;
		}
		$u = msh_hub_star_key( $s['u'] );
		if ( strlen( $u ) > 500 || ! preg_match( '#^(https://[^\s"<>]+|/[^\s"<>]*)$#D', $u ) ) {
			return null;
		}
		/* "//host" and "/\host" are protocol-relative: they leave the Hub. */
		if ( preg_match( '#^/[/\\\\]#', $u ) ) {
			return null;
		}
		$t = $s['t'];
		$t = trim( preg_replace( '/\s+/u', ' ', preg_replace( '/<[^>]*>/', '', $t ) ) );
		$t = msh_hub_cut( $t, 200 );
		if ( '' === $t ) {
			return null;
		}
		$k  = ( isset( $s['k'] ) && 'story' === $s['k'] ) ? 'story' : 'page';
		$at = ( isset( $s['at'] ) && is_string( $s['at'] ) && preg_match( '/^\d{4}-\d{2}-\d{2}$/D', $s['at'] ) ) ? $s['at'] : '';
		return array( 'u' => $u, 't' => $t, 'k' => $k, 'at' => $at );
	}
}

if ( ! function_exists( 'msh_hub_state_clean' ) ) {
	function msh_hub_state_clean( $s ) {
		$out = msh_hub_state_blank();
		if ( ! is_array( $s ) ) {
			return $out;
		}
		if ( isset( $s['wnSeen'] ) && msh_hub_is_list( $s['wnSeen'] ) ) {
			$seen = array();
			foreach ( array_slice( $s['wnSeen'], 0, 2000 ) as $id ) {
				if ( is_string( $id ) && preg_match( '/^[a-z0-9-]{1,64}$/D', $id ) && ! in_array( $id, $seen, true ) ) {
					$seen[] = $id;
				}
			}
			$out['wnSeen'] = array_values( array_slice( $seen, -300 ) );
		}
		foreach ( array( 'tour', 'tourSeen', 'briefing', 'phone' ) as $k ) {
			$out[ $k ] = isset( $s[ $k ] ) && true === $s[ $k ];
		}
		$out['scope'] = ( isset( $s['scope'] ) && 'all' === $s['scope'] ) ? 'all' : 'mine';
		if ( isset( $s['stars'] ) && msh_hub_is_list( $s['stars'] ) ) {
			$have = array();
			foreach ( array_slice( $s['stars'], 0, 2000 ) as $x ) {
				$c = msh_hub_star_clean( $x );
				if ( $c && ! isset( $have[ $c['u'] ] ) ) {
					$have[ $c['u'] ] = 1;
					$out['stars'][] = $c;
				}
				if ( count( $out['stars'] ) >= 200 ) {
					break;
				}
			}
		}
		return $out;
	}
}

/* Merge a POST body into the stored state. `state` sets only the keys it
   names; `star` puts one item first (replacing the same address); `unstar`
   removes one. The result is cleaned again before it is returned. */
if ( ! function_exists( 'msh_hub_state_apply' ) ) {
	function msh_hub_state_apply( $old, $body, $today ) {
		$state = msh_hub_state_clean( $old );
		if ( isset( $body['state'] ) && is_array( $body['state'] ) ) {
			foreach ( array_keys( $state ) as $k ) {
				if ( 'v' !== $k && array_key_exists( $k, $body['state'] ) ) {
					$state[ $k ] = $body['state'][ $k ];
				}
			}
			$state = msh_hub_state_clean( $state );
		}
		if ( isset( $body['star'] ) && is_array( $body['star'] ) ) {
			$c = msh_hub_star_clean( array_merge( $body['star'], array( 'at' => (string) $today ) ) );
			if ( $c ) {
				$keep = array( $c );
				foreach ( $state['stars'] as $x ) {
					if ( $x['u'] !== $c['u'] ) {
						$keep[] = $x;
					}
				}
				$state['stars'] = array_slice( $keep, 0, 200 );
			}
		}
		if ( isset( $body['unstar'] ) && is_string( $body['unstar'] ) ) {
			$key   = msh_hub_star_key( $body['unstar'] );
			$keep  = array();
			foreach ( $state['stars'] as $x ) {
				if ( $x['u'] !== $key ) {
					$keep[] = $x;
				}
			}
			$state['stars'] = $keep;
		}
		return $state;
	}
}

/* Same rule as before 2026-10 (WordPress sanitize_key, written out so the
   test can run it without WordPress): lower case, a-z 0-9 _ -, at most 80
   characters, no repeats, at most 150 ids. */
if ( ! function_exists( 'msh_hub_pins_clean' ) ) {
	function msh_hub_pins_clean( $in ) {
		$out = array();
		foreach ( $in as $id ) {
			$id = strtolower( preg_replace( '/[^a-zA-Z0-9_\-]/', '', is_string( $id ) ? $id : '' ) );
			if ( '' !== $id && strlen( $id ) <= 80 && ! in_array( $id, $out, true ) ) {
				$out[] = $id;
			}
			if ( count( $out ) >= 150 ) {
				break;
			}
		}
		return $out;
	}
}

if ( ! function_exists( 'msh_hub_rest_payload' ) ) {
	function msh_hub_rest_payload( $uid ) {
		$pins = get_user_meta( $uid, 'msh_hub_pins', true );
		$raw  = get_user_meta( $uid, 'msh_hub_state', true );
		return array(
			'saved'      => metadata_exists( 'user', $uid, 'msh_hub_pins' ),
			'pins'       => is_array( $pins ) ? array_values( $pins ) : array(),
			'stateSaved' => metadata_exists( 'user', $uid, 'msh_hub_state' ),
			'state'      => msh_hub_state_clean( is_array( $raw ) ? $raw : array() ),
		);
	}
}

add_action( 'rest_api_init', function () {
	register_rest_route( 'msh/v1', '/my-hub', array(
		array(
			'methods'             => 'GET',
			'permission_callback' => function () { return is_user_logged_in(); },
			'callback'            => function () {
				nocache_headers();
				return msh_hub_rest_payload( get_current_user_id() );
			},
		),
		array(
			'methods'             => 'POST',
			'permission_callback' => function () { return is_user_logged_in(); },
			'callback'            => function ( WP_REST_Request $req ) {
				$uid  = get_current_user_id();
				$body = $req->get_json_params();
				if ( ! is_array( $body ) ) {
					$body = array();
				}
				$did = false;
				if ( array_key_exists( 'pins', $body ) ) {
					if ( ! is_array( $body['pins'] ) ) {
						return new WP_Error( 'msh_bad_pins', 'pins must be a list', array( 'status' => 400 ) );
					}
					update_user_meta( $uid, 'msh_hub_pins', msh_hub_pins_clean( $body['pins'] ) );
					$did = true;
				}
				if ( isset( $body['state'] ) || isset( $body['star'] ) || isset( $body['unstar'] ) ) {
					$old = get_user_meta( $uid, 'msh_hub_state', true );
					update_user_meta( $uid, 'msh_hub_state', msh_hub_state_apply( is_array( $old ) ? $old : array(), $body, wp_date( 'Y-m-d' ) ) );
					$did = true;
				}
				if ( ! $did ) {
					return new WP_Error( 'msh_nothing', 'nothing to save', array( 'status' => 400 ) );
				}
				return msh_hub_rest_payload( $uid );
			},
		),
	) );
} );

/* REST cookie auth needs a wp_rest nonce on the page. Printed for logged-in
   members only. */
add_action( 'wp_footer', function () {
	if ( ! is_user_logged_in() ) {
		return;
	}
	echo '<script>window.mshRestNonce=' . wp_json_encode( wp_create_nonce( 'wp_rest' ) ) . ';</script>';
}, 5 );
