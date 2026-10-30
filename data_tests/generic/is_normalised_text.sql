{% test is_normalised_text(model, column_name) %}
    -- lower case and no surrounding whitespace
    select *
    from {{ model }}
    where {{ column_name }} <> lower(trim({{ column_name }}))
{% endtest %}
