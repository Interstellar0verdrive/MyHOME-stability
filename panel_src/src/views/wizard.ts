// `<myhome-wizard>` - the guided calibration's screen.
//
// One snapshot arrives, `wizard/model.ts` turns it into a `ScreenModel`, and
// `<myhome-screen>` draws it. Everything that is not "what does this step look like" lives
// here and nowhere else: the clock the motor line counts on, what the one field holds, the
// two disclosures of the review, the signal at the start, where the keyboard lands, and
// the question the ✕ asks.
//
// What was already real before the screens existed, because it is the part the v2 panel
// got wrong (SPEC §5.8, lesson 1):
//
// * **every drawing is inside a `try`, and so is the model.** An exception building the
//   model or rendering it shows the card below - which says the calibration is still
//   running, offers "Try again" and offers the robust way of ending it - instead of an
//   empty panel. It is logged once; the second identical stack trace tells nobody
//   anything;
// * **nothing on this path keeps the session alive.** The presence signal is
//   `SessionClient`'s own timer (`engine/session.ts`); this element cannot start it, stop
//   it or delay it, which is the whole point of the class having no DOM in it. The ten
//   repaints a second the motor line asks for are repaints and nothing else;
// * **a refusal always arrives with something to press.** `state.sessionError` carries the
//   recovery tokens the client worked out, and each becomes one button here. A screen that
//   says "Cancel failed" and nothing else is the silent failure with a sentence on it.
//
// **Two clocks, and neither of them measures anything.** The seconds beside "Motor" are
// `movement.started_at` - the server's instant - plus the time since, corrected by the
// difference this tab measured between its own clock and `server_time` when the snapshot
// arrived. It is drawn at about ten hertz so that it reads as a running number; no
// measurement is taken from it, and the press is timed by its arrival at the server
// (SPEC decision 15). The estimated position beside it is the shutter's own estimate out
// of `hass.states`, at about one hertz, and is a different claim from a different source.

import { LitElement, css, html, nothing, type TemplateResult } from "lit";

import { FocusReturn, FocusTrap, alertRegion, focusWhenPainted, liveRegion } from "../engine/a11y";
import { readCue, signalStart, writeCue } from "../engine/cue";
import { I18n } from "../engine/i18n";
import { MyHomeScreen } from "../engine/screen";
import { type SessionRecovery } from "../engine/session";
import {
  type SessionAction,
  type SessionSaveTarget,
  type SessionSnapshot,
  type SessionSubmit,
} from "../engine/session-contract";
import { type BusyAsk, type PanelState } from "../engine/store";
import { buttonStyles, cardStyles, srOnly, themeStyles } from "../engine/theme";
import { type WizardIntent } from "../engine/session";
import { type HomeAssistant } from "../types/ha";
import { coverOf, coverPickerModel } from "../components/cover-picker";
import { exitDialog, exitDialogStyles } from "../components/exit-dialog";
import {
  ACT,
  AGAIN,
  CHOOSE,
  CLAIM,
  CLOSE,
  CUE,
  OPEN_COVER,
  PICK,
  SAVE,
  SHOW_AFFECTED,
  SHOW_ALL,
  STOP,
  SUBMIT,
  screenModel,
} from "../wizard/model";
import { STEPPER, readStepperOpen, writeStepperOpen } from "../wizard/stepper";

// The element has to be referenced so the bundler keeps it: the template below names it as
// a tag and nothing else imports it.
void MyHomeScreen;

/** What the screen can ask the shell to do. */
export interface WizardActions {
  /** Read the session again. */
  refresh(): void;
  /** One step of the conversation, or the value of the step's form. */
  act(action: SessionAction | SessionSubmit, value?: string): void;
  /** The one verb that touches the shutter: stop it, and make this step repeatable. */
  stop(): void;
  /** Write the result, once, from the review. */
  save(target: SessionSaveTarget): void;
  /** End the session, through the four branches of SPEC §5.2. */
  cancel(): void;
  /**
   * Take the session from the client that owns it, and **stop there**: the screen comes
   * back with its actions live and the user presses the one they meant to press.
   */
  claim(): void;
  /** Take it and end it - the offer a refused "Cancel" makes, and only that one. */
  claimAndCancel(): void;
  /** End it whoever owns it. */
  force(): void;
  /** Open or shut the question the ✕ asks. It is in the store, because the ✕ is not here. */
  exit(open: boolean): void;
  /** Measure another shutter. */
  again(): void;
  /**
   * Open a session on the shutter the user just chose (lot F3).
   *
   * It is the shell's `calibrate`, the one road into a session, and it is here because the
   * choice of shutter is a screen of the wizard: pressing a row on it is the same gesture
   * as pressing "Misura di nuovo" on a shutter's card.
   */
  start(intent: WizardIntent): void;
  /**
   * Close every *Configure* dialog of this gateway and free the shutter (SPEC §3.10).
   *
   * Offered by the screen a refused `start` leaves, which is the wizard's half of the
   * banner's own offer - and asked about first, through `ask`.
   */
  endOther(): void;
  /** Put the question about the other holder on the screen, or take it back. */
  ask(question: BusyAsk): void;
  /** "Apri Configura": the one offer here that still leaves the panel. */
  openFlow(source: HTMLElement): void;
  /** The card of the shutter that was just calibrated. */
  openCover(cover: string): void;
  /** Back to the list. */
  back(): void;
}

const NO_ACTIONS: WizardActions = {
  refresh: () => undefined,
  act: () => undefined,
  stop: () => undefined,
  save: () => undefined,
  cancel: () => undefined,
  claim: () => undefined,
  claimAndCancel: () => undefined,
  force: () => undefined,
  exit: () => undefined,
  again: () => undefined,
  start: () => undefined,
  endOther: () => undefined,
  ask: () => undefined,
  openFlow: () => undefined,
  openCover: () => undefined,
  back: () => undefined,
};

/** How often the motor line is redrawn: ten times a second, as SPEC §5.4 asks. */
const TICK_MS = 100;

/**
 * What `_focusedFor` holds while the screen is the choice of shutter.
 *
 * A step of a session is named by its session, state and step; the choice belongs to no
 * session, so it needs a name of its own - and it needs one at all so that focus is moved
 * **once**, on arrival, and not again on every repaint.
 */
const PICK_PAINT = "pick";

export class MyHomeWizard extends LitElement {
  static override properties = {
    i18n: { attribute: false },
    state: { attribute: false },
    actions: { attribute: false },
    hass: { attribute: false },
  };

  declare i18n: I18n;
  declare state: PanelState;
  declare actions: WizardActions;
  /** Only for one number: the shutter's own estimate of where it is. */
  declare hass: HomeAssistant | null;

  /** Set by a drawing that threw, cleared by "Try again". */
  private _broken: unknown = null;
  private _reported = false;
  /** What the one field on the screen holds, and which step it was typed on. */
  private _typed: string | null = null;
  private _typedFor = "";
  /**
   * What the choice on the screen has selected, or `null` before anybody pressed a row.
   *
   * It belongs here for the same reason the field does: it is this tab's, it is thrown
   * away when the step changes, and the session never hears about it. A choice takes two
   * gestures - the row selects and "Continue" acts (live finding 3) - and this is the one
   * of the two that is not a verb.
   */
  private _chosen: string | null = null;
  /** The review's two disclosures. Shut on arrival: the model stays behind the flow. */
  private _showAll = false;
  private _showAffected = false;
  /** The signal at the start, as this browser remembers it. */
  private _cue = readCue();
  /**
   * Whether the collapsible stepper is open, as this tab remembers it.
   *
   * Shut on arrival unless this tab opened it earlier in the same session (live finding 29
   * and the design's own rule). It is here for the same reason the field and the choice are:
   * it is this tab's, the session never hears about it, and it survives the step changing -
   * a reader who opened the list to see where they are does not want it shut again by the
   * next screen.
   */
  private _stepperOpen = readStepperOpen();
  /** This tab's clock minus the server's, measured when the snapshot arrived. */
  private _skewMs = 0;
  private _skewFor = "";
  /** The ten-hertz repaint of the motor line, while something of the session is moving. */
  private _clock: number | null = null;
  private _painted = 0;
  /** What the last paint was about, so that focus and the signal fire once each. */
  private _focusedFor = "";
  private _signalledFor = "";
  /** The waiting screen's question, as it stood on the last paint. */
  private _askedFor: BusyAsk = null;
  /** The keyboard stays inside the exit question while it is open, and comes back after. */
  private _trap = new FocusTrap();
  private _return = new FocusReturn();
  private _trapped = false;

  constructor() {
    super();
    this.i18n = new I18n();
    this.state = {} as PanelState;
    this.actions = NO_ACTIONS;
    this.hass = null;
  }

  static override styles = [
    themeStyles,
    cardStyles,
    buttonStyles,
    srOnly,
    exitDialogStyles,
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

  override connectedCallback(): void {
    super.connectedCallback();
    this.addEventListener("keydown", this._onKey);
  }

  override disconnectedCallback(): void {
    this.removeEventListener("keydown", this._onKey);
    this._stopClock();
    this._trap.release();
    this._trapped = false;
    super.disconnectedCallback();
  }

  protected override render(): TemplateResult {
    if (this._broken) {
      return this._renderBroken();
    }
    try {
      return html`${this._renderSession()}${this._renderTrouble()}${this._renderExit()}`;
    } catch (error) {
      // Caught here rather than left to Lit, because what Lit does with it is leave the
      // screen half-painted. The flag makes the next paint the error card, which is a
      // screen the user can act on.
      this._fail(error);
      return this._renderBroken();
    }
  }

  protected override updated(): void {
    const session = this.state.session ?? null;
    this._followClock(session);
    this._followExit();
    this._followBusy();
    if (this._broken) {
      return;
    }
    if (!session) {
      // The choice of shutter is a screen of this wizard like any other, so the keyboard
      // lands on its heading too (SPEC §5.7). Without this, pressing "Misura una
      // tapparella" on the overview left focus on a button that is no longer in the
      // document, which is the top of the page for whoever is using the keyboard.
      if (this._focusedFor !== PICK_PAINT) {
        this._focusedFor = PICK_PAINT;
        // A fresh arrival on the list: nothing is selected, whatever the screen before it
        // had chosen.
        this._chosen = null;
        const screen = this.shadowRoot?.querySelector("myhome-screen") as MyHomeScreen | null;
        void screen?.updateComplete.then(() => screen.focusEntry("title"));
      }
      return;
    }
    const here = `${session.session_id}:${session.state}:${session.step ?? ""}`;
    if (here !== this._focusedFor) {
      this._focusedFor = here;
      // SPEC §5.7: the title, except where the step *is* the button - Space and Enter
      // press it, and a user who had to Tab to it would have missed the moment.
      //
      // After the screen's own update and not in this one: a child element's shadow root
      // is painted after its parent's, so the heading this is aiming at does not exist yet
      // when `updated()` runs here. Asked for before it is drawn, focus stays wherever it
      // was - which on the first step of a calibration is the top of the document.
      const screen = this.shadowRoot?.querySelector("myhome-screen") as MyHomeScreen | null;
      const where = session.substate === "awaiting_endpoint" ? "primary" : "title";
      void screen?.updateComplete.then(() => screen.focusEntry(where));
    }
    // The motor really has begun: the transition to `awaiting_endpoint` is the echo of the
    // actuator and nothing this browser worked out (SPEC §4.3).
    const moving = `${session.session_id}:${session.substate === "awaiting_endpoint" ? session.step : ""}`;
    if (session.substate === "awaiting_endpoint" && moving !== this._signalledFor) {
      this._signalledFor = moving;
      signalStart(this._cue);
    }
  }

  /** The screen of the step, built from the snapshot and from nothing else. */
  private _renderSession(): TemplateResult {
    const session: SessionSnapshot | null = this.state.session ?? null;
    if (!session) {
      return this._renderPick();
    }
    this._rememberField(session);
    const model = screenModel(session, {
      i18n: this.i18n,
      now: Date.now(),
      skewMs: this._skew(session),
      typed: this._typed,
      position: this._position(session),
      readOnly: this._readOnly(session),
      showAll: this._showAll,
      showAffected: this._showAffected,
      cue: this._cue,
      selected: this._chosen,
      profiles: this.state.overview?.profiles ?? [],
      stepperOpen: this._stepperOpen,
    });
    return html`<div data-wizard>
      ${liveRegion(model.announce ?? "")}${alertRegion(model.alert ?? "")}
      <myhome-screen
        .model=${model}
        .i18n=${this.i18n}
        @myhome-screen-action=${this._onScreenAction}
      ></myhome-screen>
    </div>`;
  }

  /**
   * No session on the gateway: the choice of which shutter to measure (SPEC §5.1).
   *
   * This is what the address alone produces - a reload, a pasted link, "Calibra un'altra
   * tapparella" - and it is a screen and not an instruction: nothing moves until a row is
   * pressed. The list is `overview.covers`, which the server has already narrowed to the
   * shutters a travel model applies to.
   */
  private _renderPick(): TemplateResult {
    const covers = this.state.overview?.covers ?? [];
    if (covers.length === 0) {
      // A gateway whose shutters all report their own position: there is nothing here to
      // calibrate, and the overview's own sentence says so in every language already.
      return html`<div class="card" data-wizard-empty>
        <h2>${this.i18n.t("panel.overview.no_basic_covers_title")}</h2>
        <p>${this.i18n.t("panel.overview.no_basic_covers")}</p>
        <div class="actions">
          <button class="cta text" type="button" @click=${() => this.actions.back()}>
            ${this.i18n.t("panel.common.action.back")}
          </button>
        </div>
      </div>`;
    }
    const model = coverPickerModel(this.i18n, covers, this._chosen);
    // **The banner is not drawn on this route**, and this is the one screen of it where
    // that costs something: offering twelve shutters of a gateway that is already holding
    // one is offering a refusal. So the same card the refusal would leave is drawn
    // *before* the list, which is the guarantee the banner's own comment claims - the
    // user meets the condition rather than discovering it by pressing.
    return html`<div data-wizard-pick>
      ${this.state.overview?.measuring ? this._renderBusy(null) : nothing}
      ${liveRegion(model.announce ?? "")}
      <myhome-screen
        .model=${model}
        .i18n=${this.i18n}
        @myhome-screen-action=${this._onScreenAction}
      ></myhome-screen>
    </div>`;
  }

  /**
   * Which of the two clients this tab is.
   *
   * Off the snapshot rather than off the heartbeat: ownership only ever changes on a verb
   * that does something, and every one of those produces a new snapshot (contract §11.1,
   * amended). A snapshot with no owner at all is not read-only - nobody is holding the
   * tape, and the first act takes the session.
   */
  private _readOnly(session: SessionSnapshot): boolean {
    const owner = session.owner?.client_id;
    return owner !== undefined && owner !== this.state.clientId;
  }

  /** The shutter's own estimate of where it is, when Home Assistant has one. */
  private _position(session: SessionSnapshot): number | null {
    const entity = session.cover?.entity_id;
    const value = entity ? this.hass?.states?.[entity]?.attributes?.current_position : undefined;
    return typeof value === "number" && Number.isFinite(value) ? value : null;
  }

  /**
   * How far this tab's clock is from the server's, measured once per snapshot.
   *
   * Memoised in `render` on purpose: the difference is a property of the snapshot that
   * just arrived, and recomputing it on every one of the ten repaints a second would make
   * the elapsed time stand still. A `server_time` that will not parse leaves it at zero,
   * which shows this tab's own clock - wrong by whatever the two disagree, and never
   * wrong by an hour of counting.
   */
  private _skew(session: SessionSnapshot): number {
    const stamp = `${session.session_id}:${session.revision}`;
    if (stamp !== this._skewFor) {
      this._skewFor = stamp;
      const server = Date.parse(session.server_time);
      this._skewMs = Number.isNaN(server) ? 0 : Date.now() - server;
    }
    return this._skewMs;
  }

  /**
   * The field opens on what the step suggests, and keeps what was typed until the step
   * changes.
   *
   * Keeping it across revisions is the point: a reading the backend refused comes back as
   * the same step with `form.error` on it, and a field emptied under a refusal is a field
   * that makes the reader measure the wall again.
   */
  private _rememberField(session: SessionSnapshot): void {
    const form = session.form;
    const here = `${session.session_id}:${session.step ?? ""}:${form?.field ?? ""}`;
    if (here === this._typedFor) {
      return;
    }
    this._typedFor = here;
    this._chosen = null;
    this._showAll = false;
    this._showAffected = false;
    const suggested = form && form.kind !== "choice" ? form.suggested : null;
    this._typed =
      suggested === null || suggested === undefined
        ? ""
        : typeof suggested === "number"
          ? this.i18n.number(suggested, 1)
          : suggested;
  }

  /**
   * The keyboard, while the exit question is open.
   *
   * It is a real confirmation - two buttons, one of which throws three minutes of
   * measurements away - so Tab stays inside it and focus comes back to whatever opened it
   * when it closes. `FocusTrap` is the panel's own, the same one the review sheet and the
   * profile choice use.
   */
  private _followExit(): void {
    const open = Boolean(this.state.wizardExit);
    if (open === this._trapped) {
      return;
    }
    this._trapped = open;
    if (!open) {
      this._trap.release();
      this._return.restore();
      return;
    }
    this._return.remember(
      (this.getRootNode() as ShadowRoot | Document | null as DocumentOrShadowRoot | null)
        ?.activeElement ?? null,
    );
    const dialog = this.shadowRoot?.querySelector("[data-exit-dialog]") as HTMLElement | null;
    if (dialog) {
      this._trap.hold(dialog);
    }
  }

  /**
   * The keyboard follows the waiting screen's question, and comes back when it is answered.
   *
   * The question **replaces** the offers in the same card, so the button that was just
   * pressed leaves the document and focus would otherwise fall to `<body>` - on a card
   * whose whole job is to be answered.
   */
  private _followBusy(): void {
    const ask = this.state.busy?.ask ?? null;
    if (ask === this._askedFor) {
      return;
    }
    const before = this._askedFor;
    this._askedFor = ask;
    const root = this.shadowRoot;
    if (ask) {
      focusWhenPainted(() => root?.querySelector('[data-busy="confirm"]') as HTMLElement | null);
      return;
    }
    if (before) {
      focusWhenPainted(
        () => root?.querySelector('[data-busy="end-other"]') as HTMLElement | null,
      );
    }
  }

  /** The ten-hertz repaint, running only while something of the session is moving. */
  private _followClock(session: SessionSnapshot | null): void {
    const running = session?.movement?.started_at != null && !this._broken;
    if (running) {
      this._startClock();
    } else {
      this._stopClock();
    }
  }

  private _startClock(): void {
    if (this._clock !== null) {
      return;
    }
    const frame = (globalThis as { requestAnimationFrame?: (cb: () => void) => number })
      .requestAnimationFrame;
    if (typeof frame !== "function") {
      return;
    }
    const loop = (): void => {
      this._clock = frame(loop);
      const now = Date.now();
      if (now - this._painted < TICK_MS) {
        return;
      }
      this._painted = now;
      this.requestUpdate();
    };
    this._clock = frame(loop);
  }

  private _stopClock(): void {
    if (this._clock === null) {
      return;
    }
    const cancel = (globalThis as { cancelAnimationFrame?: (id: number) => void })
      .cancelAnimationFrame;
    if (typeof cancel === "function") {
      cancel(this._clock);
    }
    this._clock = null;
  }

  /** Escape is the ✕: it asks the question, and on the question it answers "keep going". */
  private _onKey = (event: KeyboardEvent): void => {
    if (event.key !== "Escape") {
      return;
    }
    if (!this.state.session) {
      return;
    }
    event.stopPropagation();
    this.actions.exit(!this.state.wizardExit);
  };

  private _onScreenAction = (event: Event): void => {
    const detail = (event as CustomEvent<{ action: string; value?: string }>).detail;
    const action = detail?.action ?? "";
    const value = detail?.value;
    if (action.startsWith(CHOOSE)) {
      // A row of a choice: selected, and nothing more. The screen repaints so that the
      // chosen one is marked and "Continue" comes alive; nothing is sent.
      this._chosen = action.slice(CHOOSE.length);
      this.requestUpdate();
      return;
    }
    if (action === "field") {
      // Recorded and **not** repainted: the characters are already in the field, and
      // writing them back into it on every keystroke is how a caret ends up at the end of
      // a number somebody is editing in the middle.
      this._typed = value ?? "";
      return;
    }
    if (action === SUBMIT) {
      this.actions.act("submit", this._typed ?? "");
      return;
    }
    if (action.startsWith(PICK)) {
      this.actions.act("submit", action.slice(PICK.length));
      return;
    }
    // The choice of shutter, which is the one screen here that has no session behind it:
    // pressing a row is what opens one, with the shutter in the intention and never in
    // the address.
    const picked = coverOf(action);
    if (picked !== null) {
      const cover = (this.state.overview?.covers ?? []).find((one) => one.unique_id === picked);
      this.actions.start({ cover: picked, name: cover?.name });
      return;
    }
    if (action.startsWith(ACT)) {
      this.actions.act(action.slice(ACT.length) as SessionAction);
      return;
    }
    if (action.startsWith(SAVE)) {
      this.actions.save(action.slice(SAVE.length) as SessionSaveTarget);
      return;
    }
    if (action === STOP) {
      this.actions.stop();
      return;
    }
    if (action === CLAIM) {
      this.actions.claim();
      return;
    }
    if (action === CUE) {
      this._cue = value !== "off";
      writeCue(this._cue);
      this.requestUpdate();
      return;
    }
    if (action === STEPPER) {
      // Orientation and nothing else: opening the list sends nothing to the session, and
      // the only thing that changes is this tab's own paint.
      this._stepperOpen = !this._stepperOpen;
      writeStepperOpen(this._stepperOpen);
      this.requestUpdate();
      return;
    }
    if (action === SHOW_ALL) {
      this._showAll = !this._showAll;
      this.requestUpdate();
      return;
    }
    if (action === SHOW_AFFECTED) {
      this._showAffected = !this._showAffected;
      this.requestUpdate();
      return;
    }
    if (action === AGAIN) {
      this.actions.again();
      return;
    }
    if (action === OPEN_COVER) {
      const cover = this.state.session?.cover?.unique_id;
      if (cover) {
        this.actions.openCover(cover);
      }
      return;
    }
    if (action === CLOSE) {
      this.actions.back();
    }
  };

  /** The question the ✕ asks, and the only answer that throws measurements away. */
  private _renderExit(): TemplateResult | typeof nothing {
    if (!this.state.wizardExit) {
      return nothing;
    }
    return exitDialog({
      i18n: this.i18n,
      onStay: () => this.actions.exit(false),
      onLeave: () => {
        this.actions.exit(false);
        this.actions.cancel();
      },
    });
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
    if (trouble.error.translation_key === "already_calibrating") {
      // …unless the choice of shutter has already drawn it: two identical cards saying the
      // same thing is one card and a copy of it.
      return this.state.session || !this.state.overview?.measuring
        ? this._renderBusy(trouble)
        : nothing;
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
      ${trouble.recovery.includes("wait")
        ? html`<p class="soft">
            ${freed
              ? this.i18n.t("panel.wizard.trouble.freed", { time: freed })
              : this.i18n.t("panel.wizard.trouble.freed_later")}
          </p>`
        : nothing}
      <div class="actions">
        ${trouble.recovery.map((token) => this._recoveryButton(token))}
      </div>
    </div>`;
  }

  /**
   * The gateway is busy: the waiting screen, with the same offers the banner makes.
   *
   * `start` is refused with `already_calibrating` whenever somebody is already holding a
   * shutter of this gateway, and `{by}` says who - which is the only thing that decides
   * what can be offered. A bare refusal here would be the one screen of the wizard with
   * nothing on it to do, on the one occasion a user arrives at it by pressing a button.
   *
   * * `panel` - another panel or another tab is driving one: it can be read, so the way on
   *    is to go and look at it;
   * * `other` - a *Configure* dialog: it can be closed from here, after the question that
   *    says what closing it costs, or opened;
   * * `reserved` - the gateway is reserved for a run that is about to start, or the 0.4.2
   *    action is holding it: there is nothing to close, only to wait for.
   */
  private _renderBusy(trouble: NonNullable<PanelState["sessionError"]> | null): TemplateResult {
    const placeholders = trouble?.error.translation_placeholders ?? {};
    const held = this.state.overview?.measuring ?? null;
    const cover = placeholders.cover ?? held?.name ?? this.state.wizardIntent?.name ?? "";
    // **An unknown `by` waits; it never offers to close somebody's dialog.** `end_other`
    // aborts every options flow of the gateway and can reload the integration, so a
    // placeholder that did not arrive - an older backend, a refusal that came another way
    // - must not choose it by default. `reserved` says to wait, and waiting is never wrong.
    //
    // With no refusal at all (the card drawn over the choice of shutter) there is no
    // placeholder to be missing: who is holding it is read off the gateway, exactly as the
    // banner reads it, and "the dialog or the action" is a distinction only `end_other`
    // can settle.
    const by = this.state.busy.service
      ? "reserved"
      : trouble === null
        ? (this.state.overview?.session ? "panel" : "other")
        : (placeholders.by ?? "reserved");
    // "Another panel or another tab" has to be true: `already_calibrating` is raised for
    // *any* session of the gateway, this tab's own included - which is reachable, because
    // opening a shutter's card and pressing "Misura di nuovo" while this very tab is
    // measuring another one is a thing a person does.
    const mine = this.state.overview?.session?.owner === this.state.clientId;
    const body =
      by === "panel"
        ? mine
          ? this.i18n.t("panel.wizard.busy.here", { cover })
          : this.i18n.t("panel.wizard.busy.panel", { cover })
        : by === "other"
          ? this.i18n.t("panel.wizard.busy.other", { cover })
          : this.i18n.t("panel.wizard.busy.service");
    if (this.state.busy.ask === "end_other") {
      return html`<div class="card problem" role="alert" data-session-busy>
        <h2>${this.i18n.t("panel.wizard.busy.title")}</h2>
        <p data-busy-question>${this.i18n.t("panel.wizard.busy.end_other_confirm")}</p>
        <div class="actions">
          <button
            class="cta text"
            type="button"
            data-busy="confirm"
            @click=${() => this.actions.endOther()}
          >
            ${this.i18n.t("panel.wizard.busy.end_other")}
          </button>
          <button
            class="cta text"
            type="button"
            data-busy="keep"
            @click=${() => this.actions.ask(null)}
          >
            ${this.i18n.t("panel.common.action.cancel")}
          </button>
        </div>
      </div>`;
    }
    return html`<div class="card problem" role="alert" data-session-busy>
      <h2>${this.i18n.t("panel.wizard.busy.title")}</h2>
      <p>${body}</p>
      <div class="actions">
        ${by === "panel"
          ? html`<button
              class="cta text"
              type="button"
              data-busy="resume"
              @click=${() => this.actions.refresh()}
            >
              ${this.i18n.t("panel.banner.measuring.action.resume")}
            </button>`
          : nothing}
        ${by === "other"
          ? html`<button
                class="cta text"
                type="button"
                data-busy="end-other"
                @click=${() => this.actions.ask("end_other")}
              >
                ${this.i18n.t("panel.wizard.busy.end_other")}
              </button>
              <button
                class="cta text"
                type="button"
                data-busy="configure"
                @click=${(event: Event) =>
                  this.actions.openFlow(event.currentTarget as HTMLElement)}
              >
                ${this.i18n.t("panel.common.action.configure")}
              </button>`
          : nothing}
        <button class="cta text" type="button" data-busy="back" @click=${() => this.actions.back()}>
          ${this.i18n.t("panel.common.action.back")}
        </button>
      </div>
    </div>`;
  }

  /**
   * One token, one button - except `wait`, which is the one token with nothing to press and
   * is therefore always drawn as the sentence above instead. That pairing is what makes the
   * card impossible to leave empty: every other token is a button, and `wait` is a line.
   */
  private _recoveryButton(token: SessionRecovery): TemplateResult | typeof nothing {
    if (token === "wait") {
      return nothing;
    }
    const label =
      token === "claim"
        ? this.i18n.t("panel.wizard.action.claim")
        : token === "claim_cancel"
          ? this.i18n.t("panel.wizard.action.claim_cancel")
          : token === "force"
            ? this.i18n.t("panel.wizard.action.force")
            : this.i18n.t("panel.common.action.retry");
    const press =
      token === "claim"
        ? () => this.actions.claim()
        : token === "claim_cancel"
          ? () => this.actions.claimAndCancel()
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
    // A screen that cannot be drawn is a screen that cannot count seconds either, and a
    // loop asking for a repaint that throws every time is a loop nobody can read past.
    this._stopClock();
    // …and the error card is the whole of the next paint, so the exit question goes with
    // the rest of it. Left alone, `_followExit` would see the flag it left behind, decide
    // nothing had changed, and hold the keyboard inside a dialog that is no longer in the
    // document - on the one screen whose whole job is to offer a way on.
    this._trap.release();
    this._trapped = false;
    if (!this._reported) {
      this._reported = true;
      console.error("MyHOME panel: the guided calibration could not be drawn", error);
    }
  }
}

if (!customElements.get("myhome-wizard")) {
  customElements.define("myhome-wizard", MyHomeWizard);
}
