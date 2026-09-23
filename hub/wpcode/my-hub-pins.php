/* My Hub: the pages a member has chosen for their own front page.
   WPCode snippet, type "PHP Snippet", location "Run Everywhere", on
   medsalesintelligencehub.co.uk only. Paste from the line below this comment
   (WPCode adds the opening PHP tag itself).

   Source of truth: hub/wpcode/my-hub-pins.php in louisehoult-beep/msh-compare-data.
   Edit it there, then paste it here again. Read by app/my-hub.js.

   Stores a list of catalogue ids (hub/my-hub-catalogue.json) in user meta
   msh_hub_pins. Logged-in members only, each reads and writes their own list,
   nothing else. Separate from the existing /msh/v1/prefs endpoint, which is
   left exactly as it is. */

add_action('rest_api_init', function () {
    register_rest_route('msh/v1', '/my-hub', array(
        array(
            'methods'             => 'GET',
            'permission_callback' => function () { return is_user_logged_in(); },
            'callback'            => function () {
                $uid  = get_current_user_id();
                $pins = get_user_meta($uid, 'msh_hub_pins', true);
                return array(
                    'saved' => metadata_exists('user', $uid, 'msh_hub_pins'),
                    'pins'  => is_array($pins) ? array_values($pins) : array(),
                );
            },
        ),
        array(
            'methods'             => 'POST',
            'permission_callback' => function () { return is_user_logged_in(); },
            'callback'            => function (WP_REST_Request $req) {
                $in = $req->get_param('pins');
                if (!is_array($in)) {
                    return new WP_Error('msh_bad_pins', 'pins must be a list', array('status' => 400));
                }
                $out = array();
                foreach ($in as $id) {
                    $id = sanitize_key(is_string($id) ? $id : '');
                    if ($id !== '' && strlen($id) <= 80 && !in_array($id, $out, true)) { $out[] = $id; }
                    if (count($out) >= 150) { break; }
                }
                update_user_meta(get_current_user_id(), 'msh_hub_pins', $out);
                return array('saved' => true, 'pins' => $out);
            },
        ),
    ));
});

/* REST cookie auth needs a wp_rest nonce on the page. Printed for logged-in
   members only. */
add_action('wp_footer', function () {
    if (!is_user_logged_in()) { return; }
    echo '<script>window.mshRestNonce=' . wp_json_encode(wp_create_nonce('wp_rest')) . ';</script>';
}, 5);
