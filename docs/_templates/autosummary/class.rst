{%- set is_root = basename == project.lower() -%}
{%- set module_footer = ["base", "exception"] -%}
{%- set module_caps = ["api", "m3u", "xautopf", "flac", "mp3", "m4a", "wma"] -%}

{%- macro formatname(name) -%}
    {%- if name.endswith(".exception") -%}
        {%- set name = "exceptions"-%}
    {%- else -%}
        {%- set name = name.replace(project + ".", "").replace("_", " ").split(".") | last -%}
    {%- endif -%}

    {%- if name | lower in module_caps -%}
        {{- name | upper -}}
    {%- else -%}
        {{- name | title -}}
    {%- endif -%}
{%- endmacro -%}

{{ formatname(fullname) | escape | underline}}

.. currentmodule:: {{ module }}

.. autoclass:: {{ objname }}

   {%- block methods -%}
   .. automethod:: __init__

   {%- if methods -%}
   .. rubric:: {{ _('Methods') }}

   .. autosummary::
   {%- for item in methods -%}
      ~{{ name }}.{{ item }}
   {%- endfor %}
   {%- endif -%}
   {%- endblock -%}

   {%- block attributes -%}
   {%- if attributes -%}
   .. rubric:: {{ _('Attributes') }}

   .. autosummary::
   {%- for item in attributes -%}
      ~{{ name }}.{{ item }}
   {%- endfor %}
   {%- endif -%}
   {%- endblock -%}
