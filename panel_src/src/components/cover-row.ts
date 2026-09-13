// One shutter, one row: the name, where it is and how far it runs, and the chip that says
// where its numbers come from.
//
// Transcribed from the prototype's own markup, which is the specification: 48 px minimum
// height, 8 px padding, an 8 px radius, and a 1 px divider at 60 % opacity between rows
// rather than a border on each. The name wraps to two lines and then truncates, with the
// full name on hover, because a German label is a third longer than an Italian one and a
// house full of "Tapparella camera da letto grande" must still be readable.
//
// **The handle is rendered and inert in this lot.** Assignment - drag, tap, keyboard - is
// lot 7. It is drawn because the row's geometry depends on it and because a control that
// appears later moves everything else when it does; it is `disabled` because a grab that
// does nothing is worse than no grab at all, and a disabled button is out of the tab order
// rather than a trap. Below 600 px it is not drawn at all, which is the handoff's rule for
// the phone (there the gesture is press-and-tap, not drag).

import { css, html, nothing, type TemplateResult } from "lit";

import { type I18n } from "../engine/i18n";
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

  @media (max-width: 599px) {
    .row .handle {
      display: none;
    }
  }

  .row .main {
    flex: 1 1 auto;
    min-width: 0;
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
    color: var(--myhome-warning);
    margin-top: 4px;
  }
`;

export interface CoverRowContext {
  i18n: I18n;
  /** True when the row sits in the group of the profile it follows. */
  short: boolean;
  /** The first row of a group has no divider above it. */
  first: boolean;
  onOpen: (cover: CoverRow) => void;
}

const subtitle = (i18n: I18n, cover: CoverRow): string => {
  const travel =
    cover.height === null
      ? i18n.t("panel.common.travel_unknown")
      : i18n.t("panel.common.travel", { travel: i18n.number(cover.height, 0) });
  return cover.area ? `${cover.area} · ${travel}` : travel;
};

export const coverRow = (cover: CoverRow, context: CoverRowContext): TemplateResult => {
  const { i18n } = context;
  return html`<div class="row" data-row=${cover.unique_id}>
    ${context.first ? nothing : html`<div class="divider" aria-hidden="true"></div>`}
    <button
      class="handle"
      type="button"
      disabled
      aria-label=${i18n.t("panel.overview.handle_label", { cover: cover.name })}
      title=${i18n.t("panel.overview.handle_inert")}
    >
      ⠿
    </button>
    <button
      class="main"
      type="button"
      title=${cover.name}
      aria-label=${i18n.t("panel.overview.action.open_cover", { cover: cover.name })}
      @click=${() => context.onOpen(cover)}
    >
      <span class="name">${cover.name}</span>
      <span class="sub">${subtitle(i18n, cover)}</span>
      <span class="chips">
        ${originChip(i18n, cover.origin, cover.profile, context.short)}
      </span>
      ${cover.profile_missing
        ? html`<span class="warn"
            >${i18n.t("panel.overview.row_profile_missing", { profile: cover.profile ?? "" })}</span
          >`
        : nothing}
      ${cover.profile_from_file && !cover.profile_missing
        ? html`<span class="sub">${i18n.t("panel.overview.row_from_file")}</span>`
        : nothing}
    </button>
  </div>`;
};
