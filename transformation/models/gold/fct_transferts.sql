-- Ventes de véhicules d'occasion : un transfert de certificat par ligne.
select
    horodatage_transaction,
    date_transaction,
    numero_immat,
    commune,
    code_energie,
    code_genre,
    marque,
    modele,
    carrosserie,
    puissance_administrative_cv,
    date_premiere_circulation,
    type_nouveau_proprietaire,
    en_location,
    par_teleservice
from {{ ref('silver_transferts') }}
