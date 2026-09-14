// One shutter, one row: the name, where it is and how far it runs, the chip that says
// where its numbers come from - and, once the user has moved it, where it is heading.
//
// Transcribed from the prototype's own markup, which is the specification: 48 px minimum
// height, 8 px padding, an 8 px radius, and a 1 px divider at 60 % opacity between rows
// rather than a border on each. The name wraps to two lines and then truncates, with the
// full name on hover, because a German label is a third longer than an Italian one and a
// house full of "Tapparella camera da letto grande" must still be readable.
//
// **The row is three siblings, not one button with things inside it.** The name and the
// two texts are a button that opens the detail; the chips - the origin and, once a change
// is pending, the route with its ✕ - are a `<div>` beside it. They used to be inside that
// button, and the ✕ was a `<span role="button" tabindex="0">` nested in it: invalid HTML
// (a button may contain no interactive content), and Safari does not put a button's
// descendants in the tab order, so on that browser the only way to take a change back was
// to drag the shutter home. The chips are still read with the row, through
// `aria-describedby`, which is what an `aria-label` on the button would have thrown away.
//
// The row's button carries **no `aria-label`**. An `aria-label` replaces everything inside
// the element it is on, so one saying "open the details of X" would hide the room and the
// travel from a screen reader while leaving them on the screen for everybody else. The
// button's own contents are already the sentence to read.
//
// **The handle is the way in to all three gestures.** A pointer press starts a drag on a
// desktop and arms a long press on a phone; Enter or Space opens "Quale profilo?", which
// is the same pending change by another road. It is 48×48, `touch-action: none`, and
// hidden below 600 px, where the gesture is press-and-tap and a drag handle would be a
// control that looks draggable and is not.
//
// Five row states are drawn, and each is one absolutely positioned overlay rather than a
// border on the row: a border would change the row's size and make the whole group jump
// the moment a change went pending. Insertion line, pending outline, dimmed source,
// divider - all `pointer-events: none`, because a drag hit-tests what is under the pointer
// and an overlay that answered would be a row that cannot be dropped onto itself.

import { css, html, nothing, type TemplateResult } from "lit";

import { type I18n } from "../engine/i18n";
import { MEASURABLE_KEYS } from "../engine/assign";
import { type PendingChange } from "../engine/store";
import { type CoverRow } from "../engine/ws";
import { originChip } from "./origin-chip";

export const coverRowStyles = css`
  .row {
    position: relative;
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 8px;
    border-radius: 8px;
    min-height: 48px;
    -webkit-user-select: none;
    -webkit-touch-callout: none;
  }

  .row .divider {
    position: absolute;
    left: 8px;
    right: 8px;
    top: -1px;
    height: 1px;
    background: var(--myhome-divider);
    opacity: 0.6;
    pointer-events: none;
  }

  /* The insertion line takes the divider's place while a row is in flight. */
  .row .insert-line {
    position: absolute;
    left: 8px;
    right: 8px;
    top: -2px;
    height: 3px;
    border-radius: 2px;
    background: var(--myhome-primary-ink);
    pointer-events: none;
  }

  .row .pending-outline {
    position: absolute;
    inset: 0;
    border: 2px dashed var(--myhome-primary-ink);
    border-radius: 8px;
    pointer-events: none;
  }

  .row .source-veil {
    position: absolute;
    inset: 0;
    background: var(--myhome-background-soft);
    opacity: 0.7;
    border-radius: 8px;
    pointer-events: none;
  }

  .row .handle {
    width: 48px;
    height: 48px;
    flex: 0 0 48px;
    border: none;
    background: transparent;
    color: var(--myhome-text-soft);
    cursor: grab;
    font-size: 18px;
    letter-spacing: 2px;
    border-radius: 8px;
    touch-action: none;
    -webkit-user-select: none;
    user-select: none;
  }

  .row .handle[disabled] {
    cursor: default;
    color: var(--myhome-text-off);
  }

  /*
   * Below 600 px the design does not draw the handle: the gesture there is press-and-tap,
   * and a control that looks draggable and is not would be a lie about what it does.
   *
   * It is hidden rather than removed, because "display: none" takes it out of the tab
   * order too - and Enter on the handle is the *only* way to reach an assignment that
   * does not need a pointer. A phone is not the only thing under 600 px: a desktop window
   * dragged narrow is one, and it has a keyboard. So the handle is taken out of the flow
   * and out of sight in the way a skip link is, and it comes back at its full 48 px the
   * moment the keyboard reaches it.
   */
  @media (max-width: 599px) {
    .row .handle {
      position: absolute;
      width: 1px;
      height: 1px;
      padding: 0;
      margin: -1px;
      overflow: hidden;
      clip-path: inset(50%);
      white-space: nowrap;
    }

    .row .handle:focus-visible {
      position: static;
      width: 48px;
      height: 48px;
      margin: 0;
      overflow: visible;
      clip-path: none;
    }
  }

  /*
   * The column beside the handle. It exists so that the chips can be a sibling of the
   * button rather than a child of it, and still sit under the texts as the design draws
   * them - the button is no longer the thing that owns the row's width.
   */
  .row .body {
    flex: 1 1 auto;
    min-width: 0;
  }

  .row .main {
    display: block;
    width: 100%;
    text-align: left;
    border: none;
    background: transparent;
    color: inherit;
    font: inherit;
    cursor: pointer;
    padding: 2px 0;
    border-radius: 6px;
  }

  .row .name {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    font-size: 14.5px;
    line-height: 1.35;
  }

  .row .sub {
    display: block;
    font-size: 12.5px;
    color: var(--myhome-text-soft);
    margin-top: 2px;
  }

  .row .chips:empty {
    display: none;
  }

  .row .chips {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    margin-top: 6px;
    align-items: center;
  }

  .row .warn {
    display: block;
    font-size: 12.5px;
    color: var(--myhome-warning-ink);
    margin-top: 4px;
  }

  /* The pending chip: the route this shutter is on, and the way to take it back. */
  .route {
    display: inline-flex;
    align-items: center;
    gap: 2px;
    font-size: 12px;
    color: var(--myhome-primary-ink);
    background: var(--myhome-primary-faint);
    border: 1px dashed var(--myhome-primary-ink);
    border-radius: 10px;
    padding: 2px 2px 2px 8px;
    max-width: 100%;
  }

  .route .text {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  /*
   * 20 px of ink inside a 48 px target: the design fixes the little cross at 20 px, and
   * the handoff's minimum target at 48. Negative margins keep the chip the height it is
   * drawn at while the hit area reaches the row's edges.
   */
  .route .withdraw {
    width: 48px;
    height: 48px;
    margin: -14px -14px -14px 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border: none;
    background: transparent;
    color: inherit;
    font: inherit;
    font-size: 14px;
    line-height: 1;
    cursor: pointer;
    border-radius: 24px;
  }

  .row .note {
    display: block;
    font-size: 12.5px;
    color: var(--myhome-info-ink);
    margin-top: 4px;
  }
`;

export interface CoverRowContext {
  i18n: I18n;
  /** True when the row sits in the group of the profile it follows. */
  short: boolean;
  /** The first row of a group has no divider above it. */
  first: boolean;
  /** The change this shutter is carrying, if any. */
  pending: PendingChange | undefined;
  /** Where the shutter is heading, in the words the group headings use. */
  route: string;
  /** True while nothing may be moved: a measurement, or a write in flight. */
  locked: boolean;
  /** True when a drop would land immediately above this row. */
  insertBefore: boolean;
  /** True when this is the row in flight. */
  dragging: boolean;
  onOpen: (cover: CoverRow) => void;
  /** A press on the handle: a drag where there is one, a long press where there is not. */
  onGrab: (cover: CoverRow, event: PointerEvent) => void;
  /**
   * A press on the row itself. It only ever arms the phone's long press: on a desktop the
   * body of the row is the way into the detail view, and a press that both opened a screen
   * and picked the row up would do neither reliably.
   */
  onRowPress: (cover: CoverRow, event: PointerEvent) => void;
  onPick: (cover: CoverRow) => void;
  onWithdraw: (cover: CoverRow) => void;
}

/**
 * The second line: the room, and how far the curtain runs.
 *
 * A shutter on its way into a profile with no travel recorded says "corsa da inserire"
 * rather than "corsa non indicata": the first is a thing the user is about to be asked
 * for, the second is a fact about a shutter nobody is moving.
 */
const subtitle = (i18n: I18n, cover: CoverRow, needsTravel: boolean): string => {
  const travel =
    cover.height !== null
      ? i18n.t("panel.overview.cover.travel", { travel: i18n.number(cover.height, 0) })
      : needsTravel
        ? i18n.t("panel.overview.cover.travel_needed")
        : i18n.t("panel.overview.cover.travel_unknown");
  return cover.area ? `${cover.area} · ${travel}` : travel;
};

/**
 * "Some of its numbers are its own, and those stay."
 *
 * The one thing a user moving a measured shutter into a profile needs to be told before
 * they confirm, because it is the opposite of what the gesture looks like it does.
 */
const ownNote = (i18n: I18n, cover: CoverRow): string => {
  if (cover.has_own.length === 0) {
    return "";
  }
  // Every one of the five a window can have measured on it: the profile would answer for
  // nothing at all, which is a different sentence from "some of these stay".
  return MEASURABLE_KEYS.every((key) => cover.has_own.includes(key))
    ? i18n.t("panel.assign.pending.all_own")
    : i18n.t("panel.assign.pending.some_own");
};

export const coverRow = (cover: CoverRow, context: CoverRowContext): TemplateResult => {
  const { i18n, pending } = context;
  const needsTravel = !!pending && pending.to !== null && cover.height === null;
  const note = pending ? ownNote(i18n, cover) : "";
  // The chips are outside the button now, so the button has to point at them: a unique id
  // per row, and `unique_id` is the one string on a row that is guaranteed to be one.
  const chipsId = `chips-${cover.unique_id}`;
  return html`<div class="row" data-row=${cover.unique_id}>
    ${context.insertBefore
      ? html`<div class="insert-line" aria-hidden="true"></div>`
      : context.first
        ? nothing
        : html`<div class="divider" aria-hidden="true"></div>`}
    ${pending ? html`<div class="pending-outline" aria-hidden="true"></div>` : nothing}
    ${context.dragging ? html`<div class="source-veil" aria-hidden="true"></div>` : nothing}
    <button
      class="handle"
      type="button"
      ?disabled=${context.locked}
      aria-label=${i18n.t("panel.assign.handle", { cover: cover.name })}
      title=${context.locked
        ? i18n.t("panel.banner.measuring.title")
        : i18n.t("panel.assign.handle_hint")}
      @pointerdown=${(event: PointerEvent) => context.onGrab(cover, event)}
      @click=${(event: Event) => event.stopPropagation()}
      @keydown=${(event: KeyboardEvent) => {
        // Enter and Space open "Quale profilo?", which is the drop's own confirmation
        // step by another road. Every assignment is reachable without a pointer.
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          if (!context.locked) {
            context.onPick(cover);
          }
        }
      }}
    >
      ⠿
    </button>
    <div
      class="body"
      @pointerdown=${(event: PointerEvent) => context.onRowPress(cover, event)}
    >
      <button class="main" type="button" title=${cover.name} aria-describedby=${chipsId}
        @click=${() => context.onOpen(cover)}>
        <span class="name">${cover.name}</span>
        <span class="sub">${subtitle(i18n, cover, needsTravel)}</span>
        ${note ? html`<span class="note">${note}</span>` : nothing}
        ${cover.profile_missing
          ? html`<span class="warn"
              >${i18n.t("panel.overview.cover.profile_missing", {
                profile: cover.profile ?? "",
              })}</span
            >`
          : nothing}
        ${cover.profile_from_file && !cover.profile_missing
          ? html`<span class="sub">${i18n.t("panel.overview.cover.from_file")}</span>`
          : nothing}
      </button>
      <div class="chips" id=${chipsId}>
        ${originChip(i18n, cover.origin, cover.profile, context.short)}
        ${pending
          ? html`<span class="route">
              <span class="text">${context.route}</span>
              <button
                class="withdraw"
                type="button"
                aria-label=${i18n.t("panel.assign.action.withdraw")}
                title=${i18n.t("panel.assign.action.withdraw")}
                @pointerdown=${(event: Event) => event.stopPropagation()}
                @click=${() => context.onWithdraw(cover)}
              >
                ✕
              </button>
            </span>`
          : nothing}
      </div>
    </div>
  </div>`;
};
