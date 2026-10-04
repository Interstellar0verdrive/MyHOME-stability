/**
 * The drawings of the calibration wizard (A-05, A-06, A-07…), one per illustration id.
 *
 * The screens pick an id per mockup code (`screen.illustration`); this module is the only place that
 * knows what an id looks like: an inline SVG from `panel-calibration-illustrations-svg.js` (generated from
 * the Figma exports), drawn at the Figma size (1×) and shrinking with the column on a phone. Its colours are
 * the `--wiz-ill-*` properties of the wizard, light or dark with the Home Assistant theme.
 * Never a picture of the live position: the same drawing for every cover and every moment of the step.
 */
const asset = (name) => { const url = new URL(name, import.meta.url); url.search = new URL(import.meta.url).search; return url.href; };
const { SVG } = await import(asset("panel-calibration-illustrations-svg.js"));

/** Width and height in px of each drawing in the Figma frames, rounded. */
export const ILLUSTRATIONS = {
  "window-closed": { width: 259, height: 250 },
  "two-runs": { width: 560, height: 346 },
  "lift-sequence": { width: 560, height: 160 },
  "descent-sequence": { width: 560, height: 142 },
  "ascent-sequence": { width: 560, height: 142 },
  "lift-zoom": { width: 289, height: 222 },
  "curtain-open-tape": { width: 207, height: 200 },
  "curtain-partial-tape": { width: 207, height: 200 },
  check: { width: 208, height: 200 },
};

export { SVG };

/** The drawing of one illustration id, described as a whole for assistive technology. */
export function illustrationMarkup(id, label, escape) {
  const size = ILLUSTRATIONS[id], svg = SVG[id];
  if (!size || !svg) return "";
  // The ratio is set too: with only width and height attributes some browsers (Safari) keep the full height when the
  // column is narrower than the drawing, and it overlaps the text under it.
  return svg.replace(/^<svg /, `<svg class="wiz-illustration" data-illustration="${escape(id)}" role="img" aria-label="${escape(label)}" width="${size.width}" height="${size.height}" style="width: min(100%, ${size.width}px); aspect-ratio: ${size.width} / ${size.height}" focusable="false" `);
}
