/**
 * The drawings of the calibration wizard (A-05, A-06, A-07…), one per illustration id.
 *
 * The screens pick an id per mockup code (`screen.illustration`); this module is the only place that
 * knows what an id looks like. Today every id is a neutral box with the size of its Figma drawing;
 * the drawings exported from Figma replace the boxes here, in `DRAWINGS`, without touching the screens.
 * Never a picture of the live position: the same drawing for every cover and every moment of the step.
 */

/** Width and height in px of each drawing in the Figma frames (sequences span the column, up to 564 px). */
export const ILLUSTRATIONS = {
  "window-closed": { width: 260, height: 250 },
  "two-runs": { width: 564, height: 340 },
  "lift-sequence": { width: 564, height: 150 },
  "descent-sequence": { width: 564, height: 150 },
  "ascent-sequence": { width: 564, height: 150 },
  "lift-zoom": { width: 285, height: 220 },
  "curtain-open-tape": { width: 235, height: 225 },
  "curtain-partial-tape": { width: 210, height: 195 },
  check: { width: 200, height: 195 },
};

/** Inline SVG per id, once exported from Figma; an id without one is drawn as a placeholder box. */
const DRAWINGS = {};

/** The figure of one illustration id, described as a whole for assistive technology. */
export function illustrationMarkup(id, label, escape) {
  const size = ILLUSTRATIONS[id];
  if (!size) return "";
  const drawing = DRAWINGS[id];
  return `<figure class="wiz-illustration${drawing ? "" : " is-placeholder"}" data-illustration="${escape(id)}" role="img" aria-label="${escape(label)}"
    style="--wiz-illustration-width: ${size.width}px; --wiz-illustration-ratio: ${size.width} / ${size.height};">${drawing || ""}</figure>`;
}
