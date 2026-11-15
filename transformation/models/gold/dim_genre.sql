-- Genres de véhicules (code de la carte grise).
select distinct code_genre, libelle_genre
from {{ ref('silver_vehicules') }}
where code_genre is not null
