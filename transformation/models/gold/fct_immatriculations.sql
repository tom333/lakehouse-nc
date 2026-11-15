-- Parc immatriculé : un véhicule par ligne, daté par sa première mise en
-- circulation en Nouvelle-Calédonie.
select
    numero_immat,
    date_premiere_circulation_nc,
    date_premiere_circulation,
    commune,
    code_energie,
    code_genre,
    marque,
    modele,
    carrosserie,
    puissance_administrative_cv,
    puissance_kw,
    cylindree_cm3,
    nb_places_assises,
    type_proprietaire,
    en_location,
    case
        when date_destruction is not null then 'Détruit'
        when date_exportation is not null then 'Exporté'
        when date_retrait is not null then 'Retiré'
        when date_heure_vol is not null and date_heure_retrouve is null then 'Volé'
        else 'En circulation'
    end as statut
from {{ ref('silver_vehicules') }}
