// A profile and the shutters that follow it, as one card.
//
// The header is three lines and each of them answers a different question. The **title**
// says which profile, and is a link into its card because the numbers behind the summary
// are one click away. The **values line** is the summary itself - reference travel, ascent,
// descent, slats - so that "which of my two profiles is the tall one?" does not need a
// second screen. The **provenance line** says on which shutter and when it was measured,
// which is what `measured_on` / `measured_at` were added to the store for; when nothing
// recorded it, it says so, because a profile of unknown provenance is a fact about the
// installation and not a blank.
//
// "Senza profilo" is the same card with the same three lines: a group, not a leftover. Its
// meta line is the one sentence that keeps a user from thinking it is a failure state.
//
// Each heading is a real `<h2>`, so the page has an outline a screen reader can jump
// through, and the section points at its own heading rather than repeating the name in an
// `aria-label`.

import { css, html, nothing, type TemplateResult } from "lit";

import { type I18n } from "../engine/i18n";
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
   * is what makes a drag between two profiles one gesture (lot 7). Below it they stack.
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
  onOpenProfile: (name: string) => void;
  onOpenCover: (cover: CoverRow) => void;
}

export const groupCard = (group: PanelGroup, context: GroupContext): TemplateResult => {
  const { i18n } = context;
  const count =
    group.covers.length === 1
      ? i18n.t("panel.overview.group.count_one")
      : i18n.t("panel.overview.group.count", { count: group.covers.length });
  return html`<section class="group" data-group=${group.key ?? "none"} aria-labelledby=${group.id}>
    <div class="group-head">
      <div class="line">
        <h2 id=${group.id}>
          ${group.key === null
            ? group.title
            : html`<button
                type="button"
                title=${i18n.t("panel.overview.group.open")}
                @click=${() => context.onOpenProfile(group.key as string)}
              >
                ${group.title}
              </button>`}
        </h2>
        <span class="count">${count}</span>
      </div>
      ${group.values ? html`<p class="meta">${group.values}</p>` : nothing}
      ${group.warning
        ? html`<p class="meta second warn">${group.warning}</p>`
        : group.provenance
          ? html`<p class="meta second">${group.provenance}</p>`
          : nothing}
    </div>
    <div class="group-body">
      ${group.covers.map((cover, index) =>
        coverRow(cover, {
          i18n,
          short: cover.profile === group.key,
          first: index === 0,
          onOpen: context.onOpenCover,
        }),
      )}
      ${group.covers.length === 0
        ? html`<p class="empty">${i18n.t("panel.overview.group.empty")}</p>`
        : nothing}
    </div>
  </section>`;
};
