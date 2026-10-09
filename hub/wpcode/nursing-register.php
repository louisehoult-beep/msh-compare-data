/* Nursing Register: nurses on the Clinical Hub list their experience and
   skills; approved employers browse them without names or contact details,
   and ask Elevate & Thrive for an introduction. Added 08/10/2026.

   WPCode snippet, type "PHP Snippet", location "Run Everywhere", on
   medsalesintelligencehub.co.uk only. Paste from the line below this comment
   (WPCode adds the opening PHP tag itself). Needs the My Hub snippet (4503,
   hub/wpcode/my-hub-pins.php) active too: that prints window.mshRestNonce.

   Source of truth: hub/wpcode/nursing-register.php in
   louisehoult-beep/msh-compare-data. Edit it there, then paste it here again.
   Read by app/nursing-register.js. The tick lists below are the only copy:
   the page draws them from GET, so a new skill is added here and nowhere else.
   Never rename an option id, members' saved profiles hold it.

   PERSONAL DATA. Profiles live in WordPress user meta on the Hub, never in
   this repo (it is public). verify.py refuses named personal data here.

   WHO SEES WHAT
   * The nurse: their whole profile.
   * An employer (role msh_employer, given by Lou in Users) or an admin: the
     employer view from msh_nr_public(). No name, email, phone, NMC PIN or
     LinkedIn. Only profiles the nurse has made visible, with consent, and
     confirmed in the last MSH_NR_STALE_DAYS days.
   * Where the nurse has also ticked the separate share consent
     (shareContact, dated shareAt), employers and admins get their name,
     email, phone and LinkedIn too (msh_nr_contact). Never the NMC PIN.
   * An admin also gets the private fields, to check the NMC PIN and make
     introductions.
   An employer's "Request introduction" emails Lou. Nothing goes to the
   employer until Lou has checked with the nurse.

   WEEKLY JOBS EMAIL (added 08/10/2026; the nurse ticks jobsEmail)
   Monday 07:00 UK time. Reads data/supplier-careers.json from this repo, keeps
   UK roles flagged commercial or clinical, places each in regions from its
   title and location (msh_nr_job_regions), and emails each nurse the roles in
   their region plus UK-wide ones they haven't been sent before. Nothing new,
   no email. Sent in batches of MSH_NR_BATCH. Every email carries a one-click
   unsubscribe link (?msh_nr_unsub=). User meta msh_nr_jobs_sent holds the
   role URLs already emailed (newest 400).

   ROUTES (logged-in only, wp_rest nonce)
   GET    /wp-json/msh/v1/nurse-register         { options, profile, canBrowse, isAdmin }
   POST   /wp-json/msh/v1/nurse-register         save own profile, returns the same
   DELETE /wp-json/msh/v1/nurse-register         delete own profile
   GET    /wp-json/msh/v1/nurse-register/browse  { profiles: [...] }      employers, admins
   POST   /wp-json/msh/v1/nurse-register/intro   { ref, message }         employers, admins
   POST   /wp-json/msh/v1/nurse-register/verify  { ref, checked }         admins

   User meta: msh_nurse_register (the profile), msh_nurse_ref (its public
   reference, for lookups), msh_nr_intro_log (an employer's requests today).
   The pure functions are tested by test_nursing_register.py. */

if ( ! defined( 'MSH_NR_STALE_DAYS' ) ) {
	define( 'MSH_NR_STALE_DAYS', 365 );
}
if ( ! defined( 'MSH_NR_INTROS_PER_DAY' ) ) {
	define( 'MSH_NR_INTROS_PER_DAY', 10 );
}
if ( ! defined( 'MSH_NR_BATCH' ) ) {
	define( 'MSH_NR_BATCH', 40 );
}
if ( ! defined( 'MSH_NR_CAREERS_URL' ) ) {
	define( 'MSH_NR_CAREERS_URL', 'https://raw.githubusercontent.com/louisehoult-beep/msh-compare-data/main/data/supplier-careers.json' );
}

if ( ! function_exists( 'msh_nr_options' ) ) {
	function msh_nr_options() {
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
			'registration' => array(
				'adult' => 'Adult nursing', 'child' => "Children's nursing", 'mental-health' => 'Mental health nursing',
				'learning-disability' => 'Learning disability nursing', 'midwife' => 'Midwifery',
				'nursing-associate' => 'Nursing associate', 'scphn' => 'Specialist community public health nursing',
			),
			'bands' => array(
				'5' => 'Band 5', '6' => 'Band 6', '7' => 'Band 7', '8a' => 'Band 8a', '8b' => 'Band 8b',
				'8c' => 'Band 8c or above', 'non-nhs' => 'Outside Agenda for Change',
			),
			'sectors' => array(
				'nhs-acute' => 'NHS acute hospital', 'nhs-community' => 'NHS community services', 'primary-care' => 'GP practice or primary care',
				'mental-health-trust' => 'Mental health trust', 'independent-hospital' => 'Independent hospital',
				'care-home' => 'Care or nursing home', 'hospice' => 'Hospice', 'industry' => 'Industry or medtech already',
				'education' => 'University or education', 'armed-forces' => 'Armed forces',
			),
			'specialities' => array(
				'acute-medicine' => 'Acute and general medicine', 'general-surgery' => 'General surgery', 'theatres' => 'Theatres and perioperative',
				'critical-care' => 'Critical care', 'emergency' => 'Emergency and urgent care', 'cardiology' => 'Cardiology and cardiac surgery',
				'respiratory' => 'Respiratory', 'renal' => 'Renal and dialysis', 'oncology' => 'Oncology and SACT', 'haematology' => 'Haematology',
				'diabetes' => 'Diabetes and endocrinology', 'gastro' => 'Gastroenterology, colorectal and endoscopy', 'stoma' => 'Stoma care',
				'urology' => 'Urology', 'continence' => 'Continence, bladder and bowel', 'tissue-viability' => 'Tissue viability and wound care',
				'vascular' => 'Vascular surgery', 'vascular-access' => 'Vascular access and IV therapy', 'orthopaedics' => 'Orthopaedics and trauma',
				'neurology' => 'Neurology and neurosurgery', 'stroke' => 'Stroke', 'ent' => 'ENT', 'ophthalmology' => 'Ophthalmology',
				'plastics-burns' => 'Plastics and burns', 'dermatology' => 'Dermatology', 'gynaecology' => "Gynaecology and women's health",
				'maternity' => 'Maternity', 'neonatal' => 'Neonatal', 'paediatrics' => 'Paediatrics', 'older-people' => 'Older people and frailty',
				'palliative' => 'Palliative and end-of-life care', 'mental-health' => 'Mental health', 'learning-disability' => 'Learning disability',
				'infection-prevention' => 'Infection prevention and control', 'pain' => 'Pain management', 'nutrition' => 'Nutrition',
				'radiology' => 'Radiology and interventional radiology', 'community' => 'District and community nursing',
				'practice-nursing' => 'Practice nursing', 'clinical-education' => 'Clinical education and practice development',
				'research' => 'Clinical research', 'moving-handling' => 'Moving and handling', 'sepsis' => 'Sepsis and the deteriorating patient',
			),
			'clinicalSkills' => array(
				'wound-assessment' => 'Wound assessment and dressing selection', 'npwt' => 'Negative pressure wound therapy',
				'compression' => 'Compression therapy and Doppler (ABPI)', 'pressure-ulcer' => 'Pressure ulcer prevention and equipment',
				'stoma-care' => 'Stoma care and appliances', 'catheterisation' => 'Catheterisation (male and female)',
				'continence-assessment' => 'Continence assessment and products', 'cannulation' => 'Cannulation', 'venepuncture' => 'Venepuncture',
				'picc-midline' => 'PICC or midline insertion', 'central-lines' => 'Central venous access care', 'iv-pumps' => 'IV therapy and infusion pumps',
				'transfusion' => 'Blood transfusion', 'sact' => 'Chemotherapy or SACT administration', 'enteral-feeding' => 'Enteral feeding',
				'tracheostomy' => 'Tracheostomy care', 'niv' => 'Non-invasive ventilation', 'ventilation' => 'Invasive ventilation',
				'abg' => 'Arterial blood gases', 'ecg' => 'ECG recording and interpretation', 'haemodynamic' => 'Haemodynamic monitoring',
				'insulin-pumps' => 'Insulin pumps and CGM', 'anticoagulation' => 'Anticoagulation management', 'dialysis' => 'Haemodialysis or peritoneal dialysis',
				'scrub' => 'Scrub practice', 'anaesthetics' => 'Anaesthetic practice', 'recovery' => 'Post-anaesthetic recovery',
				'endoscopy-assist' => 'Endoscopy assisting and decontamination', 'cath-lab' => 'Cath lab', 'poct' => 'Point-of-care testing',
				'infection-audit' => 'IPC audit and outbreak management', 'moving-handling-equipment' => 'Moving and handling equipment',
				'neonatal-care' => 'Neonatal intensive care', 'triage' => 'Triage', 'falls' => 'Falls prevention',
			),
			'qualifications' => array(
				'nmp' => 'Non-medical prescriber (V300)', 'v150' => 'Community prescriber (V100 or V150)', 'acp' => 'Advanced clinical practitioner',
				'cns' => 'Clinical nurse specialist role', 'masters' => "Master's degree", 'degree' => "Bachelor's degree",
				'pg-specialist' => 'Postgraduate specialist course', 'practice-assessor' => 'Practice assessor or supervisor',
				'teaching-qual' => 'Teaching qualification', 'als' => 'ALS', 'epls' => 'EPLS or PILS', 'nls' => 'NLS', 'trauma' => 'ATNC or TNCC',
			),
			'transferable' => array(
				'teaching' => 'Teaching and in-service training', 'presenting' => 'Presenting to groups', 'link-nurse' => 'Link nurse or champion role',
				'product-evaluation' => 'Product evaluations and trials', 'procurement' => 'Product selection or procurement panels',
				'formulary' => 'Formulary or wound care formulary work', 'audit' => 'Audit and data', 'guidelines' => 'Writing policies or guidelines',
				'project-lead' => 'Leading a project or service change', 'budget' => 'Budget management', 'stakeholders' => 'Working with consultants and managers',
				'industry-contact' => 'Working with company reps', 'business-case' => 'Writing business cases', 'digital' => 'Digital systems and EPR',
			),
			'roles' => array(
				'clinical-specialist' => 'Clinical specialist', 'clinical-educator' => 'Clinical educator or trainer',
				'territory-manager' => 'Territory manager or sales rep', 'account-manager' => 'Key account manager',
				'product-specialist' => 'Product specialist', 'theatre-specialist' => 'Theatre or procedure specialist',
				'market-access' => 'Market access or NHS liaison', 'homecare' => 'Homecare or patient support nurse',
				'medical-affairs' => 'Medical affairs or MSL', 'marketing' => 'Product marketing',
			),
			'availability' => array(
				'now' => 'Available now', '1-month' => 'Within a month', '3-months' => 'Within three months',
				'6-months' => 'Within six months', 'exploring' => 'Exploring, no rush',
			),
		);
	}
}

if ( ! function_exists( 'msh_nr_text' ) ) {
	/* Plain text, tags gone, whitespace collapsed, at most $max characters. */
	function msh_nr_text( $s, $max ) {
		if ( ! is_string( $s ) ) {
			return '';
		}
		$s = preg_replace( '/<[^>]*>/', '', $s );
		$s = trim( preg_replace( '/\s+/u', ' ', $s ) );
		return mb_substr( $s, 0, $max );
	}
}

if ( ! function_exists( 'msh_nr_scrub' ) ) {
	/* Employers see the bio and role title, so contact details typed into them
	   are taken out: email addresses, phone-shaped numbers, web links. */
	function msh_nr_scrub( $s ) {
		$s = preg_replace( '/[^\s@]+@[^\s@]+\.[^\s@]+/u', '[removed]', $s );
		$s = preg_replace( '/(?:https?:\/\/|www\.)\S+/iu', '[removed]', $s );
		$s = preg_replace( '/\+?\d[\d\s().-]{8,}\d/u', '[removed]', $s );
		return $s;
	}
}

if ( ! function_exists( 'msh_nr_pick' ) ) {
	/* The known ids from a list, in option order, each once. Unknown ids are
	   dropped, not refused: an option retired later must not lock a nurse out. */
	function msh_nr_pick( $list, $allowed ) {
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

if ( ! function_exists( 'msh_nr_one' ) ) {
	function msh_nr_one( $v, $allowed ) {
		return ( is_string( $v ) && array_key_exists( $v, $allowed ) ) ? $v : '';
	}
}

if ( ! function_exists( 'msh_nr_clean' ) ) {
	/* The profile to store from what the browser sent.
	   $old: the stored profile (or array()). $today: Y-m-d. $ref: the public
	   reference to use when $old has none.
	   Returns array( 'ok' => true, 'profile' => ... ) or array( 'ok' => false, 'why' => code ). */
	function msh_nr_clean( $b, $old, $today, $ref ) {
		if ( ! is_array( $b ) ) {
			return array( 'ok' => false, 'why' => 'body' );
		}
		$o    = msh_nr_options();
		$year = (int) substr( $today, 0, 4 );

		$region = msh_nr_one( isset( $b['region'] ) ? $b['region'] : '', $o['regions'] );
		if ( '' === $region ) {
			return array( 'ok' => false, 'why' => 'region' );
		}
		$reg = msh_nr_pick( isset( $b['registration'] ) ? $b['registration'] : array(), $o['registration'] );
		if ( ! $reg ) {
			return array( 'ok' => false, 'why' => 'registration' );
		}
		$qy = isset( $b['qualYear'] ) ? $b['qualYear'] : null;
		if ( is_string( $qy ) && preg_match( '/^\d{4}$/', $qy ) ) {
			$qy = (int) $qy;
		}
		if ( ! is_int( $qy ) || $qy < 1960 || $qy > $year ) {
			return array( 'ok' => false, 'why' => 'qualYear' );
		}
		$specs = msh_nr_pick( isset( $b['specialities'] ) ? $b['specialities'] : array(), $o['specialities'] );
		if ( ! $specs ) {
			return array( 'ok' => false, 'why' => 'specialities' );
		}

		/* NMC PIN: two digits, a letter, four digits, a letter (e.g. 12A3456E).
		   Optional, private, only for Lou to check against the NMC register. */
		$pin = isset( $b['nmcPin'] ) && is_string( $b['nmcPin'] ) ? strtoupper( preg_replace( '/\s+/', '', $b['nmcPin'] ) ) : '';
		if ( '' !== $pin && ! preg_match( '/^\d{2}[A-Z]\d{4}[A-Z]$/', $pin ) ) {
			return array( 'ok' => false, 'why' => 'nmcPin' );
		}
		$li = isset( $b['linkedin'] ) && is_string( $b['linkedin'] ) ? trim( $b['linkedin'] ) : '';
		if ( '' !== $li && ! preg_match( '#^https://([a-z]{2,3}\.)?linkedin\.com/in/[A-Za-z0-9_%-]{2,100}/?$#', $li ) ) {
			return array( 'ok' => false, 'why' => 'linkedin' );
		}
		$phone = isset( $b['phone'] ) && is_string( $b['phone'] ) ? trim( $b['phone'] ) : '';
		if ( '' !== $phone && ! preg_match( '/^\+?[\d\s()-]{10,20}$/', $phone ) ) {
			return array( 'ok' => false, 'why' => 'phone' );
		}

		$visible = ! empty( $b['visible'] ) && true === $b['visible'];
		$consent = ! empty( $b['consent'] ) && true === $b['consent'];
		if ( $visible && ! $consent ) {
			return array( 'ok' => false, 'why' => 'consent' );
		}

		$old     = is_array( $old ) ? $old : array();
		$oldPin  = isset( $old['nmcPin'] ) ? $old['nmcPin'] : '';
		$checked = ( isset( $old['nmcChecked'] ) && $oldPin === $pin && '' !== $pin ) ? $old['nmcChecked'] : '';

		return array(
			'ok'      => true,
			'profile' => array(
				'v'              => 1,
				'ref'            => ( isset( $old['ref'] ) && is_string( $old['ref'] ) && '' !== $old['ref'] ) ? $old['ref'] : $ref,
				'region'         => $region,
				'area'           => msh_nr_scrub( msh_nr_text( isset( $b['area'] ) ? $b['area'] : '', 60 ) ),
				'travel'         => msh_nr_one( isset( $b['travel'] ) ? $b['travel'] : '', $o['travel'] ),
				'relocate'       => ! empty( $b['relocate'] ) && true === $b['relocate'],
				'registration'   => $reg,
				'qualYear'       => $qy,
				'band'           => msh_nr_one( isset( $b['band'] ) ? $b['band'] : '', $o['bands'] ),
				'currentRole'    => msh_nr_scrub( msh_nr_text( isset( $b['currentRole'] ) ? $b['currentRole'] : '', 80 ) ),
				'sectors'        => msh_nr_pick( isset( $b['sectors'] ) ? $b['sectors'] : array(), $o['sectors'] ),
				'specialities'   => $specs,
				'clinicalSkills' => msh_nr_pick( isset( $b['clinicalSkills'] ) ? $b['clinicalSkills'] : array(), $o['clinicalSkills'] ),
				'qualifications' => msh_nr_pick( isset( $b['qualifications'] ) ? $b['qualifications'] : array(), $o['qualifications'] ),
				'transferable'   => msh_nr_pick( isset( $b['transferable'] ) ? $b['transferable'] : array(), $o['transferable'] ),
				'roles'          => msh_nr_pick( isset( $b['roles'] ) ? $b['roles'] : array(), $o['roles'] ),
				'availability'   => msh_nr_one( isset( $b['availability'] ) ? $b['availability'] : '', $o['availability'] ),
				'driving'        => ! empty( $b['driving'] ) && true === $b['driving'],
				'rightToWork'    => ! empty( $b['rightToWork'] ) && true === $b['rightToWork'],
				'training'       => ! empty( $b['training'] ) && true === $b['training'],
				'jobsEmail'      => ! empty( $b['jobsEmail'] ) && true === $b['jobsEmail'],
				'shareContact'   => ! empty( $b['shareContact'] ) && true === $b['shareContact'],
				'shareAt'        => ( ! empty( $b['shareContact'] ) && true === $b['shareContact'] ) ? ( ( ! empty( $old['shareAt'] ) && ! empty( $old['shareContact'] ) ) ? $old['shareAt'] : $today ) : '',
				'bio'            => msh_nr_scrub( msh_nr_text( isset( $b['bio'] ) ? $b['bio'] : '', 600 ) ),
				'nmcPin'         => $pin,
				'nmcChecked'     => $checked,
				'phone'          => $phone,
				'linkedin'       => $li,
				'visible'        => $visible,
				'consentAt'      => $consent ? ( ( isset( $old['consentAt'] ) && $old['consentAt'] ) ? $old['consentAt'] : $today ) : '',
				'updated'        => $today,
			),
		);
	}
}

if ( ! function_exists( 'msh_nr_days_between' ) ) {
	function msh_nr_days_between( $from, $to ) {
		$a = strtotime( $from . ' 00:00:00 UTC' );
		$b = strtotime( $to . ' 00:00:00 UTC' );
		if ( false === $a || false === $b ) {
			return PHP_INT_MAX;
		}
		return (int) floor( ( $b - $a ) / 86400 );
	}
}

if ( ! function_exists( 'msh_nr_public' ) ) {
	/* What an employer sees, or null when the profile must not be shown:
	   not visible, no consent, or not confirmed within MSH_NR_STALE_DAYS. */
	function msh_nr_public( $p, $today ) {
		if ( ! is_array( $p ) || empty( $p['visible'] ) || empty( $p['consentAt'] ) || empty( $p['updated'] ) ) {
			return null;
		}
		if ( msh_nr_days_between( $p['updated'], $today ) > MSH_NR_STALE_DAYS ) {
			return null;
		}
		$keep = array( 'ref', 'region', 'area', 'travel', 'relocate', 'registration', 'qualYear', 'band', 'currentRole',
			'sectors', 'specialities', 'clinicalSkills', 'qualifications', 'transferable', 'roles', 'availability',
			'driving', 'rightToWork', 'training', 'bio', 'updated' );
		$out = array();
		foreach ( $keep as $k ) {
			$out[ $k ] = isset( $p[ $k ] ) ? $p[ $k ] : null;
		}
		$out['yearsQualified'] = max( 0, (int) substr( $today, 0, 4 ) - (int) $p['qualYear'] );
		$out['nmcChecked']     = ! empty( $p['nmcChecked'] ) ? $p['nmcChecked'] : '';
		return $out;
	}
}

if ( ! function_exists( 'msh_nr_contact' ) ) {
	/* Contact details a recruiter or employer may see, or null. Only when the
	   nurse has ticked the separate share consent (Lou, 08/10/2026: "get
	   permission to share"), which records shareAt. Never the NMC PIN. Call
	   only for a profile msh_nr_public() already shows. */
	function msh_nr_contact( $p, $name, $email ) {
		if ( ! is_array( $p ) || empty( $p['shareContact'] ) || true !== $p['shareContact'] || empty( $p['shareAt'] ) ) {
			return null;
		}
		return array(
			'name'     => (string) $name,
			'email'    => (string) $email,
			'phone'    => isset( $p['phone'] ) ? (string) $p['phone'] : '',
			'linkedin' => isset( $p['linkedin'] ) ? (string) $p['linkedin'] : '',
		);
	}
}

if ( ! function_exists( 'msh_nr_job_regions' ) ) {
	/* The register regions a role sits in, from its title and location, or an
	   empty list when it names none (shown as UK-wide). Two-word areas are
	   matched first and taken out, so "North West" is not also "North".
	   Head-office towns place a role where the company published it; a field
	   role's territory usually sits in its title, which is read too. */
	function msh_nr_job_regions( $title, $location ) {
		$s = ' ' . strtolower( preg_replace( '/[^A-Za-z0-9]+/', ' ', (string) $title . ' ' . (string) $location ) ) . ' ';
		$found = array();
		$areas = array(
			'north east' => array( 'north-east' ), 'north west' => array( 'north-west' ),
			'south east' => array( 'south-east' ), 'south west' => array( 'south-west' ),
			'east midlands' => array( 'east-midlands' ), 'west midlands' => array( 'west-midlands' ),
			'east of england' => array( 'east-of-england' ), 'east anglia' => array( 'east-of-england' ),
			'northern ireland' => array( 'northern-ireland' ), 'home counties' => array( 'south-east', 'east-of-england' ),
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
			'peterborough' => 'east-of-england', 'stevenage' => 'east-of-england', 'colchester' => 'east-of-england', 'welwyn' => 'east-of-england',
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
		/* Broad halves a territory title often uses. Only when nothing more
		   precise matched, so "Leeds, North" stays Yorkshire. */
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

if ( ! function_exists( 'msh_nr_digest_jobs' ) ) {
	/* The roles for one nurse's weekly email from supplier-careers.json.
	   Returns array( 'local' => [...], 'national' => [...] ), each role
	   array( title, company, location, url ), unsent ones only. */
	function msh_nr_digest_jobs( $feed, $region, $sent ) {
		$out  = array( 'local' => array(), 'national' => array() );
		$sent = is_array( $sent ) ? array_flip( $sent ) : array();
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
				if ( empty( $r['commercial'] ) && empty( $r['clinical'] ) ) {
					continue;
				}
				if ( ! preg_match( '#^https://#', $r['url'] ) || isset( $sent[ $r['url'] ] ) || isset( $seen[ $r['url'] ] ) ) {
					continue;
				}
				$seen[ $r['url'] ] = true;
				$loc  = isset( $r['location'] ) && is_string( $r['location'] ) ? $r['location'] : '';
				$job  = array( 'title' => (string) $r['title'], 'company' => isset( $sup['name'] ) ? (string) $sup['name'] : '', 'location' => $loc, 'url' => $r['url'] );
				$regs = msh_nr_job_regions( $r['title'], $loc );
				if ( ! $regs ) {
					$out['national'][] = $job;
				} elseif ( in_array( $region, $regs, true ) ) {
					$out['local'][] = $job;
				}
			}
		}
		return $out;
	}
}

if ( ! function_exists( 'msh_nr_digest_email' ) ) {
	/* Subject and HTML body of one weekly email, or null when there is
	   nothing to send. $links: array( careers, register, unsub ) absolute URLs. */
	function msh_nr_digest_email( $first, $regionLabel, $jobs, $links ) {
		$local = array_slice( $jobs['local'], 0, 12 );
		$nat   = array_slice( $jobs['national'], 0, 6 );
		if ( ! $local && ! $nat ) {
			return null;
		}
		$e    = function ( $s ) { return htmlspecialchars( (string) $s, ENT_QUOTES, 'UTF-8' ); };
		$list = function ( $rows ) use ( $e ) {
			$h = '';
			foreach ( $rows as $j ) {
				$h .= '<tr><td style="padding:10px 0;border-bottom:1px solid #E6E2D8">'
					. '<a href="' . $e( $j['url'] ) . '" style="color:#14304F;font-weight:600;text-decoration:none">' . $e( $j['title'] ) . '</a><br>'
					. '<span style="color:#5A6676;font-size:13px">' . $e( $j['company'] ) . ( '' !== $j['location'] ? ' &middot; ' . $e( $j['location'] ) : '' ) . '</span></td></tr>';
			}
			return '<table role="presentation" width="100%" cellpadding="0" cellspacing="0">' . $h . '</table>';
		};
		$n    = count( $local );
		$subj = $n ? ( $n . ' new role' . ( 1 === $n ? '' : 's' ) . ' in ' . $regionLabel . ' this week' ) : 'New UK-wide roles this week';
		$h    = '<div style="font-family:Arial,sans-serif;font-size:15px;line-height:1.5;color:#1C2633;max-width:600px">'
			. '<p>Hi' . ( '' !== $first ? ' ' . $e( $first ) : '' ) . ',</p>'
			. '<p>Here are this week\'s new roles from the companies\' own careers pages.</p>';
		if ( $local ) {
			$h .= '<h2 style="font-size:17px;color:#14304F;margin:24px 0 4px">In ' . $e( $regionLabel ) . '</h2>' . $list( $local );
		}
		if ( $nat ) {
			$h .= '<h2 style="font-size:17px;color:#14304F;margin:24px 0 4px">UK-wide or several locations</h2>' . $list( $nat );
		}
		$h .= '<p style="margin-top:24px"><a href="' . $e( $links['careers'] ) . '" style="color:#14304F">See every role on the Career Centre</a><br>'
			. '<a href="' . $e( $links['register'] ) . '" style="color:#14304F">Update your register profile</a></p>'
			. '<p style="color:#5A6676;font-size:12px;margin-top:24px">You get this because you asked for a weekly jobs email on the Nursing Register. '
			. '<a href="' . $e( $links['unsub'] ) . '" style="color:#5A6676">Stop these emails</a>.</p></div>';
		return array( 'subject' => $subj, 'html' => $h );
	}
}

if ( ! function_exists( 'msh_nr_unsub_token' ) ) {
	function msh_nr_unsub_token( $uid ) {
		return substr( hash_hmac( 'sha256', 'nr-unsub|' . (int) $uid, wp_salt( 'auth' ) ), 0, 32 );
	}
}

if ( ! function_exists( 'msh_nr_jobs_batch' ) ) {
	/* One batch of the weekly email. Schedules the next batch itself. */
	function msh_nr_jobs_batch() {
		$feed = get_transient( 'msh_nr_jobs_feed' );
		if ( ! is_array( $feed ) ) {
			$r = wp_remote_get( MSH_NR_CAREERS_URL, array( 'timeout' => 30 ) );
			if ( is_wp_error( $r ) || 200 !== (int) wp_remote_retrieve_response_code( $r ) ) {
				return;
			}
			$feed = json_decode( wp_remote_retrieve_body( $r ), true );
			if ( ! is_array( $feed ) ) {
				return;
			}
			set_transient( 'msh_nr_jobs_feed', $feed, 6 * HOUR_IN_SECONDS );
		}
		$o      = msh_nr_options();
		$cursor = (int) get_option( 'msh_nr_jobs_cursor', 0 );
		$ids    = get_users( array( 'meta_key' => 'msh_nurse_ref', 'fields' => 'ID', 'orderby' => 'ID', 'order' => 'ASC', 'number' => MSH_NR_BATCH, 'offset' => $cursor ) );
		$links  = array(
			'careers'  => home_url( '/medical-sales-hub/careers/' ),
			'register' => home_url( '/clinical-hub/nursing-register/' ),
		);
		foreach ( $ids as $id ) {
			$p = get_user_meta( $id, 'msh_nurse_register', true );
			if ( ! is_array( $p ) || empty( $p['jobsEmail'] ) || empty( $p['region'] ) || ! isset( $o['regions'][ $p['region'] ] ) ) {
				continue;
			}
			$sent = get_user_meta( $id, 'msh_nr_jobs_sent', true );
			$sent = is_array( $sent ) ? $sent : array();
			$jobs = msh_nr_digest_jobs( $feed, $p['region'], $sent );
			$u    = get_userdata( $id );
			if ( ! $u ) {
				continue;
			}
			$links['unsub'] = add_query_arg( array( 'msh_nr_unsub' => $id, 't' => msh_nr_unsub_token( $id ) ), home_url( '/' ) );
			$mail = msh_nr_digest_email( (string) $u->first_name, $o['regions'][ $p['region'] ], $jobs, $links );
			if ( null === $mail ) {
				continue;
			}
			$ok = wp_mail( $u->user_email, $mail['subject'], $mail['html'], array(
				'Content-Type: text/html; charset=UTF-8',
				'List-Unsubscribe: <' . $links['unsub'] . '>',
			) );
			if ( $ok ) {
				foreach ( array_merge( array_slice( $jobs['local'], 0, 12 ), array_slice( $jobs['national'], 0, 6 ) ) as $j ) {
					array_unshift( $sent, $j['url'] );
				}
				update_user_meta( $id, 'msh_nr_jobs_sent', array_slice( array_values( array_unique( $sent ) ), 0, 400 ) );
			}
		}
		if ( count( $ids ) === MSH_NR_BATCH ) {
			update_option( 'msh_nr_jobs_cursor', $cursor + MSH_NR_BATCH, false );
			wp_schedule_single_event( time() + 120, 'msh_nr_jobs_batch' );
		} else {
			update_option( 'msh_nr_jobs_cursor', 0, false );
			delete_transient( 'msh_nr_jobs_feed' );
		}
	}
}

add_action( 'msh_nr_jobs_batch', 'msh_nr_jobs_batch' );
add_action( 'msh_nr_jobs_week', function () {
	update_option( 'msh_nr_jobs_cursor', 0, false );
	delete_transient( 'msh_nr_jobs_feed' );
	msh_nr_jobs_batch();
} );

/* Weekly, from the next Monday 07:00 UK time. */
add_action( 'init', function () {
	if ( wp_next_scheduled( 'msh_nr_jobs_week' ) ) {
		return;
	}
	$next = new DateTime( 'next monday 07:00', new DateTimeZone( 'Europe/London' ) );
	wp_schedule_event( $next->getTimestamp(), 'weekly', 'msh_nr_jobs_week' );
} );

/* One-click unsubscribe from the weekly email. The token proves the link
   came from an email sent to that member; no login needed. */
add_action( 'init', function () {
	if ( empty( $_GET['msh_nr_unsub'] ) || empty( $_GET['t'] ) ) {
		return;
	}
	$uid = (int) $_GET['msh_nr_unsub'];
	if ( $uid <= 0 || ! hash_equals( msh_nr_unsub_token( $uid ), (string) $_GET['t'] ) ) {
		wp_die( 'That link has expired or is not complete. Log in and untick the weekly jobs email on your Nursing Register profile instead.', 'Nursing Register', array( 'response' => 400 ) );
	}
	$p = get_user_meta( $uid, 'msh_nurse_register', true );
	if ( is_array( $p ) ) {
		$p['jobsEmail'] = false;
		update_user_meta( $uid, 'msh_nurse_register', $p );
	}
	wp_die( 'Done. You won\'t get the weekly jobs email any more. Your register profile is unchanged.', 'Nursing Register', array( 'response' => 200 ) );
}, 1 );

if ( ! function_exists( 'msh_nr_can_browse' ) ) {
	function msh_nr_can_browse() {
		return current_user_can( 'manage_options' ) || current_user_can( 'msh_view_nurse_register' );
	}
}

if ( ! function_exists( 'msh_nr_new_ref' ) ) {
	function msh_nr_new_ref() {
		$abc = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
		for ( $try = 0; $try < 20; $try++ ) {
			$r = 'NR-';
			for ( $i = 0; $i < 6; $i++ ) {
				$r .= $abc[ random_int( 0, strlen( $abc ) - 1 ) ];
			}
			if ( ! get_users( array( 'meta_key' => 'msh_nurse_ref', 'meta_value' => $r, 'number' => 1, 'fields' => 'ID' ) ) ) {
				return $r;
			}
		}
		return 'NR-' . strtoupper( wp_generate_password( 10, false ) );
	}
}

if ( ! function_exists( 'msh_nr_user_by_ref' ) ) {
	function msh_nr_user_by_ref( $ref ) {
		if ( ! is_string( $ref ) || ! preg_match( '/^NR-[A-Z0-9]{6,10}$/', $ref ) ) {
			return 0;
		}
		$ids = get_users( array( 'meta_key' => 'msh_nurse_ref', 'meta_value' => $ref, 'number' => 1, 'fields' => 'ID' ) );
		return $ids ? (int) $ids[0] : 0;
	}
}

if ( ! function_exists( 'msh_nr_payload' ) ) {
	function msh_nr_payload( $uid ) {
		$p = get_user_meta( $uid, 'msh_nurse_register', true );
		return array(
			'options'   => msh_nr_options(),
			'profile'   => is_array( $p ) ? $p : null,
			'canBrowse' => msh_nr_can_browse(),
			'isAdmin'   => current_user_can( 'manage_options' ),
			'staleDays' => MSH_NR_STALE_DAYS,
		);
	}
}

/* Employers get their own role, given by Lou in Users > Edit. They can read
   the Hub and browse the register, nothing else. */
add_action( 'init', function () {
	if ( ! get_role( 'msh_employer' ) ) {
		add_role( 'msh_employer', 'Hub Employer', array( 'read' => true, 'msh_view_nurse_register' => true ) );
	}
} );

add_action( 'rest_api_init', function () {
	$logged_in = function () { return is_user_logged_in(); };
	$browser   = function () { return is_user_logged_in() && msh_nr_can_browse(); };
	$admin     = function () { return current_user_can( 'manage_options' ); };

	register_rest_route( 'msh/v1', '/nurse-register', array(
		array(
			'methods'             => 'GET',
			'permission_callback' => $logged_in,
			'callback'            => function () {
				nocache_headers();
				return msh_nr_payload( get_current_user_id() );
			},
		),
		array(
			'methods'             => 'POST',
			'permission_callback' => $logged_in,
			'callback'            => function ( WP_REST_Request $req ) {
				$uid = get_current_user_id();
				$old = get_user_meta( $uid, 'msh_nurse_register', true );
				$ref = ( is_array( $old ) && ! empty( $old['ref'] ) ) ? '' : msh_nr_new_ref();
				$r   = msh_nr_clean( $req->get_json_params(), is_array( $old ) ? $old : array(), wp_date( 'Y-m-d' ), $ref );
				if ( ! $r['ok'] ) {
					return new WP_Error( 'msh_nr_' . $r['why'], $r['why'], array( 'status' => 400, 'field' => $r['why'] ) );
				}
				update_user_meta( $uid, 'msh_nurse_register', $r['profile'] );
				update_user_meta( $uid, 'msh_nurse_ref', $r['profile']['ref'] );
				return msh_nr_payload( $uid );
			},
		),
		array(
			'methods'             => 'DELETE',
			'permission_callback' => $logged_in,
			'callback'            => function () {
				$uid = get_current_user_id();
				delete_user_meta( $uid, 'msh_nurse_register' );
				delete_user_meta( $uid, 'msh_nurse_ref' );
				return msh_nr_payload( $uid );
			},
		),
	) );

	register_rest_route( 'msh/v1', '/nurse-register/browse', array(
		'methods'             => 'GET',
		'permission_callback' => $browser,
		'callback'            => function () {
			nocache_headers();
			$today   = wp_date( 'Y-m-d' );
			$isAdmin = current_user_can( 'manage_options' );
			$ids     = get_users( array( 'meta_key' => 'msh_nurse_ref', 'fields' => 'ID', 'number' => 2000 ) );
			$out     = array();
			foreach ( $ids as $id ) {
				$p   = get_user_meta( $id, 'msh_nurse_register', true );
				$pub = msh_nr_public( $p, $today );
				if ( null === $pub ) {
					if ( ! $isAdmin || ! is_array( $p ) ) {
						continue;
					}
					$pub = msh_nr_public( array_merge( $p, array( 'visible' => true, 'consentAt' => 'x', 'updated' => $today ) ), $today );
					$pub['hidden'] = true;
				}
				$u = get_userdata( $id );
				if ( empty( $pub['hidden'] ) ) {
					$c = msh_nr_contact( $p, $u ? $u->display_name : '', $u ? $u->user_email : '' );
					if ( null !== $c ) {
						$pub['contact'] = $c;
					}
				}
				if ( $isAdmin ) {
					$pub['private'] = array(
						'name'     => $u ? $u->display_name : '',
						'email'    => $u ? $u->user_email : '',
						'phone'    => isset( $p['phone'] ) ? $p['phone'] : '',
						'nmcPin'   => isset( $p['nmcPin'] ) ? $p['nmcPin'] : '',
						'linkedin' => isset( $p['linkedin'] ) ? $p['linkedin'] : '',
						'updated'  => isset( $p['updated'] ) ? $p['updated'] : '',
					);
				}
				$out[] = $pub;
			}
			usort( $out, function ( $a, $b ) { return strcmp( (string) $b['updated'], (string) $a['updated'] ); } );
			return array( 'profiles' => $out );
		},
	) );

	register_rest_route( 'msh/v1', '/nurse-register/intro', array(
		'methods'             => 'POST',
		'permission_callback' => $browser,
		'callback'            => function ( WP_REST_Request $req ) {
			$b     = $req->get_json_params();
			$b     = is_array( $b ) ? $b : array();
			$today = wp_date( 'Y-m-d' );
			$nid   = msh_nr_user_by_ref( isset( $b['ref'] ) ? $b['ref'] : '' );
			$p     = $nid ? get_user_meta( $nid, 'msh_nurse_register', true ) : null;
			if ( ! $nid || null === msh_nr_public( $p, $today ) ) {
				return new WP_Error( 'msh_nr_ref', 'not on the register', array( 'status' => 404 ) );
			}
			$eid = get_current_user_id();
			$log = get_user_meta( $eid, 'msh_nr_intro_log', true );
			$log = ( is_array( $log ) && isset( $log['d'] ) && $log['d'] === $today ) ? $log : array( 'd' => $today, 'n' => 0 );
			if ( $log['n'] >= MSH_NR_INTROS_PER_DAY ) {
				return new WP_Error( 'msh_nr_limit', 'daily limit', array( 'status' => 429 ) );
			}
			$msg = msh_nr_text( isset( $b['message'] ) ? $b['message'] : '', 1000 );
			$e   = get_userdata( $eid );
			$n   = get_userdata( $nid );
			$body = "An employer has asked to be introduced to a nurse on the Nursing Register.\n\n"
				. "Employer: " . $e->display_name . " <" . $e->user_email . ">\n"
				. "Their message: " . ( '' !== $msg ? $msg : '(none)' ) . "\n\n"
				. "Nurse: " . $p['ref'] . "\n"
				. "Name: " . ( $n ? $n->display_name : '' ) . "\n"
				. "Email: " . ( $n ? $n->user_email : '' ) . "\n"
				. "Phone: " . ( $p['phone'] ? $p['phone'] : '(not given)' ) . "\n"
				. "NMC PIN: " . ( $p['nmcPin'] ? $p['nmcPin'] : '(not given)' ) . ( $p['nmcChecked'] ? ' (checked ' . $p['nmcChecked'] . ')' : ' (not checked yet)' ) . "\n\n"
				. "Check with the nurse before passing on any of their details.\n";
			$sent = wp_mail( get_option( 'admin_email' ), 'Nursing Register: introduction request for ' . $p['ref'], $body, array( 'Reply-To: ' . $e->user_email ) );
			if ( ! $sent ) {
				return new WP_Error( 'msh_nr_mail', 'could not send', array( 'status' => 502 ) );
			}
			$log['n']++;
			update_user_meta( $eid, 'msh_nr_intro_log', $log );
			return array( 'ok' => true );
		},
	) );

	register_rest_route( 'msh/v1', '/nurse-register/verify', array(
		'methods'             => 'POST',
		'permission_callback' => $admin,
		'callback'            => function ( WP_REST_Request $req ) {
			$b   = $req->get_json_params();
			$b   = is_array( $b ) ? $b : array();
			$nid = msh_nr_user_by_ref( isset( $b['ref'] ) ? $b['ref'] : '' );
			$p   = $nid ? get_user_meta( $nid, 'msh_nurse_register', true ) : null;
			if ( ! is_array( $p ) ) {
				return new WP_Error( 'msh_nr_ref', 'not on the register', array( 'status' => 404 ) );
			}
			if ( ! empty( $b['checked'] ) && '' === $p['nmcPin'] ) {
				return new WP_Error( 'msh_nr_nopin', 'no NMC PIN to check', array( 'status' => 400 ) );
			}
			$p['nmcChecked'] = ! empty( $b['checked'] ) ? wp_date( 'Y-m-d' ) : '';
			update_user_meta( $nid, 'msh_nurse_register', $p );
			return array( 'ok' => true, 'nmcChecked' => $p['nmcChecked'] );
		},
	) );
} );
