# Brand

merge-carlo uses two marks, not one. A single drawing cannot both carry the
argument at README size and stay legible at 16 pixels, so each size band gets
the mark built for it.

## The marks

### Merge Fan — `assets/logo.svg`

Two branches converge on a single merge node, and the node throws a fan of
samples to the right: a workflow goes in, a distribution comes out. Sample
opacity thins outward so the spray reads as density rather than decoration.

Use it in the README, the documentation header, and the social preview. Never
below 32 pixels — the fan collapses into noise and the merge stroke loses its
curve.

### Merge Die — `assets/favicon.svg`

A die whose pips form a merge graph rather than a face: two on the left, one on
the right, joined by faint connectors. It reads as a die immediately and as a
merge on the second look.

Use it for the favicon, the GitHub avatar, and anywhere the mark drops below 32
pixels. The connectors drop out under that size by design; three pips in a
rounded square still read as a die.

The two share a vocabulary — one accent node as the merge point, dots as
samples, a single stroke weight scaled to the box — so they read as a family
without either needing the other present.

## Files

| File | Contents |
| --- | --- |
| `assets/logo.svg` | Merge Fan, theme-adaptive. The README and docs mark. |
| `assets/favicon.svg` | Merge Die, theme-adaptive. The browser tab mark. |
| `assets/icon-tile.svg` | Merge Die on a full-bleed ink tile. Source for the avatar. |
| `assets/icon-512.png` | 512×512 render of the tile, for the GitHub avatar. |
| `assets/social-preview.svg` | 1280×640 link card. Source; needs Inter installed. |
| `assets/social-preview.png` | Rendered card, uploaded under Settings → Social preview. |

## Light and dark

`logo.svg` and `favicon.svg` carry their own palette switch. The light palette
sits in presentation attributes and the dark palette overrides it by class,
because a class selector outranks a presentation attribute:

```svg
<style>
  @media (prefers-color-scheme: dark) {
    .pip  { fill: #F1EEF9; }
    .node { fill: #9E8BFF; }
  }
</style>
<circle class="pip" cx="22" cy="22" r="4.3" fill="#14161C"/>
```

Do not move the light palette into a CSS custom property. Browsers resolve
`var()` in SVG, but several non-browser renderers do not — librsvg drops the
declaration and leaves the shape unpainted, so a `fill: none` element disappears
entirely. Presentation attributes mean the worst case is a mark in the light
palette rather than no mark at all.

The media query is evaluated by the viewer's browser even when the file is
embedded as an `<img>`, which is how GitHub renders repository images. One file
therefore serves both themes, and no `<picture>` element with paired sources is
needed.

The two PNGs are single-theme on purpose. Both sit on their own ink ground, so
they do not depend on what is behind them: an avatar and a link card are
composited by GitHub against surfaces this repository does not control.

## Palette

| Token | Light | Dark | Role |
| --- | --- | --- | --- |
| ink | `#14161C` | — | Strokes, pips, PNG ground |
| paper | `#F6F4FA` | — | Light ground |
| foreground | `#14161C` | `#F1EEF9` | The mark itself |
| accent | `#5B3DEF` | `#9E8BFF` | The merge node, one per mark |

Violet was chosen because it collides with nothing in the surrounding interface.
It is not the green or red of a CI status, not the orange of a failing check,
and it is pushed bluer and darker than the `#8250DF` GitHub uses for a merged
pull request so the mark stays distinct beside one. Amber `#C98A1E` is the
documented alternate if the identity ever has to sit inside a violet-heavy tool.

## Rules

- The mark is monochrome plus one accent node. It is never recoloured to a CI
  status hue, and never gains a second accent.
- Clearspace is the diameter of the merge node on every side.
- Minimum sizes: Merge Fan 32 px, Merge Die 16 px.
- Do not place the fan mark on a busy background; the outer samples are already
  at 32 % opacity and lose their read.
- Do not redraw either mark at a new size. Both are built in a 64-unit box and
  scale from there; the stroke weight is part of the drawing.

## Regenerating the rasters

```sh
rsvg-convert -w 512 -h 512 assets/icon-tile.svg -o assets/icon-512.png
rsvg-convert -w 1280 -h 640 assets/social-preview.svg -o assets/social-preview.png
```

`social-preview.svg` sets type in Inter and falls back to DejaVu Sans. Render it
with Inter installed, or the card ships in the fallback face.
