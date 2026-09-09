---
id: T-031-add-the-project-visual-identity-assets
title: Add the project visual identity assets
status: completed
priority: medium
spec_ref: specs/v0.1.0.md#release-hardening
dependencies: []
updated_at: "2026-09-09T19:53:58Z"
---

# T-031-add-the-project-visual-identity-assets Add the project visual identity assets

## Description

Give the project a visual identity that holds at every size it is actually
rendered at. A repository mark spends most of its life as a favicon and an
avatar rather than as a README header, so one drawing cannot serve both bands.
Ship two marks with a documented split of roles, plus the brand rules that keep
them from drifting.

## Acceptance

- A fan mark for the README, documentation, and social preview, and a die mark
  for the favicon and avatar, each legible at the sizes it is used at.
- Both vector marks adapt to light and dark from a single file, with no paired
  sources to keep in step.
- Raster outputs carry their own ground, so neither depends on a surface this
  repository does not control.
- `docs/brand.md` records the roles, palette, clearspace, minimum sizes, and the
  commands that regenerate the rasters.
- The README shows the mark and links the brand documentation.

## Verification Notes

- Both marks were rasterised at 16, 32, and 64 pixels with `rsvg-convert`
  and inspected. The die keeps its silhouette, three pips, and accent node
  at 16 px; the fan loses its sample columns to blur below 32 px, which is
  why `docs/brand.md` sets that as its minimum size.
- The first draft used CSS custom properties for the palette. librsvg does
  not resolve `var()`, so the die body rendered unpainted and vanished. The
  shipped files carry the light palette in presentation attributes instead.

## Implementation Notes

- 2026-09-09T19:53:58Z: verification pass
