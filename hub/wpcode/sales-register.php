/* Medical Sales Register: anyone working in medical sales, or moving into it,
   lists their experience, level and the roles they want; Hub Employers browse
   them without names or contact details and ask Elevate & Thrive for an
   introduction. Weekly jobs email through MailerLite. Added 14/10/2026,
   modelled on the Nursing Register (hub/wpcode/nursing-register.php).

   WPCode snippet, type "PHP Snippet", location "Run Everywhere", on
   medsalesintelligencehub.co.uk only. Paste from the line below this comment
   (WPCode adds the opening PHP tag itself). Needs the My Hub snippet (4503,
   hub/wpcode/my-hub-pins.php) active too: that prints window.mshRestNonce.
   Uses the MailerLite key the MailerLite WooCommerce plugin already holds on
   the Hub (as the "Hub sign-up -> MailerLite" snippet does). No key is stored
   here.

   Source of truth: hub/wpcode/sales-register.php in
   louisehoult-beep/msh-compare-data. Edit it there, then paste it here again.
   Read by app/sales-register.js. The tick lists below are the only copy: the
   page draws them from GET. Never rename an option id, saved profiles hold it.

   PERSONAL DATA. Profiles live in WordPress user meta on the Hub, never in
   this repo (it is public).

   WHO SEES WHAT
   * The member: their whole profile.
   * A Hub Employer or an admin: msh_sr_public(). No name, email, phone,
     LinkedIn or current employer. Only profiles made visible, with consent,
     confirmed in the last MSH_SR_STALE_DAYS days. The Hub Employer access
     is the SAME one the Nursing Register uses (role msh_employer, or the
     "Hub Employer" tick on the user screen, meta msh_nr_employer, or a live
     Hub Employer plan 5167): msh_nr_can_browse() from the Nursing Register
     snippet decides. One paid Hub Employer subscription covers both registers.
   * With the separate share consent (shareContact, dated shareAt), Hub
     Employers also get name, email, phone, LinkedIn and current employer.
   An employer's "Request introduction" emails Lou. Nothing goes to the
   employer until Lou has checked with the member.

   WEEKLY JOBS EMAIL, THROUGH MAILERLITE (Lou, 14/10/2026)
   Ticking jobsEmail puts the member in the MailerLite group for their region
   (msh_sr_ml_groups(), "Medical Sales Register jobs - <region>"); unticking,
   deleting or changing region takes them out of the others. Every Tuesday at
   08:00 UK time, after the supplier careers refresh (Tuesdays 03:40 UTC), one
   MailerLite campaign per region group with subscribers: new roles in that
   region plus UK-wide ones, grouped by role type and level, read from
   data/supplier-careers.json in this repo. Roles already sent to a region are
   not sent again (option msh_sr_ml_sent). Nothing new, no campaign.
   MailerLite handles the unsubscribe link. MSH_SR_ML_SEND false makes the
   campaigns drafts instead of sending them.

   ROUTES (logged-in only, wp_rest nonce)
   GET    /wp-json/msh/v1/sales-register         { options, profile, canBrowse, isAdmin, links }
   POST   /wp-json/msh/v1/sales-register         save own profile; emails a copy (msh_sr_summary_email)
   DELETE /wp-json/msh/v1/sales-register         delete own profile
   POST   /wp-json/msh/v1/sales-register/cv      { text } -> suggested ticks; nothing stored
   GET    /wp-json/msh/v1/sales-register/roles   { generatedOn, roles }  live roles, typed
   GET    /wp-json/msh/v1/sales-register/browse  { profiles }   Hub Employers, admins
   POST   /wp-json/msh/v1/sales-register/intro   { ref, message } Hub Employers, admins
   ADMIN CHECK (sends nothing): /?msh_sr_ml_check=1 shows the MailerLite key
   state, groups, next run and the log. /?msh_sr_ml_check=draft builds this
   week's campaigns as DRAFTS so they can be previewed in MailerLite.

   User meta: msh_sales_register (the profile), msh_sales_ref (its public
   reference), msh_sr_intro_log (an employer's requests today).
   The pure functions are tested by test_sales_register.py. */

if ( ! defined( 'MSH_SR_STALE_DAYS' ) ) {
	define( 'MSH_SR_STALE_DAYS', 365 );
}
if ( ! defined( 'MSH_SR_INTROS_PER_DAY' ) ) {
	define( 'MSH_SR_INTROS_PER_DAY', 10 );
}
if ( ! defined( 'MSH_SR_ML_SEND' ) ) {
	define( 'MSH_SR_ML_SEND', true );
}
if ( ! defined( 'MSH_SR_CAREERS_URL' ) ) {
	define( 'MSH_SR_CAREERS_URL', 'https://raw.githubusercontent.com/louisehoult-beep/msh-compare-data/main/data/supplier-careers.json' );
}
if ( ! defined( 'MSH_SR_PAGE' ) ) {
	define( 'MSH_SR_PAGE', '/medical-sales-register/' );
}

if ( ! function_exists( 'msh_sr_options' ) ) {
	function msh_sr_options() {
		return array(
			'regions' => array(
				'north-east' => 'North East', 'north-west' => 'North West', 'yorkshire-humber' => 'Yorkshire and the Humber',
				'east-midlands' => 'East Midlands', 'west-midlands' => 'West Midlands', 'east-of-england' => 'East of England',
				'london' => 'London', 'south-east' => 'South East', 'south-west' => 'South West',
				'wales' => 'Wales', 'scotland' => 'Scotland', 'northern-ireland' => 'Northern Ireland',
			),
			'travel' => array(
				'local' => 'Local only (about 30 miles)', 'region' => 'Across my region',
				'multi-region' => 'Several regions', 'national' => 'UK-wide',
			),
			'levels' => array(
				'entry' => 'Trainee or first role in medical sales', 'experienced' => 'Experienced (two years or more)',
				'senior' => 'Senior or specialist', 'manager' => 'First-line manager (area or regional)',
				'senior-manager' => 'Senior manager (national, head of)', 'director' => 'Director or above',
			),
			'roles' => array(
				'field-sales' => 'Territory manager or sales representative', 'kam' => 'Key account manager',
				'clinical-specialist' => 'Clinical specialist', 'theatre-specialist' => 'Theatre or procedure specialist',
				'product-specialist' => 'Product specialist', 'clinical-educator' => 'Clinical educator or trainer',
				'sales-trainer' => 'Sales trainer or learning and development', 'sales-manager' => 'Area or regional sales manager',
				'national-manager' => 'National sales manager or head of sales', 'director' => 'Sales or commercial director',
				'product-manager' => 'Product manager', 'marketing' => 'Marketing',
				'market-access' => 'Market access or NHS liaison', 'tenders' => 'Tenders and bids',
				'business-development' => 'Business development', 'inside-sales' => 'Inside sales or customer service',
				'service-engineer' => 'Field service or technical support', 'medical-affairs' => 'Medical affairs or medical science liaison',
				'recruiter' => 'Medical sales recruitment',
			),
			'background' => array(
				'medical-sales' => 'Already in medical sales', 'pharma' => 'Pharmaceutical sales',
				'other-sales' => 'Business-to-business sales outside healthcare', 'clinical' => 'Clinician (nurse, operating department practitioner, allied health)',
				'graduate' => 'Graduate', 'armed-forces' => 'Armed forces', 'other' => 'Another career',
			),
			'areas' => array(
				'wound-care' => 'Wound care', 'orthopaedics' => 'Orthopaedics and spine', 'cardiology' => 'Cardiology and vascular',
				'surgical' => 'General surgery and theatres', 'critical-care' => 'Critical care and anaesthesia', 'endoscopy' => 'Endoscopy',
				'urology' => 'Urology and continence', 'ostomy' => 'Ostomy', 'diabetes' => 'Diabetes', 'respiratory' => 'Respiratory',
				'neurology' => 'Neurology', 'ophthalmology' => 'Ophthalmology', 'ent' => 'Ear, nose and throat', 'womens-health' => "Women's health",
				'oncology' => 'Oncology', 'renal' => 'Renal', 'diagnostics' => 'Diagnostics and laboratory', 'imaging' => 'Imaging',
				'capital' => 'Capital equipment', 'consumables' => 'Clinical consumables', 'community-equipment' => 'Mobility and community equipment',
				'infection-prevention' => 'Infection prevention', 'dental' => 'Dental', 'aesthetics' => 'Aesthetics',
				'digital' => 'Digital health and software', 'pharma-primary' => 'Pharmaceuticals, primary care',
				'pharma-secondary' => 'Pharmaceuticals, hospital', 'nutrition' => 'Nutrition',
			),
			'customers' => array(
				'surgeons' => 'Surgeons and theatre teams', 'ward-nurses' => 'Ward and specialist nurses', 'procurement' => 'Procurement and supply chain',
				'icb' => 'Integrated care boards and medicines management', 'gp' => 'General practice and primary care', 'pharmacy' => 'Pharmacists',
				'community' => 'Community and district nursing', 'care-homes' => 'Care homes', 'private' => 'Private hospitals',
				'engineering' => 'Clinical engineering and estates', 'finance' => 'Finance and executive teams', 'distributors' => 'Distributors and wholesalers',
			),
			'skills' => array(
				'new-business' => 'Winning new business', 'account-growth' => 'Growing existing accounts', 'tenders' => 'Tenders and framework bids',
				'business-case' => 'Writing business cases and value propositions', 'evaluations' => 'Running product evaluations and trials',
				'theatre-support' => 'Supporting cases in theatre', 'kol' => 'Working with key opinion leaders', 'launch' => 'Product launches',
				'presenting' => 'Presenting and running training sessions', 'forecasting' => 'Forecasting and customer relationship management systems',
				'negotiation' => 'Negotiating contracts and pricing', 'territory-planning' => 'Territory and account planning',
				'coaching' => 'Coaching and managing a team', 'hiring' => 'Recruiting and onboarding', 'budget' => 'Budget or profit and loss',
				'market-analysis' => 'Market analysis and insight', 'virtual-selling' => 'Remote and virtual selling',
				'nhs-structures' => 'Knowledge of NHS structures and buying', 'clinical-setting' => 'At ease in clinical settings (theatre, cath lab, wards)',
				'compliance' => 'Selling compliantly to industry codes of practice',
			),
			'qualifications' => array(
				'degree' => 'Degree', 'life-science' => 'Life science or healthcare degree', 'abpi' => 'Association of the British Pharmaceutical Industry (ABPI) Representatives Examination',
				'clinical-registration' => 'Clinical registration (Nursing and Midwifery Council (NMC) or Health and Care Professions Council (HCPC))', 'sales-method' => 'Formal sales methodology training',
				'management-qual' => 'Management or leadership qualification', 'masters' => "Master's degree or Master of Business Administration (MBA)",
				'et-programme' => 'Elevate & Thrive Medical Sales Training Programme',
			),
			'availability' => array(
				'now' => 'Available now', '1-month' => 'Within a month', '3-months' => 'Within three months',
				'6-months' => 'Within six months', 'exploring' => 'Exploring, no rush',
			),
			'notice' => array(
				'none' => 'No notice', '1-month' => 'One month', '2-months' => 'Two months', '3-months' => 'Three months or more',
			),
			'salary' => array(
				'under-30' => 'Under £30,000', '30-40' => '£30,000 to £40,000', '40-50' => '£40,000 to £50,000', '50-60' => '£50,000 to £60,000',
				'60-75' => '£60,000 to £75,000', '75-100' => '£75,000 to £100,000', 'over-100' => 'Over £100,000',
			),
		);
	}
}

if ( ! function_exists( 'msh_sr_career_links' ) ) {
	/* Shown after a member submits and in their confirmation email. Each URL
	   answered 200 on the Hub on 14/10/2026. */
	function msh_sr_career_links() {
		return array(
			array( 'label' => 'Career Centre: live roles and recruiters', 'url' => '/medical-sales-hub/careers/', 'main' => true ),
			array( 'label' => 'Interview prep', 'url' => '/medical-sales-hub/interview-prep/', 'main' => true ),
			array( 'label' => 'Clinical to commercial routes', 'url' => '/medical-sales-hub/clinical-to-commercial-routes/', 'main' => false ),
			array( 'label' => 'Nursing Register', 'url' => '/clinical-hub/nursing-register/', 'main' => false ),
		);
	}
}

if ( ! function_exists( 'msh_sr_cv_terms' ) ) {
	/* Words in a CV that mean an option applies. Lower case, matched on whole
	   words after punctuation is flattened. No entry: matched on its label. */
	function msh_sr_cv_terms() {
		return array(
			'roles' => array(
				'field-sales' => array( 'territory manager', 'sales representative', 'sales rep', 'territory sales', 'sales executive', 'area sales executive' ),
				'kam' => array( 'key account manager', 'key account', 'kam', 'account manager', 'strategic account' ),
				'clinical-specialist' => array( 'clinical specialist', 'clinical application specialist', 'clinical applications' ),
				'theatre-specialist' => array( 'theatre specialist', 'surgical specialist', 'procedure specialist', 'case support' ),
				'product-specialist' => array( 'product specialist' ),
				'clinical-educator' => array( 'clinical educator', 'clinical trainer', 'clinical nurse educator', 'education specialist' ),
				'sales-trainer' => array( 'sales trainer', 'learning and development', 'sales training manager' ),
				'sales-manager' => array( 'regional sales manager', 'area sales manager', 'regional manager', 'area manager', 'rsm', 'asm', 'regional business manager' ),
				'national-manager' => array( 'national sales manager', 'head of sales', 'nsm', 'national account manager' ),
				'director' => array( 'sales director', 'commercial director', 'general manager', 'managing director', 'vp sales', 'vice president' ),
				'product-manager' => array( 'product manager', 'brand manager', 'portfolio manager' ),
				'marketing' => array( 'marketing manager', 'marketing executive', 'product marketing', 'marketing' ),
				'market-access' => array( 'market access', 'nhs liaison', 'healthcare economics', 'health economics', 'value based' ),
				'tenders' => array( 'tender', 'tenders', 'bid manager', 'bid writer', 'bids' ),
				'business-development' => array( 'business development' ),
				'inside-sales' => array( 'inside sales', 'customer service', 'internal sales', 'telesales' ),
				'service-engineer' => array( 'field service', 'service engineer', 'biomedical engineer', 'technical support' ),
				'medical-affairs' => array( 'medical science liaison', 'msl', 'medical affairs' ),
				'recruiter' => array( 'recruitment consultant', 'recruiter', 'talent acquisition' ),
			),
			'background' => array(
				'medical-sales' => array( 'medical device', 'medical devices', 'medtech', 'medical technology', 'territory manager', 'clinical specialist' ),
				'pharma' => array( 'pharmaceutical', 'pharma', 'abpi' ),
				'other-sales' => array( 'b2b', 'business to business', 'field sales', 'new business', 'sales executive' ),
				'clinical' => array( 'registered nurse', 'staff nurse', 'operating department practitioner', 'odp', 'nmc', 'hcpc', 'physiotherapist', 'radiographer', 'paramedic' ),
				'graduate' => array( 'graduate', 'graduated' ),
				'armed-forces' => array( 'royal navy', 'royal air force', 'raf', 'british army', 'armed forces', 'royal marines' ),
				'other' => array(),
			),
			'areas' => array(
				'wound-care' => array( 'wound care', 'wound management', 'tissue viability', 'npwt', 'negative pressure' ),
				'orthopaedics' => array( 'orthopaedic', 'orthopaedics', 'spine', 'spinal', 'trauma', 'arthroplasty', 'joint replacement' ),
				'cardiology' => array( 'cardiology', 'cardiac', 'cardiovascular', 'vascular', 'electrophysiology', 'interventional cardiology' ),
				'surgical' => array( 'general surgery', 'surgical', 'theatres', 'theatre', 'operating theatre', 'laparoscopic', 'energy devices' ),
				'critical-care' => array( 'critical care', 'intensive care', 'icu', 'anaesthesia', 'anaesthetic' ),
				'endoscopy' => array( 'endoscopy', 'endoscopic' ),
				'urology' => array( 'urology', 'continence', 'catheter', 'catheters' ),
				'ostomy' => array( 'ostomy', 'stoma' ),
				'diabetes' => array( 'diabetes', 'insulin', 'cgm', 'glucose monitoring' ),
				'respiratory' => array( 'respiratory', 'inhaler', 'inhalers', 'ventilation', 'sleep apnoea' ),
				'neurology' => array( 'neurology', 'neurosurgery', 'neuromodulation', 'neuro' ),
				'ophthalmology' => array( 'ophthalmology', 'ophthalmic', 'cataract', 'eye care' ),
				'ent' => array( 'ent', 'ear nose and throat', 'audiology', 'hearing' ),
				'womens-health' => array( 'women s health', 'womens health', 'gynaecology', 'obstetrics', 'maternity' ),
				'oncology' => array( 'oncology', 'cancer', 'radiotherapy' ),
				'renal' => array( 'renal', 'dialysis', 'nephrology' ),
				'diagnostics' => array( 'diagnostics', 'diagnostic', 'ivd', 'in vitro', 'laboratory', 'point of care' ),
				'imaging' => array( 'imaging', 'ultrasound', 'radiology', 'mri', 'x ray', 'ct' ),
				'capital' => array( 'capital equipment', 'capital sales', 'capital' ),
				'consumables' => array( 'consumables', 'disposables' ),
				'community-equipment' => array( 'mobility', 'community equipment', 'moving and handling', 'pressure care', 'wheelchair', 'hoists' ),
				'infection-prevention' => array( 'infection prevention', 'infection control', 'decontamination', 'sterilisation' ),
				'dental' => array( 'dental', 'dentist', 'orthodontic' ),
				'aesthetics' => array( 'aesthetics', 'aesthetic', 'dermal' ),
				'digital' => array( 'digital health', 'software', 'saas', 'healthtech', 'health tech' ),
				'pharma-primary' => array( 'primary care', 'gp surgeries', 'general practice' ),
				'pharma-secondary' => array( 'secondary care', 'hospital pharmacy', 'specialty care' ),
				'nutrition' => array( 'nutrition', 'enteral', 'clinical nutrition' ),
			),
			'customers' => array(
				'surgeons' => array( 'surgeons', 'surgeon', 'consultants', 'theatre teams', 'theatre staff' ),
				'ward-nurses' => array( 'nurse specialists', 'ward nurses', 'specialist nurses', 'clinical nurse specialists', 'nursing teams' ),
				'procurement' => array( 'procurement', 'supply chain', 'purchasing', 'buyers' ),
				'icb' => array( 'icb', 'icbs', 'integrated care board', 'medicines management', 'medicines optimisation', 'ccg', 'formulary' ),
				'gp' => array( 'gp', 'gps', 'general practice', 'primary care', 'pcn' ),
				'pharmacy' => array( 'pharmacist', 'pharmacists', 'pharmacy' ),
				'community' => array( 'district nurses', 'community nurses', 'community teams', 'community nursing' ),
				'care-homes' => array( 'care home', 'care homes', 'nursing homes' ),
				'private' => array( 'private hospital', 'private hospitals', 'independent sector', 'private sector' ),
				'engineering' => array( 'clinical engineering', 'ebme', 'estates' ),
				'finance' => array( 'finance director', 'finance directors', 'c suite', 'executive team', 'board level', 'chief executive' ),
				'distributors' => array( 'distributor', 'distributors', 'wholesaler', 'wholesalers', 'dealer', 'dealers' ),
			),
			'skills' => array(
				'new-business' => array( 'new business', 'new accounts', 'business development', 'hunter', 'converted' ),
				'account-growth' => array( 'account growth', 'grew', 'growing accounts', 'account management', 'retention' ),
				'tenders' => array( 'tender', 'tenders', 'framework', 'frameworks', 'bid', 'bids' ),
				'business-case' => array( 'business case', 'business cases', 'value proposition', 'health economics', 'cost saving' ),
				'evaluations' => array( 'product evaluation', 'product evaluations', 'evaluation', 'evaluations', 'trial', 'trials' ),
				'theatre-support' => array( 'case support', 'theatre support', 'supporting cases', 'in theatre', 'scrubbed' ),
				'kol' => array( 'kol', 'kols', 'key opinion leader', 'key opinion leaders' ),
				'launch' => array( 'launch', 'launched', 'product launch' ),
				'presenting' => array( 'presented', 'presenting', 'presentations', 'training sessions', 'in service', 'study days' ),
				'forecasting' => array( 'crm', 'forecast', 'forecasting', 'pipeline management' ),
				'negotiation' => array( 'negotiation', 'negotiated', 'negotiating', 'pricing', 'contract' ),
				'territory-planning' => array( 'territory plan', 'territory planning', 'account plan', 'account planning', 'business plan' ),
				'coaching' => array( 'coaching', 'coached', 'line managed', 'line management', 'managed a team', 'team of', 'direct reports' ),
				'hiring' => array( 'recruited', 'recruiting', 'onboarding', 'hiring' ),
				'budget' => array( 'budget', 'p l', 'profit and loss' ),
				'market-analysis' => array( 'market analysis', 'market insight', 'market research', 'competitor analysis' ),
				'virtual-selling' => array( 'virtual', 'remote selling', 'virtual selling' ),
				'nhs-structures' => array( 'nhs structures', 'commissioning', 'icb', 'icbs', 'integrated care', 'nhs supply chain', 'nhs procurement' ),
				'clinical-setting' => array( 'theatre', 'theatres', 'cath lab', 'operating room', 'clinical environment', 'ward' ),
				'compliance' => array( 'abpi code', 'medtech europe', 'abhi', 'code of practice', 'compliance', 'compliantly' ),
			),
			'qualifications' => array(
				'degree' => array( 'bsc', 'ba hons', 'ba', 'bachelor', 'degree', 'beng', 'bn' ),
				'life-science' => array( 'biomedical science', 'biology', 'biological', 'life science', 'life sciences', 'pharmacology', 'sports science', 'physiology', 'biochemistry', 'nursing degree', 'bn' ),
				'abpi' => array( 'abpi' ),
				'clinical-registration' => array( 'nmc', 'hcpc', 'registered nurse', 'gphc' ),
				'sales-method' => array( 'spin selling', 'challenger', 'miller heiman', 'sales methodology', 'consultative selling', 'solution selling' ),
				'management-qual' => array( 'cmi', 'ilm', 'leadership programme', 'management qualification', 'leadership qualification' ),
				'masters' => array( 'msc', 'mba', 'master s', 'masters', 'ma' ),
				'et-programme' => array( 'elevate thrive', 'elevate and thrive', 'medical sales training programme' ),
			),
		);
	}
}

if ( ! function_exists( 'msh_sr_cv_suggest' ) ) {
	/* What a CV's text suggests for the form, to pre-tick before the member
	   checks it. Nothing is stored. Returns lists of option ids plus
	   yearsInSales and region where found. */
	function msh_sr_cv_suggest( $text ) {
		$o    = msh_sr_options();
		$t    = msh_sr_cv_terms();
		$flat = ' ' . trim( preg_replace( '/[^a-z0-9]+/', ' ', strtolower( (string) $text ) ) ) . ' ';
		$out  = array();
		foreach ( array( 'roles', 'background', 'areas', 'customers', 'skills', 'qualifications' ) as $k ) {
			$out[ $k ] = array();
			foreach ( $o[ $k ] as $id => $label ) {
				$terms = isset( $t[ $k ][ $id ] ) ? $t[ $k ][ $id ] : array( $label );
				foreach ( $terms as $term ) {
					$term = trim( preg_replace( '/[^a-z0-9]+/', ' ', strtolower( $term ) ) );
					if ( '' !== $term && false !== strpos( $flat, ' ' . $term . ' ' ) ) {
						$out[ $k ][] = (string) $id;
						break;
					}
				}
			}
		}
		/* A role on the CV is experience, not necessarily what they want, so
		   roles are suggested as "done", not "wanted". */
		$out['rolesDone'] = $out['roles'];
		unset( $out['roles'] );
		/* Years in sales: "X years" next to sales, the largest under 45. */
		$out['yearsInSales'] = null;
		if ( preg_match_all( '/(\d{1,2})\+?\s*years?[^.\n]{0,40}\b(?:sales|selling|commercial|industry)\b/', strtolower( (string) $text ), $m ) ) {
			$ys = array_filter( array_map( 'intval', $m[1] ), function ( $y ) { return $y > 0 && $y < 45; } );
			$out['yearsInSales'] = $ys ? max( $ys ) : null;
		}
		$regs          = msh_sr_job_regions( substr( (string) $text, 0, 500 ), '' );
		$out['region'] = 1 === count( $regs ) ? $regs[0] : '';
		return $out;
	}
}

if ( ! function_exists( 'msh_sr_text' ) ) {
	function msh_sr_text( $s, $max ) {
		if ( ! is_string( $s ) ) {
			return '';
		}
		$s = preg_replace( '/<[^>]*>/', '', $s );
		$s = trim( preg_replace( '/\s+/u', ' ', $s ) );
		return mb_substr( $s, 0, $max );
	}
}

if ( ! function_exists( 'msh_sr_scrub' ) ) {
	/* Employers see the bio, area and role title, so contact details typed
	   into them are taken out. */
	function msh_sr_scrub( $s ) {
		$s = preg_replace( '/[^\s@]+@[^\s@]+\.[^\s@]+/u', '[removed]', $s );
		$s = preg_replace( '/(?:https?:\/\/|www\.)\S+/iu', '[removed]', $s );
		$s = preg_replace( '/\+?\d[\d\s().-]{8,}\d/u', '[removed]', $s );
		return $s;
	}
}

if ( ! function_exists( 'msh_sr_pick' ) ) {
	/* Known ids from a list, in option order, each once. Unknown ids are
	   dropped, not refused. */
	function msh_sr_pick( $list, $allowed ) {
		if ( ! is_array( $list ) ) {
			return array();
		}
		$want = array();
		foreach ( $list as $v ) {
			if ( is_string( $v ) ) {
				$want[ $v ] = true;
			}
		}
		$out = array();
		foreach ( array_keys( $allowed ) as $id ) {
			if ( isset( $want[ (string) $id ] ) ) {
				$out[] = (string) $id;
			}
		}
		return $out;
	}
}

if ( ! function_exists( 'msh_sr_one' ) ) {
	function msh_sr_one( $v, $allowed ) {
		return ( is_string( $v ) && array_key_exists( $v, $allowed ) ) ? $v : '';
	}
}

if ( ! function_exists( 'msh_sr_flag' ) ) {
	function msh_sr_flag( $b, $k ) {
		return isset( $b[ $k ] ) && true === $b[ $k ];
	}
}

if ( ! function_exists( 'msh_sr_clean' ) ) {
	/* The profile to store from what the browser sent. $old: the stored
	   profile (or array()). $today: Y-m-d. $ref: the reference to use when
	   $old has none. Returns array( 'ok' => true, 'profile' => ... ) or
	   array( 'ok' => false, 'why' => field ). */
	function msh_sr_clean( $b, $old, $today, $ref ) {
		if ( ! is_array( $b ) ) {
			return array( 'ok' => false, 'why' => 'body' );
		}
		$o = msh_sr_options();

		$region = msh_sr_one( isset( $b['region'] ) ? $b['region'] : '', $o['regions'] );
		if ( '' === $region ) {
			return array( 'ok' => false, 'why' => 'region' );
		}
		$level = msh_sr_one( isset( $b['level'] ) ? $b['level'] : '', $o['levels'] );
		if ( '' === $level ) {
			return array( 'ok' => false, 'why' => 'level' );
		}
		$wanted = msh_sr_pick( isset( $b['roles'] ) ? $b['roles'] : array(), $o['roles'] );
		if ( ! $wanted ) {
			return array( 'ok' => false, 'why' => 'roles' );
		}
		$yrs = isset( $b['yearsInSales'] ) ? $b['yearsInSales'] : '';
		if ( is_string( $yrs ) && preg_match( '/^\d{1,2}$/', $yrs ) ) {
			$yrs = (int) $yrs;
		}
		if ( '' === $yrs || null === $yrs ) {
			$yrs = null;
		} elseif ( ! is_int( $yrs ) || $yrs < 0 || $yrs > 50 ) {
			return array( 'ok' => false, 'why' => 'yearsInSales' );
		}
		$tgt = isset( $b['targetPct'] ) ? $b['targetPct'] : '';
		if ( is_string( $tgt ) && preg_match( '/^\d{1,3}$/', $tgt ) ) {
			$tgt = (int) $tgt;
		}
		if ( '' === $tgt || null === $tgt ) {
			$tgt = null;
		} elseif ( ! is_int( $tgt ) || $tgt < 0 || $tgt > 500 ) {
			return array( 'ok' => false, 'why' => 'targetPct' );
		}
		$li = isset( $b['linkedin'] ) && is_string( $b['linkedin'] ) ? trim( $b['linkedin'] ) : '';
		if ( '' !== $li && ! preg_match( '#^https://([a-z]{2,3}\.)?linkedin\.com/in/[A-Za-z0-9_%-]{2,100}/?$#', $li ) ) {
			return array( 'ok' => false, 'why' => 'linkedin' );
		}
		$phone = isset( $b['phone'] ) && is_string( $b['phone'] ) ? trim( $b['phone'] ) : '';
		if ( '' !== $phone && ! preg_match( '/^\+?[\d\s()-]{10,20}$/', $phone ) ) {
			return array( 'ok' => false, 'why' => 'phone' );
		}
		$visible = msh_sr_flag( $b, 'visible' );
		$consent = msh_sr_flag( $b, 'consent' );
		if ( $visible && ! $consent ) {
			return array( 'ok' => false, 'why' => 'consent' );
		}
		$share = msh_sr_flag( $b, 'shareContact' );
		$old   = is_array( $old ) ? $old : array();
		$s     = function ( $k, $n ) use ( $b ) { return msh_sr_scrub( msh_sr_text( isset( $b[ $k ] ) ? $b[ $k ] : '', $n ) ); };
		$l     = function ( $k ) use ( $b, $o ) { return msh_sr_pick( isset( $b[ $k ] ) ? $b[ $k ] : array(), $o[ $k ] ); };
		$one   = function ( $k, $list ) use ( $b, $o ) { return msh_sr_one( isset( $b[ $k ] ) ? $b[ $k ] : '', $o[ $list ] ); };

		return array(
			'ok'      => true,
			'profile' => array(
				'v'               => 1,
				'ref'             => ( isset( $old['ref'] ) && is_string( $old['ref'] ) && '' !== $old['ref'] ) ? $old['ref'] : $ref,
				'region'          => $region,
				'area'            => $s( 'area', 60 ),
				'travel'          => $one( 'travel', 'travel' ),
				'relocate'        => msh_sr_flag( $b, 'relocate' ),
				'overnights'      => msh_sr_flag( $b, 'overnights' ),
				'level'           => $level,
				'yearsInSales'    => $yrs,
				'currentRole'     => $s( 'currentRole', 80 ),
				'rolesDone'       => msh_sr_pick( isset( $b['rolesDone'] ) ? $b['rolesDone'] : array(), $o['roles'] ),
				'roles'           => $wanted,
				'background'      => $l( 'background' ),
				'areas'           => $l( 'areas' ),
				'customers'       => $l( 'customers' ),
				'skills'          => $l( 'skills' ),
				'qualifications'  => $l( 'qualifications' ),
				'targetPct'       => $tgt,
				'achievement'     => $s( 'achievement', 200 ),
				'availability'    => $one( 'availability', 'availability' ),
				'notice'          => $one( 'notice', 'notice' ),
				'salary'          => $one( 'salary', 'salary' ),
				'driving'         => msh_sr_flag( $b, 'driving' ),
				'rightToWork'     => msh_sr_flag( $b, 'rightToWork' ),
				'jobsEmail'       => msh_sr_flag( $b, 'jobsEmail' ),
				'shareContact'    => $share,
				'shareAt'         => $share ? ( ( ! empty( $old['shareAt'] ) && ! empty( $old['shareContact'] ) ) ? $old['shareAt'] : $today ) : '',
				'bio'             => $s( 'bio', 600 ),
				'employer'        => msh_sr_text( isset( $b['employer'] ) ? $b['employer'] : '', 80 ),
				'phone'           => $phone,
				'linkedin'        => $li,
				'visible'         => $visible,
				'consentAt'       => $consent ? ( ( isset( $old['consentAt'] ) && $old['consentAt'] ) ? $old['consentAt'] : $today ) : '',
				'updated'         => $today,
			),
		);
	}
}

if ( ! function_exists( 'msh_sr_days_between' ) ) {
	function msh_sr_days_between( $from, $to ) {
		$a = strtotime( $from . ' 00:00:00 UTC' );
		$b = strtotime( $to . ' 00:00:00 UTC' );
		if ( false === $a || false === $b ) {
			return PHP_INT_MAX;
		}
		return (int) floor( ( $b - $a ) / 86400 );
	}
}

if ( ! function_exists( 'msh_sr_public' ) ) {
	/* What a Hub Employer sees, or null when the profile must not be shown:
	   not visible, no consent, or not confirmed within MSH_SR_STALE_DAYS.
	   Never the name, email, phone, LinkedIn or current employer. */
	function msh_sr_public( $p, $today ) {
		if ( ! is_array( $p ) || empty( $p['visible'] ) || empty( $p['consentAt'] ) || empty( $p['updated'] ) ) {
			return null;
		}
		if ( msh_sr_days_between( $p['updated'], $today ) > MSH_SR_STALE_DAYS ) {
			return null;
		}
		$keep = array( 'ref', 'region', 'area', 'travel', 'relocate', 'overnights', 'level', 'yearsInSales', 'currentRole',
			'rolesDone', 'roles', 'background', 'areas', 'customers', 'skills', 'qualifications', 'targetPct', 'achievement',
			'availability', 'notice', 'salary', 'driving', 'rightToWork', 'bio', 'updated' );
		$out = array();
		foreach ( $keep as $k ) {
			$out[ $k ] = isset( $p[ $k ] ) ? $p[ $k ] : null;
		}
		return $out;
	}
}

if ( ! function_exists( 'msh_sr_contact' ) ) {
	/* Contact details for Hub Employers, only with the separate share
	   consent. Call only for a profile msh_sr_public() shows. */
	function msh_sr_contact( $p, $name, $email ) {
		if ( ! is_array( $p ) || empty( $p['shareContact'] ) || true !== $p['shareContact'] || empty( $p['shareAt'] ) ) {
			return null;
		}
		return array(
			'name'     => (string) $name,
			'email'    => (string) $email,
			'phone'    => isset( $p['phone'] ) ? (string) $p['phone'] : '',
			'linkedin' => isset( $p['linkedin'] ) ? (string) $p['linkedin'] : '',
			'employer' => isset( $p['employer'] ) ? (string) $p['employer'] : '',
		);
	}
}

if ( ! function_exists( 'msh_sr_summary_email' ) ) {
	/* The copy a member gets each time they save. No phone number in it.
	   $home: the site's address with no trailing slash. */
	function msh_sr_summary_email( $first, $p, $home ) {
		$o  = msh_sr_options();
		$e  = function ( $s ) { return htmlspecialchars( (string) $s, ENT_QUOTES, 'UTF-8' ); };
		$ls = function ( $k, $opt = null ) use ( $o, $p ) {
			$opt = $opt ? $opt : $k;
			$out = array();
			foreach ( ( isset( $p[ $k ] ) && is_array( $p[ $k ] ) ) ? $p[ $k ] : array() as $id ) {
				if ( isset( $o[ $opt ][ $id ] ) ) {
					$out[] = $o[ $opt ][ $id ];
				}
			}
			return $out ? implode( ', ', $out ) : 'None ticked';
		};
		$one  = function ( $k, $v ) use ( $o ) { return ( '' !== (string) $v && isset( $o[ $k ][ $v ] ) ) ? $o[ $k ][ $v ] : 'Not given'; };
		$yes  = function ( $v ) { return $v ? 'Yes' : 'No'; };
		$rows = array(
			'Your reference'        => $p['ref'],
			'Region'                => $one( 'regions', $p['region'] ) . ( '' !== $p['area'] ? ', ' . $p['area'] : '' ),
			'Travel'                => $one( 'travel', $p['travel'] ) . ( $p['overnights'] ? '. Overnight stays fine' : '' ) . ( $p['relocate'] ? '. Would relocate' : '' ),
			'Level'                 => $one( 'levels', $p['level'] ),
			'Years in sales'        => null === $p['yearsInSales'] ? 'Not given' : $p['yearsInSales'],
			'Current role'          => '' !== $p['currentRole'] ? $p['currentRole'] : 'Not given',
			'Roles you have done'   => $ls( 'rolesDone', 'roles' ),
			'Roles you want'        => $ls( 'roles' ),
			'Background'            => $ls( 'background' ),
			'Therapy and product areas' => $ls( 'areas' ),
			'Customers you sell to' => $ls( 'customers' ),
			'Skills'                => $ls( 'skills' ),
			'Qualifications'        => $ls( 'qualifications' ),
			'Last full year against target' => null === $p['targetPct'] ? 'Not given' : $p['targetPct'] . '%',
			'Achievement'           => '' !== $p['achievement'] ? $p['achievement'] : 'Not given',
			'Could start'           => $one( 'availability', $p['availability'] ),
			'Notice period'         => $one( 'notice', $p['notice'] ),
			'Base salary looking for' => $one( 'salary', $p['salary'] ),
			'Full UK driving licence' => $yes( $p['driving'] ),
			'Right to work in the UK' => $yes( $p['rightToWork'] ),
			'Visible to employers'  => $yes( $p['visible'] ),
			'Recruiters may contact you directly' => $yes( ! empty( $p['shareContact'] ) ),
			'Weekly jobs email'     => $yes( ! empty( $p['jobsEmail'] ) ),
		);
		$h = '<div style="font-family:Arial,sans-serif;font-size:15px;line-height:1.5;color:#1D2733;max-width:600px">'
			. '<p>Hi' . ( '' !== (string) $first ? ' ' . $e( $first ) : '' ) . ',</p>'
			. '<p>Thank you, your Medical Sales Register profile is saved. Here is what you told us, so you have a copy.</p>'
			. '<table role="presentation" cellpadding="6" cellspacing="0" style="border-collapse:collapse;width:100%">';
		foreach ( $rows as $k => $v ) {
			$h .= '<tr><td style="border-bottom:1px solid #E6E2D8;color:#4A5666;vertical-align:top;width:40%">' . $e( $k ) . '</td><td style="border-bottom:1px solid #E6E2D8">' . $e( $v ) . '</td></tr>';
		}
		$h .= '</table><p style="margin-top:20px"><strong>Next steps for your career</strong></p><ul>';
		foreach ( msh_sr_career_links() as $l ) {
			$h .= '<li><a href="' . $e( $home . $l['url'] ) . '" style="color:#14304F">' . $e( $l['label'] ) . '</a></li>';
		}
		$h .= '</ul><p>To change anything, or to hide or delete your profile, go to <a href="' . $e( $home . MSH_SR_PAGE ) . '" style="color:#14304F">your register profile</a>.</p></div>';
		return array( 'subject' => 'Your Medical Sales Register profile is saved (' . $p['ref'] . ')', 'html' => $h );
	}
}

if ( ! function_exists( 'msh_sr_job_regions' ) ) {
	/* The register regions a role sits in, from its title and location, or an
	   empty list when it names none (UK-wide). Same mapping as the Nursing
	   Register's msh_nr_job_regions(); kept here so each snippet stands alone. */
	function msh_sr_job_regions( $title, $location ) {
		$s = ' ' . strtolower( preg_replace( '/[^A-Za-z0-9]+/', ' ', (string) $title . ' ' . (string) $location ) ) . ' ';
		$found = array();
		$areas = array(
			'north east' => array( 'north-east' ), 'north west' => array( 'north-west' ),
			'south east' => array( 'south-east' ), 'south west' => array( 'south-west' ),
			'east midlands' => array( 'east-midlands' ), 'west midlands' => array( 'west-midlands' ),
			'east of england' => array( 'east-of-england' ), 'east anglia' => array( 'east-of-england' ),
			'northern ireland' => array( 'northern-ireland' ), 'home counties' => array( 'south-east', 'east-of-england' ),
			'south coast' => array( 'south-east', 'south-west' ), 'east england' => array( 'east-of-england' ),
		);
		foreach ( $areas as $k => $rs ) {
			if ( false !== strpos( $s, ' ' . $k . ' ' ) ) {
				$found = array_merge( $found, $rs );
				$s     = str_replace( ' ' . $k . ' ', ' ', $s );
			}
		}
		$words = array(
			'scotland' => 'scotland', 'glasgow' => 'scotland', 'edinburgh' => 'scotland', 'dundee' => 'scotland', 'aberdeen' => 'scotland', 'inverness' => 'scotland',
			'wales' => 'wales', 'cardiff' => 'wales', 'swansea' => 'wales', 'newport' => 'wales', 'wrexham' => 'wales',
			'belfast' => 'northern-ireland',
			'london' => 'london', 'croydon' => 'london', 'romford' => 'london', 'rainham' => 'london', 'uxbridge' => 'london',
			'kent' => 'south-east', 'surrey' => 'south-east', 'sussex' => 'south-east', 'berkshire' => 'south-east', 'hampshire' => 'south-east',
			'oxford' => 'south-east', 'oxfordshire' => 'south-east', 'witney' => 'south-east', 'abingdon' => 'south-east', 'maidenhead' => 'south-east',
			'reading' => 'south-east', 'crawley' => 'south-east', 'sittingbourne' => 'south-east', 'camberley' => 'south-east', 'watchmoor' => 'south-east',
			'guildford' => 'south-east', 'brighton' => 'south-east', 'southampton' => 'south-east', 'portsmouth' => 'south-east', 'slough' => 'south-east',
			'milton keynes' => 'south-east', 'buckinghamshire' => 'south-east', 'maidstone' => 'south-east', 'basingstoke' => 'south-east', 'woking' => 'south-east',
			'bristol' => 'south-west', 'exeter' => 'south-west', 'plymouth' => 'south-west', 'devon' => 'south-west', 'cornwall' => 'south-west',
			'somerset' => 'south-west', 'gloucester' => 'south-west', 'gloucestershire' => 'south-west', 'swindon' => 'south-west', 'dorset' => 'south-west',
			'bournemouth' => 'south-west', 'bath' => 'south-west', 'wiltshire' => 'south-west', 'cheltenham' => 'south-west',
			'essex' => 'east-of-england', 'suffolk' => 'east-of-england', 'norfolk' => 'east-of-england', 'cambridge' => 'east-of-england',
			'cambridgeshire' => 'east-of-england', 'hertfordshire' => 'east-of-england', 'loughton' => 'east-of-england', 'chelmsford' => 'east-of-england',
			'norwich' => 'east-of-england', 'ipswich' => 'east-of-england', 'luton' => 'east-of-england', 'bedford' => 'east-of-england',
			'peterborough' => 'east-of-england', 'stevenage' => 'east-of-england', 'colchester' => 'east-of-england', 'welwyn' => 'east-of-england', 'elstree' => 'east-of-england',
			'birmingham' => 'west-midlands', 'solihull' => 'west-midlands', 'coventry' => 'west-midlands', 'wolverhampton' => 'west-midlands',
			'stoke' => 'west-midlands', 'staffordshire' => 'west-midlands', 'worcester' => 'west-midlands', 'hereford' => 'west-midlands',
			'shropshire' => 'west-midlands', 'warwickshire' => 'west-midlands', 'telford' => 'west-midlands',
			'nottingham' => 'east-midlands', 'leicester' => 'east-midlands', 'derby' => 'east-midlands', 'lincoln' => 'east-midlands',
			'northampton' => 'east-midlands', 'lincolnshire' => 'east-midlands', 'derbyshire' => 'east-midlands', 'nottinghamshire' => 'east-midlands',
			'yorkshire' => 'yorkshire-humber', 'leeds' => 'yorkshire-humber', 'sheffield' => 'yorkshire-humber', 'bradford' => 'yorkshire-humber',
			'york' => 'yorkshire-humber', 'hull' => 'yorkshire-humber', 'wakefield' => 'yorkshire-humber', 'humber' => 'yorkshire-humber', 'doncaster' => 'yorkshire-humber',
			'manchester' => 'north-west', 'liverpool' => 'north-west', 'lancashire' => 'north-west', 'cheshire' => 'north-west', 'preston' => 'north-west',
			'cumbria' => 'north-west', 'chester' => 'north-west', 'warrington' => 'north-west', 'bolton' => 'north-west', 'stockport' => 'north-west',
			'newcastle' => 'north-east', 'sunderland' => 'north-east', 'durham' => 'north-east', 'teesside' => 'north-east', 'middlesbrough' => 'north-east',
			'northumberland' => 'north-east', 'gateshead' => 'north-east',
		);
		foreach ( $words as $k => $r ) {
			if ( false !== strpos( $s, ' ' . $k . ' ' ) ) {
				$found[] = $r;
			}
		}
		if ( ! $found ) {
			if ( preg_match( '/ north /', $s ) ) {
				$found = array( 'north-east', 'north-west', 'yorkshire-humber' );
			} elseif ( preg_match( '/ (midlands|central) /', $s ) ) {
				$found = array( 'east-midlands', 'west-midlands' );
			}
		}
		return array_values( array_unique( $found ) );
	}
}

if ( ! function_exists( 'msh_sr_job_kind' ) ) {
	/* A role's type and level from its title, for grouping the weekly email
	   and the "Roles for you" list. type: a 'roles' option id or 'other';
	   level: a 'levels' option id or ''. A filing aid read from the title
	   only, never a claim about the role. Order matters: the first match wins. */
	function msh_sr_job_kind( $title ) {
		$s     = ' ' . strtolower( preg_replace( '/[^A-Za-z0-9]+/', ' ', (string) $title ) ) . ' ';
		$types = array(
			'director' => array( 'sales director', 'commercial director', 'general manager', 'managing director', 'country manager', 'vp sales', 'vice president sales', 'vp commercial' ),
			'national-manager' => array( 'national sales manager', 'head of sales', 'national account', 'head of commercial', 'national manager' ),
			'sales-manager' => array( 'regional sales manager', 'area sales manager', 'regional manager', 'area manager', 'regional business manager', 'sales manager', 'district manager', 'team leader' ),
			'medical-affairs' => array( 'medical science liaison', ' msl ', 'medical affairs', 'medical advisor' ),
			'market-access' => array( 'market access', 'nhs liaison', 'health economics', 'value based', 'reimbursement' ),
			'tenders' => array( 'tender', 'bid manager', 'bid writer', 'bid coordinator' ),
			'product-manager' => array( 'product manager', 'brand manager', 'portfolio manager', 'product owner' ),
			'marketing' => array( 'marketing' ),
			'clinical-educator' => array( 'clinical educator', 'clinical trainer', 'education specialist', 'educator', 'professional education' ),
			'sales-trainer' => array( 'sales trainer', 'sales training', 'learning and development', 'training manager' ),
			'theatre-specialist' => array( 'theatre specialist', 'surgical specialist', 'procedure specialist', 'case support', 'mako' ),
			'clinical-specialist' => array( 'clinical specialist', 'clinical application', 'clinical support specialist', 'clinical consultant', 'clinical development specialist', 'clinical solution specialist', 'clinical solutions specialist' ),
			'product-specialist' => array( 'product specialist' ),
			'kam' => array( 'key account', 'account manager', 'strategic account', 'account executive' ),
			'business-development' => array( 'business development', 'bdm' ),
			'field-sales' => array( 'territory manager', 'territory sales', 'sales representative', 'sales rep', 'sales executive', 'sales specialist', 'sales consultant', 'area sales' ),
			'inside-sales' => array( 'inside sales', 'internal sales', 'customer service', 'telesales', 'sales administrator', 'sales coordinator', 'sales operations' ),
			'service-engineer' => array( 'service engineer', 'field service', 'technical support', 'field engineer', 'biomedical engineer' ),
			/* Last: any other title with "sales" in it, e.g. "Sales Spine Specialist". */
			'field-sales-any' => array( 'sales' ),
		);
		$type = 'other';
		foreach ( $types as $id => $terms ) {
			foreach ( $terms as $t ) {
				if ( false !== strpos( $s, ' ' . trim( $t ) . ' ' ) ) {
					$type = $id;
					break 2;
				}
			}
		}
		if ( 'field-sales-any' === $type ) {
			$type = 'field-sales';
		}
		$level = '';
		if ( 'director' === $type || ( 'other' !== $type && preg_match( '/ (director|vice president|vp|general manager) /', $s ) ) ) {
			$level = 'director';
		} elseif ( 'national-manager' === $type || preg_match( '/ (head of|national) /', $s ) ) {
			$level = 'senior-manager';
		} elseif ( 'sales-manager' === $type || preg_match( '/ (team leader|manager of) /', $s ) ) {
			$level = 'manager';
		} elseif ( preg_match( '/ (trainee|graduate|junior|jr|entry level|apprentice|intern) /', $s ) ) {
			$level = 'entry';
		} elseif ( preg_match( '/ (senior|principal|lead|sr) /', $s ) ) {
			$level = 'senior';
		} elseif ( 'other' !== $type ) {
			$level = 'experienced';
		}
		return array( 'type' => $type, 'level' => $level );
	}
}

if ( ! function_exists( 'msh_sr_feed_roles' ) ) {
	/* Every usable UK role in supplier-careers.json, each once: title,
	   company, location, url, regions, type, level. Roles must be flagged
	   commercial or clinical, or read as a sales-family role from the title. */
	function msh_sr_feed_roles( $feed ) {
		$out = array();
		if ( ! is_array( $feed ) || empty( $feed['suppliers'] ) || ! is_array( $feed['suppliers'] ) ) {
			return $out;
		}
		$seen = array();
		foreach ( $feed['suppliers'] as $sup ) {
			if ( ! is_array( $sup ) || empty( $sup['roles'] ) || ! is_array( $sup['roles'] ) ) {
				continue;
			}
			foreach ( $sup['roles'] as $r ) {
				if ( ! is_array( $r ) || empty( $r['url'] ) || ! is_string( $r['url'] ) || empty( $r['title'] ) ) {
					continue;
				}
				if ( isset( $r['uk'] ) && false === $r['uk'] ) {
					continue;
				}
				if ( ! preg_match( '#^https://#', $r['url'] ) || isset( $seen[ $r['url'] ] ) ) {
					continue;
				}
				$kind = msh_sr_job_kind( $r['title'] );
				if ( empty( $r['commercial'] ) && empty( $r['clinical'] ) && 'other' === $kind['type'] ) {
					continue;
				}
				$seen[ $r['url'] ] = true;
				$loc   = isset( $r['location'] ) && is_string( $r['location'] ) ? $r['location'] : '';
				$out[] = array(
					'title'    => (string) $r['title'],
					'company'  => isset( $sup['name'] ) ? (string) $sup['name'] : '',
					'location' => $loc,
					'url'      => $r['url'],
					'regions'  => msh_sr_job_regions( $r['title'], $loc ),
					'type'     => $kind['type'],
					'level'    => $kind['level'],
				);
			}
		}
		return $out;
	}
}

if ( ! function_exists( 'msh_sr_region_jobs' ) ) {
	/* The roles for one region's weekly email: in that region or UK-wide,
	   not already sent to it. Returns array( 'local' => [...], 'national' => [...] ). */
	function msh_sr_region_jobs( $roles, $region, $sent ) {
		$sent = is_array( $sent ) ? array_flip( $sent ) : array();
		$out  = array( 'local' => array(), 'national' => array() );
		foreach ( (array) $roles as $j ) {
			if ( isset( $sent[ $j['url'] ] ) ) {
				continue;
			}
			if ( ! $j['regions'] ) {
				$out['national'][] = $j;
			} elseif ( in_array( $region, $j['regions'], true ) ) {
				$out['local'][] = $j;
			}
		}
		return $out;
	}
}

if ( ! function_exists( 'msh_sr_digest_email' ) ) {
	/* Subject and HTML of one region's weekly MailerLite campaign, or null
	   when there is nothing to send. Roles grouped by type, each with its
	   level. $links: array( careers, register ) absolute URLs. MailerLite
	   fills {$unsubscribe} and {$name}. */
	function msh_sr_digest_email( $regionLabel, $jobs, $links ) {
		$local = array_slice( $jobs['local'], 0, 20 );
		$nat   = array_slice( $jobs['national'], 0, 12 );
		if ( ! $local && ! $nat ) {
			return null;
		}
		$o     = msh_sr_options();
		$e     = function ( $s ) { return htmlspecialchars( (string) $s, ENT_QUOTES, 'UTF-8' ); };
		$block = function ( $rows ) use ( $e, $o ) {
			$by = array();
			foreach ( $rows as $j ) {
				$by[ $j['type'] ][] = $j;
			}
			$order = array_merge( array_keys( $o['roles'] ), array( 'other' ) );
			$h     = '';
			foreach ( $order as $t ) {
				if ( empty( $by[ $t ] ) ) {
					continue;
				}
				$h .= '<p style="margin:18px 0 4px;font-size:12px;font-weight:bold;letter-spacing:.06em;text-transform:uppercase;color:#14304F">'
					. $e( 'other' === $t ? 'Other commercial and clinical roles' : $o['roles'][ $t ] ) . '</p>'
					. '<table role="presentation" width="100%" cellpadding="0" cellspacing="0">';
				foreach ( $by[ $t ] as $j ) {
					$lv = ( '' !== $j['level'] && isset( $o['levels'][ $j['level'] ] ) ) ? $o['levels'][ $j['level'] ] : '';
					$h .= '<tr><td style="padding:10px 0;border-bottom:1px solid #E6E2D8">'
						. '<a href="' . $e( $j['url'] ) . '" style="color:#14304F;font-weight:bold;text-decoration:none">' . $e( $j['title'] ) . '</a><br>'
						. '<span style="color:#4A5666;font-size:13px">' . $e( $j['company'] ) . ( '' !== $j['location'] ? ' &middot; ' . $e( $j['location'] ) : '' )
						. ( '' !== $lv ? ' &middot; ' . $e( $lv ) : '' ) . '</span></td></tr>';
				}
				$h .= '</table>';
			}
			return $h;
		};
		$n    = count( $local );
		$subj = $n ? ( $n . ' new medical sales role' . ( 1 === $n ? '' : 's' ) . ' in ' . $regionLabel . ' this week' ) : 'New UK-wide medical sales roles this week';
		$h    = '<!DOCTYPE html><html><body style="margin:0;background:#F6F5F1">'
			. '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#F6F5F1"><tr><td align="center" style="padding:24px 12px">'
			. '<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#FFFFFF">'
			. '<tr><td style="background:#0B1C33;padding:28px 32px">'
			. '<p style="margin:0;font-family:Arial,sans-serif;font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:#E0BE8E">Medical Sales Register</p>'
			. '<p style="margin:8px 0 0;font-family:Georgia,serif;font-size:26px;line-height:1.2;color:#FFFFFF">This week&rsquo;s roles' . ( $n ? ' in ' . $e( $regionLabel ) : '' ) . '</p></td></tr>'
			. '<tr><td style="padding:24px 32px;font-family:Arial,sans-serif;font-size:15px;line-height:1.5;color:#1D2733">'
			. '<p style="margin:0 0 8px">Hi {$name},</p>'
			. '<p style="margin:0 0 8px">Here are this week&rsquo;s new roles, read from the companies&rsquo; own careers pages. Each link opens the advert on the company&rsquo;s site.</p>';
		if ( $local ) {
			$h .= '<h2 style="font-family:Georgia,serif;font-size:20px;color:#14304F;margin:24px 0 0">In ' . $e( $regionLabel ) . '</h2>' . $block( $local );
		}
		if ( $nat ) {
			$h .= '<h2 style="font-family:Georgia,serif;font-size:20px;color:#14304F;margin:28px 0 0">UK-wide or several locations</h2>' . $block( $nat );
		}
		$h .= '<p style="margin:28px 0 0"><a href="' . $e( $links['careers'] ) . '" style="display:inline-block;background:#14304F;color:#FFFFFF;padding:12px 22px;text-decoration:none;font-weight:bold">See every role on the Career Centre</a></p>'
			. '<p style="margin:16px 0 0"><a href="' . $e( $links['register'] ) . '" style="color:#14304F">Update your register profile</a></p>'
			. '<p style="margin:16px 0 0;color:#4A5666;font-size:13px">Role types and levels are read from each job title, to help you scan. Check the advert for the detail.</p>'
			. '</td></tr><tr><td style="padding:16px 32px 28px;font-family:Arial,sans-serif;font-size:12px;line-height:1.5;color:#4A5666;border-top:1px solid #E6E2D8">'
			. 'You get this because you asked for the weekly jobs email on the Medical Sales Register. '
			. '<a href="{$unsubscribe}" style="color:#4A5666">Unsubscribe</a>.</td></tr></table></td></tr></table></body></html>';
		return array( 'subject' => $subj, 'html' => $h );
	}
}

/* ---------- MailerLite ---------- */

if ( ! function_exists( 'msh_sr_ml_groups' ) ) {
	/* One MailerLite group per region, created 14/10/2026 (names
	   "Medical Sales Register jobs - <region>"). */
	function msh_sr_ml_groups() {
		return array(
			'north-east' => '201297842148476294', 'north-west' => '201297843935249872', 'yorkshire-humber' => '201297845423178846',
			'east-midlands' => '201297847001286360', 'west-midlands' => '201297848550033143', 'east-of-england' => '201297849956173213',
			'london' => '201297851443054362', 'south-east' => '201297852858631521', 'south-west' => '201297854457710329',
			'wales' => '201297856116557613', 'scotland' => '201297857605535677', 'northern-ireland' => '201297858999092350',
		);
	}
}

if ( ! function_exists( 'msh_sr_ml_key' ) ) {
	function msh_sr_ml_key() {
		if ( defined( 'MSH_ML_API_KEY' ) && MSH_ML_API_KEY ) {
			return MSH_ML_API_KEY;
		}
		$o = get_option( 'woo_mailerlite_options', array() );
		return ( is_array( $o ) && ! empty( $o['apiKey'] ) ) ? $o['apiKey'] : '';
	}
}

if ( ! function_exists( 'msh_sr_ml' ) ) {
	/* One MailerLite API call. Returns array( code, body ) ; code 0 on error. */
	function msh_sr_ml( $method, $path, $payload = null ) {
		$key = msh_sr_ml_key();
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
}

if ( ! function_exists( 'msh_sr_ml_log' ) ) {
	function msh_sr_ml_log( $msg ) {
		$log = get_option( 'msh_sr_ml_log', array() );
		$log = is_array( $log ) ? $log : array();
		$log[] = gmdate( 'Y-m-d H:i:s' ) . ' ' . $msg;
		update_option( 'msh_sr_ml_log', array_slice( $log, -40 ), false );
	}
}

if ( ! function_exists( 'msh_sr_ml_plan' ) ) {
	/* Which region groups a member should be in, and which to leave. Pure. */
	function msh_sr_ml_plan( $profile, $groups ) {
		$want = array();
		if ( is_array( $profile ) && ! empty( $profile['jobsEmail'] ) && ! empty( $profile['region'] ) && ! empty( $groups[ $profile['region'] ] ) ) {
			$want[] = (string) $groups[ $profile['region'] ];
		}
		$leave = array();
		foreach ( $groups as $g ) {
			if ( '' !== (string) $g && ! in_array( (string) $g, $want, true ) ) {
				$leave[] = (string) $g;
			}
		}
		return array( 'join' => $want, 'leave' => $leave );
	}
}

if ( ! function_exists( 'msh_sr_ml_sync' ) ) {
	/* Put a member in the right region group, out of the others. Run from
	   WP-Cron two seconds after a save so the save never waits on it. */
	function msh_sr_ml_sync( $uid ) {
		$u = get_userdata( (int) $uid );
		if ( ! $u || ! is_email( $u->user_email ) ) {
			return;
		}
		$p    = get_user_meta( $u->ID, 'msh_sales_register', true );
		$plan = msh_sr_ml_plan( is_array( $p ) ? $p : null, msh_sr_ml_groups() );
		$o    = msh_sr_options();
		if ( $plan['join'] ) {
			$first = trim( (string) $u->first_name );
			list( $code, $b ) = msh_sr_ml( 'POST', '/subscribers', array(
				'email'  => $u->user_email,
				'fields' => array_filter( array(
					'name'      => '' !== $first ? $first : $u->display_name,
					'last_name' => trim( (string) $u->last_name ),
				) ),
				'groups' => $plan['join'],
			) );
			msh_sr_ml_log( 'user ' . $u->ID . ' join ' . $o['regions'][ $p['region'] ] . ': ' . $code . ( $code >= 300 || 0 === $code ? ' ' . substr( wp_json_encode( $b ), 0, 160 ) : '' ) );
		}
		list( $code, $b ) = msh_sr_ml( 'GET', '/subscribers/' . rawurlencode( $u->user_email ) );
		$sid  = ( 200 === $code && ! empty( $b['data']['id'] ) ) ? $b['data']['id'] : '';
		$have = array();
		if ( $sid && ! empty( $b['data']['groups'] ) && is_array( $b['data']['groups'] ) ) {
			foreach ( $b['data']['groups'] as $g ) {
				$have[] = (string) $g['id'];
			}
		}
		foreach ( array_intersect( $plan['leave'], $have ) as $g ) {
			list( $c ) = msh_sr_ml( 'DELETE', '/subscribers/' . $sid . '/groups/' . $g );
			msh_sr_ml_log( 'user ' . $u->ID . ' leave group ' . $g . ': ' . $c );
		}
	}
}
add_action( 'msh_sr_ml_sync', 'msh_sr_ml_sync' );

if ( ! function_exists( 'msh_sr_ml_week' ) ) {
	/* This week's campaigns, one per region group with active subscribers.
	   $draft true: create them but never schedule (preview). Returns a list
	   of what happened, also written to the log. */
	function msh_sr_ml_week( $draft = false ) {
		$did = array();
		$r   = wp_remote_get( MSH_SR_CAREERS_URL, array( 'timeout' => 30 ) );
		$feed = ( ! is_wp_error( $r ) && 200 === (int) wp_remote_retrieve_response_code( $r ) ) ? json_decode( wp_remote_retrieve_body( $r ), true ) : null;
		if ( ! is_array( $feed ) ) {
			msh_sr_ml_log( 'week: careers feed unreadable, nothing sent' );
			return array( 'careers feed unreadable' );
		}
		$roles = msh_sr_feed_roles( $feed );
		$o     = msh_sr_options();
		$sent  = get_option( 'msh_sr_ml_sent', array() );
		$sent  = is_array( $sent ) ? $sent : array();
		$links = array( 'careers' => home_url( '/medical-sales-hub/careers/' ), 'register' => home_url( MSH_SR_PAGE ) );
		$week  = wp_date( 'j F Y' );
		foreach ( msh_sr_ml_groups() as $region => $gid ) {
			if ( '' === (string) $gid ) {
				continue;
			}
			list( $code, $g ) = msh_sr_ml( 'GET', '/groups/' . $gid );
			$n = ( 200 === $code && isset( $g['data']['active_count'] ) ) ? (int) $g['data']['active_count'] : 0;
			if ( $n < 1 ) {
				continue;
			}
			$jobs = msh_sr_region_jobs( $roles, $region, isset( $sent[ $region ] ) ? $sent[ $region ] : array() );
			$mail = msh_sr_digest_email( $o['regions'][ $region ], $jobs, $links );
			if ( null === $mail ) {
				$did[] = $o['regions'][ $region ] . ': nothing new';
				continue;
			}
			list( $code, $c ) = msh_sr_ml( 'POST', '/campaigns', array(
				'name'   => 'Medical Sales Register jobs - ' . $o['regions'][ $region ] . ' - ' . $week . ( $draft ? ' (preview)' : '' ),
				'type'   => 'regular',
				'emails' => array( array(
					'subject'   => $mail['subject'],
					'from_name' => 'Medical Sales Hub',
					'from'      => 'hub@elevateandthrive.uk',
					'reply_to'  => 'louisehoult@elevateandthrive.uk',
					'content'   => $mail['html'],
				) ),
				'groups' => array( (string) $gid ),
			) );
			$cid = ( $code >= 200 && $code < 300 && ! empty( $c['data']['id'] ) ) ? $c['data']['id'] : '';
			if ( ! $cid ) {
				$did[] = $o['regions'][ $region ] . ': campaign not created (' . $code . ' ' . substr( wp_json_encode( $c ), 0, 160 ) . ')';
				continue;
			}
			if ( $draft || ! MSH_SR_ML_SEND ) {
				$did[] = $o['regions'][ $region ] . ': draft ' . $cid . ' for ' . $n;
				continue;
			}
			list( $code, $s ) = msh_sr_ml( 'POST', '/campaigns/' . $cid . '/schedule', array( 'delivery' => 'instant' ) );
			if ( $code >= 200 && $code < 300 ) {
				$urls = array();
				foreach ( array_merge( array_slice( $jobs['local'], 0, 20 ), array_slice( $jobs['national'], 0, 12 ) ) as $j ) {
					$urls[] = $j['url'];
				}
				$sent[ $region ] = array_slice( array_values( array_unique( array_merge( $urls, isset( $sent[ $region ] ) ? $sent[ $region ] : array() ) ) ), 0, 600 );
				$did[] = $o['regions'][ $region ] . ': sent ' . $cid . ' to ' . $n;
			} else {
				$did[] = $o['regions'][ $region ] . ': campaign ' . $cid . ' not sent (' . $code . ' ' . substr( wp_json_encode( $s ), 0, 160 ) . ')';
			}
		}
		if ( ! $draft ) {
			update_option( 'msh_sr_ml_sent', $sent, false );
		}
		foreach ( $did as $d ) {
			msh_sr_ml_log( ( $draft ? 'preview ' : 'week ' ) . $d );
		}
		$bad = array_filter( $did, function ( $d ) { return false !== strpos( $d, 'not ' ); } );
		if ( $bad && ! $draft ) {
			wp_mail( get_option( 'admin_email' ), 'Medical Sales Register: weekly jobs email had a problem', "Some region campaigns did not go:\n\n" . implode( "\n", $bad ) . "\n\nLog: " . home_url( '/?msh_sr_ml_check=1' ) );
		}
		return $did;
	}
}

add_action( 'msh_sr_ml_week', function () { msh_sr_ml_week( false ); } );

/* Weekly, Tuesdays 08:00 UK time: after the careers refresh (Tuesdays 03:40 UTC). */
add_action( 'init', function () {
	if ( wp_next_scheduled( 'msh_sr_ml_week' ) ) {
		return;
	}
	$next = new DateTime( 'next tuesday 08:00', new DateTimeZone( 'Europe/London' ) );
	wp_schedule_event( $next->getTimestamp(), 'weekly', 'msh_sr_ml_week' );
} );

/* Admin-only check: ?msh_sr_ml_check=1 reports, =draft builds preview drafts. */
add_action( 'template_redirect', function () {
	if ( ! isset( $_GET['msh_sr_ml_check'] ) || ! current_user_can( 'manage_options' ) ) {
		return;
	}
	nocache_headers();
	header( 'Content-Type: application/json; charset=utf-8' );
	$out = array(
		'api_key_found' => '' !== msh_sr_ml_key(),
		'send'          => MSH_SR_ML_SEND,
		'groups'        => msh_sr_ml_groups(),
		'next_run'      => wp_next_scheduled( 'msh_sr_ml_week' ) ? wp_date( 'Y-m-d H:i', wp_next_scheduled( 'msh_sr_ml_week' ) ) : null,
	);
	if ( 'draft' === $_GET['msh_sr_ml_check'] ) {
		$out['preview'] = msh_sr_ml_week( true );
	}
	$out['log'] = get_option( 'msh_sr_ml_log', array() );
	echo wp_json_encode( $out );
	exit;
} );

/* ---------- access ---------- */

if ( ! function_exists( 'msh_sr_employer_access' ) ) {
	/* Who may browse: an admin, a Hub Employer by role (either register's
	   capability), or a Hub member Lou has ticked as a Hub Employer. The
	   same paid Hub Employer access as the Nursing Register. */
	function msh_sr_employer_access( $isAdmin, $hasCap, $meta ) {
		return (bool) $isAdmin || (bool) $hasCap || '1' === (string) $meta;
	}
}

if ( ! function_exists( 'msh_sr_can_browse' ) ) {
	function msh_sr_can_browse() {
		/* The Nursing Register snippet (4919) owns Hub Employer access: admin,
		   role msh_employer, the Hub Employer tick, or a live Hub Employer
		   plan (5167). One subscription opens both registers. */
		if ( function_exists( 'msh_nr_can_browse' ) && msh_nr_can_browse() ) {
			return true;
		}
		$uid = get_current_user_id();
		return msh_sr_employer_access( current_user_can( 'manage_options' ),
			current_user_can( 'msh_view_nurse_register' ) || current_user_can( 'msh_view_sales_register' ),
			$uid ? get_user_meta( $uid, 'msh_nr_employer', true ) : '' );
	}
}

/* The Hub Employer role reads both registers. Added to the role the
   Nursing Register snippet creates; created here if that snippet is off. */
add_action( 'init', function () {
	$r = get_role( 'msh_employer' );
	if ( ! $r ) {
		add_role( 'msh_employer', 'Hub Employer', array( 'read' => true, 'msh_view_nurse_register' => true, 'msh_view_sales_register' => true ) );
	} elseif ( ! $r->has_cap( 'msh_view_sales_register' ) ) {
		$r->add_cap( 'msh_view_sales_register' );
	}
} );

if ( ! function_exists( 'msh_sr_new_ref' ) ) {
	function msh_sr_new_ref() {
		$abc = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
		for ( $try = 0; $try < 20; $try++ ) {
			$r = 'MSR-';
			for ( $i = 0; $i < 6; $i++ ) {
				$r .= $abc[ random_int( 0, strlen( $abc ) - 1 ) ];
			}
			if ( ! get_users( array( 'meta_key' => 'msh_sales_ref', 'meta_value' => $r, 'number' => 1, 'fields' => 'ID' ) ) ) {
				return $r;
			}
		}
		return 'MSR-' . strtoupper( wp_generate_password( 10, false ) );
	}
}

if ( ! function_exists( 'msh_sr_user_by_ref' ) ) {
	function msh_sr_user_by_ref( $ref ) {
		if ( ! is_string( $ref ) || ! preg_match( '/^MSR-[A-Z0-9]{6,10}$/', $ref ) ) {
			return 0;
		}
		$ids = get_users( array( 'meta_key' => 'msh_sales_ref', 'meta_value' => $ref, 'number' => 1, 'fields' => 'ID' ) );
		return $ids ? (int) $ids[0] : 0;
	}
}

if ( ! function_exists( 'msh_sr_payload' ) ) {
	function msh_sr_payload( $uid ) {
		$p = get_user_meta( $uid, 'msh_sales_register', true );
		return array(
			'options'   => msh_sr_options(),
			'profile'   => is_array( $p ) ? $p : null,
			'canBrowse' => msh_sr_can_browse(),
			'isAdmin'   => current_user_can( 'manage_options' ),
			'staleDays' => MSH_SR_STALE_DAYS,
			'links'     => msh_sr_career_links(),
			'feed'      => MSH_SR_CAREERS_URL,
		);
	}
}

add_action( 'rest_api_init', function () {
	$logged_in = function () { return is_user_logged_in(); };
	$browser   = function () { return is_user_logged_in() && msh_sr_can_browse(); };

	register_rest_route( 'msh/v1', '/sales-register', array(
		array(
			'methods'             => 'GET',
			'permission_callback' => $logged_in,
			'callback'            => function () {
				nocache_headers();
				return msh_sr_payload( get_current_user_id() );
			},
		),
		array(
			'methods'             => 'POST',
			'permission_callback' => $logged_in,
			'callback'            => function ( WP_REST_Request $req ) {
				$uid = get_current_user_id();
				$old = get_user_meta( $uid, 'msh_sales_register', true );
				$ref = ( is_array( $old ) && ! empty( $old['ref'] ) ) ? '' : msh_sr_new_ref();
				$r   = msh_sr_clean( $req->get_json_params(), is_array( $old ) ? $old : array(), wp_date( 'Y-m-d' ), $ref );
				if ( ! $r['ok'] ) {
					return new WP_Error( 'msh_sr_' . $r['why'], $r['why'], array( 'status' => 400, 'field' => $r['why'] ) );
				}
				update_user_meta( $uid, 'msh_sales_register', $r['profile'] );
				update_user_meta( $uid, 'msh_sales_ref', $r['profile']['ref'] );
				$wasJobs = is_array( $old ) && ! empty( $old['jobsEmail'] );
				$moved   = is_array( $old ) && isset( $old['region'] ) && $old['region'] !== $r['profile']['region'];
				if ( $r['profile']['jobsEmail'] || $wasJobs || $moved ) {
					wp_schedule_single_event( time() + 2, 'msh_sr_ml_sync', array( $uid ) );
				}
				$u    = get_userdata( $uid );
				$mail = msh_sr_summary_email( $u ? $u->first_name : '', $r['profile'], untrailingslashit( home_url() ) );
				$sent = $u ? wp_mail( $u->user_email, $mail['subject'], $mail['html'], array( 'Content-Type: text/html; charset=UTF-8' ) ) : false;
				$out  = msh_sr_payload( $uid );
				$out['emailed'] = (bool) $sent;
				return $out;
			},
		),
		array(
			'methods'             => 'DELETE',
			'permission_callback' => $logged_in,
			'callback'            => function () {
				$uid = get_current_user_id();
				$old = get_user_meta( $uid, 'msh_sales_register', true );
				delete_user_meta( $uid, 'msh_sales_register' );
				delete_user_meta( $uid, 'msh_sales_ref' );
				if ( is_array( $old ) && ! empty( $old['jobsEmail'] ) ) {
					wp_schedule_single_event( time() + 2, 'msh_sr_ml_sync', array( $uid ) );
				}
				return msh_sr_payload( $uid );
			},
		),
	) );

	register_rest_route( 'msh/v1', '/sales-register/cv', array(
		'methods'             => 'POST',
		'permission_callback' => $logged_in,
		'callback'            => function ( WP_REST_Request $req ) {
			$b    = $req->get_json_params();
			$text = ( is_array( $b ) && isset( $b['text'] ) && is_string( $b['text'] ) ) ? substr( $b['text'], 0, 60000 ) : '';
			if ( strlen( trim( $text ) ) < 200 ) {
				return new WP_Error( 'msh_sr_cv_empty', 'no readable text', array( 'status' => 400 ) );
			}
			nocache_headers();
			return msh_sr_cv_suggest( $text );
		},
	) );

	/* Live roles from the companies' own careers pages, with region, type
	   and level read from each title, for the member's "Roles for you" tab. */
	register_rest_route( 'msh/v1', '/sales-register/roles', array(
		'methods'             => 'GET',
		'permission_callback' => $logged_in,
		'callback'            => function () {
			$roles = get_transient( 'msh_sr_roles' );
			if ( ! is_array( $roles ) ) {
				$r    = wp_remote_get( MSH_SR_CAREERS_URL, array( 'timeout' => 30 ) );
				$feed = ( ! is_wp_error( $r ) && 200 === (int) wp_remote_retrieve_response_code( $r ) ) ? json_decode( wp_remote_retrieve_body( $r ), true ) : null;
				if ( ! is_array( $feed ) ) {
					return new WP_Error( 'msh_sr_feed', 'careers feed unreadable', array( 'status' => 502 ) );
				}
				$roles = array( 'generatedOn' => isset( $feed['generatedOn'] ) ? (string) $feed['generatedOn'] : '', 'roles' => msh_sr_feed_roles( $feed ) );
				set_transient( 'msh_sr_roles', $roles, 6 * HOUR_IN_SECONDS );
			}
			return $roles;
		},
	) );

	register_rest_route( 'msh/v1', '/sales-register/browse', array(
		'methods'             => 'GET',
		'permission_callback' => $browser,
		'callback'            => function () {
			nocache_headers();
			$today   = wp_date( 'Y-m-d' );
			$isAdmin = current_user_can( 'manage_options' );
			$ids     = get_users( array( 'meta_key' => 'msh_sales_ref', 'fields' => 'ID', 'number' => 3000 ) );
			$out     = array();
			foreach ( $ids as $id ) {
				$p   = get_user_meta( $id, 'msh_sales_register', true );
				$pub = msh_sr_public( $p, $today );
				if ( null === $pub ) {
					if ( ! $isAdmin || ! is_array( $p ) ) {
						continue;
					}
					$pub = msh_sr_public( array_merge( $p, array( 'visible' => true, 'consentAt' => 'x', 'updated' => $today ) ), $today );
					$pub['hidden'] = true;
				}
				$u = get_userdata( $id );
				if ( empty( $pub['hidden'] ) ) {
					$c = msh_sr_contact( $p, $u ? $u->display_name : '', $u ? $u->user_email : '' );
					if ( null !== $c ) {
						$pub['contact'] = $c;
					}
				}
				if ( $isAdmin ) {
					$pub['private'] = array(
						'name'     => $u ? $u->display_name : '',
						'email'    => $u ? $u->user_email : '',
						'phone'    => isset( $p['phone'] ) ? $p['phone'] : '',
						'linkedin' => isset( $p['linkedin'] ) ? $p['linkedin'] : '',
						'employer' => isset( $p['employer'] ) ? $p['employer'] : '',
						'updated'  => isset( $p['updated'] ) ? $p['updated'] : '',
					);
				}
				$out[] = $pub;
			}
			usort( $out, function ( $a, $b ) { return strcmp( (string) $b['updated'], (string) $a['updated'] ); } );
			return array( 'profiles' => $out );
		},
	) );

	register_rest_route( 'msh/v1', '/sales-register/intro', array(
		'methods'             => 'POST',
		'permission_callback' => $browser,
		'callback'            => function ( WP_REST_Request $req ) {
			$b     = $req->get_json_params();
			$b     = is_array( $b ) ? $b : array();
			$today = wp_date( 'Y-m-d' );
			$mid   = msh_sr_user_by_ref( isset( $b['ref'] ) ? $b['ref'] : '' );
			$p     = $mid ? get_user_meta( $mid, 'msh_sales_register', true ) : null;
			if ( ! $mid || null === msh_sr_public( $p, $today ) ) {
				return new WP_Error( 'msh_sr_ref', 'not on the register', array( 'status' => 404 ) );
			}
			$eid = get_current_user_id();
			$log = get_user_meta( $eid, 'msh_sr_intro_log', true );
			$log = ( is_array( $log ) && isset( $log['d'] ) && $log['d'] === $today ) ? $log : array( 'd' => $today, 'n' => 0 );
			if ( $log['n'] >= MSH_SR_INTROS_PER_DAY ) {
				return new WP_Error( 'msh_sr_limit', 'daily limit', array( 'status' => 429 ) );
			}
			$msg  = msh_sr_text( isset( $b['message'] ) ? $b['message'] : '', 1000 );
			$e    = get_userdata( $eid );
			$n    = get_userdata( $mid );
			$body = "An employer has asked to be introduced to someone on the Medical Sales Register.\n\n"
				. 'Employer: ' . $e->display_name . ' <' . $e->user_email . ">\n"
				. 'Their message: ' . ( '' !== $msg ? $msg : '(none)' ) . "\n\n"
				. 'Member: ' . $p['ref'] . "\n"
				. 'Name: ' . ( $n ? $n->display_name : '' ) . "\n"
				. 'Email: ' . ( $n ? $n->user_email : '' ) . "\n"
				. 'Phone: ' . ( $p['phone'] ? $p['phone'] : '(not given)' ) . "\n\n"
				. "Check with the member before passing on any of their details.\n";
			$sent = wp_mail( get_option( 'admin_email' ), 'Medical Sales Register: introduction request for ' . $p['ref'], $body, array( 'Reply-To: ' . $e->user_email ) );
			if ( ! $sent ) {
				return new WP_Error( 'msh_sr_mail', 'could not send', array( 'status' => 502 ) );
			}
			$log['n']++;
			update_user_meta( $eid, 'msh_sr_intro_log', $log );
			return array( 'ok' => true );
		},
	) );
} );
