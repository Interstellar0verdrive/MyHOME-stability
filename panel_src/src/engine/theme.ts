// The theme layer: Home Assistant's CSS variables, and never a literal colour.
//
// Because the panel is registered with `embed_iframe: false`, its element is created in
// the main frontend document and inherits every variable the active theme defines -
// light, dark, and whatever the user installed, with no code of ours. The rule from the
// design handoff (section 1) is that each variable is used for the one thing it is for,
// and that each `var()` carries a fallback, so that an exotic theme which omits one
// cannot blank a screen.
//
// Two variables the handoff names are *this project's*, and Home Assistant guarantees
// neither, so they are defined here with the documented defaults:
//
// * `--text-primary-color` - the text on a filled primary button (white on light,
//   near-black on dark; Home Assistant does define it in its own themes, but not in
//   every third-party one).
// * `--snack-action-color` - the action word inside an inverted feedback strip.
//
// Pastel tints are `color-mix(in srgb, var(--X) N%, var(--card-background-color))` at the
// percentages the handoff fixes; they are backgrounds only, and text on them uses the
// theme's full colours, which is what keeps AA contrast in both themes.

import { css } from "lit";

export const themeStyles = css`
  :host {
    /* Project-introduced, with the documented fallbacks. */
    --myhome-text-on-primary: var(--text-primary-color, #ffffff);
    --myhome-snack-action: var(--snack-action-color, #ffc107);

    /* Home Assistant's own, each behind a fallback. */
    --myhome-primary: var(--primary-color, #03a9f4);
    --myhome-accent: var(--accent-color, #ff9800);
    --myhome-text: var(--primary-text-color, #212121);
    --myhome-text-soft: var(--secondary-text-color, #727272);
    --myhome-text-off: var(--disabled-text-color, #bdbdbd);
    --myhome-background: var(--primary-background-color, #fafafa);
    --myhome-background-soft: var(--secondary-background-color, #e5e5e5);
    --myhome-card: var(--card-background-color, #ffffff);
    --myhome-divider: var(--divider-color, #e0e0e0);
    --myhome-error: var(--error-color, #db4437);
    --myhome-warning: var(--warning-color, #ffa600);
    --myhome-success: var(--success-color, #43a047);
    --myhome-info: var(--info-color, #039be5);
    --myhome-header: var(--app-header-background-color, var(--primary-color, #03a9f4));
    --myhome-header-text: var(--app-header-text-color, #ffffff);
    --myhome-radius: var(--ha-card-border-radius, 12px);

    display: block;
    min-height: 100%;
    /* The font comes from the host document; the panel never loads one. */
    color: var(--myhome-text);
    background: var(--myhome-background);
  }
`;
