# AquaPin design system ("field notebook")

Source of truth for tokens: `fields/static/fields/css/app.css` (`:root`). Keep both in sync.

## Principles
- Class: APP UI (workspace). The map dominates on desktop and on mobile.
- Calm surfaces, one accent, utility language (status, action). No marketing copy.
- Cards only when the card is the interaction. "Why this advice" is a disclosure, not a card.
- Never rely on colour alone: NDVI has a numeric legend; confidence is a text badge.

## Tokens (contrast measured on `--paper`)
| Token | Value | Use | Contrast |
|---|---|---|---|
| `--paper` | `#F3EFE4` | page background | - |
| `--panel` | `#FAF7EE` | side panel | - |
| `--ink` | `#1D2620` | text | 13.5 |
| `--muted` | `#5B655D` | secondary text | 5.3 |
| `--water` | `#1E6B8C` | single accent, links, primary button | 5.2 |
| `--amber-text` | `#8A5A00` | low confidence, errors (text) | 5.2 |
| `--line` | `#D9D3C3` | hairlines only (decorative) | 1.3 |

NDVI ramp (user decision): classic red to green, ColorBrewer RdYlGn anchors
`#a50026 #f46d43 #fee08b #a6d96a #1a9850 #006837` over NDVI 0..0.9, with a numeric legend.
Known limitation: red-green is hard for colour-blind users; the legend and the observation table carry the numbers.

## Type
One typeface: IBM Plex Sans (latin, latin-ext, cyrillic woff2, self-hosted so the demo works offline),
`font-variant-numeric: tabular-nums` for data. Body >= 16px.
(Atkinson Hyperlegible was the first candidate but does not cover Cyrillic.)

## Interaction and accessibility
- Breakpoints 375 / 768 / 1280 (layout switches at 900px). Touch targets >= 44px.
- Season slider: arrows = 1 day, PageUp/PageDown = 1 week, `aria-valuetext` = "date, NDVI value".
- Text summary (`#summary`) and an observation table for screen readers. Visible focus ring.
- `prefers-reduced-motion`: no autoplay.
- EN and RU, `lang` attribute set. Bot replies are plain text.

## Banned
Purple gradients, icon-in-circle decoration, everything centred, uniform bubbly radius,
decorative blobs, emoji as decoration, coloured left-border blocks, "Welcome to..." copy.
