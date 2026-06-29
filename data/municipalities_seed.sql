-- data/municipalities_seed.sql
-- Three test municipalities for local / staging setup.
-- Run after 003_water_bills.sql.

insert into municipalities (name, preferred_method, email, fax, portal_url, notes) values
(
    'City of Minneapolis',
    'email',
    'waterbills@minneapolismn.gov',
    null,
    null,
    'Turnaround 5–7 business days. Request must include parcel ID.'
),
(
    'City of St. Paul',
    'portal',
    null,
    null,
    'https://stpaul.gov/departments/public-works/water-billing',
    'Use the online portal. Account number required; found on tax records.'
),
(
    'City of Edina',
    'fax',
    null,
    '952-826-0389',
    null,
    'Fax to Utility Billing. Include closing date and property address on cover sheet.'
);
