// The amber banner: a guided calibration has one of these shutters, so everything here is
// read-only until it lets go.
//
// It is a `role="status"` region with `aria-live="polite"`, not an alert: it is a standing
// condition of the page rather than an event, and a user who arrives mid-session must meet
// it rather than be interrupted by it. It is announced **before** anything is attempted -
// `overview.measuring` carries the shutter's name, and the subscription pushes the change
// the moment a holder takes or releases one - so the refusal the backend would send is a
// backstop the user never has to read (contract §8, R-W1).
//
// **Three shapes, and the difference between them is one field** (SPEC §6). `measuring`
// says *that* a shutter of this gateway is being measured; `overview.session` says *who*:
//
// 1. **a session of the panel's** (`session` is there): it can be resumed, because the
//    wizard is a screen of this panel, and it can be ended from here - with `force`, since
//    the tab that opened it may be somebody else's phone;
// 2. **the *Configure* dialog** (`measuring` with no `session`): this panel cannot drive
//    it, so the two things it can honestly offer are the dialog itself and closing it.
//    Closing is `end_other`, which aborts every options flow of this gateway;
// 3. **the 0.4.2 action**: indistinguishable from the dialog until `end_other` has been
//    tried - every dialog closed and the shutter still held *is* the answer - so this
//    shape is reached only afterwards, and it is a sentence with nothing to press, because
//    an action running on the gateway has no window to close.
//
// Both destructive offers ask first, in the banner itself rather than in a dialog over it:
// the question is one sentence, it belongs to the strip it was asked from, and a modal
// over a list nobody is touching would be a focus trap for a "no".
//
// The links that used to be here both went to the integration page - where the user still
// had to find "Configura" - and said nothing about which of the three situations they were
// in (design check, row 24). Only "Apri Configura" still leaves the panel.

import { css, html, nothing, type TemplateResult } from "lit";

import { type I18n } from "../engine/i18n";
import { type BusyAsk, type BusyState } from "../engine/store";
import { type Overview } from "../engine/ws";

export const measuringBannerStyles = css`
  .measuring {
    max-width: 1200px;
    margin: 16px auto 0;
    padding: 12px 16px;
    border-radius: var(--myhome-radius);
    background: var(--myhome-warning-pastel);
    display: flex;
    gap: 12px;
    align-items: baseline;
    flex-wrap: wrap;
  }

  .measuring strong {
    color: var(--myhome-warning-ink);
    font-weight: 500;
  }

  .measuring .body {
    flex: 1 1 320px;
    line-height: 1.5;
  }

  .measuring .links {
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
  }

  .measuring a {
    color: var(--myhome-primary-ink);
    min-height: 44px;
    display: inline-flex;
    align-items: center;
  }

  /*
   * The offers are buttons now and not links, because four of the five change something on
   * this gateway rather than going somewhere. They are drawn as the panel's textual call
   * to action, at the link's own colour, so the strip reads as it did.
   */
  .measuring button.offer {
    /* SPEC §5.7's minimum target: these are five narrow controls side by side, and the
       44 px they inherited from the links that used to be here left the hit area exactly
       as tall as the text. */
    min-height: 48px;
    padding: 0 4px;
    border: none;
    background: none;
    font: inherit;
    font-size: inherit;
    color: var(--myhome-primary-ink);
    text-decoration: underline;
    cursor: pointer;
  }

  .measuring button.offer.destructive {
    color: var(--myhome-error-ink);
  }
`;

/** What the banner can ask the shell to do. Implemented once, in `main.ts`. */
export interface BannerActions {
  /** Back to the wizard, which is where a session of the panel's own is driven. */
  resume: () => void;
  /** Put one of the two questions on the screen, or take it back. */
  ask: (question: BusyAsk) => void;
  /** End the panel's session whoever owns it: `cancel` with `force`. */
  endPanel: () => void;
  /** Close every *Configure* dialog of this gateway and free the shutter. */
  endOther: () => void;
  /** The one offer here that still leaves the panel. */
  openFlow: (source: HTMLElement) => void;
}

const offer = (
  label: string,
  press: (event: Event) => void,
  mark: string,
  destructive = false,
): TemplateResult =>
  html`<button
    class="offer ${destructive ? "destructive" : ""}"
    type="button"
    data-banner=${mark}
    @click=${press}
  >
    ${label}
  </button>`;

/** The question, with the answer that does the thing and the answer that does nothing. */
const question = (
  i18n: I18n,
  body: string,
  confirm: string,
  onConfirm: () => void,
  onCancel: () => void,
): TemplateResult =>
  html`<span class="body" data-banner-question>${body}</span>
    <span class="links">
      ${offer(confirm, onConfirm, "confirm", true)}
      ${offer(i18n.t("panel.common.action.cancel"), onCancel, "keep")}
    </span>`;

/**
 * The banner, in whichever of its three shapes this gateway is in.
 *
 * `overview` is passed whole rather than a name and a flag: which shape this is is read
 * off `measuring` and `session` together, and a caller that worked it out would be a
 * second place where "the dialog or the action" is decided.
 */
export const measuringBanner = (
  i18n: I18n,
  overview: Overview,
  busy: BusyState,
  actions: BannerActions,
): TemplateResult | typeof nothing => {
  const measuring = overview.measuring;
  if (!measuring) {
    return nothing;
  }
  const panel = overview.session !== null;
  const body = panel
    ? i18n.t("panel.banner.measuring.panel_body", { cover: measuring.name })
    : busy.service
      ? i18n.t("panel.wizard.busy.service")
      : i18n.t("panel.banner.measuring.body", { cover: measuring.name });
  return html`<div
    class="measuring"
    role="status"
    aria-live="polite"
    data-banner-measuring
    ?data-banner-service=${!panel && busy.service}
  >
    <strong>${i18n.t("panel.banner.measuring.title")}</strong>
    ${busy.ask === "end_panel"
      ? question(
          i18n,
          i18n.t("panel.banner.measuring.end_panel_confirm", { cover: measuring.name }),
          i18n.t("panel.banner.measuring.action.stop"),
          actions.endPanel,
          () => actions.ask(null),
        )
      : busy.ask === "end_other"
        ? question(
            i18n,
            i18n.t("panel.wizard.busy.end_other_confirm"),
            i18n.t("panel.wizard.busy.end_other"),
            actions.endOther,
            () => actions.ask(null),
          )
        : html`<span class="body">${body}</span>
            <span class="links">
              ${panel
                ? html`${offer(
                    i18n.t("panel.banner.measuring.action.resume"),
                    actions.resume,
                    "resume",
                  )}${offer(
                    i18n.t("panel.banner.measuring.action.stop"),
                    () => actions.ask("end_panel"),
                    "end-panel",
                  )}`
                : // The action of 0.4.2 has already been found out, so there is nothing to
                  // close and nothing to open: the sentence above is the whole of it.
                  busy.service
                  ? nothing
                  : html`${offer(
                      i18n.t("panel.common.action.configure"),
                      (event: Event) => actions.openFlow(event.currentTarget as HTMLElement),
                      "configure",
                    )}${offer(
                      i18n.t("panel.wizard.busy.end_other"),
                      () => actions.ask("end_other"),
                      "end-other",
                    )}`}
            </span>`}
  </div>`;
};
