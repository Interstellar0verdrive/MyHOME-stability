// `lettura` - a step that only reads: a title, a drawing, some prose and the way on.
//
// It is the plainest of the eight and the one 0.6.0 actually uses: the first-run welcome,
// "no basic shutters", "that gateway is not loaded", and every screen whose whole job is to
// say something before offering a button. The text and the drawing are rendered by the host
// (they are common to all eight); what belongs to this template is the operative column,
// and for a reading step that column is empty - the footer's buttons are the step.

import { html, nothing, type TemplateResult } from "lit";

import type { ScreenContext, ScreenModel } from "../engine/screen";

export const renderLettura = (
  model: ScreenModel,
  _context: ScreenContext,
): TemplateResult | typeof nothing => {
  if (!model.summary?.note) {
    return nothing;
  }
  // A reading step occasionally carries one aside - "this is what will happen next" - and
  // the operative column is where it goes, so that the prose above stays prose.
  return html`<div class="stub">${model.summary.note}</div>`;
};
