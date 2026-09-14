// The amber banner: a guided calibration has one of these shutters, so everything here is
// read-only until it lets go.
//
// It is a `role="status"` region with `aria-live="polite"`, not an alert: it is a standing
// condition of the page rather than an event, and a user who arrives mid-session must meet
// it rather than be interrupted by it. It is announced **before** anything is attempted -
// `overview.measuring` carries the shutter's name, and the subscription pushes the change
// the moment the flow takes or releases one - so the refusal the backend would send is a
// backstop the user never has to read (contract §8, R-W1).
//
// Both links leave for the options flow, which is where a running session can be resumed or
// ended. They are plain `<a href>`: the integration page always exists, needs no private
// frontend API, and a link the user can see the destination of beats a button that changes
// their environment silently.

import { css, html, type TemplateResult } from "lit";

import { type I18n } from "../engine/i18n";

export const measuringBannerStyles = css`
  .measuring {
    max-width: 1200px;
    margin: 16px auto 0;
    padding: 12px 16px;
    border-radius: var(--myhome-radius);
    background: var(--myhome-warning-pastel);
    display: flex;
    gap: 12px;
    align-items: baseline;
    flex-wrap: wrap;
  }

  .measuring strong {
    color: var(--myhome-warning-ink);
    font-weight: 500;
  }

  .measuring .body {
    flex: 1 1 320px;
    line-height: 1.5;
  }

  .measuring .links {
    display: flex;
    gap: 16px;
  }

  .measuring a {
    color: var(--myhome-primary-ink);
    min-height: 44px;
    display: inline-flex;
    align-items: center;
  }
`;

export const measuringBanner = (i18n: I18n, coverName: string, flowUrl: string): TemplateResult =>
  html`<div class="measuring" role="status" aria-live="polite">
    <strong>${i18n.t("panel.banner.measuring.title")}</strong>
    <span class="body">${i18n.t("panel.banner.measuring.body", { cover: coverName })}</span>
    <span class="links">
      <a href=${flowUrl}>${i18n.t("panel.banner.measuring.action.resume")}</a>
      <a href=${flowUrl}>${i18n.t("panel.banner.measuring.action.stop")}</a>
    </span>
  </div>`;
