// "Leave the calibration?" - the one question the ✕ asks, and the only way out of the
// wizard that throws measurements away.
//
// It is a confirmation and not a menu: two buttons, one of which is where the user already
// was. The wording is the panel's own (SPEC §5.5) and it says the two things somebody
// standing in front of a moving shutter needs to know - that nothing has been written, and
// that a run already under way finishes by itself at its end stop. A dialog that said only
// "are you sure?" would leave the second one to be found out.
//
// Escape closes it (back to measuring, which is the safe answer), the backdrop closes it,
// and the keyboard is held inside it by `FocusTrap` while it is open. Escape on the wizard
// *behind* it opens this rather than cancelling anything, which is the whole reason the
// question exists.

import { css, html, type TemplateResult } from "lit";

import { type I18n } from "../engine/i18n";

export const exitDialogStyles = css`
  .exit-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.4);
    z-index: 60;
  }

  .exit {
    position: fixed;
    left: 16px;
    right: 16px;
    top: 50%;
    transform: translateY(-50%);
    margin: 0 auto;
    max-width: 400px;
    box-sizing: border-box;
    background: var(--myhome-card);
    color: var(--myhome-text);
    border-radius: var(--myhome-radius);
    box-shadow: var(--myhome-shadow);
    z-index: 61;
    padding: 20px;
  }

  .exit h2 {
    margin: 0 0 8px;
    font-size: 18px;
    font-weight: 500;
  }

  .exit p {
    margin: 0 0 16px;
    font-size: 13.5px;
    line-height: 1.55;
    color: var(--myhome-text-soft);
  }

  .exit .foot {
    display: flex;
    gap: 10px;
    justify-content: flex-end;
  }

  .exit .foot button {
    flex: 1 1 0;
    min-width: 0;
    min-height: 44px;
    padding: 0 10px;
    border: none;
    border-radius: 22px;
    font: inherit;
    font-size: 13.5px;
    font-weight: 500;
    cursor: pointer;
  }

  .exit .foot .stay {
    background: var(--myhome-primary-faint);
    color: var(--myhome-primary-ink);
  }

  .exit .foot .leave {
    background: var(--myhome-error-strong);
    color: var(--myhome-error-ink);
  }
`;

export interface ExitDialogContext {
  i18n: I18n;
  onStay: () => void;
  onLeave: () => void;
}

export const exitDialog = (context: ExitDialogContext): TemplateResult => {
  const { i18n } = context;
  return html`
    <div class="exit-backdrop" aria-hidden="true" @click=${context.onStay}></div>
    <div
      class="exit"
      role="dialog"
      aria-modal="true"
      aria-labelledby="exit-title"
      data-exit-dialog
      data-focus-root
    >
      <h2 id="exit-title">${i18n.t("panel.wizard.exit.title")}</h2>
      <p>${i18n.t("panel.wizard.exit.body")}</p>
      <div class="foot">
        <button class="stay" type="button" data-exit-stay @click=${context.onStay}>
          ${i18n.t("panel.wizard.exit.stay")}
        </button>
        <button class="leave" type="button" data-exit-leave @click=${context.onLeave}>
          ${i18n.t("panel.wizard.exit.leave")}
        </button>
      </div>
    </div>
  `;
};
