-- Sources d'énergie des véhicules (code de la carte grise).
select code_energie, libelle as libelle_energie, famille as famille_energie
from {{ ref('energies') }}
