// The frame every panel over the overview is cut from.
//
// A side panel from the right at 600 px and up, a sheet from the bottom below it, a
// backdrop, a head with a title and one control, and a body that scrolls. The review panel
// was the first to need it; since the first live pass the cover's detail and the profile's
// card are drawn in the same frame, so it is one stylesheet here rather than two that
// drift apart the next time somebody changes a radius.
//
// The measurements are the design's (Consegna 0.6.0, §3): 480 px from the right, 86 vh at
// most from the bottom, and every anchored action above `env(safe-area-inset-bottom)`.
//
// What is **not** here is anything either panel puts *inside* the body: the review's
// tables and travel fields are in `review-panel.ts`, and the drawer's title and its two
// routed cards are in `drawer.ts`. This file owns the box and nothing in it.
//
// **Nobody adopts this directly.** `reviewPanelStyles` and `drawerStyles` each carry it,
// because a rule reaches only the shadow root that adopts it and the two panels are drawn
// in different roots (the overview's and the shell's). Imported on its own by the shell
// alone, it once left the review panel with no frame at all; `npm run keyboard` now checks
// that every `.sheet` on the screen has these rules in its own root.

import { css } from "lit";

export const sheetStyles = css`
  .sheet-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.4);
    z-index: 50;
  }

  /* The phone: a sheet from the bottom, never taller than 86 vh. */
  .sheet {
    position: fixed;
    left: 0;
    right: 0;
    bottom: 0;
    max-height: 86vh;
    background: var(--myhome-card);
    color: var(--myhome-text);
    z-index: 51;
    border-radius: 16px 16px 0 0;
    box-shadow: var(--myhome-shadow);
    display: flex;
    flex-direction: column;
  }

  /* From 600 px, a panel from the right instead. */
  @media (min-width: 600px) {
    .sheet {
      top: 0;
      left: auto;
      right: 0;
      bottom: 0;
      width: min(480px, 100vw);
      max-height: none;
      border-radius: 0;
    }
  }

  .sheet .head {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px 16px;
    border-bottom: 1px solid var(--myhome-divider);
  }

  .sheet .head h2 {
    margin: 0;
    font-size: 18px;
    font-weight: 500;
    flex: 1;
    min-width: 0;
  }

  .sheet .head button {
    width: 48px;
    height: 48px;
    flex: 0 0 48px;
    border: none;
    background: transparent;
    color: var(--myhome-text-soft);
    font-size: 20px;
    cursor: pointer;
    border-radius: 24px;
  }

  .sheet .body {
    flex: 1;
    overflow: auto;
    padding: 16px;
    padding-bottom: calc(16px + env(safe-area-inset-bottom, 0px));
  }
`;
