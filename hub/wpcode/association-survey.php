/* Association for Industry Professional Nurses: member survey form.
   Added 23/10/2026 (Lou: answers collected in a form with drop-downs, an
   "Other" box and free text, not by email reply).

   WPCode snippet, type "PHP Snippet", location "Run Everywhere", on
   medsalesintelligencehub.co.uk only. Paste from the line below this comment
   (WPCode adds the opening PHP tag itself).

   Source of truth: hub/wpcode/association-survey.php in
   louisehoult-beep/msh-compare-data. Edit it there, paste it again, confirm
   the stored code by SHA-256.

   [msh_assoc_survey] renders the form on a public page. The form posts to
   /wp-json/msh-assoc/v1/survey, which writes the answers to the member's
   MailerLite record (fields work_setting, work_setting_other,
   role_description, resources_wanted, resources_other, revalidation_issues,
   revalidation_note, networking_now, networking_event, event_format,
   event_location, survey_comments, survey_completed). It only updates a
   subscriber who is already in the association group; it never creates one.
   Same MailerLite key as the join snippet (the WooCommerce plugin's). */

if ( ! defined( 'MSH_ASSOC_SURVEY_GROUP' ) ) {
	define( 'MSH_ASSOC_SURVEY_GROUP', '202112609174946953' );
}

function msh_assoc_survey_ml( $method, $path, $payload = null ) {
	$key = defined( 'MSH_ML_API_KEY' ) && MSH_ML_API_KEY ? MSH_ML_API_KEY : '';
	if ( ! $key ) {
		$o   = get_option( 'woo_mailerlite_options', array() );
		$key = ( is_array( $o ) && ! empty( $o['apiKey'] ) ) ? $o['apiKey'] : '';
	}
	if ( ! $key ) {
		return array( 0, array() );
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
		return array( 0, array() );
	}
	$body = json_decode( wp_remote_retrieve_body( $r ), true );
	return array( (int) wp_remote_retrieve_response_code( $r ), is_array( $body ) ? $body : array() );
}

add_action( 'rest_api_init', function () {
	register_rest_route( 'msh-assoc/v1', '/survey', array(
		'methods'             => 'POST',
		'permission_callback' => '__return_true',
		'callback'            => 'msh_assoc_survey_save',
	) );
} );

function msh_assoc_survey_save( WP_REST_Request $req ) {
	$p = $req->get_params();
	if ( ! empty( $p['website_url'] ) ) {
		return new WP_REST_Response( array( 'ok' => true ), 200 ); // honeypot
	}
	$email = isset( $p['email'] ) ? strtolower( sanitize_email( $p['email'] ) ) : '';
	if ( ! is_email( $email ) ) {
		return new WP_REST_Response( array( 'ok' => false, 'error' => 'email' ), 400 );
	}

	$ip  = isset( $_SERVER['REMOTE_ADDR'] ) ? (string) $_SERVER['REMOTE_ADDR'] : '';
	$k_e = 'msh_assoc_svrl_' . md5( $email );
	$k_i = 'msh_assoc_svrli_' . md5( $ip );
	if ( (int) get_transient( $k_e ) >= 5 || (int) get_transient( $k_i ) >= 30 ) {
		return new WP_REST_Response( array( 'ok' => false, 'error' => 'limit' ), 429 );
	}
	set_transient( $k_e, (int) get_transient( $k_e ) + 1, DAY_IN_SECONDS );
	set_transient( $k_i, (int) get_transient( $k_i ) + 1, DAY_IN_SECONDS );

	// Only people already in the association group.
	list( $code, $body ) = msh_assoc_survey_ml( 'GET', '/subscribers/' . rawurlencode( $email ) );
	$in_group = false;
	if ( 200 === $code && ! empty( $body['data']['groups'] ) ) {
		foreach ( $body['data']['groups'] as $g ) {
			if ( isset( $g['id'] ) && (string) $g['id'] === MSH_ASSOC_SURVEY_GROUP ) {
				$in_group = true;
			}
		}
	}
	if ( ! $in_group ) {
		return new WP_REST_Response( array( 'ok' => false, 'error' => 'notfound' ), 404 );
	}

	$short = array( 'work_setting', 'work_setting_other', 'revalidation_issues', 'networking_now', 'networking_event', 'event_format', 'event_location' );
	$long  = array( 'role_description', 'resources_other', 'revalidation_note', 'survey_comments' );
	$fields = array();
	foreach ( $short as $k ) {
		if ( isset( $p[ $k ] ) && '' !== trim( (string) $p[ $k ] ) ) {
			$fields[ $k ] = substr( sanitize_text_field( $p[ $k ] ), 0, 200 );
		}
	}
	foreach ( $long as $k ) {
		if ( isset( $p[ $k ] ) && '' !== trim( (string) $p[ $k ] ) ) {
			$fields[ $k ] = substr( sanitize_textarea_field( $p[ $k ] ), 0, 1500 );
		}
	}
	if ( ! empty( $p['resources_wanted'] ) && is_array( $p['resources_wanted'] ) ) {
		$fields['resources_wanted'] = substr( implode( '; ', array_map( 'sanitize_text_field', $p['resources_wanted'] ) ), 0, 500 );
	}
	if ( ! $fields ) {
		return new WP_REST_Response( array( 'ok' => false, 'error' => 'empty' ), 400 );
	}
	$fields['survey_completed'] = gmdate( 'Y-m-d H:i' );

	list( $code ) = msh_assoc_survey_ml( 'POST', '/subscribers', array( 'email' => $email, 'fields' => $fields ) );
	if ( $code < 200 || $code > 299 ) {
		return new WP_REST_Response( array( 'ok' => false, 'error' => 'save' ), 502 );
	}
	return new WP_REST_Response( array( 'ok' => true ), 200 );
}

add_shortcode( 'msh_assoc_survey', function () {
	if ( ! defined( 'DONOTCACHEPAGE' ) ) {
		define( 'DONOTCACHEPAGE', true );
	}
	$url = esc_url_raw( rest_url( 'msh-assoc/v1/survey' ) );
	$opt = function ( $list ) {
		$h = '<option value="">Choose one</option>';
		foreach ( $list as $o ) {
			$h .= '<option>' . esc_html( $o ) . '</option>';
		}
		return $h;
	};
	$setting = array( 'Medical device company', 'Pharmaceutical company', 'Diagnostics company', 'Digital health or health technology company', 'Recruitment or consultancy', 'Education or training provider', 'Charity, professional body or regulator', 'Other' );
	$yn      = array( 'Yes', 'No', 'Not sure' );
	$res     = array( 'Revalidation support and templates', 'Moving from the NHS into industry guidance', 'Career pathways and job roles', 'Clinical evidence and product training', 'Compliance guidance (ABPI, ethics, conduct)', 'Peer networking and mentoring', 'Webinars and events', 'Job opportunities' );
	$boxes   = '';
	foreach ( $res as $i => $r ) {
		$boxes .= '<label class="aipns-chk"><input type="checkbox" name="resources_wanted[]" value="' . esc_attr( $r ) . '"> ' . esc_html( $r ) . '</label>';
	}
	ob_start();
	?>
<style>
body .wp-site-blocks .aipns{max-width:720px;margin:0 auto;padding:0 20px;font-family:Arial,Helvetica,sans-serif;color:#1D2733}
body .wp-site-blocks .aipns h2{color:#0B1C33;font-size:24px;margin:34px 0 6px}
body .wp-site-blocks .aipns p,body .wp-site-blocks .aipns label{color:#1D2733;font-size:16px;line-height:1.55}
body .wp-site-blocks .aipns .aipns-q{margin:20px 0 6px;font-weight:bold;color:#0B1C33;display:block}
body .wp-site-blocks .aipns select,body .wp-site-blocks .aipns input[type=text],body .wp-site-blocks .aipns input[type=email],body .wp-site-blocks .aipns textarea{width:100%;box-sizing:border-box;padding:12px;font-size:16px;border:1px solid #8795A8;border-radius:4px;background:#fff;color:#1D2733}
body .wp-site-blocks .aipns textarea{min-height:96px}
body .wp-site-blocks .aipns .aipns-chk{display:block;margin:8px 0;font-weight:normal}
body .wp-site-blocks .aipns .aipns-chk input{margin-right:8px}
body .wp-site-blocks .aipns .aipns-other{display:none;margin-top:8px}
body .wp-site-blocks .aipns button{margin:28px 0 10px;background:#0B1C33;color:#fff;border:0;border-radius:4px;padding:14px 32px;font-size:16px;font-weight:bold;cursor:pointer}
body .wp-site-blocks .aipns .aipns-msg{margin:12px 0;font-weight:bold}
body .wp-site-blocks .aipns .aipns-hp{position:absolute;left:-9999px}
</style>
<div class="aipns">
<form id="aipns-form" novalidate>
<p>Answer as many or as few as you like. Every question is optional apart from your email. Nothing here is shared with anyone outside the association.</p>
<label class="aipns-q" for="aipns-email">Your email address (the one you joined with)</label>
<input type="email" id="aipns-email" name="email" autocomplete="email" required>

<h2>About you</h2>
<label class="aipns-q" for="work_setting">Where do you work?</label>
<select id="work_setting" name="work_setting"><?php echo $opt( $setting ); // phpcs:ignore ?></select>
<div class="aipns-other" id="work_setting_other_wrap"><input type="text" name="work_setting_other" placeholder="Please tell us where you work" maxlength="200"></div>
<label class="aipns-q" for="role_description">In a few lines, what do you do day to day?</label>
<textarea id="role_description" name="role_description" maxlength="1500"></textarea>

<h2>Resources</h2>
<span class="aipns-q">Which resources would you find most helpful? Tick any.</span>
<?php echo $boxes; // phpcs:ignore ?>
<label class="aipns-chk"><input type="checkbox" id="res_other_tick"> Something else</label>
<div class="aipns-other" id="resources_other_wrap"><textarea name="resources_other" placeholder="Tell us what would help" maxlength="1500"></textarea></div>

<h2>Revalidation</h2>
<label class="aipns-q" for="revalidation_issues">Have you had any difficulty keeping up with revalidation while working in industry?</label>
<select id="revalidation_issues" name="revalidation_issues"><?php echo $opt( array( 'No difficulty', 'Some difficulty', 'A lot of difficulty', 'I am not sure how revalidation applies to my role', 'Other' ) ); // phpcs:ignore ?></select>
<div class="aipns-other" id="revalidation_issues_other_wrap"></div>
<label class="aipns-q" for="revalidation_note">What got in the way, or what would make it easier? (practice hours, reflection, evidence of practice, anything else)</label>
<textarea id="revalidation_note" name="revalidation_note" maxlength="1500"></textarea>

<h2>Networking</h2>
<label class="aipns-q" for="networking_now">Do you network with other nurses working in industry?</label>
<select id="networking_now" name="networking_now"><?php echo $opt( array( 'Yes, regularly', 'Occasionally', 'No, but I would like to', 'No, and I do not need to' ) ); // phpcs:ignore ?></select>
<label class="aipns-q" for="networking_event">Would you be interested in a networking event for industry nurses?</label>
<select id="networking_event" name="networking_event"><?php echo $opt( array( 'Yes', 'Maybe', 'No' ) ); // phpcs:ignore ?></select>
<label class="aipns-q" for="event_format">Would you prefer in person or online?</label>
<select id="event_format" name="event_format"><?php echo $opt( array( 'In person', 'Online', 'Either' ) ); // phpcs:ignore ?></select>
<label class="aipns-q" for="event_location">Roughly where are you based? (town, city or region)</label>
<input type="text" id="event_location" name="event_location" maxlength="200">

<h2>Anything else</h2>
<label class="aipns-q" for="survey_comments">Is there anything else you would like to tell us?</label>
<textarea id="survey_comments" name="survey_comments" maxlength="1500"></textarea>

<div class="aipns-hp"><input type="text" name="website_url" tabindex="-1" autocomplete="off"></div>
<button type="submit" id="aipns-go">Send my answers</button>
<div class="aipns-msg" id="aipns-msg" role="status"></div>
</form>
</div>
<script>
(function(){
var f=document.getElementById('aipns-form'),m=document.getElementById('aipns-msg');
function tog(sel,wrap,val){var s=document.getElementById(sel),w=document.getElementById(wrap);s.addEventListener('change',function(){w.style.display=(s.value===val)?'block':'none';});}
tog('work_setting','work_setting_other_wrap','Other');
document.getElementById('res_other_tick').addEventListener('change',function(e){document.getElementById('resources_other_wrap').style.display=e.target.checked?'block':'none';});
var rs=document.getElementById('revalidation_issues');
rs.addEventListener('change',function(){var w=document.getElementById('revalidation_issues_other_wrap');if(rs.value==='Other'){if(!w.firstChild){w.innerHTML='<input type="text" name="revalidation_other" placeholder="Please tell us more" maxlength="200">';}w.style.display='block';}else{w.style.display='none';}});
f.addEventListener('submit',function(ev){
ev.preventDefault();m.style.color='#0B1C33';
var d=new FormData(f),o={resources_wanted:[]};
d.forEach(function(v,k){if(k==='resources_wanted[]'){o.resources_wanted.push(v);}else{o[k]=v;}});
if(!o.email||o.email.indexOf('@')<1){m.style.color='#9B1C1C';m.textContent='Please enter the email address you joined with.';return;}
if(!(!o.revalidation_other||o.revalidation_issues!=='Other')){o.revalidation_issues='Other: '+o.revalidation_other;}
if(!(o.work_setting!=='Other'||o.work_setting_other)){o.work_setting='Other';}
document.getElementById('aipns-go').disabled=true;m.textContent='Sending...';
fetch(<?php echo wp_json_encode( $url ); ?>,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(o)})
.then(function(r){return r.json().then(function(j){return[r.status,j];});})
.then(function(a){
if(!(!a[1]||!a[1].ok)){f.style.display='none';m.style.color='#0B1C33';m.textContent='Thank you. Your answers are saved and will shape what the association builds first.';}
else{document.getElementById('aipns-go').disabled=false;m.style.color='#9B1C1C';
m.textContent=(!(!a[1]||a[1].error!=='notfound'))?'We could not find that email address among our members. Please use the address you joined with.':(!(!a[1]||a[1].error!=='empty'))?'Please answer at least one question.':'Sorry, something went wrong. Please try again.';}
}).catch(function(){document.getElementById('aipns-go').disabled=false;m.style.color='#9B1C1C';m.textContent='Sorry, something went wrong. Please try again.';});
});
})();
</script>
	<?php
	return ob_get_clean();
} );
