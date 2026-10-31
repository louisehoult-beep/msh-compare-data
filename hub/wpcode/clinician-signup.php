<?php
/* Clinician programme sign-up (Lou, 31/10/2026).

   NMC-registered nurses and allied health professionals moving into industry
   sign up for Lou's free training and support. One form, shortcode
   [msh_clinician_signup], on a draft Hub page until the agreement text is in.

   What it does:
   - Saves each sign-up as a private msh_clinician post (wp-admin shows them
     under "Clinician sign-ups"). Only administrators can read them, through
     wp-admin or wp/v2/msh-clinicians, which is how the local intake script
     (Clinician-Programme/clinician_intake.py) pulls them into Lou's database.
   - Keeps the CV outside any listed folder under a random name, served only
     through a signed link (msh_cp_cv_url).
   - Emails the clinician a welcome with next steps and a copy of the agreement
     they ticked, and emails Lou the full details and the CV link.
   - Hands back the reference and the Bookings link, so the page moves straight
     to booking the 60-minute Teams call.

   The gate: the form only accepts submissions from administrators (for
   testing) and shows everyone else "opening soon" until all three hold:
   MSH_CP_SIGNED_OFF is true (Lou or the solicitor has signed off the
   wording), the version no longer starts with PLACEHOLDER, and both the
   terms and privacy notice links are set.

   Process: 02-Elevate-and-Thrive/Process flows for all brands/clinician-signup-pipeline.md */

/* Agreement and privacy notice wording: CSP-PA-v0.3 and CSP-PN-v0.3, from
   02-Elevate-and-Thrive/Clinical-Recruitment/Agreement/01 and 04. DRAFT
   pending solicitor review; never edit the wording here without a new
   version there. */
if ( ! defined( 'MSH_CP_SIGNED_OFF' ) ) {
	define( 'MSH_CP_SIGNED_OFF', false );
}
if ( ! defined( 'MSH_CP_AGREEMENT_VERSION' ) ) {
	define( 'MSH_CP_AGREEMENT_VERSION', 'CSP-PA-v0.3' );
}
if ( ! defined( 'MSH_CP_PRIVACY_VERSION' ) ) {
	define( 'MSH_CP_PRIVACY_VERSION', 'CSP-PN-v0.3' );
}
if ( ! defined( 'MSH_CP_TERMS_URL' ) ) {
	define( 'MSH_CP_TERMS_URL', '' );
}
if ( ! defined( 'MSH_CP_PRIVACY_URL' ) ) {
	define( 'MSH_CP_PRIVACY_URL', '' );
}
if ( ! defined( 'MSH_CP_AGREEMENT_TEXT' ) ) {
	/* Plain text, paragraphs separated by blank lines. {terms} and {privacy}
	   become links to the full terms and the privacy notice. */
	define( 'MSH_CP_AGREEMENT_TEXT', "DRAFT – solicitor review. Not for use until signed off.

Your free programme with Elevate and Thrive

This is a short summary of how the programme works. The full terms are here: {terms}. If anything here differs from the full terms, the full terms apply.

Who we are. Elevate and Thrive Ltd (company number 17154474), 2 Lakeside, Sturton by Stow, Lincoln, LN1 2TZ. Contact: Louise Hoult, louisehoult@elevateandthrive.uk.

What you get, free. Exactly three things:
1. The Clinical Interview Playbook: the full Clinical Interview Playbook bundle, the same bundle sold at elevateandthrive.uk/training-courses/: the 9-module video course, the Medical Device Interview Preparation Pack and the Beyond the Bedside nursing careers guide, with 12 months' access from the date we set up your account.
2. 12 months of Medical Sales Hub access (the Medical Sales Intelligence Hub, medsalesintelligencehub.co.uk), the Hub access that comes with the paid bundle, from the date we set up your account.
3. One-to-one support from Louise Hoult through the whole process: your first call, CV and LinkedIn profile, preparation for each role, interviews and presentations, offers, and your first six months in post if you are placed through us.

The Playbook bundle, including its Hub access, is a paid product; you do not pay for it. The current price is shown on that page.

It costs you nothing, now or later. We never charge you for finding you work, and there is nothing to repay if you leave.

How placement works. We work with one recruitment partner, Kore Executive Limited (KORE). When a suitable role comes up, we will ask you first. Only if you say yes do we put you forward, through KORE, to that employer. The employer pays KORE's fee, never you.

What we ask of you.
1. Before each role, confirm you want to be put forward and that no one else has put you forward to that employer for that role in the last six months.
2. Once we have put you forward for a role, do not let another agency put you forward for the same role while ours is live.
3. Please tell us before you register with another agency for industry roles, so you are not put forward twice. This is a request. You never have to tell us who your next employer is.
4. Give us accurate details, including your professional registration.

Leaving. You can leave at any time by emailing us. There is no penalty and nothing to pay back. Playbook and Hub access already set up continue to the end of their 12 months. One-to-one support and future introductions to roles stop when you leave.

Your details. We keep your details safely and only share them as explained in our {privacy}. We share your CV and details with KORE only if you tick the separate box below, and with an employer only when you agree to each role. We never contact your current employer." );
}
if ( ! function_exists( 'msh_cp_boxes' ) ) {
	/* The three sign-up boxes, word for word from CSP-PA-v0.3. All start
	   unticked; only box 1 is required. */
	function msh_cp_boxes() {
		return array(
			'box1' => array( 'Programme agreement (required).', 'I have read and agree to the Clinical Selection Pathway programme agreement and terms, version CSP-PA-v0.3. I understand I receive the Clinical Interview Playbook course, 12 months of Medical Sales Hub access and one-to-one support free, I can leave at any time without penalty or repayment, and I will never be charged for being found work.' ),
			'box2' => array( 'Sharing my details with KORE (optional, needed for placement).', 'I agree that Elevate and Thrive Ltd may share my CV, contact details, registration details and assessment notes with Kore Executive Limited so that KORE can consider me for industry roles. I understand nothing is sent to any employer without my agreement for each role, and that I can withdraw this consent at any time by emailing louisehoult@elevateandthrive.uk.' ),
			'box3' => array( 'Updates (optional).', 'I would like to receive emails from Elevate and Thrive Ltd about new roles, training and events. I can unsubscribe at any time.' ),
		);
	}
}
if ( ! defined( 'MSH_CP_BOOKING_URL' ) ) {
	define( 'MSH_CP_BOOKING_URL', 'https://bookings.cloud.microsoft/book/ElevateThrive@elevateandthrive.uk/s/DMxhuXZTw0Sfr_KVQKx7ng2' );
}
if ( ! defined( 'MSH_CP_LOU' ) ) {
	define( 'MSH_CP_LOU', 'louisehoult@elevateandthrive.uk' );
}

if ( ! function_exists( 'msh_cp_options' ) ) {
	/* Every tick list. Keys are what the database stores; labels are what
	   people see. Pure, so it is tested. */
	function msh_cp_options() {
		return array(
			'regions' => array(
				'north-east' => 'North East', 'north-west' => 'North West', 'yorkshire-humber' => 'Yorkshire and the Humber',
				'east-midlands' => 'East Midlands', 'west-midlands' => 'West Midlands', 'east-of-england' => 'East of England',
				'london' => 'London', 'south-east' => 'South East', 'south-west' => 'South West',
				'wales' => 'Wales', 'scotland' => 'Scotland', 'northern-ireland' => 'Northern Ireland',
			),
			'travel' => array(
				'local' => 'Local only (about 30 miles)', 'region' => 'Across my region',
				'multi-region' => 'Several regions', 'national' => 'UK-wide, including overnight stays',
			),
			'relocate' => array( 'yes' => 'Yes', 'maybe' => 'For the right role', 'no' => 'No' ),
			'licence' => array( 'full' => 'Full UK licence', 'provisional' => 'Provisional', 'none' => 'No licence', 'other' => 'Other licence (say in notes)' ),
			'profession' => array(
				'nurse' => 'NMC-registered nurse', 'midwife' => 'NMC-registered midwife', 'nursing-associate' => 'NMC-registered nursing associate',
				'odp' => 'Operating Department Practitioner (ODP)', 'physio' => 'Physiotherapist', 'ot' => 'Occupational therapist',
				'radiographer' => 'Radiographer', 'paramedic' => 'Paramedic', 'dietitian' => 'Dietitian',
				'slt' => 'Speech and language therapist', 'podiatrist' => 'Podiatrist', 'scientist' => 'Healthcare scientist',
				'other' => 'Other (say in notes)',
			),
			'regstatus' => array(
				'live' => 'Registered and live', 'revalidation' => 'Registered, revalidation due within six months',
				'lapsed' => 'Lapsed', 'pending' => 'Awaiting registration',
			),
			'band' => array(
				'5' => 'Band 5', '6' => 'Band 6', '7' => 'Band 7', '8a' => 'Band 8a', '8b' => 'Band 8b',
				'8c' => 'Band 8c or above', 'non-afc' => 'Not on Agenda for Change',
			),
			'employer' => array( 'nhs' => 'NHS', 'private' => 'Independent or private sector', 'agency' => 'Agency or bank', 'other' => 'Other' ),
			'specialities' => array(
				'theatres' => 'Theatres and perioperative', 'icu' => 'Intensive care (ICU) and critical care', 'emergency' => 'Emergency and urgent care',
				'acute-medicine' => 'Acute and general medicine', 'general-surgery' => 'General surgery', 'wound-care' => 'Wound care',
				'tissue-viability' => 'Tissue viability', 'renal' => 'Renal and dialysis', 'cardiology' => 'Cardiology and cardiac surgery',
				'cath-lab' => 'Cath lab and interventional', 'orthopaedics' => 'Orthopaedics and trauma', 'oncology' => 'Oncology and systemic anti-cancer therapy (SACT)',
				'haematology' => 'Haematology', 'diabetes' => 'Diabetes and endocrinology', 'continence' => 'Continence, bladder and bowel',
				'urology' => 'Urology', 'stoma' => 'Stoma care', 'gastro' => 'Gastroenterology and endoscopy',
				'infection-prevention' => 'Infection prevention and control', 'community' => 'Community and district nursing',
				'respiratory' => 'Respiratory', 'vascular' => 'Vascular', 'vascular-access' => 'Vascular access and IV therapy',
				'neurology' => 'Neurology and stroke', 'ophthalmology' => 'Ophthalmology', 'ent' => 'Ear, nose and throat (ENT)', 'plastics-burns' => 'Plastics and burns',
				'womens-health' => "Gynaecology and women's health", 'maternity' => 'Maternity', 'neonatal' => 'Neonatal', 'paediatrics' => 'Paediatrics',
				'older-people' => 'Older people and frailty', 'palliative' => 'Palliative care', 'mental-health' => 'Mental health',
				'radiology' => 'Radiology and imaging', 'pain' => 'Pain management', 'nutrition' => 'Nutrition',
				'practice-nursing' => 'Practice nursing and primary care', 'education' => 'Clinical education and practice development',
				'research' => 'Clinical research', 'moving-handling' => 'Moving and handling', 'other' => 'Other (say in notes)',
			),
			'roles' => array(
				'medical-sales' => 'Medical sales (territory or account manager)', 'clinical-specialist' => 'Clinical specialist',
				'product-specialist' => 'Product specialist', 'nurse-advisor' => 'Nurse advisor', 'clinical-nurse-advisor' => 'Clinical nurse advisor',
				'trainer-educator' => 'Clinical trainer or educator', 'product-manager' => 'Product manager',
				'pharma' => 'Pharmaceutical roles', 'medical-devices' => 'Any medical devices role', 'not-sure' => 'Not sure yet',
			),
			'notice' => array(
				'none' => 'No notice', '4-weeks' => 'Up to 4 weeks', '8-weeks' => 'Up to 8 weeks', '12-weeks' => 'Up to 12 weeks', 'longer' => 'Longer than 12 weeks',
			),
			'availability' => array(
				'now' => 'Ready now', '1-month' => 'Within a month', '3-months' => 'Within three months',
				'6-months' => 'Within six months', 'exploring' => 'Exploring, no rush',
			),
		);
	}
}

if ( ! function_exists( 'msh_cp_live' ) ) {
	function msh_cp_live() {
		return MSH_CP_SIGNED_OFF && 0 !== strpos( MSH_CP_AGREEMENT_VERSION, 'PLACEHOLDER' ) && MSH_CP_TERMS_URL && MSH_CP_PRIVACY_URL;
	}
}

if ( ! function_exists( 'msh_cp_clean' ) ) {
	/* Raw form fields in, a clean record or a list of errors out. $now is an
	   ISO 8601 time, $version and $privacy the agreement and privacy notice
	   versions on show. Pure, so it is tested. */
	function msh_cp_clean( $in, $now, $version, $privacy ) {
		$o   = msh_cp_options();
		$err = array();
		$s   = function ( $k, $max = 200 ) use ( $in ) {
			$v = isset( $in[ $k ] ) && is_scalar( $in[ $k ] ) ? (string) $in[ $k ] : '';
			$v = trim( preg_replace( '/[\x00-\x08\x0B\x0C\x0E-\x1F<>]/', '', $v ) );
			return function_exists( 'mb_substr' ) ? mb_substr( $v, 0, $max ) : substr( $v, 0, $max );
		};
		$one = function ( $k, $list, $required = false ) use ( $in, $o, &$err ) {
			$v = isset( $in[ $k ] ) && is_string( $in[ $k ] ) ? $in[ $k ] : '';
			if ( isset( $o[ $list ][ $v ] ) ) {
				return $v;
			}
			if ( $required ) {
				$err[] = $k;
			}
			return '';
		};
		$many = function ( $k, $list ) use ( $in, $o ) {
			$v = isset( $in[ $k ] ) ? $in[ $k ] : array();
			$v = is_array( $v ) ? $v : explode( ',', (string) $v );
			return array_values( array_unique( array_filter( $v, function ( $x ) use ( $o, $list ) {
				return is_string( $x ) && isset( $o[ $list ][ $x ] );
			} ) ) );
		};

		$r = array(
			'first_name'   => $s( 'first_name', 80 ),
			'last_name'    => $s( 'last_name', 80 ),
			'email'        => strtolower( $s( 'email', 160 ) ),
			'phone'        => preg_replace( '/[^0-9+ ()-]/', '', $s( 'phone', 40 ) ),
			'region'       => $one( 'region', 'regions', true ),
			'icb'          => $s( 'icb', 120 ),
			'postcode'     => strtoupper( preg_replace( '/\s+/', '', $s( 'postcode', 8 ) ) ),
			'travel'       => $one( 'travel', 'travel', true ),
			'relocate'     => $one( 'relocate', 'relocate' ),
			'licence'      => $one( 'licence', 'licence', true ),
			'profession'   => $one( 'profession', 'profession', true ),
			'pin'          => strtoupper( preg_replace( '/[^A-Za-z0-9]/', '', $s( 'pin', 20 ) ) ),
			'regstatus'    => $one( 'regstatus', 'regstatus', true ),
			'band'         => $one( 'band', 'band' ),
			'current_role' => $s( 'current_role', 160 ),
			'employer'     => $one( 'employer', 'employer', true ),
			'employer_name' => $s( 'employer_name', 160 ),
			'years'        => '',
			'specialities' => $many( 'specialities', 'specialities' ),
			'procedures'   => $s( 'procedures', 2000 ),
			'industry'     => $s( 'industry', 2000 ),
			'roles'        => $many( 'roles', 'roles' ),
			'salary'       => $s( 'salary', 80 ),
			'notice'       => $one( 'notice', 'notice' ),
			'availability' => $one( 'availability', 'availability', true ),
			'linkedin'     => $s( 'linkedin', 300 ),
			'notes'        => $s( 'notes', 3000 ),
			'source'       => preg_replace( '/[^a-z0-9_-]/', '', strtolower( $s( 'source', 60 ) ) ),
			'signed_up'    => $now,
			'agreement_version'  => '',
			'privacy_version'    => '',
			'agreement_accepted' => '',
			'box1'               => false,
			'box2'               => false,
			'box3'               => false,
		);
		$y = $s( 'years', 4 );
		if ( preg_match( '/^\d{1,2}$/', $y ) ) {
			$r['years'] = (int) $y;
		} else {
			$err[] = 'years';
		}
		foreach ( array( 'first_name', 'last_name', 'current_role' ) as $k ) {
			if ( '' === $r[ $k ] ) {
				$err[] = $k;
			}
		}
		if ( ! preg_match( '/^[^@\s]+@[^@\s]+\.[a-z]{2,}$/i', $r['email'] ) ) {
			$err[] = 'email';
		}
		if ( strlen( preg_replace( '/\D/', '', $r['phone'] ) ) < 10 ) {
			$err[] = 'phone';
		}
		/* Outward code only: LN6, SW1A, B1. */
		if ( ! preg_match( '/^[A-Z]{1,2}[0-9][0-9A-Z]?$/', $r['postcode'] ) ) {
			$err[] = 'postcode';
		}
		/* NMC PINs are 2 digits, a letter, 4 digits, a letter (e.g. 12A3456E);
		   HCPC numbers are 2 letters and digits (e.g. PA123456, ODP12345 is
		   written OD12345). Anything else is kept but not rejected, because
		   registers outside the UK differ; the format is checked again on
		   the call. */
		if ( '' === $r['pin'] && 'pending' !== $r['regstatus'] ) {
			$err[] = 'pin';
		}
		if ( ! $r['specialities'] ) {
			$err[] = 'specialities';
		}
		if ( ! $r['roles'] ) {
			$err[] = 'roles';
		}
		if ( '' !== $r['linkedin'] && ! preg_match( '#^https?://([a-z]{2,3}\.)?linkedin\.com/#i', $r['linkedin'] ) ) {
			$err[] = 'linkedin';
		}
		$tick = function ( $k ) use ( $in ) {
			return isset( $in[ $k ] ) && in_array( (string) $in[ $k ], array( '1', 'on', 'yes', 'true' ), true );
		};
		/* Box 1 is the only required tick, and only counts against the
		   versions on show; boxes 2 and 3 are stored as given. */
		if ( ! $tick( 'box1' ) || $s( 'agreement_version', 40 ) !== $version || $s( 'privacy_version', 40 ) !== $privacy ) {
			$err[] = 'box1';
		} else {
			$r['agreement_version']  = $version;
			$r['privacy_version']    = $privacy;
			$r['agreement_accepted'] = $now;
			$r['box1']               = true;
		}
		$r['box2'] = $tick( 'box2' );
		$r['box3'] = $tick( 'box3' );
		return array( 'record' => $r, 'errors' => array_values( array_unique( $err ) ) );
	}
}

if ( ! function_exists( 'msh_cp_ref' ) ) {
	function msh_cp_ref( $n ) {
		return 'CLN-' . strtoupper( substr( $n, 0, 6 ) );
	}
}

if ( ! function_exists( 'msh_cp_labels' ) ) {
	/* A record as label => readable value, for both emails. Pure, so it is
	   tested. */
	function msh_cp_labels( $r ) {
		$o   = msh_cp_options();
		$one = function ( $list, $v ) use ( $o ) {
			return isset( $o[ $list ][ $v ] ) ? $o[ $list ][ $v ] : '';
		};
		$ls  = function ( $list, $vs ) use ( $o ) {
			return implode( ', ', array_map( function ( $v ) use ( $o, $list ) {
				return isset( $o[ $list ][ $v ] ) ? $o[ $list ][ $v ] : $v;
			}, (array) $vs ) );
		};
		return array(
			'Name'                    => trim( $r['first_name'] . ' ' . $r['last_name'] ),
			'Email'                   => $r['email'],
			'Phone'                   => $r['phone'],
			'Region'                  => $one( 'regions', $r['region'] ),
			'Integrated Care Board (ICB) area' => $r['icb'],
			'Postcode district'       => $r['postcode'],
			'Travel'                  => $one( 'travel', $r['travel'] ),
			'Would relocate'          => $one( 'relocate', $r['relocate'] ),
			'Driving licence'         => $one( 'licence', $r['licence'] ),
			'Profession'              => $one( 'profession', $r['profession'] ),
			'PIN'                     => $r['pin'],
			'Registration status'     => $one( 'regstatus', $r['regstatus'] ),
			'Band'                    => $one( 'band', $r['band'] ),
			'Current role'            => $r['current_role'],
			'Employer type'           => $one( 'employer', $r['employer'] ),
			'Employer'                => $r['employer_name'],
			'Years qualified'         => (string) $r['years'],
			'Specialities'            => $ls( 'specialities', $r['specialities'] ),
			'Procedures and devices'  => $r['procedures'],
			'Industry experience'     => $r['industry'],
			'Target roles'            => $ls( 'roles', $r['roles'] ),
			'Salary expectation'      => $r['salary'],
			'Notice period'           => $one( 'notice', $r['notice'] ),
			'Availability'            => $one( 'availability', $r['availability'] ),
			'LinkedIn'                => $r['linkedin'],
			'Notes'                   => $r['notes'],
			'Source'                  => $r['source'],
			'Agreement'               => $r['agreement_version'] . ', accepted ' . $r['agreement_accepted'],
			'Privacy notice'          => $r['privacy_version'],
			'Share with KORE (box 2)' => $r['box2'] ? 'Yes' : 'No: never share with KORE',
			'Email updates (box 3)'   => $r['box3'] ? 'Yes' : 'No',
		);
	}
}

if ( ! function_exists( 'msh_cp_agreement_html' ) ) {
	function msh_cp_agreement_html() {
		$paras = preg_split( '/\n\s*\n/', trim( MSH_CP_AGREEMENT_TEXT ) );
		$links = array(
			'{terms}'   => msh_cp_link( MSH_CP_TERMS_URL, 'Programme terms ' . MSH_CP_AGREEMENT_VERSION ),
			'{privacy}' => msh_cp_link( MSH_CP_PRIVACY_URL, 'privacy notice' ),
		);
		return implode( '', array_map( function ( $p ) use ( $links ) {
			return '<p>' . strtr( nl2br( htmlspecialchars( $p, ENT_QUOTES ) ), $links ) . '</p>';
		}, $paras ) );
	}
	/* A link, or plain text marked as waiting while the URL is not set. */
	function msh_cp_link( $url, $text ) {
		return $url ? '<a href="' . htmlspecialchars( $url, ENT_QUOTES ) . '" target="_blank" rel="noopener" style="color:#14304F">' . htmlspecialchars( $text ) . '</a>' : htmlspecialchars( $text ) . ' (link added at sign-off)';
	}
}

if ( ! function_exists( 'msh_cp_uk_time' ) ) {
	/* 2026-10-31T16:53:44Z -> 31/10/2026 16:53 (UK time). */
	function msh_cp_uk_time( $iso ) {
		try {
			$d = new DateTime( $iso );
			$d->setTimezone( new DateTimeZone( 'Europe/London' ) );
			return $d->format( 'd/m/Y H:i' ) . ' (UK time)';
		} catch ( Exception $e ) {
			return (string) $iso;
		}
	}
}

if ( ! function_exists( 'msh_cp_welcome_email' ) ) {
	/* The clinician's welcome, from the CSP v0.3 welcome email
	   (Clinical-Recruitment/Agreement/03): what they chose, what they get
	   free, the key points, then the booking step and a copy of the
	   agreement they ticked. Pure apart from the agreement constants, so it
	   is tested. */
	function msh_cp_welcome_email( $r, $ref, $booking ) {
		$h    = function ( $v ) {
			return htmlspecialchars( (string) $v, ENT_QUOTES );
		};
		$yn   = function ( $v ) {
			return $v ? 'yes' : 'no';
		};
		$btn  = $booking ? '<p style="margin:22px 0"><a href="' . $h( $booking ) . '" style="background:#0B1C33;color:#FFFFFF;padding:14px 26px;text-decoration:none;font-weight:700;display:inline-block">Book your 60-minute call</a></p>' : '';
		$when = msh_cp_uk_time( $r['agreement_accepted'] );
		$html = '<div style="font-family:Arial,sans-serif;font-size:16px;line-height:1.55;color:#1D2733;background:#FFFFFF;max-width:640px">'
			. '<div style="background:#0B1C33;color:#FFFFFF;padding:22px 26px"><div style="font-size:13px;letter-spacing:.12em;text-transform:uppercase;color:#E0BE8E">Clinical Selection Pathway</div>'
			. '<div style="font-size:24px;margin-top:6px;color:#FFFFFF">Welcome, ' . $h( $r['first_name'] ) . '</div></div>'
			. '<div style="padding:22px 26px;border:1px solid #DBE3EE;border-top:0">'
			. '<p>Thank you for joining the Clinical Selection Pathway. Your reference is <strong>' . $h( $ref ) . '</strong>. Here is your copy of what you agreed on ' . $h( $when ) . ':</p><ul>'
			. '<li>Programme agreement and terms, version ' . $h( $r['agreement_version'] ) . ': ' . msh_cp_link( MSH_CP_TERMS_URL, 'read the terms' ) . ' (the summary is copied below)</li>'
			. '<li>Privacy notice, version ' . $h( $r['privacy_version'] ) . ': ' . msh_cp_link( MSH_CP_PRIVACY_URL, 'read the privacy notice' ) . '</li></ul>'
			. '<p><strong>What you chose</strong></p><ul>'
			. '<li>Programme agreement: agreed</li>'
			. '<li>Share my CV and details with Kore Executive Limited for industry roles: ' . $yn( $r['box2'] ) . '</li>'
			. '<li>Emails about new roles, training and events: ' . $yn( $r['box3'] ) . '</li></ul>'
			. '<p><strong>What you receive, free</strong></p><ul>'
			. "<li>The Clinical Interview Playbook (full bundle, 12 months' access).</li>"
			. '<li>12 months of Medical Sales Hub access.</li></ul>'
			. '<p>Your login details for both follow within 5 business days.</p><ul>'
			. '<li>One-to-one support from me through the whole process, from our first call to your first six months in a new role if you are placed through us.</li></ul>'
			. '<p><strong>The key points</strong></p><ul>'
			. '<li>The programme is free, including the Playbook and the Hub. You will never be charged for being found work, and there is nothing to repay if you leave.</li>'
			. '<li>I will always ask you before putting you forward for a role, and nothing goes to an employer without your agreement for that role.</li>'
			. '<li>I will never contact your current employer.</li>'
			. '<li>You can leave, or change what you agreed to share, at any time by replying to this email.</li></ul>'
			. '<p><strong>What happens next</strong></p>'
			. '<p>Book your 60-minute Microsoft Teams call with me, if you have not already, and put your reference in the booking form so I have your details in front of me. Before then, have your CV to hand and your registration number.</p>'
			. $btn
			. '<p>If anything here does not match what you meant to agree to, just reply and I will put it right.</p>'
			. '<p>Best wishes,</p><p>Louise Hoult<br>Director, Elevate and Thrive Ltd<br>louisehoult@elevateandthrive.uk</p>'
			. '<hr style="border:0;border-top:2px solid #A8842C;margin:26px 0">'
			. '<p><strong>Your copy of the agreement you accepted</strong><br>Version ' . $h( $r['agreement_version'] ) . ', accepted ' . $h( $when ) . '</p>'
			. '<div style="background:#EDE7DC;color:#1D2733;padding:16px 18px;font-size:14px">' . msh_cp_agreement_html() . '</div>'
			. "<p style=\"font-size:13px;color:#1D2733\">Elevate and Thrive Ltd, company number 17154474, 2 Lakeside, Sturton by Stow, Lincoln, LN1 2TZ. Information Commissioner's Office registration ZC203137.</p>"
			. '</div></div>';
		return array(
			'subject' => 'Welcome to the Clinical Selection Pathway: your copy of what you agreed (' . $ref . ')',
			'html'    => $html,
		);
	}
}

if ( ! function_exists( 'msh_cp_lou_email' ) ) {
	function msh_cp_lou_email( $r, $ref, $cv_url ) {
		$rows = '';
		foreach ( msh_cp_labels( $r ) as $k => $v ) {
			$rows .= '<tr><th style="text-align:left;padding:5px 10px;background:#EDE7DC;color:#1D2733;vertical-align:top">' . htmlspecialchars( $k ) . '</th><td style="padding:5px 10px;color:#1D2733">' . nl2br( htmlspecialchars( (string) $v ) ) . '</td></tr>';
		}
		$cv = $cv_url ? '<p><a href="' . htmlspecialchars( $cv_url ) . '" style="color:#14304F">Open CV</a> (signed link)</p>' : '<p>No CV uploaded.</p>';
		return array(
			'subject' => 'Clinician sign-up ' . $ref . ': ' . trim( $r['first_name'] . ' ' . $r['last_name'] ),
			'html'    => '<div style="font-family:Arial,sans-serif;font-size:15px;color:#1D2733;background:#FFFFFF">' . $cv . '<table style="border-collapse:collapse">' . $rows . '</table></div>',
		);
	}
}

/* ---- WordPress wiring below; nothing above calls WordPress. ---- */

if ( ! function_exists( 'msh_cp_cv_dir' ) ) {
	function msh_cp_cv_dir() {
		$u   = wp_upload_dir();
		$dir = trailingslashit( $u['basedir'] ) . 'msh-cp-private';
		if ( ! is_dir( $dir ) ) {
			wp_mkdir_p( $dir );
			file_put_contents( $dir . '/index.php', '<?php // Silence.' );
			file_put_contents( $dir . '/.htaccess', "Require all denied\nDeny from all\n" );
		}
		return $dir;
	}
	function msh_cp_cv_token( $ref, $file ) {
		return hash_hmac( 'sha256', $ref . '|' . $file, wp_salt( 'auth' ) );
	}
	function msh_cp_cv_url( $ref, $file ) {
		return $file ? add_query_arg( array( 'ref' => $ref, 't' => msh_cp_cv_token( $ref, $file ) ), rest_url( 'msh-cp/v1/cv' ) ) : '';
	}
}

add_action( 'init', function () {
	$admin = 'manage_options';
	register_post_type( 'msh_clinician', array(
		'labels'          => array( 'name' => 'Clinician sign-ups', 'singular_name' => 'Clinician sign-up' ),
		'public'          => false,
		'show_ui'         => true,
		'menu_icon'       => 'dashicons-id',
		'supports'        => array( 'title', 'custom-fields' ),
		'show_in_rest'    => true,
		'rest_base'       => 'msh-clinicians',
		'capabilities'    => array(
			'edit_post' => $admin, 'read_post' => $admin, 'delete_post' => $admin, 'edit_posts' => $admin,
			'edit_others_posts' => $admin, 'publish_posts' => $admin, 'read_private_posts' => $admin,
			'delete_posts' => $admin, 'create_posts' => 'do_not_allow',
		),
		'map_meta_cap'    => false,
	) );
	foreach ( array( 'msh_cp_json', 'msh_cp_ref', 'msh_cp_cv_url' ) as $k ) {
		register_post_meta( 'msh_clinician', $k, array(
			'type'          => 'string',
			'single'        => true,
			'show_in_rest'  => true,
			'auth_callback' => function () {
				return current_user_can( 'manage_options' );
			},
		) );
	}
} );

/* A trashed sign-up that is later deleted for good takes its CV with it. */
add_action( 'before_delete_post', function ( $id ) {
	if ( 'msh_clinician' !== get_post_type( $id ) ) {
		return;
	}
	$f = (string) get_post_meta( $id, 'msh_cp_cv_file', true );
	if ( $f && preg_match( '/^[a-f0-9]{32}\.(pdf|docx?)$/', $f ) ) {
		@unlink( msh_cp_cv_dir() . '/' . $f );
	}
} );

add_action( 'rest_api_init', function () {
	/* Nursing Register profiles, for administrators only, so the intake
	   script can bring register nurses into Lou's clinician database. */
	register_rest_field( 'user', 'msh_cp_nurse_register', array(
		'get_callback' => function ( $u ) {
			if ( ! current_user_can( 'manage_options' ) ) {
				return null;
			}
			$p = get_user_meta( $u['id'], 'msh_nurse_register', true );
			return is_array( $p ) && $p ? array( 'email' => get_userdata( $u['id'] )->user_email, 'profile' => $p ) : null;
		},
		'schema'       => null,
	) );

	register_rest_route( 'msh-cp/v1', '/signup', array(
		'methods'             => 'POST',
		'permission_callback' => '__return_true',
		'callback'            => function ( WP_REST_Request $req ) {
			$is_admin = current_user_can( 'manage_options' );
			if ( ! msh_cp_live() && ! $is_admin ) {
				return new WP_Error( 'msh_cp_closed', 'Sign-ups open soon.', array( 'status' => 403 ) );
			}
			$p = $req->get_body_params();
			if ( ! empty( $p['website'] ) ) { /* honeypot */
				return array( 'ok' => true, 'ref' => '', 'booking' => MSH_CP_BOOKING_URL );
			}
			$ip_key = 'msh_cp_rl_' . md5( isset( $_SERVER['REMOTE_ADDR'] ) ? $_SERVER['REMOTE_ADDR'] : '' );
			$hits   = (int) get_transient( $ip_key );
			if ( $hits >= 5 && ! $is_admin ) {
				return new WP_Error( 'msh_cp_slow', 'Too many sign-ups from here. Please email Lou.', array( 'status' => 429 ) );
			}
			set_transient( $ip_key, $hits + 1, HOUR_IN_SECONDS );

			$c = msh_cp_clean( $p, gmdate( 'Y-m-d\TH:i:s\Z' ), MSH_CP_AGREEMENT_VERSION, MSH_CP_PRIVACY_VERSION );
			$files = $req->get_file_params();
			$cv    = isset( $files['cv'] ) && is_array( $files['cv'] ) && UPLOAD_ERR_OK === $files['cv']['error'] ? $files['cv'] : null;
			$ext   = '';
			if ( $cv ) {
				$ext = strtolower( pathinfo( $cv['name'], PATHINFO_EXTENSION ) );
				$ok  = in_array( $ext, array( 'pdf', 'doc', 'docx' ), true ) && $cv['size'] > 0 && $cv['size'] <= 5 * MB_IN_BYTES;
				$head = $ok ? file_get_contents( $cv['tmp_name'], false, null, 0, 8 ) : '';
				$magic = ( 'pdf' === $ext && 0 === strpos( $head, '%PDF' ) ) || ( 'docx' === $ext && 0 === strpos( $head, "PK\x03\x04" ) ) || ( 'doc' === $ext && 0 === strpos( $head, "\xD0\xCF\x11\xE0" ) );
				if ( ! $ok || ! $magic ) {
					$c['errors'][] = 'cv';
				}
			}
			if ( $c['errors'] ) {
				return new WP_Error( 'msh_cp_invalid', 'Please check the highlighted answers.', array( 'status' => 400, 'fields' => $c['errors'] ) );
			}
			$r    = $c['record'];
			$ref  = msh_cp_ref( wp_generate_password( 12, false ) );
			$file = '';
			if ( $cv ) {
				$file = bin2hex( random_bytes( 16 ) ) . '.' . $ext;
				if ( ! move_uploaded_file( $cv['tmp_name'], msh_cp_cv_dir() . '/' . $file ) ) {
					$file = '';
				}
			}
			$test = 0 === stripos( $r['first_name'] . ' ' . $r['last_name'], 'TEST' );
			$id   = wp_insert_post( array(
				'post_type'   => 'msh_clinician',
				'post_status' => 'private',
				'post_title'  => $ref . ' ' . $r['first_name'] . ' ' . $r['last_name'] . ( $test ? ' (TEST)' : '' ),
			), true );
			if ( is_wp_error( $id ) ) {
				return new WP_Error( 'msh_cp_save', 'Could not save. Please email Lou.', array( 'status' => 500 ) );
			}
			$cv_url = msh_cp_cv_url( $ref, $file );
			update_post_meta( $id, 'msh_cp_json', wp_slash( wp_json_encode( $r ) ) );
			update_post_meta( $id, 'msh_cp_ref', $ref );
			update_post_meta( $id, 'msh_cp_cv_file', $file );
			update_post_meta( $id, 'msh_cp_cv_url', $cv_url );

			/* Sent as Lou's elevateandthrive.uk address (the domain's SPF covers
			   WordPress.com's servers), never the site's wordpress@ default. */
			$from = array( 'Content-Type: text/html; charset=UTF-8', 'From: Louise Hoult, Elevate & Thrive <' . MSH_CP_LOU . '>', 'Reply-To: Louise Hoult <' . MSH_CP_LOU . '>' );
			$w = msh_cp_welcome_email( $r, $ref, MSH_CP_BOOKING_URL );
			wp_mail( $r['email'], $w['subject'], $w['html'], $from );
			$l = msh_cp_lou_email( $r, $ref, $cv_url );
			wp_mail( MSH_CP_LOU, $l['subject'], $l['html'], array( 'Content-Type: text/html; charset=UTF-8', 'From: Clinician sign-ups <' . MSH_CP_LOU . '>', 'Reply-To: ' . $r['email'] ) );

			return array( 'ok' => true, 'ref' => $ref, 'booking' => MSH_CP_BOOKING_URL );
		},
	) );

	register_rest_route( 'msh-cp/v1', '/cv', array(
		'methods'             => 'GET',
		'permission_callback' => '__return_true',
		'callback'            => function ( WP_REST_Request $req ) {
			$ref = (string) $req->get_param( 'ref' );
			$t   = (string) $req->get_param( 't' );
			$q   = get_posts( array( 'post_type' => 'msh_clinician', 'post_status' => 'any', 'meta_key' => 'msh_cp_ref', 'meta_value' => $ref, 'numberposts' => 1, 'fields' => 'ids' ) );
			$f   = $q ? (string) get_post_meta( $q[0], 'msh_cp_cv_file', true ) : '';
			if ( ! $f || ! hash_equals( msh_cp_cv_token( $ref, $f ), $t ) || ! preg_match( '/^[a-f0-9]{32}\.(pdf|docx?)$/', $f, $m ) ) {
				return new WP_Error( 'msh_cp_cv', 'Not found', array( 'status' => 404 ) );
			}
			$types = array( 'pdf' => 'application/pdf', 'doc' => 'application/msword', 'docx' => 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' );
			nocache_headers();
			header( 'Content-Type: ' . $types[ $m[1] ] );
			header( 'Content-Disposition: attachment; filename="' . $ref . '-CV.' . $m[1] . '"' );
			header( 'X-Robots-Tag: noindex' );
			readfile( msh_cp_cv_dir() . '/' . $f );
			exit;
		},
	) );
} );

add_shortcode( 'msh_clinician_signup', function () {
	$o     = msh_cp_options();
	$live  = msh_cp_live();
	$admin = current_user_can( 'manage_options' );
	if ( ! $live && ! $admin ) {
		return '<div class="mshcp"><div class="mshcp-card"><h2>Sign-ups open soon</h2><p>The programme opens shortly. To hear when, email <a href="mailto:' . MSH_CP_LOU . '">' . MSH_CP_LOU . '</a>.</p></div></div>';
	}
	$h = function ( $v ) {
		return esc_html( $v );
	};
	$sel = function ( $name, $list, $label, $req = true, $help = '' ) use ( $o, $h ) {
		$x = '<label class="mshcp-f" data-f="' . $name . '"><span>' . $label . ( $req ? ' *' : '' ) . '</span>' . ( $help ? '<small>' . $help . '</small>' : '' ) . '<select name="' . $name . '"' . ( $req ? ' required' : '' ) . '><option value="">Choose</option>';
		foreach ( $o[ $list ] as $k => $v ) {
			$x .= '<option value="' . esc_attr( $k ) . '">' . $h( $v ) . '</option>';
		}
		return $x . '</select><em>Please answer this</em></label>';
	};
	$ticks = function ( $name, $list, $label, $help = '' ) use ( $o, $h ) {
		$x = '<fieldset class="mshcp-f mshcp-ticks" data-f="' . $name . '"><legend>' . $label . ' *</legend>' . ( $help ? '<small>' . $help . '</small>' : '' ) . '<div>';
		foreach ( $o[ $list ] as $k => $v ) {
			$x .= '<label><input type="checkbox" name="' . $name . '[]" value="' . esc_attr( $k ) . '"> ' . $h( $v ) . '</label>';
		}
		return $x . '</div><em>Tick at least one</em></fieldset>';
	};
	$txt = function ( $name, $label, $req = true, $type = 'text', $help = '', $extra = '' ) {
		return '<label class="mshcp-f" data-f="' . $name . '"><span>' . $label . ( $req ? ' *' : '' ) . '</span>' . ( $help ? '<small>' . $help . '</small>' : '' ) . '<input type="' . $type . '" name="' . $name . '"' . ( $req ? ' required' : '' ) . $extra . '><em>Please check this</em></label>';
	};
	$area = function ( $name, $label, $help = '' ) {
		return '<label class="mshcp-f" data-f="' . $name . '"><span>' . $label . '</span>' . ( $help ? '<small>' . $help . '</small>' : '' ) . '<textarea name="' . $name . '" rows="4"></textarea></label>';
	};

	$form  = '<form class="mshcp-form" novalidate enctype="multipart/form-data">';
	$form .= ( $live ? '' : '<p class="mshcp-warn">Admin preview: the wording is not signed off yet, so only administrators can submit. Name a test entry starting TEST.</p>' );
	$form .= '<h3>About you</h3><div class="mshcp-grid">' . $txt( 'first_name', 'First name' ) . $txt( 'last_name', 'Last name' ) . $txt( 'email', 'Email', true, 'email' ) . $txt( 'phone', 'Mobile number', true, 'tel' ) . $txt( 'linkedin', 'LinkedIn profile link', false, 'url' ) . '</div>';
	$form .= '<h3>Where you are</h3><div class="mshcp-grid">' . $sel( 'region', 'regions', 'Home region' ) . $txt( 'postcode', 'Postcode district', true, 'text', 'The first half only, for example LN6', ' maxlength="4"' )
		. $txt( 'icb', 'Integrated Care Board (ICB) area', false, 'text', 'If you know it, for example Lincolnshire' ) . $sel( 'travel', 'travel', 'How far would you travel for work?' ) . $sel( 'relocate', 'relocate', 'Would you relocate?', false ) . $sel( 'licence', 'licence', 'Driving licence' ) . '</div>';
	$form .= '<h3>Your registration</h3><div class="mshcp-grid">' . $sel( 'profession', 'profession', 'Profession' )
		. $txt( 'pin', 'Registration number (PIN)', false, 'text', 'Nursing and Midwifery Council (NMC) PIN or Health and Care Professions Council (HCPC) number. Used only to check your registration; never shared.' )
		. $sel( 'regstatus', 'regstatus', 'Registration status' ) . $txt( 'years', 'Years since you qualified', true, 'number', '', ' min="0" max="60"' ) . '</div>';
	$form .= '<h3>Your current work</h3><div class="mshcp-grid">' . $txt( 'current_role', 'Current job title' ) . $sel( 'employer', 'employer', 'Who employs you?' ) . $txt( 'employer_name', 'Employer name', false )
		. $sel( 'band', 'band', 'NHS Agenda for Change band', false ) . '</div>';
	$form .= $ticks( 'specialities', 'specialities', 'Your specialities', 'Tick every area you have worked in' );
	$form .= $area( 'procedures', 'Procedures and devices you use or have trained others on', 'For example negative pressure wound therapy, peripherally inserted central catheter (PICC) insertion, insulin pumps, cell salvage' );
	$form .= $area( 'industry', 'Any industry experience', 'Product evaluations, link nurse roles, company training, secondments. Leave blank if none' );
	$form .= '<h3>What you are looking for</h3>' . $ticks( 'roles', 'roles', 'Roles that interest you' );
	$form .= '<div class="mshcp-grid">' . $txt( 'salary', 'Salary you would be looking for', false, 'text', 'A figure or a range' ) . $sel( 'notice', 'notice', 'Notice period', false ) . $sel( 'availability', 'availability', 'When could you start?' ) . '</div>';
	$form .= '<label class="mshcp-f" data-f="cv"><span>Your CV</span><small>PDF or Word, up to 5 MB. You can email it later instead.</small><input type="file" name="cv" accept=".pdf,.doc,.docx"><em>PDF or Word only, up to 5 MB</em></label>';
	$form .= $area( 'notes', 'Anything else I should know' );
	$form .= '<input type="text" name="website" tabindex="-1" autocomplete="off" class="mshcp-hp" aria-hidden="true">';
	$form .= '<input type="hidden" name="source" value=""><input type="hidden" name="agreement_version" value="' . esc_attr( MSH_CP_AGREEMENT_VERSION ) . '"><input type="hidden" name="privacy_version" value="' . esc_attr( MSH_CP_PRIVACY_VERSION ) . '">';
	$form .= '<h3>The agreement</h3><div class="mshcp-agreement" tabindex="0"><p class="mshcp-ver">Version ' . esc_html( MSH_CP_AGREEMENT_VERSION ) . ' (draft, pending solicitor review)</p>' . msh_cp_agreement_html() . '</div>';
	foreach ( msh_cp_boxes() as $k => $b ) {
		$req   = 'box1' === $k;
		$form .= '<label class="mshcp-tick" data-f="' . $k . '"><input type="checkbox" name="' . $k . '" value="1"' . ( $req ? ' required' : '' ) . '> <strong>' . substr( $k, 3 ) . '. ' . esc_html( $b[0] ) . '</strong> ' . esc_html( $b[1] ) . ( $req ? '<em>Please tick box 1 to continue</em>' : '' ) . '</label>';
	}
	$form .= '<p class="mshcp-tick">Read our ' . msh_cp_link( MSH_CP_PRIVACY_URL, 'privacy notice' ) . ' to see how we use your details. <span class="mshcp-ver">Privacy notice version ' . esc_html( MSH_CP_PRIVACY_VERSION ) . ' (draft, pending solicitor review)</span></p>';
	$form .= '<p class="mshcp-err" role="alert" hidden></p><button type="submit" class="mshcp-btn">Sign up and book my call</button></form>';

	$done = '<div class="mshcp-done" hidden><h2>You are signed up</h2><p>Your reference is <strong class="mshcp-ref"></strong> <button type="button" class="mshcp-copy">Copy</button></p>'
		. '<p>Now book your 60-minute Microsoft Teams call with me. <strong>Paste your reference into the booking form</strong> so I have your details and CV in front of me. A welcome email with your next steps, what you chose and a copy of the agreement is on its way.</p>'
		. '<p><a class="mshcp-btn mshcp-book" href="#" target="_top">Book my call</a></p><iframe class="mshcp-frame" title="Book your call" hidden></iframe></div>';

	$css = '<style>.mshcp{max-width:1080px;margin:0 auto;padding:0 40px;font-family:inherit;color:#1D2733}.mshcp .mshcp-card,.mshcp .mshcp-form,.mshcp .mshcp-done{background:#FFFFFF;color:#1D2733;border-top:4px solid #A8842C;padding:36px 40px;margin:0 0 40px}'
		. '.mshcp h2{color:#0B1C33;margin:0 0 12px}.mshcp h3{color:#0B1C33;font-size:22px;margin:30px 0 12px;padding-top:18px;border-top:1px solid #DBE3EE}.mshcp-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px 22px}'
		. '.mshcp-f{display:block;margin:0 0 14px}.mshcp-f>span,.mshcp-f legend{display:block;font-weight:700;color:#0B1C33;margin-bottom:4px}.mshcp-f small{display:block;color:#1D2733;font-size:14px;margin-bottom:6px}'
		. '.mshcp input[type=text],.mshcp input[type=email],.mshcp input[type=tel],.mshcp input[type=url],.mshcp input[type=number],.mshcp select,.mshcp textarea{width:100%;box-sizing:border-box;font-size:16px;color:#1D2733;background:#FFFFFF;border:1px solid #8794A6;padding:11px 12px}'
		. '.mshcp-ticks{border:0;padding:0;margin:0 0 14px}.mshcp-ticks div{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px 16px}.mshcp-ticks label{font-weight:400;color:#1D2733}'
		. '.mshcp em{display:none;color:#8A1C1C;font-style:normal;font-size:14px;font-weight:700}.mshcp .bad em{display:block}.mshcp .bad input,.mshcp .bad select{border-color:#8A1C1C}'
		. '.mshcp-agreement{max-height:260px;overflow:auto;background:#EDE7DC;color:#1D2733;padding:16px 18px;font-size:15px;margin-bottom:14px}.mshcp-ver{font-weight:700;color:#0B1C33}'
		. '.mshcp-tick{display:block;margin:0 0 14px;color:#1D2733}.mshcp-tick a{color:#14304F}.mshcp-hp{position:absolute;left:-9999px}.mshcp-warn{background:#0B1C33;color:#FFFFFF;padding:12px 16px}.mshcp-err{color:#8A1C1C;font-weight:700}'
		. '.mshcp-btn{display:inline-block;background:#0B1C33;color:#FFFFFF!important;border:0;padding:16px 30px;font-weight:700;font-size:15px;letter-spacing:.06em;text-transform:uppercase;cursor:pointer;text-decoration:none}.mshcp-btn:hover{background:#14304F}'
		. '.mshcp-copy{background:#FFFFFF;color:#0B1C33;border:1px solid #0B1C33;padding:4px 10px;cursor:pointer}.mshcp-frame{width:100%;height:1100px;border:1px solid #DBE3EE;margin-top:20px}'
		. '@media(max-width:700px){.mshcp{padding:0 20px}.mshcp .mshcp-form,.mshcp .mshcp-done,.mshcp .mshcp-card{padding:24px 18px}.mshcp-grid,.mshcp-ticks div{grid-template-columns:1fr}}</style>';

	$js = '<script>(function(){var w=document.currentScript.parentNode,f=w.querySelector(".mshcp-form");if(!f)return;'
		. 'var q=new URLSearchParams(location.search);f.source.value=(q.get("src")||q.get("utm_campaign")||"").slice(0,60);'
		. 'f.addEventListener("submit",function(e){e.preventDefault();w.querySelectorAll(".bad").forEach(function(x){x.classList.remove("bad")});var er=f.querySelector(".mshcp-err");er.hidden=true;'
		. 'var b=f.querySelector("button[type=submit]");b.disabled=true;b.textContent="Sending";'
		. 'fetch(' . wp_json_encode( esc_url_raw( rest_url( 'msh-cp/v1/signup' ) ) ) . ',{method:"POST",body:new FormData(f),credentials:"same-origin"' . ( is_user_logged_in() ? ',headers:{"X-WP-Nonce":' . wp_json_encode( wp_create_nonce( 'wp_rest' ) ) . '}' : '' ) . '})'
		. '.then(function(r){return r.json().then(function(j){return{ok:r.ok,j:j}})}).then(function(x){b.disabled=false;b.textContent="Sign up and book my call";'
		. 'if(!x.ok){var fs=(x.j.data&&x.j.data.fields)||[];fs.forEach(function(n){var el=f.querySelector("[data-f="+n+"]");if(el)el.classList.add("bad")});er.textContent=x.j.message||"Something went wrong. Please email Lou.";er.hidden=false;var first=f.querySelector(".bad");(first||er).scrollIntoView({behavior:"smooth",block:"center"});return}'
		. 'var d=w.querySelector(".mshcp-done");d.querySelector(".mshcp-ref").textContent=x.j.ref;f.hidden=true;d.hidden=false;var bk=d.querySelector(".mshcp-book");'
		. 'if(x.j.booking){bk.href=x.j.booking;var fr=d.querySelector(".mshcp-frame");fr.src=x.j.booking;fr.hidden=false}else{bk.hidden=true}'
		. 'd.querySelector(".mshcp-copy").onclick=function(){navigator.clipboard&&navigator.clipboard.writeText(x.j.ref)};d.scrollIntoView({behavior:"smooth"})})'
		. '.catch(function(){b.disabled=false;b.textContent="Sign up and book my call";er.textContent="Could not send. Please check your connection, or email Lou.";er.hidden=false})})})();</script>';

	return '<div class="mshcp">' . $css . $form . $done . $js . '</div>';
} );
