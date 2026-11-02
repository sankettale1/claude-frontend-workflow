# Stack: drupal-sdc (Single Directory Components, Drupal 10.1+ / 11)

`<T>` = theme path, `<t>` = theme machine name (from `frontend.config.json`). Modules can ship components too (`modules/custom/<m>/components/`), with the ID `<m>:<name>`.

## Quick rules
- Components live in <T>/components/[<group>/]<name>/: <name>.component.yml + <name>.twig, plus <name>.css/.js (or their sources, e.g. .pcss/.scss/.behavior.js, compiled to them). Copy the grouping folders, name prefix and styling approach of 2 sibling components.
- The component gets ALL data via props (scalars, enums) and slots (render arrays/markup). Never use content.*, node.*, paragraph.* or attach_library inside a component.
- Drupal templates (paragraph--*, node--*, block--*, field--*) are thin adapters: {{ include('<t>:<name>', {…}, with_context = false) }} or {% embed '<t>:<name>' with {…} only %} for slots.
- The component's CSS/JS is attached automatically; dependencies go under libraryOverrides in the component.yml (core/once, core/drupal). Never core/jquery.once.
- JS: Drupal.behaviors + once('<name>', '.<root-class>', context). Edit sources only; never compiled .css/.js when a source exists.
- After changes: <build> (in <build.cwd>), then <cacheClear>, because SDC discovery is cached.

## Where things go

| Piece | Location |
|---|---|
| Definition | `<T>/components/[<group>/]<name>/<name>.component.yml` |
| Template | `<name>.twig` (same folder) |
| Styles | `<name>.css` (auto-attached). If the theme uses a build: the source (`<name>.pcss` / `.scss`) sits next to it and compiles to `<name>.css` |
| Behaviour | `<name>.js` (auto-attached), or the source (`<name>.behavior.js`, `.src.js`, `.ts`) compiled to `<name>.js` |
| Docs / demo | `README.md`, `thumbnail.png`, `<name>.stories.*` (if the project uses Storybook) |
| Adapter | the existing Drupal template that renders the entity, e.g. `<T>/templates/…/paragraph--<bundle>.html.twig` |
| Spec | `<T>/docs/components/<name>.md` |

Before creating anything, look at 2 sibling components and copy their: group folder (`01-atoms`, `02-molecules`, …), name prefix (e.g. `space-`), styling (Tailwind utilities, PostCSS, Sass, plain CSS), JS source naming, and README/stories conventions.

## component.yml

```yaml
'$schema': 'https://git.drupalcode.org/project/drupal/-/raw/HEAD/core/assets/schemas/v1/metadata.schema.json'
name: Pricing Card
status: stable            # experimental | stable | deprecated | obsolete
group: Molecules
description: Card that shows one pricing plan with a call to action.
props:
  type: object
  required: [heading]
  properties:
    heading:
      type: string
      title: Heading
      examples: ['Basic plan']
    variant:
      type: string
      title: Variant
      enum: [default, highlighted]
      default: default
    url:
      type: string
      format: uri-reference
slots:
  body:
    title: Body
    description: Rich text or a list of features.
  cta:
    title: Call to action
libraryOverrides:
  dependencies:
    - core/drupal
    - core/once
```
- `props` must be `type: object` with `properties`; give every prop a `type`, a `title` and `examples` (they power Storybook, Experience Builder and documentation).
- Strings, booleans, enums and URLs are props. Anything that is rendered markup (fields, images, links, nested components) is a **slot**.
- Enums instead of free strings for variants; `required` for what the design can't do without.

## Twig

```twig
{#
/**
 * @file
 * Pricing Card component. Figma: <url>. Spec: docs/components/pricing-card.md
 */
#}
{%
  set classes = [
    'pricing-card',
    variant ? 'pricing-card--' ~ variant,
  ]
%}
<article{{ attributes.addClass(classes) }}>
  <h3 class="pricing-card__title">{{ heading }}</h3>
  {% if body %}
    <div class="pricing-card__body">{% block body %}{{ body }}{% endblock %}</div>
  {% endif %}
  {% if cta %}
    <div class="pricing-card__cta">{% block cta %}{{ cta }}{% endblock %}</div>
  {% endif %}
</article>
```
- `attributes` is always available in a component; add classes to it on the root element.
- Static text: `{{ 'Read more'|t }}`. The heading level can be a prop (`heading_level: {type: integer, enum: [2,3,4]}`) when the component is used in different contexts.
- Nested components: `{{ include('<t>:button', {label: …}, with_context = false) }}`.

## JS

```js
(function (Drupal, once) {
  'use strict';
  Drupal.behaviors.pricingCard = {
    attach(context) {
      once('pricing-card', '.pricing-card', context).forEach((el) => {
        // …
      });
    },
  };
})(Drupal, once);
```
Use only the syntax your build and ESLint allow (check `.eslintrc*`/babel config).

## Adapter template (wire a Drupal entity to the component)

```twig
{# paragraph--pricing-card.html.twig: maps fields to the component's props and slots. #}
{% embed '<t>:pricing-card' with {
  attributes: attributes,
  heading: content.field_title|render|striptags|trim,
  variant: paragraph.field_variant.value ?: 'default',
} only %}
  {% block body %}{{ content.field_body }}{% endblock %}
  {% block cta %}{{ content.field_link }}{% endblock %}
{% endembed %}
```
- Render `content.field_*` in slots (keeps cache metadata). For props that need a plain value, `|render|striptags|trim` or `paragraph.field_x.value`.
- Pass `attributes` (and keep `title_prefix`/`title_suffix` when contextual links matter).

## Tailwind-based SDC themes
Use the theme's Tailwind config tokens (no arbitrary values like `p-[13px]` when a token exists). Express variants as a Twig map (`{% set variants = {default: '…', highlighted: '…'} %}`). Keep utility lists readable (group by layout → spacing → typography → colour → state).

## Existing larger tooling (optional)
If the project has `/figma-to-sdc`, `/figma-component` or `/legacy-figma-component` installed, those can build whole design systems in waves. `/frontend` builds one component at a time with the same rules, then reviews it.
