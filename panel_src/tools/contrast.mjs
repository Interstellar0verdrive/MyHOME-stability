// `npm run contrast` - the contrast of every coloured surface in the panel, in both themes.
//
// jsdom resolves no CSS variable and computes no layout, so axe's `color-contrast` rule
// cannot run in `tools/a11y.mjs` and is disabled there rather than passed silently. This is
// the other half: the same pairs, worked out from the **documented default values** of the
// theme variables - `engine/theme.ts`'s own fallbacks for the light theme, which are Home
// Assistant's defaults, and the dark values `dev/harness.html` uses, which are Home
// Assistant's dark theme.
//
// The pastels are `color-mix(in srgb, var(--X) N%, var(--card-background-color))`, and
// `color-mix` in sRGB with two opaque colours is a straight interpolation of the sRGB
// components - which is what `mix` below does. The luminance and the ratio are WCAG 2.1's
// own formulas, with no library: they are eight lines and a dependency for them would be
// a dependency to keep in step.
//
// A theme the user installed can break any of this, and nothing in the panel can stop it:
// what is asserted here is that the design's palette is AA where the design says it is.

const hex = (value) => {
  const text = value.replace("#", "");
  const full = text.length === 3 ? [...text].map((c) => c + c).join("") : text;
  return [0, 2, 4].map((at) => parseInt(full.slice(at, at + 2), 16) / 255);
};

/** `color-mix(in srgb, colour N%, ground)`. */
const mix = (colour, ground, percent) =>
  hex(colour).map((channel, index) => (channel * percent + hex(ground)[index] * (100 - percent)) / 100);

const luminance = (rgb) => {
  const [r, g, b] = rgb.map((c) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
};

const ratio = (a, b) => {
  const one = luminance(Array.isArray(a) ? a : hex(a));
  const two = luminance(Array.isArray(b) ? b : hex(b));
  return (Math.max(one, two) + 0.05) / (Math.min(one, two) + 0.05);
};

/**
 * Home Assistant's own light theme, which is what `engine/theme.ts` falls back to.
 *
 * Every value here is the default Home Assistant itself defines, and that is the point:
 * a fallback the panel invents is a colour nobody ever sees, because the theme defines
 * the variable and the fallback never fires. `--warning-color` used to be read here as
 * a darker amber than Home Assistant's `#ffa600`, and the run said the panel was AA about
 * a colour it does not paint.
 */
const LIGHT = {
  name: "light",
  primary: "#03a9f4",
  accent: "#ff9800",
  text: "#212121",
  soft: "#727272",
  off: "#bdbdbd",
  background: "#fafafa",
  backgroundSoft: "#e5e5e5",
  card: "#ffffff",
  error: "#db4437",
  warning: "#ffa600",
  success: "#43a047",
  info: "#039be5",
  onPrimary: "#ffffff",
  divider: "#e0e0e0",
};

/**
 * The words on the one amber button, which are a fixed near-black in both themes.
 *
 * `engine/theme.ts`'s `--myhome-text-on-accent`, and the one literal colour the panel
 * paints. The pair it makes with `--accent-color` is measured below in both themes,
 * because it is the button of a press timed to a tenth of a second.
 */
const ON_ACCENT = "#1a1a1a";

/** ...and its dark theme, which is what `dev/harness.html` paints. */
const DARK = {
  name: "dark",
  primary: "#4fc3f7",
  accent: "#ffb74d",
  text: "#e1e1e1",
  soft: "#9b9b9b",
  off: "#6f6f6f",
  background: "#111111",
  backgroundSoft: "#333333",
  card: "#1c1c1c",
  error: "#ef5350",
  warning: "#ffb04c",
  success: "#66bb6a",
  info: "#4fc3f7",
  onPrimary: "#0b1417",
  divider: "#3a3a3a",
};

/**
 * Every pair of ink and ground the panel draws, with the size the text is at.
 *
 * `large` is WCAG's own definition - 18.66 px bold or 24 px - and the panel has none: the
 * biggest coloured text on it is the 17 px group title. So every line below is held to
 * 4.5:1, which is the stricter reading and the one worth reporting.
 */
/**
 * `--myhome-<x>-ink`: the colour, half of it, over the theme's own text colour.
 *
 * The percentage is `engine/theme.ts`'s and has to stay in step with it. It is 50 and not
 * 60 because of one pair: amber. Home Assistant's default `--warning-color` is `#ffa600`,
 * the lightest of the five, and at 60 % of itself it is 4.21:1 on a white card - under AA
 * at the 12.5 px the sentence about a profile nobody defines is drawn at.
 */
const ink = (t, colour) => mix(colour, t.text, 50);

/**
 * `--myhome-snack-action`: the word "Annulla" on a strip that inverts the theme.
 *
 * The strip's ground is `--primary-text-color` and its text is `--primary-background-color`,
 * so the one thing an action colour can be sure of is that moving towards the *text*
 * colour moves it away from the ground - in both themes, which is the point. 40 % is the
 * number at which the darker of the two (a dark theme's near-white strip) clears 4.5:1.
 *
 * Until 14 September this was a literal per theme - `#ffc107` for light, `#8a5300` for
 * dark - and the dark one was `dev/harness.html`'s invention. Home Assistant defines
 * `--snack-action-color` nowhere, so what a real dark installation used was the amber
 * fallback on a near-white strip: 1.6:1, and unreadable, which is what the first live
 * pass found. A check that measured the harness's number and not the panel's was the
 * reason nothing caught it.
 */
const snackAction = (t) => mix(t.accent, t.background, 40);

const pairs = (t) => [
  ["chip, neutral (Inherited / From the file / Defaults)", ink(t, t.soft), t.backgroundSoft, 12],
  ["chip, Measured", t.text, mix(t.primary, t.card, 20), 12],
  ["chip, Adjusted", t.text, mix(t.accent, t.card, 18), 12],
  ["chip, the pending route", ink(t, t.primary), mix(t.primary, t.card, 10), 12],
  ["row name", t.text, t.card, 14.5],
  ["row second line", t.soft, t.card, 12.5],
  ["group values and provenance", t.soft, t.card, 13],
  ["a cover on a profile nobody defines", ink(t, t.warning), t.card, 12.5],
  ["the note about own values", ink(t, t.info), t.card, 12.5],
  ["secondary button", ink(t, t.primary), t.card, 15],
  ["a wide button on the two cards", ink(t, t.primary), mix(t.primary, t.card, 10), 14],
  ["destructive button", ink(t, t.error), mix(t.error, t.card, 14), 15],
  ["a field error", ink(t, t.error), t.card, 12.5],
  ["the measuring banner", t.text, mix(t.warning, t.card, 12), 14],
  // The origin chip an option of the choice of shutter carries, which is the overview's
  // own chip inside a template (lot F3).
  ["a measured shutter's chip in the choice of shutter", t.text, mix(t.primary, t.card, 20), 12],
  ["an adjusted shutter's chip in the choice of shutter", t.text, mix(t.accent, t.card, 18), 12],
  ["the banner's two offers", ink(t, t.primary), mix(t.warning, t.card, 12), 14],
  // The offer that ends somebody's calibration, which is the one the panel spells out in
  // the error colour rather than leaving it to read like the other one (lot F3).
  ["the banner's offer that ends a calibration", ink(t, t.error), mix(t.warning, t.card, 12), 14],
  ["the applying / undo strip", t.background, t.text, 14],
  ["the word Annulla on that strip", snackAction(t), t.text, 14],
  ["the offline banner", t.text, mix(t.warning, t.card, 12), 14],
  ["the advanced parameters note of a hand edit", t.text, mix(t.warning, t.card, 12), 13],
  ["the refusal card", t.text, mix(t.error, t.card, 12), 14],
  ["page text on the page background", t.text, t.background, 14],
  // --- the guided calibration (lot F2) -----------------------------------------------
  ["the big button while the shutter is moving", ON_ACCENT, t.accent, 16],
  ["the note of a press that was registered", t.text, mix(t.success, t.card, 12), 14],
  ["the note of a reading that no longer matches", t.text, mix(t.error, t.card, 12), 14],
  ["the note about a movement from outside", t.text, mix(t.info, t.card, 12), 14],
  ["the strip of a calibration somebody else is driving", t.text, mix(t.warning, t.card, 12), 13.5],
  ["the switch for the signal at the start", t.soft, t.card, 13.5],
  ["the motor line while it is running", ink(t, t.warning), t.card, 14],
  ["the seconds left of a positioning run", t.soft, t.card, 13],
  ["the review's lines under its rows", t.soft, t.card, 12.5],
  ["the name of a value in the review", t.soft, t.card, 13.5],
  ["a value the save would write", t.text, t.card, 13.5],
  // The three faces an outcome screen wears: a glyph at 18 px and 600, which WCAG's own
  // definition of large text (18.66 px bold) does not reach, so they are held to 4.5:1.
  ["the outcome's face, saved", ink(t, t.success), mix(t.success, t.card, 12), 18],
  ["the outcome's face, cancelled", ink(t, t.error), mix(t.error, t.card, 12), 18],
  ["the outcome's face, timed out", ink(t, t.warning), mix(t.warning, t.card, 12), 18],
  // The screen every number of a calibration is written on. It was missing from this list,
  // and that is the hole a whole-screen defect went through: the label and the value were
  // white on a white card because the field's card took the filled button's colour. The
  // rule that made that possible is caught by `npm run session`, which reads what really
  // reaches the element; these two lines are what the colours are supposed to be.
  ["the label of a tape reading", t.text, t.card, 13.5],
  ["the number typed into it, and its caret", t.text, t.card, 32],
  ["its unit, beside the field", t.soft, t.card, 18],
  ["the buttons of the question the cross asks", ink(t, t.primary), mix(t.primary, t.card, 10), 13.5],
  ["and the one that leaves without saving", ink(t, t.error), mix(t.error, t.card, 14), 13.5],
];

/**
 * WCAG's large text - 18.66 px bold or 24 px - held to 3:1 rather than to 4.5:1.
 *
 * The panel had none until 14 September. The profile's name at the head of a group is
 * 19 px and 700 now, and is painted in the theme's own `--primary-color` rather than in
 * the mixed ink lot 9 gave it: the decision of the first live pass, which read the ink on
 * a real theme and found a grey-blue where the rest of Home Assistant paints its primary.
 */
const largeText = (t) => [
  ["the profile's name at the head of a group", t.primary, t.card, "19 px / 700"],
];

/**
 * The things that are seen rather than read: WCAG 1.4.11 asks 3:1 of them against what
 * they sit on. They are the drag's own vocabulary, so a reader who cannot see a 2.6:1
 * dashed outline cannot see where a shutter is going.
 */
const indicators = (t) => [
  ["the focus ring", ink(t, t.primary), t.card],
  ["the focus ring, on the page background", ink(t, t.primary), t.background],
  ["the pending outline and the insertion line", ink(t, t.primary), t.card],
  ["the drop target's outline", ink(t, t.primary), t.card],
  ["a field's border", mix(t.soft, t.card, 80), t.card],
  ["a field's border when it is refused", ink(t, t.error), t.card],
  // What sets the advanced note apart from the intro box above it, so it has to be seen.
  ["the advanced note's left rule, on the card", ink(t, t.warning), t.card],
  ["the advanced note's left rule, on its own ground", ink(t, t.warning), mix(t.warning, t.card, 12)],
];

/** What the panel cannot fix from inside a theme, measured and reported all the same. */
const theirs = (t) => [
  ["the filled primary button (--text-primary-color on --primary-color)", t.onPrimary, t.primary],
  ["the profile's name, large, on a card (--primary-color)", t.primary, t.card],
];

let failures = 0;
for (const theme of [LIGHT, DARK]) {
  console.log(`\n${theme.name} - text, held to 4.5:1 (WCAG 1.4.3 AA)`);
  for (const [what, front, ground, size] of pairs(theme)) {
    const value = ratio(front, ground);
    const ok = value >= 4.5;
    if (!ok) {
      failures += 1;
    }
    console.log(
      `  ${ok ? "AA " : "✖  "} ${value.toFixed(2).padStart(5)}:1  ${what} (${size} px)`,
    );
  }
  console.log(`${theme.name} - large text, held to 3:1 (WCAG 1.4.3 AA)`);
  for (const [what, front, ground, size] of largeText(theme)) {
    const value = ratio(front, ground);
    // Reported and not counted, for the reason under `theirs` below: this is Home
    // Assistant's own colour on Home Assistant's own card, and the panel diverging from
    // it alone would be a panel that looks unlike the app it is in.
    console.log(`  ${value >= 3 ? "AA " : "!  "} ${value.toFixed(2).padStart(5)}:1  ${what} (${size})`);
  }
  console.log(`${theme.name} - indicators, held to 3:1 (WCAG 1.4.11 AA)`);
  for (const [what, front, ground] of indicators(theme)) {
    const value = ratio(front, ground);
    const ok = value >= 3;
    if (!ok) {
      failures += 1;
    }
    console.log(`  ${ok ? "AA " : "✖  "} ${value.toFixed(2).padStart(5)}:1  ${what}`);
  }
}

// Reported without a verdict, and deliberately not counted.
//
// A disabled control is exempt from 1.4.3, and the filled primary button is Home
// Assistant's own: --text-primary-color on --primary-color is the pair the design names,
// the pair every button in the frontend uses, and one this panel must not quietly diverge
// from. In Home Assistant's default light theme that pair is 2.63:1 - which is a finding
// about the theme, fixed for the whole installation by a theme and by nothing the panel
// can do alone. It is in the handoff as an open point for the maintainer.
console.log("\nnot counted, and why:");
for (const theme of [LIGHT, DARK]) {
  console.log(
    `  ${theme.name}: disabled control text ${ratio(theme.off, theme.backgroundSoft).toFixed(2)}:1` +
      "  (1.4.3 exempts it)",
  );
  for (const [what, front, ground] of theirs(theme)) {
    console.log(`  ${theme.name}: ${ratio(front, ground).toFixed(2)}:1  ${what}`);
  }
  // The filled bar of a positioning screen, for the same reason as the filled button: it
  // is Home Assistant's own `--primary-color` on Home Assistant's own
  // `--secondary-background-color`, the pair the design names and the pair every progress
  // bar in the frontend uses. It is also not the only way the screen says how far along it
  // is - the bar carries `role="progressbar"` with `aria-valuenow`, and the seconds left
  // are written under it in text that is measured above.
  console.log(
    `  ${theme.name}: ${ratio(theme.primary, theme.backgroundSoft).toFixed(2)}:1` +
      "  the positioning bar's fill on its track (--primary-color on --secondary-background-color)",
  );
}

console.log(`\n${failures} pair${failures === 1 ? "" : "s"} under 4.5:1`);
process.exit(failures === 0 ? 0 : 1);
