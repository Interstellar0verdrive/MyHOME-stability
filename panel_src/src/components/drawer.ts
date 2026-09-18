// The cover's detail and the profile's card, as a panel over the list.
//
// Until the first live pass these two were screens: the overview was replaced by them, and
// the toolbar grew a back arrow. The design never said that - it draws them as panels from
// the right, with the list still behind (Consegna 0.6.0, §3) - and on a real installation
// the cost of the difference was plain: a shutter tapped in the fourth group came back to
// a list scrolled somewhere else, and the review panel, which *was* a panel, felt like a
// different application.
//
// So they are drawn in the review panel's own frame (`components/sheet.ts`). What this
// file adds is the head: one leading control that is a back arrow while there is a screen
// behind and a close otherwise, and the title of whatever the drawer is showing.
//
// **The route is unchanged and still a deep link.** `#/cover/<id>` renders the overview
// *and* this, on first paint, which is the one thing the plan asks of these two addresses
// (§3.3). The back stack is `engine/drawer.ts`, and is one level deep by construction.

import { css, html, type CSSResultGroup, type TemplateResult } from "lit";

import { type I18n } from "../engine/i18n";
import { sheetStyles } from "./sheet";

/** The drawer's own rules, with the frame they sit on (see `review-panel.ts` for why). */
export const drawerStyles: CSSResultGroup = [sheetStyles, css`
  /*
   * The title is the profile's or the shutter's name, and it is painted the way the group
   * headings are painted since the first live pass: the theme's own primary colour, at
   * 19 px and 700 so that it is WCAG's large text. See group-card.ts for the whole of
   * that decision, and tools/contrast.mjs for what it measures in a default theme.
   */
  .sheet .head h2.named {
    font-size: 19px;
    font-weight: 700;
    color: var(--myhome-primary);
    overflow-wrap: anywhere;
  }

  /* The body of a drawer holds cards, which carry their own padding and margins. */
  .sheet.drawer .body {
    padding: 16px 16px 0;
    padding-bottom: calc(16px + env(safe-area-inset-bottom, 0px));
    background: var(--myhome-background);
  }
`];

export interface DrawerContext {
  i18n: I18n;
  /** The name of what is inside: a shutter, or a profile. */
  title: string;
  /** True while one screen is remembered behind this one. */
  hasBack: boolean;
  /** True while a write is in the air: every way out is inert, the backdrop included. */
  applying: boolean;
  onClose: () => void;
  content: TemplateResult;
}

export const drawer = (context: DrawerContext): TemplateResult => {
  const { i18n } = context;
  const close = (): void => {
    if (!context.applying) {
      context.onClose();
    }
  };
  return html`
    <div class="sheet-backdrop" aria-hidden="true" @click=${close}></div>
    <div
      class="sheet drawer"
      role="dialog"
      aria-modal="true"
      aria-labelledby="drawer-title"
      data-drawer
      tabindex="-1"
    >
      <div class="head">
        <!--
          One control, and which one it is is the whole of the back stack a user can see:
          an arrow while a screen is remembered behind this one, a cross when the only
          thing behind is the list. Both do the same thing to the address bar - they
          navigate - so the browser's own back button lands in the same places.
        -->
        <button
          type="button"
          aria-label=${context.hasBack
            ? i18n.t("panel.common.action.back")
            : i18n.t("panel.common.action.close")}
          title=${context.hasBack
            ? i18n.t("panel.common.action.back")
            : i18n.t("panel.common.action.close")}
          ?disabled=${context.applying}
          @click=${close}
        >
          ${context.hasBack ? "←" : "✕"}
        </button>
        <h2 id="drawer-title" class="named">${context.title}</h2>
      </div>
      <div class="body">${context.content}</div>
    </div>
  `;
};
