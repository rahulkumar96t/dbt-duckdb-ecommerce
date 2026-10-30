{# Shared cleaning rules, used by staging and by the snapshot-based customer history. #}

{% macro clean_email(column) -%}
    lower(trim({{ column }}))
{%- endmacro %}

{% macro clean_country(column) -%}
    upper(trim({{ column }}))
{%- endmacro %}

{% macro cents_to_amount(column) -%}
    cast({{ column }} as decimal(12, 2)) / 100
{%- endmacro %}

{% macro money(column) -%}
    cast(round({{ column }}, 2) as decimal(12, 2))
{%- endmacro %}
