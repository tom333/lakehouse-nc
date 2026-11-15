-- Calendrier, un jour par ligne, de 1900 (véhicules de collection) à aujourd'hui.
-- sequence() est limité à 10 000 valeurs : on génère les jours année par année.
with jours as (
    select d as date_jour
    from unnest(sequence(1900, year(current_date))) as a (annee)
    cross join unnest(
        sequence(
            date_trunc('year', date(format('%d-01-01', annee))),
            least(date(format('%d-12-31', annee)), current_date),
            interval '1' day
        )
    ) as t (d)
)

select
    date_jour,
    year(date_jour) as annee,
    quarter(date_jour) as trimestre,
    month(date_jour) as mois,
    element_at(
        array['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet',
              'août', 'septembre', 'octobre', 'novembre', 'décembre'],
        month(date_jour)
    ) as libelle_mois,
    day_of_week(date_jour) as jour_semaine,
    element_at(
        array['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche'],
        day_of_week(date_jour)
    ) as libelle_jour
from jours
