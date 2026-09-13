// The gesture layer: FLIP, the pointer drag, and the long press.
//
// **Pointer events, not HTML5 drag and drop.** `dragstart` is not fired by touch on iOS
// Safari at all, and where it is fired the drag image is a screenshot the page cannot
// style. Pointer events are one API for mouse, pen and touch, they work in a shadow root,
// and they let the row in flight be an element of ours with the theme's own colours on it.
// The cost is that the drop target has to be found by hit-testing, which is what
// `elementFromPoint` below does - against the shadow root, because every row of every
// group lives in one (`myhome-overview`'s) and a document-level hit test would return the
// host element and nothing inside it.
//
// **iOS Safari.** The handle sets `touch-action: none` and `pointerdown` is
// `preventDefault`ed, which stops the page scrolling under the finger and suppresses the
// long-press callout; the row carries `-webkit-touch-callout: none`. Below 900 px there is
// no drag at all: a long press arms the shutter and a tap on a collapsed group title moves
// it, which is the design's own pattern for the phone rather than a workaround for one.
//
// This module owns no state the screen can see. It reports - armed, started, moved over a
// group, ended - and the store decides what any of that means.

/** What one row's position was, before the list changed under it. */
export type FlipSnapshot = Map<string, { top: number; left: number }>;

/** How long a moved row takes to slide into its new place. The handoff fixes 220 ms. */
const FLIP_MS = 220;

export const flipStart = (root: ParentNode): FlipSnapshot => {
  const snapshot: FlipSnapshot = new Map();
  for (const element of root.querySelectorAll<HTMLElement>("[data-row]")) {
    const box = element.getBoundingClientRect();
    snapshot.set(element.getAttribute("data-row") ?? "", { top: box.top, left: box.left });
  }
  return snapshot;
};

/**
 * Put every row back where it was and let it animate to where it is now.
 *
 * The list has already been re-rendered when this runs: the transform is the *old*
 * position expressed as an offset from the new one, removed on the next frame so the
 * browser interpolates it. A row that did not move is left alone rather than given a
 * transition that does nothing - a transition that never fires is a `transitionend` that
 * never arrives, and an inline style that never comes off.
 */
export const flipPlay = (root: ParentNode, snapshot: FlipSnapshot): void => {
  if (prefersNoMotion()) {
    return;
  }
  for (const element of root.querySelectorAll<HTMLElement>("[data-row]")) {
    const was = snapshot.get(element.getAttribute("data-row") ?? "");
    if (!was) {
      continue;
    }
    const box = element.getBoundingClientRect();
    const dx = was.left - box.left;
    const dy = was.top - box.top;
    if (Math.abs(dx) < 1 && Math.abs(dy) < 1) {
      continue;
    }
    element.style.transition = "none";
    element.style.transform = `translate(${dx}px, ${dy}px)`;
    void element.offsetHeight;
    element.style.transition = `transform ${FLIP_MS}ms ease`;
    element.style.transform = "";
    const done = (): void => {
      element.style.transition = "";
      element.removeEventListener("transitionend", done);
    };
    element.addEventListener("transitionend", done);
  }
};

/** A reader who asked their system not to animate things is not asked twice. */
const prefersNoMotion = (): boolean =>
  typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;

/** Where a drop would land inside a group. */
export interface DropTarget {
  group: string;
  beforeId: string | null;
  afterId: string | null;
  end: boolean;
}

export interface DragCallbacks {
  /** The shadow root the rows and groups live in. */
  root: () => ParentNode & DocumentOrShadowRoot;
  /** True while nothing may be moved: a measurement, or a write in flight. */
  blocked: () => boolean;
  /** True on the phone, where the gesture is press-and-tap rather than drag. */
  narrow: () => boolean;
  /** The long press has held: this shutter is waiting for a destination to be tapped. */
  onArm: (cover: string) => void;
  /** The pointer has moved far enough to be a drag rather than a click. */
  onStart: (cover: string) => void;
  /** The group under the pointer, and where in it a drop would land. */
  onOver: (target: DropTarget | null) => void;
  /** The finger came up (`commit`) or Escape was pressed (`!commit`). */
  onEnd: (commit: boolean) => void;
}

/** How far the pointer travels before a press becomes a drag. */
const DRAG_THRESHOLD_PX = 6;
/** How long a finger has to rest on the handle before the shutter is armed. */
const LONG_PRESS_MS = 450;
/** How close to an edge the pointer scrolls the list, and by how much per frame. */
const EDGE_PX = 64;
const EDGE_STEP_PX = 14;

/**
 * One drag at a time, for the life of the view that owns it.
 *
 * Every listener is on `window`, because a pointer that leaves the row - which is the
 * whole point - stops sending events to it. They are all removed on `stop()`, and `stop()`
 * is called from `disconnectedCallback`: a listener outliving its element is how a panel
 * navigated away from goes on hit-testing a shadow root that is not in the document.
 */
export class DragController {
  private _callbacks: DragCallbacks;
  private _start: { cover: string; x: number; y: number; live: boolean } | null = null;
  private _longPress: ReturnType<typeof setTimeout> | null = null;
  private _ghost: HTMLElement | null = null;
  private _target: DropTarget | null = null;
  private _scroll: number | null = null;
  private _edge = 0;
  private _scroller: HTMLElement | null = null;

  constructor(callbacks: DragCallbacks) {
    this._callbacks = callbacks;
  }

  /** The row in flight, or `null`. Read by the view to dim the source row. */
  get dragging(): string | null {
    return this._start?.live ? this._start.cover : null;
  }

  /**
   * A press on the handle. On the phone it arms a long press and nothing else; on a
   * desktop it starts tracking, and becomes a drag only past the threshold, so that a
   * click on the handle is still a click.
   */
  press(cover: string, event: PointerEvent): void {
    if (this._callbacks.blocked()) {
      return;
    }
    if (this._callbacks.narrow()) {
      this._arm(cover);
      return;
    }
    // Stops the page scrolling under the finger and the long-press callout on iOS.
    event.preventDefault();
    this._start = { cover, x: event.clientX, y: event.clientY, live: false };
    window.addEventListener("pointermove", this._onMove);
    window.addEventListener("pointerup", this._onUp);
    window.addEventListener("pointercancel", this._onCancel);
  }

  /**
   * Arm the phone's long press without a pointer event to go with it.
   *
   * The row's own body is the other place a grab can start on a phone, and it starts from
   * a `pointerdown` the row handler has already seen and must not `preventDefault` - a
   * press on the row is also the way into the detail view.
   */
  arm(cover: string): void {
    if (this._callbacks.blocked()) {
      return;
    }
    this._arm(cover);
  }

  /** Give up whatever is in flight - Escape, or the view going away. */
  cancel(): void {
    if (this._start?.live) {
      this._finish(false);
      return;
    }
    this._clear();
  }

  stop(): void {
    this._clear();
    this._clearLongPress();
  }

  private _arm(cover: string): void {
    this._clearLongPress();
    this._longPress = setTimeout(() => {
      this._longPress = null;
      this._callbacks.onArm(cover);
    }, LONG_PRESS_MS);
    window.addEventListener("pointerup", this._clearLongPressOnce);
    window.addEventListener("pointermove", this._clearLongPressOnce);
    window.addEventListener("pointercancel", this._clearLongPressOnce);
  }

  private _clearLongPressOnce = (): void => this._clearLongPress();

  private _clearLongPress(): void {
    if (this._longPress) {
      clearTimeout(this._longPress);
      this._longPress = null;
    }
    window.removeEventListener("pointerup", this._clearLongPressOnce);
    window.removeEventListener("pointermove", this._clearLongPressOnce);
    window.removeEventListener("pointercancel", this._clearLongPressOnce);
  }

  private _onMove = (event: PointerEvent): void => {
    const start = this._start;
    if (!start) {
      return;
    }
    if (!start.live) {
      if (Math.hypot(event.clientX - start.x, event.clientY - start.y) < DRAG_THRESHOLD_PX) {
        return;
      }
      start.live = true;
      this._callbacks.onStart(start.cover);
    }
    this._moveGhost(event.clientX, event.clientY);
    this._autoScroll(event.clientX, event.clientY);
    const target = this._targetAt(event.clientX, event.clientY, start.cover);
    if (!sameTarget(target, this._target)) {
      this._target = target;
      this._callbacks.onOver(target);
    }
  };

  private _onUp = (): void => this._finish(true);
  private _onCancel = (): void => this._finish(false);

  private _finish(commit: boolean): void {
    const live = this._start?.live ?? false;
    this._clear();
    if (live) {
      this._callbacks.onEnd(commit);
    }
  }

  private _clear(): void {
    window.removeEventListener("pointermove", this._onMove);
    window.removeEventListener("pointerup", this._onUp);
    window.removeEventListener("pointercancel", this._onCancel);
    this._start = null;
    this._target = null;
    this._stopScrolling();
    this._ghost?.remove();
    this._ghost = null;
  }

  /**
   * The label that follows the pointer.
   *
   * Built here and not rendered by Lit, for one reason: it moves on every `pointermove`
   * and a template that did would repaint every row of every group sixty times a second.
   * It is `aria-hidden` - what is happening is said by the live region, once, in a
   * sentence - and `pointer-events: none`, so it never becomes its own drop target.
   */
  ghost(name: string, into: ParentNode): void {
    const element = document.createElement("div");
    element.className = "drag-ghost";
    element.setAttribute("aria-hidden", "true");
    element.textContent = name;
    into.appendChild(element);
    this._ghost = element;
  }

  private _moveGhost(x: number, y: number): void {
    if (this._ghost) {
      this._ghost.style.transform = `translate(${x + 12}px, ${y + 8}px)`;
    }
  }

  /**
   * The groups stand side by side from 600 px and the row of them scrolls sideways, so a
   * drag towards the edge has to bring the next group into view - otherwise a house with
   * four profiles can only ever drop into the two that happen to be on screen.
   */
  private _autoScroll(x: number, _y: number): void {
    const scroller = this._callbacks
      .root()
      .querySelector<HTMLElement>(".groups");
    if (!scroller || scroller.scrollWidth <= scroller.clientWidth) {
      this._stopScrolling();
      return;
    }
    const box = scroller.getBoundingClientRect();
    const edge = x < box.left + EDGE_PX ? -1 : x > box.right - EDGE_PX ? 1 : 0;
    this._edge = edge;
    this._scroller = scroller;
    if (edge === 0) {
      this._stopScrolling();
      return;
    }
    if (this._scroll === null) {
      const step = (): void => {
        if (this._edge === 0 || !this._scroller) {
          return;
        }
        this._scroller.scrollLeft += this._edge * EDGE_STEP_PX;
        this._scroll = requestAnimationFrame(step);
      };
      this._scroll = requestAnimationFrame(step);
    }
  }

  private _stopScrolling(): void {
    this._edge = 0;
    if (this._scroll !== null) {
      cancelAnimationFrame(this._scroll);
      this._scroll = null;
    }
  }

  /**
   * What is under the pointer: which group, and before or after which row.
   *
   * The midpoint of the row decides, which is the only rule that puts the insertion line
   * where the eye expects it on both halves of a row. A group with no row under the
   * pointer - its header, its padding, its empty state - means the end of it.
   */
  private _targetAt(x: number, y: number, dragged: string): DropTarget | null {
    const element = this._callbacks.root().elementFromPoint(x, y);
    const group = element?.closest?.("[data-group]");
    if (!group) {
      return null;
    }
    const name = group.getAttribute("data-group") ?? "";
    const row = element?.closest?.("[data-row]");
    const rowId = row?.getAttribute("data-row") ?? null;
    if (!row || !rowId || rowId === dragged) {
      return { group: name, beforeId: null, afterId: null, end: true };
    }
    const box = row.getBoundingClientRect();
    return y < box.top + box.height / 2
      ? { group: name, beforeId: rowId, afterId: null, end: false }
      : { group: name, beforeId: null, afterId: rowId, end: false };
  }
}

const sameTarget = (a: DropTarget | null, b: DropTarget | null): boolean => {
  if (a === null || b === null) {
    return a === b;
  }
  return a.group === b.group && a.beforeId === b.beforeId && a.afterId === b.afterId;
};
