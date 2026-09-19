// `<myhome-wizard>` - the guided calibration's screen. **A stub**: lot F2 replaces the
// body of `_renderSession` with the eight live models, and everything else here is what
// that lot inherits.
//
// What is already real, because it is the part the v2 panel got wrong (SPEC §5.8,
// lesson 1):
//
// * **every drawing is inside a `try`.** An exception building the model or rendering it
//   shows the card below - which says what happened, offers "Try again" and offers the
//   robust way of ending the session - instead of an empty panel. It is logged once; the
//   second identical stack trace tells nobody anything;
// * **nothing on this path keeps the session alive.** The presence signal is
//   `SessionClient`'s own timer (`engine/session.ts`); this element cannot start it, stop
//   it or delay it, which is the whole point of the class having no DOM in it;
// * **a refusal always arrives with something to press.** `state.sessionError` carries the
//   recovery tokens the client worked out, and each becomes one button here. A screen
//   that says "Cancel failed" and nothing else is the silent failure with a sentence on
//   it.
//
// The stub itself shows the shutter's name and where the session stands, as plain text.
// Those are tokens from the server, not sentences: F2 turns them into the screens.

import { LitElement, css, html, nothing, type TemplateResult } from "lit";

import { I18n } from "../engine/i18n";
import { type SessionRecovery } from "../engine/session";
import { type SessionSnapshot } from "../engine/session-contract";
import { type PanelState } from "../engine/store";
import { buttonStyles, cardStyles, themeStyles } from "../engine/theme";

/** What the screen can ask the shell to do. Lot F2 adds the verbs of the conversation. */
export interface WizardActions {
  /** Read the session again. */
  refresh(): void;
  /** End the session, through the four branches of SPEC §5.2. */
  cancel(): void;
  /** Take the session from the client that owns it, and end it. */
  claim(): void;
  /** End it whoever owns it. */
  force(): void;
  /** Back to the list. */
  back(): void;
}

export class MyHomeWizard extends LitElement {
  static override properties = {
    i18n: { attribute: false },
    state: { attribute: false },
    actions: { attribute: false },
  };

  declare i18n: I18n;
  declare state: PanelState;
  declare actions: WizardActions;

  /** Set by a drawing that threw, cleared by "Try again". */
  private _broken: unknown = null;
  private _reported = false;

  constructor() {
    super();
    this.i18n = new I18n();
    this.state = {} as PanelState;
    this.actions = {
      refresh: () => undefined,
      cancel: () => undefined,
      claim: () => undefined,
      force: () => undefined,
      back: () => undefined,
    };
  }

  static override styles = [
    themeStyles,
    cardStyles,
    buttonStyles,
    css`
      :host {
        display: block;
      }

      .card {
        padding: 16px;
      }

      .card + .card {
        margin-top: 16px;
      }

      .card.problem {
        background: var(--myhome-error-pastel);
      }

      h2 {
        margin: 0 0 8px;
        font-size: 18px;
      }

      dl {
        margin: 0;
        display: grid;
        grid-template-columns: auto 1fr;
        gap: 4px 12px;
        font-size: 14px;
      }

      dt {
        color: var(--myhome-text-soft);
      }

      dd {
        margin: 0;
        font-variant-numeric: tabular-nums;
      }

      .actions {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 16px;
      }

      .soft {
        color: var(--myhome-text-soft);
        font-size: 13px;
        margin-top: 8px;
      }
    `,
  ];

  protected override render(): TemplateResult {
    if (this._broken) {
      return this._renderBroken();
    }
    try {
      return html`${this._renderSession()}${this._renderTrouble()}`;
    } catch (error) {
      // Caught here rather than left to Lit, because what Lit does with it is leave the
      // screen half-painted. The flag makes the next paint the error card, which is a
      // screen the user can act on.
      this._fail(error);
      return this._renderBroken();
    }
  }

  /** The stub F2 replaces: the shutter, and where the session stands, as plain text. */
  private _renderSession(): TemplateResult {
    const session: SessionSnapshot | null = this.state.session ?? null;
    if (!session) {
      return html`<div class="card">
        <h2>${this.i18n.t("panel.wizard.title")}</h2>
        <p>${this.i18n.t("panel.wizard.none")}</p>
        <div class="actions">
          <button class="cta text" type="button" @click=${() => this.actions.back()}>
            ${this.i18n.t("panel.common.action.back")}
          </button>
        </div>
      </div>`;
    }
    return html`<div class="card" data-wizard>
      <h2>${session.cover.name}</h2>
      <dl>
        <dt>state</dt>
        <dd data-session-state>${session.state}</dd>
        <dt>step</dt>
        <dd data-session-step>${session.step ?? "-"}</dd>
        <dt>revision</dt>
        <dd>${session.revision}</dd>
      </dl>
      <div class="actions">
        <button class="cta text" type="button" @click=${() => this.actions.cancel()}>
          ${this.i18n.t("panel.wizard.action.end")}
        </button>
        <button class="cta text" type="button" @click=${() => this.actions.back()}>
          ${this.i18n.t("panel.common.action.back")}
        </button>
      </div>
    </div>`;
  }

  /**
   * A refusal, with the ways out the client worked out (lesson 2).
   *
   * Never an error on its own: `recovery` is never empty, and every token in it is drawn
   * as a button. `wait` is the one that is not - there is nothing left to press, so the
   * card says when the gateway frees the shutter by itself.
   */
  private _renderTrouble(): TemplateResult | typeof nothing {
    const trouble = this.state.sessionError ?? null;
    if (!trouble) {
      return nothing;
    }
    const freed = trouble.freedAt ? this.i18n.time(trouble.freedAt) : "";
    return html`<div class="card problem" role="alert" data-session-trouble>
      <h2>${this.i18n.t("panel.wizard.trouble.title")}</h2>
      <p>
        ${this.i18n.refusal(
          trouble.error.translation_key,
          trouble.error.translation_placeholders ?? {},
        )}
      </p>
      ${trouble.recovery.includes("wait") && freed
        ? html`<p class="soft">${this.i18n.t("panel.wizard.trouble.freed", { time: freed })}</p>`
        : nothing}
      <div class="actions">
        ${trouble.recovery.map((token) => this._recoveryButton(token))}
      </div>
    </div>`;
  }

  private _recoveryButton(token: SessionRecovery): TemplateResult | typeof nothing {
    if (token === "wait") {
      return nothing;
    }
    const label =
      token === "claim"
        ? this.i18n.t("panel.wizard.action.claim")
        : token === "force"
          ? this.i18n.t("panel.wizard.action.force")
          : this.i18n.t("panel.common.action.retry");
    const press =
      token === "claim"
        ? () => this.actions.claim()
        : token === "force"
          ? () => this.actions.force()
          : () => this.actions.refresh();
    return html`<button class="cta text" type="button" data-recovery=${token} @click=${press}>
      ${label}
    </button>`;
  }

  /**
   * What a drawing that threw leaves on the screen.
   *
   * Two things to press, and they are the two things that are true: draw it again, or end
   * the calibration - which goes through `SessionClient.cancel()` and therefore cannot
   * fail in silence either. The session itself is untouched by any of this: it is on the
   * server, and the presence signal has gone on the whole time.
   */
  private _renderBroken(): TemplateResult {
    return html`<div class="card problem" role="alert" data-render-error>
      <h2>${this.i18n.t("panel.wizard.render_error.title")}</h2>
      <p>${this.i18n.t("panel.wizard.render_error.body")}</p>
      <div class="actions">
        <button
          class="cta text"
          type="button"
          @click=${() => {
            this._broken = null;
            this.requestUpdate();
          }}
        >
          ${this.i18n.t("panel.common.action.retry")}
        </button>
        <button class="cta text" type="button" @click=${() => this.actions.cancel()}>
          ${this.i18n.t("panel.wizard.action.end")}
        </button>
      </div>
    </div>`;
  }

  private _fail(error: unknown): void {
    this._broken = error;
    if (!this._reported) {
      this._reported = true;
      console.error("MyHOME panel: the guided calibration could not be drawn", error);
    }
  }
}

if (!customElements.get("myhome-wizard")) {
  customElements.define("myhome-wizard", MyHomeWizard);
}
