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

Use it for the favicon, for any square icon slot — an organisation avatar, a
package listing, a docs site — and anywhere the mark drops below 32 pixels. The connectors drop out under that size by design; three pips in a
rounded square still read as a die.

The two share a vocabulary — one accent node as the merge point, dots as
samples, a single stroke weight scaled to the box — so they read as a family
without either needing the other present.

## Files

| File | Contents |
| --- | --- |
| `assets/logo.svg` | Merge Fan in accent violet. The README and docs mark. |
| `assets/favicon.svg` | Merge Die, theme-adaptive. The browser tab mark. |
| `assets/icon-tile.svg` | Merge Die on a full-bleed ink tile. Source for the avatar. |
| `assets/icon-512.png` | 512×512 render of the tile, for square icon slots. |
| `assets/social-preview.svg` | 1280×640 link card. Source; needs Inter installed. |
| `assets/social-preview.png` | Rendered card, uploaded under Settings → Social preview. |

### Where each file is wired up

| File | Status |
| --- | --- |
| `assets/logo.svg` | In use, in the README heading. |
| `assets/social-preview.png` | In use, once uploaded under Settings → General → Social preview. GitHub offers no API for it, so the upload is manual and has to be repeated whenever the card changes. |
| `assets/favicon.svg` | Not wired up. Nothing consumes it yet. |
| `assets/icon-tile.svg`, `assets/icon-512.png` | Not wired up. Nothing consumes them yet. |

github.com serves its own favicon on every page. A repository has no favicon
setting and no icon field of any kind, and a personal repository shows the
owner's avatar rather than one of its own, so neither the die nor the tile can
be attached to this project on GitHub itself. They are drawn and ready for the
surfaces that do take an icon, and unused until one of those exists:

- A documentation site, which is the real target for the die. Whoever owns the
  `<head>` links it, preferring the SVG and keeping the PNG as the fallback for
  anything that refuses an SVG favicon:

  ```html
  <link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
  <link rel="icon" href="/assets/icon-512.png" sizes="512x512">
  ```

  This is also the one surface where the die's palette switch earns its keep,
  since a browser tab follows the browser's own theme.
- An organisation account, if the project ever moves under one, which takes
  `icon-512.png` as its avatar.
- A package listing or any other tool asking for a square icon.

Do not delete the unused files to tidy up. They are the small half of the
two-tier system, and the README mark cannot stand in for them: the fan is
documented as illegible below 32 pixels, which is the entire reason the die
exists.

## Light and dark

The favicon carries its own palette switch. The light palette sits in
presentation attributes and the dark palette overrides it by class, because a
class selector outranks a presentation attribute:

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

The fan mark takes the opposite approach: one file, accent violet, no switch at
all. `prefers-color-scheme` reports the operating system's preference, and a
site theme is a separate setting — someone reading GitHub in dark mode on a
light desktop gets the light palette painted onto a dark page, where an ink mark
vanishes. A `<picture>` element with paired sources does not help, because it
reads the same signal. Violet clears contrast on both grounds, so the mark never
has to know which one it landed on.

That trade only works for the fan. The die is a hairline outline whose whole
read depends on the stroke, so it keeps the switch and accepts the mismatch
case; a browser tab follows the browser's own theme, which is the signal
`prefers-color-scheme` actually reports.

The two PNGs are single-theme on purpose. Both sit on their own ink ground, so
they do not depend on what is behind them: an icon and a link card are
composited against surfaces this repository does not control.

## Palette

| Token | Light | Dark | Role |
| --- | --- | --- | --- |
| ink | `#14161C` | — | Strokes, pips, PNG ground |
| paper | `#F6F4FA` | — | Light ground |
| foreground | `#14161C` | `#F1EEF9` | The mark itself |
| accent | `#5B3DEF` | `#9E8BFF` | The merge node in the die |
| accent, dual | `#7A5AF8` | `#7A5AF8` | The whole fan mark, on either ground |

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
