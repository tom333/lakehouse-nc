-- Un transfert de certificat d'immatriculation de véhicule d'occasion par ligne.
with source as (
    select * from {{ source('bronze', 'transferts_vehicules_occasion') }}
),

energies as (
    select code_energie, libelle_transferts from {{ ref('energies') }}
)

select
    s.timestamp_transaction as horodatage_transaction,
    s.date_transaction,
    s.numero_immat,
    s.teleservice = 'true' as par_teleservice,
    coalesce(nullif(s.type_societe_proprietaire_1, ''), 'Particulier') as type_nouveau_proprietaire,
    nullif(s.type_societe_locataire_1, '') is not null as en_location,
    upper(trim(s.marque)) as marque,
    nullif(trim(s.appellation_commerciale), '') as modele,
    s.genre as code_genre,
    e.code_energie,
    nullif(s.puissance_administrative, 0) as puissance_administrative_cv,
    nullif(s.carrosserie, '') as carrosserie,
    if(s.date_1ere_mise_en_circulation >= date '1902-01-01', s.date_1ere_mise_en_circulation) as date_premiere_circulation,
    -- La source suffixe l'article : « MONT-DORE (LE) » pour « MONT-DORE »
    nullif(regexp_replace(s.commune, '\s*\((LE|LA|LES)\)$', ''), '') as commune,
    nullif(s.centre_controle_technique, '') as centre_controle_technique,
    s.date_controle_technique
from source as s
left join energies as e on s.energie = e.libelle_transferts
