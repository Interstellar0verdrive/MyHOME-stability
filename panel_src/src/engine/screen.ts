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

import { LitElement, css, html, nothing, type TemplateResult } from "lit";
import { styleMap } from "lit/directives/style-map.js";

import { I18n } from "./i18n";
import { renderMarkdown } from "./markdown";
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
  image?: { src: string; alt: string; size?: string; pos?: string };
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

// The drawing is the one place a step's model reaches CSS, and CSS built by joining
// strings is CSS somebody else can add declarations to: a `src` carrying `");` would turn
// the illustration slot into any rule it liked, including a full-screen overlay and a
// request to a host nobody chose. So the three values are checked here, at the point of
// use, rather than trusted from wherever the model was built - `splitLeadingImage` already
// refuses an image from outside `/myhome_static/`, and this says the same thing again where
// it cannot be skipped. They are then set through `styleMap`, which writes one property at
// a time and cannot grow a second declaration.

/** A path this integration serves, and nothing else: no scheme, no host, no quoting. */
const SAFE_SRC = /^\/myhome_static\/[A-Za-z0-9._~\-/]+$/;
/** ...and no climbing back out of it with dot segments. */
const DOT_SEGMENT = /(^|\/)\.\.?(\/|$)/;
/** `background-size` / `background-position`: lengths, percentages and the CSS keywords. */
const SAFE_VALUE = /^[A-Za-z0-9 %.,\-]+$/;

const drawingStyle = (
  image: NonNullable<ScreenModel["image"]>,
): Record<string, string> | null => {
  if (!SAFE_SRC.test(image.src) || DOT_SEGMENT.test(image.src)) {
    return null;
  }
  const size = image.size && SAFE_VALUE.test(image.size) ? image.size : "100% auto";
  const position = image.pos && SAFE_VALUE.test(image.pos) ? image.pos : "50% 60%";
  return {
    backgroundImage: `url("${image.src}")`,
    backgroundSize: size,
    backgroundPosition: position,
  };
};

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

      main {
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

        main {
          display: grid;
          grid-template-columns: minmax(0, 1fr) 400px;
          gap: 0 44px;
          align-items: start;
          max-width: 1080px;
          margin: 0 auto;
          padding: 24px 32px 48px;
        }

        /* The pos template has no operative column: one centred column at every width. */
        main.single {
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
      <main class=${single ? "single" : ""}>
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
      </main>
    </div>`;
  }
}

if (!customElements.get("myhome-screen")) {
  customElements.define("myhome-screen", MyHomeScreen);
}
