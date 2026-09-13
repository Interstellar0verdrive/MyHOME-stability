// The origin chip: where the numbers this shutter runs on came from.
//
// Five states, and the panel **never works out which one** - `origin` arrives as a token
// from `resolve_cover_config`, the same call that writes the entity's `Calibration source`
// attribute. That is the parity invariant: one function answers the question, on the
// server, so the panel and the attribute cannot drift. The prototype computed it in
// JavaScript; that code is deliberately not ported.
//
// Colours, from the handoff (section 2): *Misurata* is the primary pastel at 20 % with the
// theme's full text on it; *Adattata* is the accent pastel at 18 % with a 6 px dot, because
// two pastels of similar weight are not a distinction a colour-blind reader can make;
// *Ereditata*, *Dal file* and *Predefiniti* are neutral on the secondary background. The
// chip sits **under** the texts of the row, not to the right of them (addendum).

import { css, html, nothing, type TemplateResult } from "lit";

import { type I18n } from "../engine/i18n";

export const originChipStyles = css`
  .chip {
    font-size: 12px;
    border-radius: 10px;
    padding: 3px 9px;
    white-space: nowrap;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background: var(--myhome-background-soft);
    color: var(--myhome-text-soft);
  }

  .chip.measured {
    background: var(--myhome-primary-pastel);
    color: var(--myhome-text);
  }

  .chip.adjusted {
    background: var(--myhome-accent-pastel);
    color: var(--myhome-text);
  }

  .chip .dot {
    width: 6px;
    height: 6px;
    border-radius: 3px;
    background: var(--myhome-accent);
    display: inline-block;
  }
`;

/**
 * `short` is true for a row sitting inside the group of the very profile it follows: the
 * heading already says the name, and the handoff asks for it not to be repeated on every
 * row. Everywhere else - "Senza profilo", the detail view - the full sentence is used, out
 * of `selector.calibration_origin.options.*`, which already exists in all eight languages.
 */
export const originChip = (
  i18n: I18n,
  origin: string,
  profile: string | null,
  short: boolean,
): TemplateResult => {
  const kind = origin === "measured" ? "measured" : origin === "adjusted" ? "adjusted" : "neutral";
  let label: string;
  if (short && origin === "inherited") {
    label = i18n.t("panel.overview.origin_short_inherited");
  } else if (short && origin === "adjusted") {
    label = i18n.t("panel.overview.origin_short_adjusted");
  } else {
    label = i18n.origin(origin, profile);
  }
  return html`<span class="chip ${kind}"
    >${kind === "adjusted" ? html`<span class="dot" aria-hidden="true"></span>` : nothing}${label}</span
  >`;
};
