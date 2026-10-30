{% test equal_row_count(model, compare_model) %}
    -- one failing row when the two relations have a different number of rows
    with a as (select count(*) as n from {{ model }}),
         b as (select count(*) as n from {{ compare_model }})
    select a.n as model_rows, b.n as compare_rows
    from a cross join b
    where a.n <> b.n
{% endtest %}
