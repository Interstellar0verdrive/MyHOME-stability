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
  /**
   * What the chip is saying, when it is one of the origins the rest of the panel colours.
   *
   * The choice of shutter carries the same origin chip the overview's rows do, and the
   * reason that chip is not grey there is the reason it must not be grey here: a list
   * whose point is "pick a representative one" is a list where *measured* and *inherited*
   * are the distinction being made. `origin-chip.ts` has the colours and why they are
   * those; this is the same vocabulary inside a template that cannot import an element.
   */
  chipTone?: "neutral" | "measured" | "adjusted";
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
  /**
   * Which keyboard a phone offers. A measurement wants the decimal pad; a profile name
   * wants letters, and a name field that opened a number pad would be a field nobody
   * could fill in on the device the calibration is actually done from.
   */
  inputMode?: "decimal" | "text";
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

/** A named block of rows: the side effects, or one shutter that follows the profile. */
export interface ScreenSummaryGroup {
  title: string;
  rows: ScreenSummaryRow[];
}

/** One disclosure of the review: what it says now, and whether it is open. */
export interface ScreenDisclosure {
  label: string;
  action: string;
  open: boolean;
}

export interface ScreenSummary {
  rows: ScreenSummaryRow[];
  note?: string;
  /** The YAML block of the summary screen, shown as it would be written. */
  code?: string;
  /** What the code block is: shown above it, so the block is never an unlabelled wall. */
  codeLabel?: string;
  /**
   * The rows behind "Show every value": the slat time and the two roll coefficients.
   *
   * They are absent rather than hidden when the disclosure is shut, because the principle
   * is that the model stays behind the flow - and a value in the DOM with `display: none`
   * on it is a value a screen reader still reads out.
   */
  more?: ScreenSummaryRow[];
  /** Values this calibration never measured and the save would change all the same. */
  sideEffects?: ScreenSummaryGroup;
  /** The other shutters that follow the profile, each with its own before and after. */
  affected?: ScreenSummaryGroup[];
  /** The sentences under the rows: the accuracy, the profile, where the values go. */
  lines?: string[];
  /** The buttons that open and shut the two blocks above. */
  disclose?: ScreenDisclosure[];
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
  /**
   * Sentences the panel adds under the step's own prose.
   *
   * The check of a verification is the one thing that uses them: the dialog's text says
   * how far out the shutter was and nothing else, and the numbers the check was made of -
   * where it was sent, what the tape read, what the model had predicted - are the answer
   * to "how do you know". They are lines and not a card because they belong to the
   * sentence above them.
   */
  lines?: string[];
  /** Something that happened around the step: an outside movement, a stale reading. */
  note?: { text: string; tone: "info" | "success" | "error" };
  /** A switch that belongs to this screen and to the browser, not to the session. */
  toggle?: { label: string; checked: boolean; action: string };
  /**
   * Another client is driving. The screen is the same one, without its controls, and with
   * one strip saying so and offering to take it over (SPEC §5.4).
   */
  readOnly?: { text: string; label: string; action: string };
  /** What a screen reader is told politely when this screen arrives. */
  announce?: string;
  /** …and what interrupts it: the motor starting, and a step that was abandoned. */
  alert?: string;
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

  /**
   * Where the keyboard lands when a step arrives: the title, or the big button.
   *
   * SPEC §5.7's rule, and the reason it is a method here rather than a `querySelector` in
   * the view: the two elements are inside this shadow root, and a caller that reached
   * through it would break the moment either of them moved. On a press screen the button
   * is the whole step - Space and Enter are the press - so focus goes there; everywhere
   * else it goes to the heading, which is what a reader needs read out first.
   */
  focusEntry(where: "title" | "primary"): boolean {
    const root = this.shadowRoot;
    if (!root) {
      return false;
    }
    const wanted =
      where === "primary"
        ? (root.querySelector("button.big:not([disabled])") as HTMLElement | null)
        : null;
    const target = wanted ?? (root.querySelector("h1.screen-title") as HTMLElement | null);
    if (!target) {
      return false;
    }
    target.focus();
    return true;
  }

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
            data-big
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
    // The illustrations the steps carry come out of the translation files, where their alt
    // text is empty - the dialog draws them inline, under prose that already describes
    // what they show. So they are decorative here rather than an image with no name on it:
    // `role="img"` with an empty label is a thing a screen reader stops at and says
    // nothing about.
    const labelled = (model.image?.alt ?? "") !== "";
    return html`<div class="screen">
      ${model.readOnly
        ? html`<div class="read-only" role="status">
            <span>${model.readOnly.text}</span>
            <button
              class="cta secondary"
              type="button"
              data-take-control
              @click=${() => this._fire(model.readOnly!.action)}
            >
              ${model.readOnly.label}
            </button>
          </div>`
        : nothing}
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
          <h1 class="screen-title" tabindex="-1">
            ${model.outcome ? html`<span class="outcome-icon ${model.outcome}" aria-hidden="true"></span>` : nothing}
            <span>${model.title}</span>
          </h1>
          ${drawing
            ? html`<div
                class="drawing"
                role=${labelled ? "img" : nothing}
                aria-label=${labelled ? (model.image?.alt ?? "") : nothing}
                aria-hidden=${labelled ? nothing : "true"}
                style=${styleMap(drawing)}
              ></div>`
            : nothing}
          ${model.body ? html`<div class="prose">${renderMarkdown(model.body)}</div>` : nothing}
          ${(model.lines ?? []).map((line) => html`<p class="aside">${line}</p>`)}
          ${model.note
            ? html`<div class="note ${model.note.tone}" role=${model.note.tone === "error" ? "alert" : "status"}>
                ${model.note.text}
              </div>`
            : nothing}
        </div>
        <div class="right">
          ${this._renderOperative(model, context)}
          ${model.toggle
            ? html`<label class="cue">
                <input
                  type="checkbox"
                  .checked=${model.toggle.checked}
                  @change=${(event: Event) =>
                    this._fire(
                      model.toggle!.action,
                      (event.target as HTMLInputElement).checked ? "on" : "off",
                    )}
                />
                <span>${model.toggle.label}</span>
              </label>`
            : nothing}
          ${this._renderFooter(model, context)}
        </div>
      </div>
    </div>`;
  }
}

if (!customElements.get("myhome-screen")) {
  customElements.define("myhome-screen", MyHomeScreen);
}
