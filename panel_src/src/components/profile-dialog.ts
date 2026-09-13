// "Quale profilo?" - the tap path and the keyboard path, which are the same path.
//
// Enter or Space on a row's handle opens this; so does a tap on a phone where the design
// asks for a list rather than a gesture. It is not a shortcut around the drag: it ends in
// exactly the same pending change, shown on exactly the same row, confirmed in exactly the
// same panel. That is the accessibility requirement of the handoff (§5) met by making the
// keyboard path the primary one and the drag the ornament on top of it, rather than by
// bolting a second mechanism onto a gesture.
//
// The option the shutter is on already is marked "attuale" and outlined - **it is not
// disabled**. Choosing it withdraws a pending change, which is the only way back from the
// dialog to where the shutter started, and a disabled option would make that unreachable.
//
// Focus is trapped while it is open and given back to the handle when it closes, which is
// `FocusReturn` in `engine/a11y.ts`. Escape closes it; so does the backdrop.

import { css, html, nothing, type TemplateResult } from "lit";

import { type I18n } from "../engine/i18n";
import { type CoverRow, type ProfileRow } from "../engine/ws";

export const dialogStyles = css`
  .backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.4);
    z-index: 60;
  }

  .dialog {
    position: fixed;
    left: 50%;
    top: 50%;
    transform: translate(-50%, -50%);
    width: min(440px, 92vw);
    max-height: 80vh;
    overflow: auto;
    background: var(--myhome-card);
    color: var(--myhome-text);
    border-radius: var(--myhome-radius);
    box-shadow: var(--myhome-shadow);
    z-index: 61;
    padding: 20px;
    box-sizing: border-box;
  }

  .dialog h2 {
    margin: 0 0 4px;
    font-size: 18px;
    font-weight: 500;
  }

  .dialog .subtitle {
    margin: 0 0 16px;
    font-size: 13.5px;
    color: var(--myhome-text-soft);
  }

  .dialog .options {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  /*
   * The selected option is a 1 px border plus an inset ring of the same colour, not a
   * 2 px border: the ring is drawn inside the element, so the option does not grow when it
   * becomes the current one and the list does not shuffle under the pointer.
   */
  .dialog .option {
    text-align: left;
    border-radius: 8px;
    font: inherit;
    padding: 12px;
    min-height: 48px;
    cursor: pointer;
    border: 1px solid var(--myhome-divider);
    background: transparent;
    color: inherit;
  }

  .dialog .option.current {
    border-color: var(--myhome-primary);
    box-shadow: inset 0 0 0 1px var(--myhome-primary);
    background: var(--myhome-primary-faint);
  }

  .dialog .option .line {
    display: flex;
    align-items: baseline;
    gap: 8px;
  }

  .dialog .option .title {
    font-weight: 500;
    flex: 1;
  }

  .dialog .option .tag {
    font-size: 12.5px;
    color: var(--myhome-primary);
  }

  .dialog .option .meta {
    display: block;
    font-size: 12.5px;
    color: var(--myhome-text-soft);
    margin-top: 2px;
  }

  .dialog .foot {
    display: flex;
    justify-content: flex-end;
    margin-top: 12px;
  }

  .dialog .foot button {
    min-height: 44px;
    padding: 0 16px;
    border: none;
    background: transparent;
    color: var(--myhome-text-soft);
    font: inherit;
    font-size: 14px;
    cursor: pointer;
  }
`;

export interface DialogContext {
  i18n: I18n;
  cover: CoverRow;
  profiles: readonly ProfileRow[];
  /** Where the shutter is heading now: its pending destination, else the server's. */
  current: string | null;
  onPick: (profile: string | null) => void;
  onClose: () => void;
}

/** A profile's one-line summary, in the reader's language, out of the server's numbers. */
const profileMeta = (i18n: I18n, profile: ProfileRow): string => {
  if (profile.missing || profile.values.opening_time === undefined) {
    return i18n.t("panel.overview.group.values_unknown");
  }
  return i18n.t("panel.dialog.option.profile_meta", {
    travel: profile.reference_height === null ? "?" : i18n.number(profile.reference_height, 0),
    opening: i18n.number(profile.values.opening_time, 1),
    closing: i18n.number(profile.values.closing_time, 1),
  });
};

export const profileDialog = (context: DialogContext): TemplateResult => {
  const { i18n } = context;
  const option = (
    key: string | null,
    title: string,
    meta: string,
  ): TemplateResult => html`<button
    class="option ${context.current === key ? "current" : ""}"
    type="button"
    aria-current=${context.current === key ? "true" : nothing}
    @click=${() => context.onPick(key)}
  >
    <span class="line"
      ><span class="title">${title}</span
      >${context.current === key
        ? html`<span class="tag">${i18n.t("panel.dialog.option.current")}</span>`
        : nothing}</span
    >
    <span class="meta">${meta}</span>
  </button>`;

  return html`
    <div class="backdrop" aria-hidden="true" @click=${context.onClose}></div>
    <div
      class="dialog"
      role="dialog"
      aria-modal="true"
      aria-labelledby="dialog-title"
      data-focus-root
    >
      <h2 id="dialog-title">${i18n.t("panel.dialog.title")}</h2>
      <p class="subtitle">
        ${i18n.t("panel.dialog.subtitle", { cover: context.cover.name })}
      </p>
      <div class="options">
        ${context.profiles.map((profile) =>
          option(
            profile.name,
            i18n.t("panel.dialog.option.profile", { profile: profile.name }),
            profileMeta(i18n, profile),
          ),
        )}
        ${option(
          null,
          i18n.t("panel.dialog.option.none"),
          i18n.t("panel.dialog.option.none_meta"),
        )}
      </div>
      <div class="foot">
        <button type="button" @click=${context.onClose}>
          ${i18n.t("panel.common.action.cancel")}
        </button>
      </div>
    </div>
  `;
};
