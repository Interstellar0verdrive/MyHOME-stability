// The screen engine: one data object, eight templates, one responsive law.
//
// **Why it exists in 0.6.0 at all.** The guided wizard moves into the panel in 0.7.0, not
// here. What is built here is the thing that would otherwise be built twice: the shape of
// a step. The wizard prototype (`Wizard Calibrazione.dc.html`) drives every one of its
// screens from a `steps()` table whose rows carry a `model:` field, and the eight values
// that field takes are the eight templates below. Writing the contract now, from that
// table, makes 0.7.0 a port rather than a redesign - and it gives 0.6.0 somewhere to put
// the screens it already needs (a welcome, a "not here" and an outcome are `lettura` and
// `esito`).
//
// **The responsive law lives here and nowhere else** (handoff, section 3):
//
// * **below 900 px** - one column, 480 px at most, the call to action in a fixed footer
//   with a 36 px gradient behind it and 230 px of bottom margin on the content so nothing
//   ever hides under it;
// * **900 px and up** - two columns, `minmax(0,1fr)` of text and drawing beside a 400 px
//   operative column, 44 px apart, 1080 px at most, and the right column sticky so the big
//   button keeps its place from one step to the next.
//
// Implemented in CSS media queries rather than a JavaScript width, so the switch happens
// at exactly 900 px, costs no resize listener, and is right on the first paint. The one
// exception the prototype makes is `pos`, a screen with no operative column at all, which
// stays a single centred column at every width.
//
// A screen never acts. It renders a model and fires `myhome-screen-action` with the action
// token the model gave it; what that token means belongs to whoever built the model.
//
// **No landmark is claimed here.** The two columns used to be a `<main>`, which reads as a
// layout element and is not one: a custom panel is rendered inside Home Assistant's own
// document, the shell owns whatever `main` and `banner` that document has, and a second
// `main` inside a panel is a page with two of them. The one landmark the panel declares is
// the named region in `main.ts` that holds everything it draws.

import { LitElement, css, html, nothing, type TemplateResult } from "lit";
import { styleMap } from "lit/directives/style-map.js";

import { I18n } from "./i18n";
import { renderMarkdown } from "./markdown";
import { drawingStyle, type ScreenImage } from "./safe-style";
import { buttonStyles, cardStyles, fieldStyles, srOnly, themeStyles } from "./theme";
import { renderLettura } from "../templates/lettura";
import { renderScelta } from "../templates/scelta";
import { renderPos } from "../templates/pos";
import { renderClick } from "../templates/click";
import { renderControllo } from "../templates/controllo";
import { renderMetro } from "../templates/metro";
import { renderRiepilogo } from "../templates/riepilogo";
import { renderEsito } from "../templates/esito";
import { templateStyles } from "../templates/styles";

/** The eight kinds of step, spelled as the wizard prototype spells them. */
export type ScreenTemplate =
  | "lettura"
  | "scelta"
  | "pos"
  | "click"
  | "controllo"
  | "metro"
  | "riepilogo"
  | "esito";

export interface ScreenAction {
  label: string;
  /** The token fired back; never a sentence, never a function. */
  action: string;
  disabled?: boolean;
  kind?: "primary" | "secondary" | "text" | "destructive";
}

export interface ScreenOption {
  title: string;
  meta?: string;
  action: string;
  chip?: string;
  /** The one currently chosen, drawn with a border and an inset ring so nothing moves. */
  current?: boolean;
}

export interface ScreenField {
  label: string;
  hint?: string;
  unit?: string;
  value: string;
  error?: string;
  placeholder?: string;
  /** The tape reading uses a 64 px field at 32 px; the smaller ones are 56 px at 26 px. */
  big?: boolean;
}

/** What the motor is doing, as the step was told - never as the panel worked it out. */
export interface ScreenPress {
  state: "idle" | "starting" | "moving" | "registered" | "problem";
  label: string;
  instruction?: string;
  motor?: string;
  position?: string;
  note?: string;
}

export interface ScreenProgress {
  text?: string;
  /** 0 to 1. */
  fraction: number;
  eta?: string;
  done?: boolean;
}

export interface ScreenSummaryRow {
  label: string;
  before?: string;
  after: string;
}

export interface ScreenSummary {
  rows: ScreenSummaryRow[];
  note?: string;
  /** The YAML block of the summary screen, shown as it would be written. */
  code?: string;
}

export interface ScreenModel {
  /** The translation key of the step, never a sentence. */
  id: string;
  model: ScreenTemplate;
  phase?: { label: string; index: number; count: number };
  title: string;
  /** Markdown, with any leading illustration already lifted into `image`. */
  body?: string;
  image?: ScreenImage;
  /** The handoff's "testo nuovo - da tradurre" badge. */
  newText?: boolean;
  primary?: ScreenAction;
  secondary?: ScreenAction[];
  options?: ScreenOption[];
  field?: ScreenField;
  progress?: ScreenProgress;
  press?: ScreenPress;
  summary?: ScreenSummary;
  outcome?: "saved" | "cancelled" | "expired" | "problem";
}

/** What a template is handed besides its model. */
export interface ScreenContext {
  i18n: I18n;
  fire: (action: string, value?: string) => void;
}

export class MyHomeScreen extends LitElement {
  static override properties = {
    model: { attribute: false },
    i18n: { attribute: false },
  };

  declare model: ScreenModel | null;
  declare i18n: I18n;

  constructor() {
    super();
    this.model = null;
    this.i18n = new I18n();
  }

  static override styles = [
    themeStyles,
    cardStyles,
    buttonStyles,
    fieldStyles,
    srOnly,
    templateStyles,
    css`
      :host {
        display: block;
        background: transparent;
      }

      .screen {
        width: 100%;
        max-width: 480px;
        margin: 0 auto;
        display: flex;
        flex-direction: column;
        position: relative;
      }

      .pane {
        flex: 1;
        padding: 16px 16px 230px;
      }

      .right {
        min-width: 0;
      }

      /*
       * The footer is fixed on a phone, with the gradient the handoff asks for so text
       * scrolling under it fades instead of colliding with it, and it stays above the home
       * indicator.
       */
      .footer {
        position: fixed;
        bottom: 0;
        left: 50%;
        transform: translateX(-50%);
        width: 100%;
        max-width: 480px;
        padding: 36px 16px calc(12px + env(safe-area-inset-bottom, 0px));
        background: linear-gradient(
          to top,
          var(--myhome-background) calc(100% - 36px),
          transparent
        );
        z-index: 25;
        display: flex;
        flex-direction: column;
        gap: 10px;
      }

      @media (min-width: 900px) {
        .screen {
          max-width: 100%;
        }

        .pane {
          display: grid;
          grid-template-columns: minmax(0, 1fr) 400px;
          gap: 0 44px;
          align-items: start;
          /*
           * "margin: 0 auto" centres the column, and in doing so it switches off the
           * cross-axis stretch a flex item would otherwise get - which left this element
           * as wide as its own text rather than as wide as the 1080 px the handoff fixes.
           * The explicit width says so.
           */
          width: 100%;
          max-width: 1080px;
          margin: 0 auto;
          padding: 24px 32px 48px;
        }

        /* The pos template has no operative column: one centred column at every width. */
        .pane.single {
          display: block;
          max-width: 560px;
        }

        .right {
          position: sticky;
          top: 76px;
        }

        .footer {
          position: static;
          transform: none;
          width: auto;
          max-width: none;
          padding: 0;
          background: none;
          margin-top: 20px;
        }
      }
    `,
  ];

  private _fire = (action: string, value?: string): void => {
    this.dispatchEvent(
      new CustomEvent("myhome-screen-action", {
        detail: { action, value, screen: this.model?.id ?? "" },
        bubbles: true,
        composed: true,
      }),
    );
  };

  private _renderOperative(model: ScreenModel, context: ScreenContext): TemplateResult | typeof nothing {
    switch (model.model) {
      case "scelta":
        return renderScelta(model, context);
      case "pos":
        return renderPos(model, context);
      case "click":
        return renderClick(model, context);
      case "controllo":
        return renderControllo(model, context);
      case "metro":
        return renderMetro(model, context);
      case "riepilogo":
        return renderRiepilogo(model, context);
      case "esito":
        return renderEsito(model, context);
      case "lettura":
        return renderLettura(model, context);
      default:
        return nothing;
    }
  }

  private _renderFooter(model: ScreenModel, context: ScreenContext): TemplateResult | typeof nothing {
    const secondary = model.secondary ?? [];
    if (!model.primary && secondary.length === 0) {
      return nothing;
    }
    return html`<div class="footer">
      ${model.primary
        ? html`<button
            class="big ${model.press?.state === "moving" ? "moving" : ""}"
            type="button"
            ?disabled=${model.primary.disabled}
            @click=${() => this._fire(model.primary!.action)}
          >
            ${model.primary.label}
          </button>`
        : nothing}
      ${secondary.map(
        (action) => html`<button
          class="cta ${action.kind === "text" ? "text" : "secondary"}"
          type="button"
          ?disabled=${action.disabled}
          @click=${() => context.fire(action.action)}
        >
          ${action.label}
        </button>`,
      )}
    </div>`;
  }

  protected override render(): TemplateResult | typeof nothing {
    const model = this.model;
    if (!model) {
      return nothing;
    }
    const context: ScreenContext = { i18n: this.i18n, fire: this._fire };
    const single = model.model === "pos";
    const drawing = model.image ? drawingStyle(model.image) : null;
    return html`<div class="screen">
      <div class="pane ${single ? "single" : ""}">
        <div class="text-column">
          ${model.phase
            ? html`<p class="phase">
                ${this.i18n.t("panel.screen.phase", {
                  phase: model.phase.label,
                  index: model.phase.index,
                  count: model.phase.count,
                })}
              </p>`
            : nothing}
          ${model.newText
            ? html`<p class="new-text">${this.i18n.t("panel.screen.new_text")}</p>`
            : nothing}
          <h1 class="screen-title">
            ${model.outcome ? html`<span class="outcome-icon ${model.outcome}" aria-hidden="true"></span>` : nothing}
            <span>${model.title}</span>
          </h1>
          ${drawing
            ? html`<div
                class="drawing"
                role="img"
                aria-label=${model.image?.alt ?? ""}
                style=${styleMap(drawing)}
              ></div>`
            : nothing}
          ${model.body ? html`<div class="prose">${renderMarkdown(model.body)}</div>` : nothing}
        </div>
        <div class="right">
          ${this._renderOperative(model, context)} ${this._renderFooter(model, context)}
        </div>
      </div>
    </div>`;
  }
}

if (!customElements.get("myhome-screen")) {
  customElements.define("myhome-screen", MyHomeScreen);
}
