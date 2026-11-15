-- Un véhicule immatriculé par ligne, nettoyé et typé.
with source as (
    select * from {{ source('bronze', 'vehicules_immatricules') }}
)

select
    numero_immat,
    cast(date_emission as date) as date_emission_certificat,
    date_mise_a_jour,
    -- 1901-01-01 sert de date inconnue dans la source
    if(date_1ere_mise_en_circulation >= date '1902-01-01', date_1ere_mise_en_circulation) as date_premiere_circulation,
    if(date_1ere_mise_en_circulation_nc >= date '1902-01-01', date_1ere_mise_en_circulation_nc) as date_premiere_circulation_nc,
    upper(trim(marque)) as marque,
    nullif(trim(appellation_commerciale), '') as modele,
    genre_code as code_genre,
    genre as libelle_genre,
    nullif(categorie_ce, '') as categorie_ce,
    nullif(carrosserie, '') as carrosserie,
    energie as code_energie,
    nullif(puissance_administrative, 0) as puissance_administrative_cv,
    puissance_kw,
    cylindree_cm3,
    poids_vide as poids_vide_kg,
    ptac as ptac_kg,
    nb_place_assis as nb_places_assises,
    nullif(couleur, '') as couleur,
    nullif(commune_proprietaire, '') as commune,
    case proprietaire_province
        when 'province Sud' then 'Sud'
        when 'province Nord' then 'Nord'
        when 'province des îles Loyauté' then 'Îles Loyauté'
        when 'province Nord;province Sud' then 'Nord et Sud'
    end as province,
    -- Type de société vide : propriétaire particulier
    coalesce(nullif(type_societe_proprietaire, ''), 'Particulier') as type_proprietaire,
    nullif(type_societe_locataire, '') is not null or nullif(commune_locataire, '') is not null as en_location,
    code_utilisation,
    date_limite_validite_visite_technique as date_limite_controle_technique,
    date_retrait,
    date_destruction,
    date_exportation,
    date_heure_vol,
    date_heure_retrouve
from source
