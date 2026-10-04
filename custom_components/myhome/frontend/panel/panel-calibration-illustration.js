/**
 * The drawings of the calibration wizard (A-05, A-06, A-07…), one per illustration id.
 *
 * The screens pick an id per mockup code (`screen.illustration`); this module is the only place that
 * knows what an id looks like: a lossless WebP in `illustrations/<id>.webp`, exported from the Figma
 * frames at twice their size and drawn at the Figma size (1×), shrinking with the column on a phone.
 * Never a picture of the live position: the same drawing for every cover and every moment of the step.
 */

/** Width and height in px of each drawing in the Figma frames, rounded (the files are twice as large). */
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

/** The file of an id, with the panel's build token like every other panel asset. */
export function illustrationUrl(id) {
  const url = new URL(`illustrations/${id}.webp`, import.meta.url);
  url.search = new URL(import.meta.url).search;
  return url.href;
}

/** The image of one illustration id, described as a whole for assistive technology. */
export function illustrationMarkup(id, label, escape) {
  const size = ILLUSTRATIONS[id];
  if (!size) return "";
  return `<img class="wiz-illustration" data-illustration="${escape(id)}" src="${escape(illustrationUrl(id))}" width="${size.width}" height="${size.height}" alt="${escape(label)}" decoding="async">`;
}
