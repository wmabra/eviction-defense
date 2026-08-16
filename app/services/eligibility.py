"""Eligibility rules engine for pre-screening — supports 20 states."""
from app.schema.intake import PreScreen


# Supported states
SUPPORTED_STATES = {
    "AR", "CO", "CT", "GA", "IL", "KY", "LA",
    "IL", "IN", "KY", "LA",
    "MI", "MN", "MO", "NM", "OH", "OK", "OR", "RI", "SC", "TN", "TX", "VA",
}

# Supported counties by state (from rental assistance resource databases)
SUPPORTED_COUNTIES = {
    "AR": {'Benton', 'Columbia', 'Craighead', 'Crawford', 'Faulkner', 'Garland', 'Greene', 'Hempstead', 'Independence', 'Jefferson', 'Lonoke', 'Miller', 'Mississippi', 'Ouachita', 'Pulaski', 'Saline', 'Sebastian', 'Union', 'Washington', 'White'},
    "CO": {'Adams', 'Arapahoe', 'Boulder', 'Broomfield', 'Denver', 'Douglas', 'Eagle', 'El Paso', 'Fremont', 'Garfield', 'Jefferson', 'La Plata', 'Larimer', 'Mesa', 'Montrose', 'Morgan', 'Pueblo', 'Routt', 'Summit', 'Weld'},
    "CT": {'Fairfield', 'Hartford', 'Litchfield', 'Middlesex', 'New Haven', 'New London', 'Tolland', 'Windham'},
    "GA": {'Bibb', 'Chatham', 'Cherokee', 'Clarke', 'Clayton', 'Cobb', 'Columbia', 'Coweta', 'DeKalb', 'Douglas', 'Fayette', 'Forsyth', 'Fulton', 'Gwinnett', 'Hall', 'Henry', 'Houston', 'Muscogee', 'Paulding', 'Richmond'},
    "IN": {'Marion', 'Lake', 'Allen', 'Hamilton', 'St. Joseph', 'Elkhart', 'Tippecanoe', 'Vanderburgh', 'Porter', 'Hendricks', 'Johnson', 'Monroe', 'Madison', 'Delaware', 'Clark', 'Vigo', 'Howard', 'LaPorte', 'Bartholomew', 'Boone'},
    "IL": {'Champaign', 'Cook', 'DuPage', 'Kane', 'Kankakee', 'Kendall', 'LaSalle', 'Lake', 'Macon', 'Madison', 'McHenry', 'McLean', 'Peoria', 'Rock Island', 'Sangamon', 'St. Clair', 'Tazewell', 'Vermilion', 'Will', 'Winnebago'},
    "KY": {'Jefferson', 'Fayette', 'Kenton', 'Boone', 'Warren', 'Hardin', 'Daviess', 'Campbell', 'Madison', 'Bullitt', 'Christian', 'Oldham', 'Pulaski', 'Laurel', 'Scott', 'Jessamine', 'Franklin', 'McCracken', 'Hopkins', 'Shelby'},
    "LA": {'Ascension', 'Bossier', 'Caddo', 'Calcasieu', 'East Baton Rouge', 'Iberia', 'Jefferson', 'Lafayette', 'Lafourche', 'Livingston', 'Orleans', 'Ouachita', 'Rapides', 'St. Charles', 'St. John the Baptist', 'St. Landry', 'St. Tammany', 'Tangipahoa', 'Terrebonne', 'Vernon'},
    "MI": {'Bay', 'Berrien', 'Calhoun', 'Eaton', 'Genesee', 'Ingham', 'Isabella', 'Jackson', 'Kalamazoo', 'Kent', 'Livingston', 'Macomb', 'Monroe', 'Muskegon', 'Oakland', 'Ottawa', 'Saginaw', 'St. Clair', 'Washtenaw', 'Wayne'},
    "MN": {'Anoka', 'Beltrami', 'Blue Earth', 'Carver', 'Clay', 'Crow Wing', 'Dakota', 'Hennepin', 'Kandiyohi', 'Olmsted', 'Otter Tail', 'Ramsey', 'Rice', 'Scott', 'Sherburne', 'St. Louis', 'Stearns', 'Washington', 'Winona', 'Wright'},
    "MO": {'St. Louis County', 'Jackson', 'St. Charles', 'Greene', 'St. Louis City', 'Clay', 'Jefferson', 'Boone', 'Jasper', 'Cass', 'Platte', 'Franklin', 'Christian', 'Buchanan', 'Cape Girardeau', 'Cole', 'St. Francois', 'Lincoln', 'Taney', 'Howell'},
    "OK": {'Oklahoma', 'Tulsa', 'Cleveland', 'Canadian', 'Comanche', 'Rogers', 'Payne', 'Wagoner', 'Pottawatomie', 'Creek', 'Garfield', 'Muskogee', 'Grady', 'Le Flore', 'Washington', 'Bryan', 'Logan', 'Carter', 'Okmulgee', 'Osage'},
    "OH": {'Cuyahoga', 'Franklin', 'Hamilton', 'Summit', 'Montgomery', 'Lucas', 'Stark', 'Butler', 'Lorain', 'Lake', 'Mahoning', 'Warren', 'Clermont', 'Trumbull', 'Delaware', 'Licking', 'Greene', 'Portage', 'Fairfield', 'Medina'},
    "NM": {'Bernalillo', 'Chaves', 'Curry', 'Doña Ana', 'Eddy', 'Grant', 'Lea', 'Los Alamos', 'Luna', 'McKinley', 'Otero', 'Rio Arriba', 'Roosevelt', 'San Juan', 'San Miguel', 'Sandoval', 'Santa Fe', 'Taos', 'Torrance', 'Valencia'},
    "OR": {'Baker', 'Benton', 'Clackamas', 'Coos', 'Crook', 'Deschutes', 'Douglas', 'Jackson', 'Josephine', 'Klamath', 'Lane', 'Linn', 'Malheur', 'Marion', 'Multnomah', 'Polk', 'Umatilla', 'Union', 'Washington', 'Yamhill'},
    "RI": {'Bristol', 'Kent', 'Newport', 'Providence', 'Washington'},
    "SC": {'Aiken', 'Anderson', 'Beaufort', 'Berkeley', 'Charleston', 'Dorchester', 'Florence', 'Georgetown', 'Greenville', 'Greenwood', 'Horry', 'Kershaw', 'Lexington', 'Oconee', 'Orangeburg', 'Pickens', 'Richland', 'Spartanburg', 'Sumter', 'York'},
    "TN": {'Anderson', 'Blount', 'Bradley', 'Cumberland', 'Davidson', 'Hamilton', 'Knox', 'Madison', 'Maury', 'Montgomery', 'Putnam', 'Robertson', 'Rutherford', 'Sevier', 'Shelby', 'Sullivan', 'Sumner', 'Washington', 'Williamson', 'Wilson'},
    "TX": {'Bell', 'Bexar', 'Brazoria', 'Cameron', 'Collin', 'Dallas', 'Denton', 'El Paso', 'Fort Bend', 'Galveston', 'Harris', 'Hidalgo', 'Lubbock', 'McLennan', 'Montgomery', 'Nueces', 'Tarrant', 'Travis', 'Webb', 'Williamson'},
    "VA": {'Albemarle', 'Alexandria', 'Arlington', 'Chesapeake', 'Chesterfield', 'Fairfax', 'Hampton', 'Henrico', 'Loudoun', 'Lynchburg', 'Montgomery', 'Newport News', 'Norfolk', 'Prince William', 'Richmond City', 'Roanoke City', 'Rockingham', 'Spotsylvania', 'Stafford', 'Virginia Beach'},
}


def check_eligibility(pre_screen: PreScreen) -> dict:
    """Run pre-screen checks and return eligibility result."""
    reasons = []
    state = pre_screen.state.upper()

    # State check
    if state not in SUPPORTED_STATES:
        supported = ", ".join(sorted(SUPPORTED_STATES))
        return {
            "eligible": False,
            "reason": "state_not_supported",
            "message": f"We currently support {len(SUPPORTED_STATES)} states: {supported}. Your state is coming soon."
        }

    # County check
    state_counties = SUPPORTED_COUNTIES.get(state, set())
    if state_counties and pre_screen.county:
        if pre_screen.county not in state_counties:
            return {
                "eligible": False,
                "reason": "county_not_supported",
                "message": f"We're building county-by-county in {state}. {pre_screen.county} isn't live yet."
            }

    # Must be the tenant
    if not pre_screen.is_tenant:
        reasons.append("This service is for tenants named in the eviction.")

    # Must be residential
    if not pre_screen.is_residential:
        reasons.append("We can only handle residential evictions, not commercial.")

    # Must have court papers
    if not pre_screen.received_court_papers:
        reasons.append("You need to have been served with court papers before we can prepare your answer packet.")

    # Too late - writ/sheriff stage
    if pre_screen.has_writ_or_sheriff:
        reasons.append("A writ of possession has been issued or the sheriff is involved. This is past the point where our self-help packet can help. Please contact a lawyer or legal aid immediately.")

    # Section 8 / Public housing
    if pre_screen.is_section_8:
        reasons.append("Section 8/public housing evictions have special federal rules. This case requires an attorney or legal aid.")

    # Active military
    if pre_screen.is_active_military:
        reasons.append("Active military personnel have special protections under the SCRA. Please contact a military legal assistance office.")

    # Bankruptcy
    if pre_screen.has_bankruptcy:
        reasons.append("Bankruptcy triggers an automatic stay that affects eviction proceedings. Please consult with your bankruptcy attorney.")

    if reasons:
        return {
            "eligible": False,
            "reason": "; ".join(reasons),
            "message": "Based on your answers, your situation may require legal advice. Our self-help paperwork software is not the right fit for this case."
        }

    return {
        "eligible": True,
        "reason": None,
        "message": "You're eligible! Proceed to purchase your self-help packet."
    }
