/* Poster connect: a nurse scans the conference poster QR, leaves details, and
   lands on a Connect-on-LinkedIn button. Added 26/10/2026.

   WPCode snippet, type "PHP Snippet", location "Run Everywhere", on
   medsalesintelligencehub.co.uk only. Paste from the line below this comment
   (WPCode adds the opening PHP tag itself).

   Source of truth: hub/wpcode/poster-connect.php in louisehoult-beep/msh-compare-data.

   ROUTES (public, no login)
   POST /wp-json/msh-poster/v1/join   details -> MailerLite group "Conference poster",
                                      status active (the form carries an explicit consent tick)
   POST /wp-json/msh-poster/v1/click  email -> sets linkedin_connect_clicked on that
                                      subscriber. Only counts a tap on Connect; LinkedIn
                                      does not tell us who accepted.
   Works from the poster page and from the Association page (any existing subscriber).
   Personal data lives in MailerLite, never in this repo. */

define( 'MSH_POSTER_GROUP_ID', '202400722745034323' );

function msh_poster_ml( $method, $path, $payload = null ) {
	$key = defined( 'MSH_ML_API_KEY' ) && MSH_ML_API_KEY ? MSH_ML_API_KEY : '';
	if ( ! $key ) {
		$o   = get_option( 'woo_mailerlite_options', array() );
		$key = ( is_array( $o ) && ! empty( $o['apiKey'] ) ) ? $o['apiKey'] : '';
	}
	if ( ! $key ) {
		return array( 0, array( 'error' => 'no MailerLite key on this site' ) );
	}
	$args = array(
		'method'  => $method,
		'timeout' => 20,
		'headers' => array( 'Authorization' => 'Bearer ' . $key, 'Content-Type' => 'application/json', 'Accept' => 'application/json' ),
	);
	if ( null !== $payload ) {
		$args['body'] = wp_json_encode( $payload );
	}
	$r = wp_remote_request( 'https://connect.mailerlite.com/api' . $path, $args );
	if ( is_wp_error( $r ) ) {
		return array( 0, array( 'error' => $r->get_error_message() ) );
	}
	$body = json_decode( wp_remote_retrieve_body( $r ), true );
	return array( (int) wp_remote_retrieve_response_code( $r ), is_array( $body ) ? $body : array() );
}

add_action( 'rest_api_init', function () {
	register_rest_route( 'msh-poster/v1', '/join', array(
		'methods'             => 'POST',
		'permission_callback' => '__return_true',
		'callback'            => 'msh_poster_join',
	) );
	register_rest_route( 'msh-poster/v1', '/click', array(
		'methods'             => 'POST',
		'permission_callback' => '__return_true',
		'callback'            => 'msh_poster_click',
	) );
} );

function msh_poster_rate_ok( $email ) {
	$ip  = isset( $_SERVER['REMOTE_ADDR'] ) ? (string) $_SERVER['REMOTE_ADDR'] : '';
	$k_e = 'msh_poster_rl_' . md5( $email );
	$k_i = 'msh_poster_rli_' . md5( $ip );
	$n_e = (int) get_transient( $k_e );
	$n_i = (int) get_transient( $k_i );
	if ( $n_e >= 5 || $n_i >= 60 ) {
		return false;
	}
	set_transient( $k_e, $n_e + 1, DAY_IN_SECONDS );
	set_transient( $k_i, $n_i + 1, DAY_IN_SECONDS );
	return true;
}

function msh_poster_join( WP_REST_Request $req ) {
	$p = $req->get_params();
	$f = isset( $p['fields'] ) && is_array( $p['fields'] ) ? $p['fields'] : array();

	if ( ! empty( $p['website_url'] ) ) {
		return new WP_REST_Response( array( 'ok' => true ), 200 ); // honeypot
	}
	$email = isset( $f['email'] ) ? strtolower( sanitize_email( $f['email'] ) ) : '';
	if ( ! is_email( $email ) ) {
		return new WP_REST_Response( array( 'ok' => false, 'error' => 'email' ), 400 );
	}
	foreach ( array( 'name' ) as $k ) {
		if ( empty( $f[ $k ] ) || '' === trim( (string) $f[ $k ] ) ) {
			return new WP_REST_Response( array( 'ok' => false, 'error' => $k ), 400 );
		}
	}
	if ( empty( $p['consent'] ) ) {
		return new WP_REST_Response( array( 'ok' => false, 'error' => 'consent' ), 400 );
	}
	if ( ! msh_poster_rate_ok( $email ) ) {
		return new WP_REST_Response( array( 'ok' => false, 'error' => 'limit' ), 429 );
	}

	$fields = array();
	foreach ( array( 'name', 'last_name', 'job_title', 'work_setting', 'signup_source', 'poster_interests' ) as $k ) {
		if ( isset( $f[ $k ] ) && '' !== trim( (string) $f[ $k ] ) ) {
			$fields[ $k ] = substr( sanitize_text_field( $f[ $k ] ), 0, 200 );
		}
	}
	$fields['company'] = isset( $f['company'] ) ? substr( sanitize_text_field( $f['company'] ), 0, 200 ) : '';

	$sub = array( 'email' => $email, 'fields' => $fields, 'groups' => array( MSH_POSTER_GROUP_ID ) );
	list( $code, $body ) = msh_poster_ml( 'POST', '/subscribers', $sub );
	if ( $code < 200 || $code > 299 ) {
		return new WP_REST_Response( array( 'ok' => false, 'error' => 'store' ), 502 );
	}
	return new WP_REST_Response( array( 'ok' => true ), 200 );
}

function msh_poster_click( WP_REST_Request $req ) {
	$email = strtolower( sanitize_email( (string) $req->get_param( 'email' ) ) );
	if ( ! is_email( $email ) || ! msh_poster_rate_ok( $email ) ) {
		return new WP_REST_Response( array( 'ok' => false ), 400 );
	}
	// Only an address already on the list can be marked; never creates a subscriber.
	list( $code ) = msh_poster_ml( 'GET', '/subscribers/' . rawurlencode( $email ) );
	if ( 200 !== $code ) {
		return new WP_REST_Response( array( 'ok' => false ), 404 );
	}
	msh_poster_ml( 'PUT', '/subscribers/' . rawurlencode( $email ), array(
		'fields' => array( 'linkedin_connect_clicked' => gmdate( 'Y-m-d' ) ),
	) );
	return new WP_REST_Response( array( 'ok' => true ), 200 );
}
