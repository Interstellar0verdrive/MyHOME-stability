// The theme layer: Home Assistant's CSS variables, and never a literal colour.
//
// Because the panel is registered with `embed_iframe: false`, its element is created in
// the main frontend document and inherits every variable the active theme defines - light,
// dark, and whatever the user installed, with no code of ours. The rule from the design
// handoff (section 1) is that each variable is used for the one thing it is for, and that
// each `var()` carries a fallback, so that an exotic theme which omits one cannot blank a
// screen.
//
// Two variables the handoff names are *this project's*, and Home Assistant guarantees
// neither, so they are defined here with the documented defaults:
//
// * `--text-primary-color` - the text on a filled primary button (white on light,
//   near-black on dark; Home Assistant does define it in its own themes, but not in every
//   third-party one).
// * `--snack-action-color` - the action word inside an inverted feedback strip.
//
// The pastel tints are `color-mix(in srgb, var(--X) N%, var(--card-background-color))` at
// the percentages the handoff fixes: primary 20 %, accent 18 %, error 12 % (14 % for a
// destructive button), warning 12 %, success 12 %, info 12 %. They are **backgrounds
// only**; text on them uses the theme's full colours, which is what keeps AA contrast in
// both themes without a second palette. Dark mode needs no branch here: every mix is
// against the card colour, which is what changes.

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
    --myhome-divider: var(--divider-color, rgba(0, 0, 0, 0.12));
    --myhome-error: var(--error-color, #db4437);
    --myhome-warning: var(--warning-color, #ffa600);
    --myhome-success: var(--success-color, #43a047);
    --myhome-info: var(--info-color, #039be5);
    --myhome-header: var(--app-header-background-color, var(--primary-color, #03a9f4));
    --myhome-header-text: var(--app-header-text-color, #ffffff);
    --myhome-radius: var(--ha-card-border-radius, 12px);
    --myhome-shadow: var(--ha-card-box-shadow, 0 1px 4px rgba(0, 0, 0, 0.14));

    /* The pastels, at the percentages the handoff fixes. */
    --myhome-primary-pastel: color-mix(in srgb, var(--myhome-primary) 20%, var(--myhome-card));
    --myhome-primary-faint: color-mix(in srgb, var(--myhome-primary) 10%, var(--myhome-card));
    --myhome-accent-pastel: color-mix(in srgb, var(--myhome-accent) 18%, var(--myhome-card));
    --myhome-error-pastel: color-mix(in srgb, var(--myhome-error) 12%, var(--myhome-card));
    --myhome-error-strong: color-mix(in srgb, var(--myhome-error) 14%, var(--myhome-card));
    --myhome-warning-pastel: color-mix(in srgb, var(--myhome-warning) 12%, var(--myhome-card));
    --myhome-success-pastel: color-mix(in srgb, var(--myhome-success) 12%, var(--myhome-card));
    --myhome-info-pastel: color-mix(in srgb, var(--myhome-info) 12%, var(--myhome-card));

    /*
     * The inks: the same colours, made readable as *text*.
     *
     * The pastels are backgrounds and the handoff's rule holds for them - the text on a
     * pastel is the theme's own full text colour, and that is AA in both themes. What the
     * rule does not cover is text painted in a status colour on a card: a link in
     * --primary-color, an error line, the amber sentence about a profile nobody defines
     * any more. Measured against Home Assistant's own default light theme
     * (tools/contrast.mjs), those sit between 2.4:1 and 4.3:1 - under AA, every one of
     * them, at 12.5 to 17 px.
     *
     * So a colour that is going to be read is mixed half and half with the theme's own
     * text colour. That number is the one at which every pair the panel draws clears
     * 4.5:1 in both themes with room to spare - amber included, which is the one that
     * fixes it: --warning-color is #ffa600 in Home Assistant's default light theme, the
     * lightest of the five, and at 60 % of itself it read 4.21:1 on a card. Mixing towards
     * --primary-text-color is what makes one rule work for both themes: it is near-black
     * where the ground is light and near-white where the ground is dark, so the ink always
     * moves away from the background and never towards it. The hue survives - a link is
     * still blue, an error still red - which is the point of not simply painting them all
     * in the text colour.
     *
     * Borders, dots, bars and fills keep the pure colour: they are not read, and 1.4.11
     * asks 3:1 of them, which the unmixed colours meet.
     */
    --myhome-primary-ink: color-mix(in srgb, var(--myhome-primary) 50%, var(--myhome-text));
    --myhome-error-ink: color-mix(in srgb, var(--myhome-error) 50%, var(--myhome-text));
    --myhome-warning-ink: color-mix(in srgb, var(--myhome-warning) 50%, var(--myhome-text));
    --myhome-success-ink: color-mix(in srgb, var(--myhome-success) 50%, var(--myhome-text));
    --myhome-info-ink: color-mix(in srgb, var(--myhome-info) 50%, var(--myhome-text));
    /* ...and the quiet grey of a neutral chip, which sits on the secondary background. */
    --myhome-text-soft-ink: color-mix(in srgb, var(--myhome-text-soft) 50%, var(--myhome-text));

    /*
     * The edge of a field or of a choice, which is a UI component boundary and not a
     * separator: 1.4.11 asks 3:1 of it. --divider-color is 0.12 alpha black in Home
     * Assistant's light theme - 1.3:1 against a card, which is a box a low-vision reader
     * cannot find. The dividers *between* rows go on using it, because a line that is
     * only decoration is exempt and because making them darker would draw a grid where
     * the design draws a list.
     */
    --myhome-field-border: color-mix(in srgb, var(--myhome-text-soft) 80%, var(--myhome-card));

    /*
     * The one surface that is not a theme colour, and deliberately so: the wizard's
     * drawings are black line art with a transparent ground, so the area they sit in is
     * the paper they are printed on rather than a card. The handoff fixes it white in
     * both themes for exactly that reason - on a dark card the lines disappear.
     */
    --myhome-drawing-paper: var(--myhome-drawing-surface, #ffffff);

    display: block;
    min-height: 100%;
    /* The font comes from the host document; the panel never loads one. */
    color: var(--myhome-text);
    background: var(--myhome-background);
  }

  *,
  *::before,
  *::after {
    box-sizing: border-box;
  }

  :host * :focus-visible {
    outline: 2px solid var(--myhome-primary-ink);
    outline-offset: 2px;
  }

  @media (prefers-reduced-motion: reduce) {
    :host * {
      animation-duration: 0.001ms !important;
      transition-duration: 0.001ms !important;
    }
  }
`;

/** Cards, the shape every group, panel and dialog of the handoff is cut from. */
export const cardStyles = css`
  .card {
    background: var(--myhome-card);
    border-radius: var(--myhome-radius);
    box-shadow: var(--myhome-shadow);
  }
`;

/**
 * The three levels of call to action from the handoff: filled primary, outlined secondary
 * of the same shape, and textual for Cancel and Close. Destructive is the error pastel
 * with error text - never a filled red button, which reads as the normal thing to do.
 */
export const buttonStyles = css`
  .cta {
    min-height: 48px;
    padding: 0 24px;
    border-radius: 24px;
    border: none;
    background: var(--myhome-primary);
    color: var(--myhome-text-on-primary);
    font: inherit;
    font-size: 15px;
    font-weight: 500;
    cursor: pointer;
  }

  .cta.secondary {
    background: transparent;
    border: 1px solid var(--myhome-primary-ink);
    color: var(--myhome-primary-ink);
  }

  .cta.text {
    background: transparent;
    border: none;
    color: var(--myhome-primary-ink);
    padding: 0 12px;
  }

  .cta.destructive {
    background: var(--myhome-error-strong);
    color: var(--myhome-error-ink);
  }

  .cta[disabled] {
    background: var(--myhome-background-soft);
    color: var(--myhome-text-off);
    cursor: default;
  }

  .cta.compact {
    min-height: 44px;
    padding: 0 18px;
    border-radius: 22px;
    font-size: 14px;
  }
`;

/** Text fields and selects; 44 px tall, and the decimal ones ask for a decimal keyboard. */
export const fieldStyles = css`
  .field {
    height: 44px;
    border-radius: 8px;
    border: 1px solid var(--myhome-field-border);
    background: var(--myhome-card);
    color: var(--myhome-text);
    padding: 0 12px;
    font: inherit;
    font-size: 14px;
  }

  .field:disabled {
    color: var(--myhome-text-off);
  }
`;

/**
 * Only a screen reader reads this. Used for the live region: a sentence announced but not
 * drawn, because every drop, every refusal and every applied change already shows on the
 * screen for anybody who can see it.
 */
export const srOnly = css`
  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    margin: -1px;
    padding: 0;
    overflow: hidden;
    clip: rect(0 0 0 0);
    clip-path: inset(50%);
    white-space: nowrap;
    border: 0;
  }
`;
