// The overview: every shutter of one gateway, grouped by the profile it follows, and the
// three ways of moving one to another group.
//
// This is the prototype (`Prototipo Assegnazione.dc.html`, `vista: panoramica`) translated
// into Lit, and the prototype is the specification: its measurements, its colours and its
// states are transcribed rather than redesigned. What is **not** transcribed is its
// arithmetic - `rescale`, `effKeys`, `originLabel` are a second implementation of
// `resolve_cover_config`, and two implementations of a travel model are two answers. Every
// number and every origin on this screen, the review panel's "after" column included,
// arrives from the server.
//
// **One shadow root.** Every group and every row lives in this element's, which is what
// makes a hit test during a drag and a FLIP over the whole list possible with one query;
// eight separate custom elements would have broken both. It is also why this file is long:
// the alternative was a component boundary in the middle of a gesture.
//
// **Nothing here writes.** The gestures produce pending changes in the store; the element
// that owns the socket (`main.ts`) is the only thing that calls the API, through the
// `AssignActions` it hands down. So "what does this screen change" has an answer that is
// one interface long, and a view cannot quietly acquire a second way to reach a shutter.
//
// The search box and the room select are client-side, over `overview.covers`, and the room
// comes from `area` - resolved server-side out of the entity and device registries, and
// `null` for a shutter nobody filed anywhere. Nothing groups, sorts or filters on an area
// being present.

import { LitElement, css, html, nothing, type PropertyValues, type TemplateResult } from "lit";

import { FocusTrap } from "../engine/a11y";
import {
  appendedToGroup,
  effectiveProfile,
  movedTo,
  orderedCovers,
  pendingFor,
  routeLabel,
} from "../engine/assign";
import { DragController, flipPlay, flipStart, type DropTarget } from "../engine/dnd";
import { I18n } from "../engine/i18n";
import { renderMarkdown } from "../engine/markdown";
import { type WizardIntent } from "../engine/session";
import { initialState, type PanelState } from "../engine/store";
import { buttonStyles, cardStyles, fieldStyles, themeStyles } from "../engine/theme";
import { type CoverRow, type Overview, type ProfileRow } from "../engine/ws";
import { FLOW_URL } from "../engine/flow";
import { coverRowStyles } from "../components/cover-row";
import { dialogStyles, profileDialog } from "../components/profile-dialog";
import {
  groupAttr,
  groupCard,
  groupCardStyles,
  groupKeyOf,
  type PanelGroup,
} from "../components/group-card";
import { originChipStyles } from "../components/origin-chip";
import { reviewPanel, reviewPanelStyles } from "../components/review-panel";
import {
  applyingStrip,
  armedStrip,
  dropZone,
  pendingBar,
  snackStrip,
  stripStyles,
} from "../components/strips";

// The integration page, which is the way to "Configura" and therefore to every
// measurement. It lives in `engine/flow.ts` with the rest of the opener; it is re-exported
// here because this is where it was first used and every caller already imports it.
export { FLOW_URL } from "../engine/flow";

/**
 * Everything this screen can ask for. Implemented once, in `main.ts`, beside the socket.
 *
 * The gestures are not in here: a drag is not an action, it is a way of arriving at one.
 * What is in here is every change of state that outlives the gesture - a pending change, a
 * discard, a confirm, an undo - which is also exactly the list a reviewer has to check.
 */
export interface AssignActions {
  search: (value: string) => void;
  room: (value: string) => void;
  clearFilters: () => void;
  openCover: (uniqueId: string) => void;
  openProfile: (name: string) => void;
  /** A gesture ended on a destination: record it, or withdraw the change it undoes. */
  assign: (cover: CoverRow, to: string | null) => void;
  withdraw: (cover: CoverRow) => void;
  discardAll: () => void;
  /** A drop that only moved a row inside its group: the order, and nothing else. */
  reorder: (order: string[]) => void;
  /** The order a drop implies, kept with the batch while there is one to keep it with. */
  setOrder: (order: string[]) => void;
  drag: (cover: CoverRow | null) => void;
  over: (target: DropTarget | null) => void;
  arm: (cover: CoverRow | null) => void;
  dialog: (cover: CoverRow | null) => void;
  review: (open: boolean) => void;
  height: (cover: string, value: string) => void;
  toggleShowAll: () => void;
  confirm: () => void;
  undo: () => void;
  announce: (message: string) => void;
  /**
   * The guided calibration, in the panel (SPEC §6).
   *
   * `null` is "open the wizard with nothing in mind", which is the choice of shutter;
   * an intention names the shutter and, from the shutter's own card, the path and the
   * scope. Either way it is the shell that knows how a session is opened, and the
   * intention travels as an object and never as an address (SPEC §5.1).
   */
  calibrate: (intent: WizardIntent | null) => void;
}

export class MyHomeOverview extends LitElement {
  static override properties = {
    i18n: { attribute: false },
    state: { attribute: false },
    actions: { attribute: false },
  };

  declare i18n: I18n;
  declare state: PanelState;
  declare actions: AssignActions;

  private _trap = new FocusTrap();
  private _returnTo: HTMLElement | null = null;
  private _returnToRow: string | null = null;
  private _drag: DragController;

  constructor() {
    super();
    this.i18n = new I18n();
    this.state = initialState({ view: "overview", params: {}, path: "/" });
    this.actions = {} as AssignActions;
    this._drag = new DragController({
      root: () => this.renderRoot as ShadowRoot,
      blocked: () => this._locked,
      narrow: () => this._narrow,
      onArm: (cover) => {
        const row = this._cover(cover);
        if (row) {
          this.actions.arm(row);
        }
      },
      onStart: (cover) => {
        const row = this._cover(cover);
        if (!row) {
          return;
        }
        this._drag.ghost(row.name, this.renderRoot as ShadowRoot);
        this.actions.drag(row);
      },
      onOver: (target) => this.actions.over(target),
      onEnd: (commit) => this._endDrag(commit),
    });
  }

  static override styles = [
    themeStyles,
    cardStyles,
    buttonStyles,
    fieldStyles,
    originChipStyles,
    coverRowStyles,
    groupCardStyles,
    stripStyles,
    dialogStyles,
    reviewPanelStyles,
    css`
      :host {
        display: block;
        background: transparent;
      }

      .intro {
        margin: 8px 0 4px;
        max-width: 72ch;
      }

      .intro p {
        margin: 0 0 8px;
        line-height: 1.55;
      }

      .counts {
        margin: 0 0 16px;
        color: var(--myhome-text-soft);
      }

      .controls {
        display: flex;
        gap: 12px;
        align-items: center;
        flex-wrap: wrap;
        margin: 0 0 16px;
      }

      .controls .search {
        flex: 1 1 220px;
        max-width: 340px;
      }

      .controls .spacer {
        flex: 1 1 auto;
      }

      /*
       * The select draws its own arrow: only with appearance stripped does it take the
       * theme's own background and text colours, and the native arrow goes with it.
       *
       * The prototype drew the replacement as an SVG data URI with a fixed grey painted
       * into it. A data URI cannot read a CSS variable, so that grey would be the one
       * literal colour in the panel and the same grey in both themes - which is the thing
       * the handoff's first rule forbids. The chevron here is two borders on a wrapper's
       * pseudo-element instead, in the theme's own secondary text colour.
       */
      .select-wrap {
        position: relative;
        display: inline-flex;
      }

      .select-wrap::after {
        content: "";
        position: absolute;
        right: 13px;
        top: 50%;
        width: 7px;
        height: 7px;
        border-right: 1.6px solid var(--myhome-text-soft);
        border-bottom: 1.6px solid var(--myhome-text-soft);
        border-radius: 1px;
        transform: translateY(-70%) rotate(45deg);
        pointer-events: none;
      }

      select.field {
        appearance: none;
        padding-right: 36px;
      }

      a.cta {
        display: inline-flex;
        align-items: center;
        text-decoration: none;
      }

      .welcome {
        max-width: 640px;
        margin: 48px auto;
        padding: 32px;
      }

      .welcome h2 {
        margin: 0 0 12px;
        font-size: 22px;
        font-weight: 500;
      }

      .welcome p {
        margin: 0 0 8px;
        line-height: 1.55;
      }

      .welcome .soft {
        color: var(--myhome-text-soft);
        margin-bottom: 24px;
      }

      .welcome .after {
        margin: 12px 0 0;
        font-size: 13px;
        color: var(--myhome-text-soft);
      }

      .notice {
        padding: 16px;
        margin: 16px 0;
        font-size: 14px;
        line-height: 1.55;
      }

      .notice .actions {
        margin-top: 12px;
      }

      /*
       * Room under the fixed strips, so the last group is not permanently half-covered by
       * the pending bar. It is unconditional: a page whose height changed when a change
       * went pending would scroll under the reader on every drop.
       */
      .groups {
        margin-bottom: 96px;
      }

      /*
       * While a shutter is armed every card is collapsed to a 48 px title and every title
       * is a target, so the strip saying "tap the destination" must not be drawn on top of
       * one. Ninety-six pixels is enough for every other strip and not for this one, which
       * wraps to two lines on a phone. The list is being rebuilt at that moment anyway -
       * seven cards becoming seven titles - so the extra room costs no jump anybody sees.
       */
      .groups.targeting {
        margin-bottom: 120px;
      }

      /* The label that follows the pointer. Positioned by the drag, never by Lit. */
      .drag-ghost {
        position: fixed;
        left: 0;
        top: 0;
        z-index: 80;
        pointer-events: none;
        background: var(--myhome-card);
        color: var(--myhome-text);
        border: 1px solid var(--myhome-primary-ink);
        border-radius: 8px;
        box-shadow: var(--myhome-shadow);
        padding: 10px 14px;
        font-size: 14px;
        max-width: 260px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
    `,
  ];

  override connectedCallback(): void {
    super.connectedCallback();
    window.addEventListener("keydown", this._onKey);
    this._narrowQuery?.addEventListener("change", this._onWidth);
  }

  override disconnectedCallback(): void {
    super.disconnectedCallback();
    window.removeEventListener("keydown", this._onKey);
    this._narrowQuery?.removeEventListener("change", this._onWidth);
    // A drag that outlived its view would go on hit-testing a shadow root nothing renders.
    this._drag.stop();
    this._trap.release();
  }

  /**
   * Escape gives back whatever is held: the flight first, then the armed grab, then the
   * dialog, then the review panel. One key, one step back, in the order they were opened.
   */
  private _onKey = (event: KeyboardEvent): void => {
    if (event.key !== "Escape") {
      return;
    }
    if (this.state.drag) {
      this._drag.cancel();
      return;
    }
    if (this.state.armed) {
      this.actions.arm(null);
      return;
    }
    if (this.state.dialog) {
      this.actions.dialog(null);
      return;
    }
    if (this.state.review && !this.state.applying) {
      this.actions.review(false);
    }
  };

  /**
   * Focus into a panel when it opens and back to the control that opened it when it closes,
   * and a FLIP whenever the rows have moved. Both belong here rather than in the store: they
   * are about pixels that exist, and they can only be measured after Lit has painted.
   */
  protected override updated(changed: PropertyValues): void {
    // A measurement can start while a finger is still down. `main.ts` drops `state.drag`
    // the moment the event arrives, but the controller is a different object and would go
    // on moving its ghost until the finger came up - and nothing would have been said. The
    // flight is given back here, where the lock is first *drawn*, and the same call kills a
    // long press that would otherwise arm a shutter nobody may move.
    if (this._locked) {
      const flying = this._drag.dragging !== null;
      this._drag.stop();
      if (flying) {
        this.actions.announce(this.i18n.t("panel.assign.announce.drag_cancelled"));
      }
    }
    if (changed.has("state")) {
      const before = changed.get("state") as PanelState | undefined;
      this._manageFocus(before);
      if (this._flip) {
        const snapshot = this._flip;
        this._flip = null;
        requestAnimationFrame(() => flipPlay(this.renderRoot as ShadowRoot, snapshot));
      }
    }
  }

  private _flip: ReturnType<typeof flipStart> | null = null;

  /** Measure where every row is, so the next paint can animate from here. */
  private _beforeMove(): void {
    this._flip = flipStart(this.renderRoot as ShadowRoot);
  }

  private _manageFocus(before: PanelState | undefined): void {
    const open = this.state.dialog !== null || this.state.review;
    const wasOpen = (before?.dialog ?? null) !== null || (before?.review ?? false);
    if (open && !wasOpen) {
      const from = this._activeElement();
      this._returnTo = from;
      // ...and *which row* it was on, because the node itself may not survive the dialog.
      // Picking a profile moves the shutter into another group, and the row is rendered
      // there as a new element while the old one is thrown away: a remembered node would
      // be disconnected by the time focus was given back, and the keyboard user would be
      // returned to the top of the document - the exact thing this remembers to prevent.
      this._returnToRow = from?.closest("[data-row]")?.getAttribute("data-row") ?? null;
      requestAnimationFrame(() => {
        const root = this.renderRoot.querySelector<HTMLElement>("[data-focus-root]");
        if (root) {
          this._trap.hold(root);
        }
      });
      return;
    }
    if (!open && wasOpen) {
      this._trap.release();
      const back = this._returnTo;
      const row = this._returnToRow;
      this._returnTo = null;
      this._returnToRow = null;
      requestAnimationFrame(() => {
        // Walked rather than selected. A unique id is `00:03:50:aa:bb:cc-2-81`, which needs
        // escaping before it can go inside an attribute selector - and `CSS.escape` is a
        // global this file would then be depending on, inside a callback whose exception
        // nobody catches and whose only symptom is focus quietly landing on the document.
        // Comparing the attribute needs no global and cannot throw.
        const again = row
          ? [...this.renderRoot.querySelectorAll<HTMLElement>("[data-row]")]
              .find((element) => element.getAttribute("data-row") === row)
              ?.querySelector<HTMLElement>(".handle")
          : null;
        const target = again ?? (back?.isConnected ? back : null);
        target?.focus();
      });
    }
  }

  private _activeElement(): HTMLElement | null {
    const active = (this.renderRoot as ShadowRoot).activeElement;
    return active instanceof HTMLElement ? active : null;
  }

  // --- the model ----------------------------------------------------------------------
  private get _overview(): Overview | null {
    return this.state.overview;
  }

  /**
   * True while nothing may be moved.
   *
   * A measurement is running, or a write is in the air. Both are read here and not in the
   * handlers, because the rule is that the user is told *before* they try: the handles go
   * inactive and the banner is already on the screen, rather than a refusal arriving after
   * a gesture that looked as though it had worked.
   */
  private get _locked(): boolean {
    return this._overview?.measuring != null || this.state.applying;
  }

  /**
   * Below 600 px the gesture is press-and-tap: no drag, and the handles are not drawn.
   *
   * The query is kept and listened to rather than asked at render time. A window dragged
   * across 600 px changes what the CSS draws immediately and what the gestures do only at
   * the next state change, which left the two disagreeing - a handle back on the screen
   * that still armed a long press, or gone from it while a drag was still the way in.
   */
  private _narrowQuery: MediaQueryList | null =
    typeof matchMedia === "function" ? matchMedia("(max-width: 599px)") : null;

  private _onWidth = (): void => this.requestUpdate();

  private get _narrow(): boolean {
    return this._narrowQuery?.matches ?? false;
  }

  private _cover(uniqueId: string): CoverRow | undefined {
    return this._overview?.covers.find((cover) => cover.unique_id === uniqueId);
  }

  private get _covers(): CoverRow[] {
    const overview = this._overview;
    return overview ? orderedCovers(overview, this.state.order) : [];
  }

  /** The rooms the select offers: every area a shutter of this gateway really has. */
  private get _rooms(): string[] {
    const seen = new Set<string>();
    for (const cover of this._overview?.covers ?? []) {
      if (cover.area) {
        seen.add(cover.area);
      }
    }
    return Array.from(seen).sort((a, b) => a.localeCompare(b, this.i18n.language));
  }

  private _matches(cover: CoverRow): boolean {
    const needle = this.state.search.trim().toLowerCase();
    if (needle && !cover.name.toLowerCase().includes(needle)) {
      return false;
    }
    return !this.state.room || cover.area === this.state.room;
  }

  /** "«alte» → «alte_nuovo_test»": where this shutter came from and where it is going. */
  private _route = (cover: CoverRow): string => {
    const change = pendingFor(cover.unique_id, this.state.pending);
    if (!change) {
      return "";
    }
    return routeLabel(this.i18n, cover.profile ?? null, change.to);
  };

  /**
   * The values line of a profile's header. Four numbers, in the reader's own language, and
   * the words around them from the texts - never a template assembled here out of units.
   */
  private _valuesLine(profile: ProfileRow): string {
    if (profile.missing || !profile.values || profile.values.opening_time === undefined) {
      return this.i18n.t("panel.overview.group.values_unknown");
    }
    return this.i18n.t("panel.overview.group.values", {
      travel: profile.reference_height === null ? "?" : this.i18n.number(profile.reference_height, 0),
      opening: this.i18n.number(profile.values.opening_time, 1),
      closing: this.i18n.number(profile.values.closing_time, 1),
      slat: this.i18n.number(profile.values.slat_time, 1),
    });
  }

  /**
   * Where the profile came from: the shutter it was measured on and when - and, when that
   * shutter has since been told to follow something else, that too. A profile measured on a
   * window that now follows another profile is not wrong, but it is surprising, and a
   * surprise the screen does not mention is a surprise the user finds out later.
   */
  /**
   * The third line of a group's header: where this profile came from.
   *
   * **And, once, what the file has to say about its members.** The sentence about a
   * profile the configuration file assigns used to be on every row of the group; the
   * first live pass found twelve copies of it under twelve names. It is one sentence
   * here, and it is drawn when the file states either half - the profile itself, or the
   * assignment of any shutter to it - because from the user's side both come to the same
   * thing: this is read-only, and the place to change it is the file.
   */
  private _provenanceLine(profile: ProfileRow): string {
    const statedInTheFile =
      profile.source === "yaml" ||
      (this._overview?.covers ?? []).some(
        (cover: CoverRow) => cover.profile === profile.name && cover.profile_from_file,
      );
    if (statedInTheFile) {
      return this.i18n.t("panel.overview.group.from_file");
    }
    if (!profile.measured_on) {
      return this.i18n.t("panel.overview.group.provenance_missing");
    }
    const date = profile.measured_at ? this.i18n.date(profile.measured_at) : "";
    if (!profile.measured_on_name) {
      return this.i18n.t("panel.overview.group.measured_on_gone", { date });
    }
    let line = this.i18n.t("panel.overview.group.measured_on", {
      cover: profile.measured_on_name,
      date,
    });
    const reference = (this._overview?.covers ?? []).find(
      (cover) => cover.unique_id === profile.measured_on,
    );
    if (reference && reference.profile !== profile.name) {
      const now = reference.profile ?? this.i18n.t("panel.overview.group.no_profile");
      line += ` · ${this.i18n.t("panel.profile.provenance_now_profile", { profile: now })}`;
    }
    return line;
  }

  /**
   * The groups, in the server's profile order, with "Senza profilo" last.
   *
   * A shutter is drawn in the group it is **heading for**, not the one the server has it
   * in: the pending change is laid over the model at render time, which is what makes the
   * drop look like it worked while nothing has been written.
   */
  private get _groups(): PanelGroup[] {
    const overview = this._overview;
    if (!overview) {
      return [];
    }
    const covers = this._covers;
    const inGroup = (name: string | null): CoverRow[] =>
      covers.filter(
        (cover) => effectiveProfile(cover, this.state.pending) === name && this._matches(cover),
      );
    const groups: PanelGroup[] = overview.profiles.map((profile, index) => ({
      key: profile.name,
      id: `group-${index}`,
      title: this.i18n.t("panel.overview.group.profile", { profile: profile.name }),
      values: this._valuesLine(profile),
      provenance: this._provenanceLine(profile),
      warning: profile.missing ? this.i18n.t("panel.overview.group.missing") : "",
      covers: inGroup(profile.name),
    }));
    groups.push({
      key: null,
      id: "group-none",
      title: this.i18n.t("panel.overview.group.no_profile"),
      values: this.i18n.t("panel.overview.group.no_profile_note"),
      provenance: "",
      warning: "",
      covers: inGroup(null),
    });
    return groups;
  }

  // --- the gestures -------------------------------------------------------------------
  private _onGrab = (cover: CoverRow, event: PointerEvent): void => {
    this._drag.press(cover.unique_id, event);
  };

  /**
   * A tap or a keyboard assignment lands at the end of the group it was sent to.
   *
   * While nothing has been dragged there is no local order and the batch carries none,
   * which the server already reads as "append" (contract §9.1). Once a drag has set one,
   * the batch carries the whole gateway's list and the shutter would otherwise keep the
   * place it had in it - so the appending is written into the list instead. Called before
   * the assignment, because the destination group is read out of the pending changes as
   * they are now.
   */
  private _appendAtEnd(cover: CoverRow, to: string | null): void {
    if (this.state.order === null || to === (cover.profile ?? null)) {
      return;
    }
    const covers = this._covers;
    this.actions.setOrder(
      appendedToGroup(
        covers.map((row) => row.unique_id),
        cover.unique_id,
        covers
          .filter((row) => effectiveProfile(row, this.state.pending) === to)
          .map((row) => row.unique_id),
      ),
    );
  }

  /** A press on the row's body only ever arms the phone's long press. */
  private _onRowPress = (cover: CoverRow, event: PointerEvent): void => {
    if (this._narrow && !this._locked) {
      // The event travels with it so the long press can tell a resting finger - which is
      // never perfectly still - from the start of a scroll.
      this._drag.arm(cover.unique_id, event);
    }
  };

  /**
   * The drop.
   *
   * Two things can come of it and they are not the same news. A row that landed in another
   * group is an assignment, and goes pending. A row that landed in its own group has only
   * been reordered - and an order is remembered rather than confirmed (the design's own
   * rule: "l'ordine è ricordato tra le sessioni"), so it is written straight away when
   * there is nothing pending to carry it, and carried with the batch when there is.
   */
  private _endDrag(commit: boolean): void {
    const state = this.state;
    const drag = state.drag;
    const target = drag?.insert ?? null;
    const over = drag?.over ?? null;
    const cover = drag ? this._cover(drag.cover) : undefined;
    this.actions.drag(null);
    if (!commit || !cover || over === null) {
      if (drag) {
        this.actions.announce(this.i18n.t("panel.assign.announce.drag_cancelled"));
      }
      return;
    }
    const to = groupKeyOf(over);
    const order = this._covers.map((row) => row.unique_id);
    const moved = movedTo(
      order,
      cover.unique_id,
      target ?? { beforeId: null, afterId: null },
    );
    this._beforeMove();
    const current = pendingFor(cover.unique_id, state.pending);
    const heading = current ? current.to : (cover.profile ?? null);
    if (to !== heading) {
      this.actions.setOrder(moved);
      this.actions.assign(cover, to);
      return;
    }
    // Same group: a reorder, and nothing anybody has to confirm.
    if (state.pending.length > 0) {
      this.actions.setOrder(moved);
      this.actions.announce(this.i18n.t("panel.assign.announce.reordered"));
      return;
    }
    this.actions.reorder(moved);
  }

  // --- rendering ----------------------------------------------------------------------
  private _renderControls(): TemplateResult {
    return html`<div class="controls">
      <input
        class="field search"
        type="search"
        .value=${this.state.search}
        placeholder=${this.i18n.t("panel.common.search")}
        aria-label=${this.i18n.t("panel.common.search")}
        @input=${(event: Event) =>
          this.actions.search((event.target as HTMLInputElement).value)}
      />
      <span class="select-wrap">
        <select
          class="field"
          aria-label=${this.i18n.t("panel.common.room_filter")}
          .value=${this.state.room}
          @change=${(event: Event) =>
            this.actions.room((event.target as HTMLSelectElement).value)}
        >
          <option value="">${this.i18n.t("panel.common.all_rooms")}</option>
          ${this._rooms.map((room) => html`<option value=${room}>${room}</option>`)}
        </select>
      </span>
      <span class="spacer"></span>
      <!--
        The guided calibration, in this panel (SPEC §6). It used to be a link to the
        integration page, where the user still had to find "Configura"; it is a button now
        because what it does is move between two screens of this panel, and it carries no
        shutter - the wizard asks which one.
      -->
      <button
        class="cta secondary compact"
        type="button"
        @click=${() => this.actions.calibrate(null)}
      >
        ${this.i18n.t("panel.firstrun.action.measure")}
      </button>
    </div>`;
  }

  /**
   * The first run: no profile has ever been measured. The handoff is explicit that this is
   * a welcome and not an empty list - a list with nothing in it teaches nobody what a
   * profile is, and this is the one moment the panel has the user's attention for it.
   */
  private _renderFirstRun(): TemplateResult {
    return html`<section class="card welcome">
      <h2>${this.i18n.t("panel.firstrun.title")}</h2>
      <div>${this.i18n.md("panel.firstrun.body")}</div>
      <div class="soft">${this.i18n.md("panel.firstrun.how")}</div>
      <button class="cta" type="button" @click=${() => this.actions.calibrate(null)}>
        ${this.i18n.t("panel.firstrun.action.measure")}
      </button>
      <p class="after">${this.i18n.t("panel.firstrun.note")}</p>
    </section>`;
  }

  /** The five strips, in the order of the gesture; never two of them at once. */
  private _renderStrips(): TemplateResult | typeof nothing {
    const state = this.state;
    // A drawer is over this list: the shell draws what still applies (a write in the air,
    // and its result with "Annulla" beside it) and the three that are about a gesture on
    // this screen have nothing to say while nobody can reach it. Two elements drawing a
    // strip each would be two strips, which is the one thing this file promises never to
    // do.
    if (state.route.view !== "overview") {
      return nothing;
    }
    if (state.drag) {
      return dropZone(this.i18n, state.drag.over === "none");
    }
    if (state.armed) {
      const cover = this._cover(state.armed);
      return armedStrip(this.i18n, cover?.name ?? "", () => this.actions.arm(null));
    }
    if (state.applying) {
      return applyingStrip(this.i18n);
    }
    if (state.snack) {
      return snackStrip(
        this.i18n,
        state.snack.message,
        state.snack.undoToken ? () => this.actions.undo() : null,
      );
    }
    if (state.pending.length > 0 && !state.review) {
      return pendingBar({
        i18n: this.i18n,
        count: state.pending.length,
        locked: this._locked,
        lockedCover: this._overview?.measuring?.name ?? "",
        onDiscard: () => {
          this._beforeMove();
          this.actions.discardAll();
        },
        onReview: () => this.actions.review(true),
      });
    }
    return nothing;
  }

  private _renderDialog(): TemplateResult | typeof nothing {
    const cover = this.state.dialog ? this._cover(this.state.dialog) : undefined;
    if (!cover) {
      return nothing;
    }
    return profileDialog({
      i18n: this.i18n,
      cover,
      profiles: this._overview?.profiles ?? [],
      current: effectiveProfile(cover, this.state.pending),
      onPick: (profile) => {
        this._beforeMove();
        this._appendAtEnd(cover, profile);
        this.actions.assign(cover, profile);
      },
      onClose: () => this.actions.dialog(null),
    });
  }

  private _renderReview(): TemplateResult | typeof nothing {
    const overview = this._overview;
    if (!this.state.review || !overview) {
      return nothing;
    }
    return reviewPanel({
      i18n: this.i18n,
      pending: this.state.pending,
      covers: new Map(overview.covers.map((cover) => [cover.unique_id, cover])),
      profiles: new Map(overview.profiles.map((profile) => [profile.name, profile])),
      preview: this.state.preview,
      previewing: this.state.previewing,
      heights: this.state.heights,
      forced: this.state.heightsForced,
      showAll: this.state.showAll,
      applying: this.state.applying,
      refusal: this.state.writeError
        ? this.i18n.refusal(
            this.state.writeError.translation_key,
            this.state.writeError.translation_placeholders ?? {},
          )
        : "",
      route: this._route,
      onHeight: (cover, value) => this.actions.height(cover, value),
      onToggleShowAll: () => this.actions.toggleShowAll(),
      onConfirm: () => this.actions.confirm(),
      onClose: () => this.actions.review(false),
    });
  }

  protected override render(): TemplateResult {
    const overview = this._overview;
    if (!overview) {
      return html`<p>${this.i18n.t("panel.common.loading")}</p>`;
    }
    if (overview.no_basic_covers) {
      // A gateway whose covers all report their own position has no travel model to
      // calibrate, so this is not an empty list waiting to fill: it is the answer. It is
      // drawn as the welcome is - a heading, the sentence, and the way to the dialog for
      // everything else this integration does - rather than as a notice above a list that
      // is never coming.
      return html`<section class="card welcome">
        <h2>${this.i18n.t("panel.overview.no_basic_covers_title")}</h2>
        <div>${renderMarkdown(this.i18n.t("panel.overview.no_basic_covers"))}</div>
        <!--
          No title promising the dialog: this link goes to the integration page, where
          "Configura" still has to be pressed, and it is the last place on the overview
          that said otherwise. The words on the link say where it goes.
        -->
        <a class="cta secondary" href=${FLOW_URL}
          >${this.i18n.t("panel.common.action.configure")}</a
        >
      </section>`;
    }
    // `profiles` carries every name defined *or* followed, so an empty list really is an
    // installation where nothing has ever been measured.
    if (overview.profiles.length === 0) {
      return this._renderFirstRun();
    }
    const groups = this._groups;
    const shown = groups.reduce((total, group) => total + group.covers.length, 0);
    const filtering = this.state.search.trim() !== "" || this.state.room !== "";
    const drag = this.state.drag;
    return html`
      <div class="intro">${this.i18n.md("panel.overview.explanation")}</div>
      <p class="counts">
        ${this.i18n.t("panel.overview.summary", {
          profiles: overview.profiles.length,
          covers: overview.covers.length,
        })}
      </p>
      ${this._renderControls()}
      ${shown === 0 && filtering
        ? html`<div class="card notice">
            <div>${this.i18n.t("panel.overview.no_results")}</div>
            <div class="actions">
              <button class="cta text" type="button" @click=${() => this.actions.clearFilters()}>
                ${this.i18n.t("panel.overview.action.clear_filters")}
              </button>
            </div>
          </div>`
        : html`<div class="groups ${this.state.armed !== null ? "targeting" : ""}">
            ${groups.map((group) => {
              const key = groupAttr(group.key);
              const insert = drag?.insert ?? null;
              const here = insert !== null && insert.group === key;
              return groupCard(group, {
                i18n: this.i18n,
                pending: this.state.pending,
                route: this._route,
                locked: this._locked,
                collapsed: this.state.armed !== null,
                over: drag?.over === key,
                insertBefore: here ? insert.beforeId : null,
                insertEnd: here ? insert.end || insert.afterId === group.covers.at(-1)?.unique_id : false,
                dragging: drag?.cover ?? null,
                onOpenProfile: (name) => this.actions.openProfile(name),
                onOpenCover: (cover) => this.actions.openCover(cover.unique_id),
                onGrab: this._onGrab,
                onRowPress: this._onRowPress,
                onPick: (cover) => this.actions.dialog(cover),
                onWithdraw: (cover) => {
                  this._beforeMove();
                  this.actions.withdraw(cover);
                },
                onTarget: (target) => {
                  const armed = this.state.armed ? this._cover(this.state.armed) : undefined;
                  if (armed) {
                    this._beforeMove();
                    this._appendAtEnd(armed, target);
                    this.actions.assign(armed, target);
                  }
                },
              });
            })}
          </div>`}
      ${this._renderStrips()} ${this._renderDialog()} ${this._renderReview()}
    `;
  }
}

if (!customElements.get("myhome-overview")) {
  customElements.define("myhome-overview", MyHomeOverview);
}
