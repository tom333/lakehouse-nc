-- Les communes de Nouvelle-Calédonie et leur province.
select distinct commune, province
from {{ ref('silver_vehicules') }}
where commune is not null
