// A profile and the shutters that follow it, as one card - and, during a gesture, as one
// drop target.
//
// The header is three lines and each of them answers a different question. The **title**
// says which profile, and is a link into its card because the numbers behind the summary
// are one click away. The **values line** is the summary itself - reference travel, ascent,
// descent, slats - so that "which of my two profiles is the tall one?" does not need a
// second screen. The **provenance line** says on which shutter and when it was measured;
// when nothing recorded it, it says so, because a profile of unknown provenance is a fact
// about the installation and not a blank.
//
// "Senza profilo" is the same card with the same three lines: a group, not a leftover. Its
// meta line is the one sentence that keeps a user from thinking it is a failure state.
//
// Each heading is a real `<h2>`, so the page has an outline a screen reader can jump
// through, and the section points at its own heading rather than repeating the name in an
// `aria-label`.
//
// **Two things a gesture does to this card.** A pointer drag over it draws a solid primary
// outline - the card is where the row will land. A shutter armed by a long press on the
// phone collapses every card to its title, which then becomes a 48 px target with a dashed
// outline: the design's "prendi e tocca la destinazione", and the reason it works is that
// twelve shutters' worth of rows do not fit on a phone beside the thing being moved.

import { css, html, nothing, type TemplateResult } from "lit";

import { type I18n } from "../engine/i18n";
import { type PendingChange } from "../engine/store";
import { type CoverRow } from "../engine/ws";
import { coverRow } from "./cover-row";

export const groupCardStyles = css`
  .groups {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  /*
   * From 600 px the groups stand side by side and the row of them scrolls sideways, which
   * is what makes a drag between two profiles one gesture. Below it they stack, and the
   * gesture is press-and-tap instead.
   */
  @media (min-width: 600px) {
    .groups {
      display: grid;
      grid-auto-flow: column;
      grid-auto-columns: minmax(300px, 1fr);
      gap: 16px;
      align-items: start;
      overflow-x: auto;
      padding-bottom: 8px;
      /* A drag near the edge scrolls this; the browser must not fight it with inertia. */
      overscroll-behavior-x: contain;
    }
  }

  .group {
    position: relative;
    background: var(--myhome-card);
    border-radius: var(--myhome-radius);
    box-shadow: var(--myhome-shadow);
  }

  .group-head {
    padding: 16px 16px 12px;
    border-bottom: 1px solid var(--myhome-divider);
  }

  .group-head .line {
    display: flex;
    align-items: baseline;
    gap: 8px;
    flex-wrap: wrap;
  }

  .group-head h2 {
    margin: 0;
    font-size: 17px;
    font-weight: 500;
    flex: 1 1 auto;
    min-width: 0;
  }

  .group-head h2 button {
    border: none;
    background: transparent;
    color: var(--myhome-primary);
    font: inherit;
    cursor: pointer;
    padding: 0;
    min-height: 28px;
    text-align: left;
  }

  .group-head .count {
    color: var(--myhome-text-soft);
    font-size: 13px;
  }

  .group-head .meta {
    margin: 6px 0 0;
    font-size: 13px;
    color: var(--myhome-text-soft);
    line-height: 1.5;
  }

  .group-head .meta.second {
    margin-top: 4px;
  }

  .group-head .meta.warn {
    color: var(--myhome-warning);
  }

  .group-body {
    display: flex;
    flex-direction: column;
    padding: 8px;
    gap: 2px;
    min-height: 56px;
  }

  .group-body .empty {
    margin: 8px;
    font-size: 13px;
    color: var(--myhome-text-soft);
  }

  /* A drop at the end of the group: the insertion line under the last row. */
  .group-body .insert-end {
    margin: 0 8px;
    height: 3px;
    border-radius: 2px;
    background: var(--myhome-primary);
    pointer-events: none;
  }

  /*
   * The two outlines. Solid means "let go and it lands here"; dashed means "this is a
   * target you can tap". Both are overlays and not borders, so the card does not change
   * size and the whole row of groups does not shift the moment a drag begins.
   */
  .group .over,
  .group .armed-target {
    position: absolute;
    inset: 0;
    border-radius: var(--myhome-radius);
    pointer-events: none;
  }

  .group .over {
    border: 2px solid var(--myhome-primary);
  }

  .group .armed-target {
    border: 2px dashed var(--myhome-primary);
  }

  /* Collapsed: the card is its own heading, and the heading is the target. */
  .group.collapsed .group-head {
    border-bottom: none;
    min-height: 48px;
    cursor: pointer;
  }
`;

export interface PanelGroup {
  /** The profile name, or `null` for "Senza profilo". */
  key: string | null;
  id: string;
  title: string;
  /** The values line of the header; empty for a group that has no numbers. */
  values: string;
  /** The provenance line, or the file note; empty when there is nothing to say. */
  provenance: string;
  /** A warning that outranks the provenance line: a profile nobody defines any more. */
  warning: string;
  covers: CoverRow[];
}

export interface GroupContext {
  i18n: I18n;
  /** The changes the user has made and not confirmed. */
  pending: readonly PendingChange[];
  /** Where a shutter is heading, in the words the group headings use. */
  route: (cover: CoverRow) => string;
  /** True while nothing may be moved. */
  locked: boolean;
  /** True when a shutter is armed and every group is a title-sized target. */
  collapsed: boolean;
  /** True when the pointer is over this group. */
  over: boolean;
  /** The row a drop would land above, and whether it would land at the end. */
  insertBefore: string | null;
  insertEnd: boolean;
  /** The row in flight. */
  dragging: string | null;
  onOpenProfile: (name: string) => void;
  onOpenCover: (cover: CoverRow) => void;
  onGrab: (cover: CoverRow, event: PointerEvent) => void;
  onRowPress: (cover: CoverRow) => void;
  onPick: (cover: CoverRow) => void;
  onWithdraw: (cover: CoverRow) => void;
  /** A tap on the card while a shutter is armed: this group is the destination. */
  onTarget: (group: string | null) => void;
}

export const groupCard = (group: PanelGroup, context: GroupContext): TemplateResult => {
  const { i18n } = context;
  const count =
    group.covers.length === 1
      ? i18n.t("panel.overview.group.count_one")
      : i18n.t("panel.overview.group.count", { count: group.covers.length });
  const armed = context.collapsed;
  return html`<section
    class="group ${armed ? "collapsed" : ""}"
    data-group=${group.key ?? "none"}
    aria-labelledby=${group.id}
  >
    <div
      class="group-head"
      @click=${() => {
        if (armed) {
          context.onTarget(group.key);
        }
      }}
    >
      <div class="line">
        <h2 id=${group.id}>
          ${group.key === null
            ? group.title
            : html`<button
                type="button"
                title=${armed
                  ? i18n.t("panel.assign.armed", { cover: "" })
                  : i18n.t("panel.overview.group.open")}
                @click=${(event: Event) => {
                  event.stopPropagation();
                  if (armed) {
                    context.onTarget(group.key);
                    return;
                  }
                  context.onOpenProfile(group.key as string);
                }}
              >
                ${group.title}
              </button>`}
        </h2>
        <span class="count">${count}</span>
      </div>
      ${group.values && !armed ? html`<p class="meta">${group.values}</p>` : nothing}
      ${armed
        ? nothing
        : group.warning
          ? html`<p class="meta second warn">${group.warning}</p>`
          : group.provenance
            ? html`<p class="meta second">${group.provenance}</p>`
            : nothing}
    </div>
    ${armed
      ? nothing
      : html`<div class="group-body">
          ${group.covers.map((cover, index) =>
            coverRow(cover, {
              i18n,
              short: cover.profile === group.key,
              first: index === 0,
              pending: context.pending.find((item) => item.cover === cover.unique_id),
              route: context.route(cover),
              locked: context.locked,
              insertBefore: context.insertBefore === cover.unique_id,
              dragging: context.dragging === cover.unique_id,
              onOpen: context.onOpenCover,
              onGrab: context.onGrab,
              onRowPress: context.onRowPress,
              onPick: context.onPick,
              onWithdraw: context.onWithdraw,
            }),
          )}
          ${context.insertEnd
            ? html`<div class="insert-end" aria-hidden="true"></div>`
            : nothing}
          ${group.covers.length === 0
            ? html`<p class="empty">${i18n.t("panel.overview.group.empty")}</p>`
            : nothing}
        </div>`}
    ${context.over ? html`<div class="over" aria-hidden="true"></div>` : nothing}
    ${armed ? html`<div class="armed-target" aria-hidden="true"></div>` : nothing}
  </section>`;
};
