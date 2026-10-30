{% macro safe_divide(numerator, denominator) -%}
    case when {{ denominator }} = 0 then null
         else cast({{ numerator }} as double) / {{ denominator }} end
{%- endmacro %}
