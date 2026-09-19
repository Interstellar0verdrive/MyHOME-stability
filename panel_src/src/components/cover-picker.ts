// "Which shutter is being measured?" - the screen `#/calibrate` shows when the gateway
// has no session on it.
//
// It is a model and not an element. The design draws it as one of the wizard's own
// screens (`Wizard Calibrazione.dc.html`, `vista: scelta-tapparella`) and SPEC §5.3 gives
// it the `scelta` template, so what it needs is the one thing every other screen of the
// wizard is: a `ScreenModel` that `<myhome-screen>` draws. Built as a pure function it is
// testable with `node --test` and it inherits the responsive law, the keyboard order and
// the announcements from the engine instead of restating them.
//
// **It reads the overview and nothing else** (SPEC §5.1). `overview.covers` is already
// every *basic* shutter of the gateway - the server filters them, `panel_data.basic_covers`
// - so the list is the list, and the panel neither works out nor filters which shutters a
// travel model applies to.
//
// **The second line and the chip are the overview's own.** The room and the travel are
// `subtitle()` from the row component and the origin is `originChip`'s label, both out of
// sentences that already exist in all seven languages. A second wording for "Cucina ·
// corsa 195 cm" would be a second thing to translate and a second thing to drift.
//
// **Nothing here starts anything.** Pressing an option fires `cover:<unique_id>`; what
// that means is `views/wizard.ts`'s business and, through it, the shell's - the same
// arrangement every other screen has, and the reason a reload of this address cannot set
// a shutter moving.

import { type I18n } from "../engine/i18n";
import { type ScreenModel, type ScreenOption } from "../engine/screen";
import { type CoverRow } from "../engine/ws";
import { CLOSE } from "../wizard/model";
import { coverSubtitle } from "./cover-row";

/** The prefix an option of this screen fires with, the way `act:` and `pick:` do. */
export const COVER = "cover:";

/** The unique id inside a `cover:` action, or `null` when the action is not one. */
export const coverOf = (action: string): string | null =>
  action.startsWith(COVER) ? action.slice(COVER.length) : null;

/**
 * The short form of the origin, which is what the design's chips say.
 *
 * `i18n.origin` gives the long sentence ("Ereditata dal profilo «Alte»"), which is right
 * in a detail card and too long for a chip in a list of four. The two short words already
 * exist for the overview's own rows; the other three origins have no short form because
 * they have no profile to leave out of one.
 */
const originLabel = (i18n: I18n, cover: CoverRow): string =>
  cover.origin === "inherited"
    ? i18n.t("panel.overview.cover.origin_inherited")
    : cover.origin === "adjusted"
      ? i18n.t("panel.overview.cover.origin_adjusted")
      : i18n.origin(cover.origin, cover.profile);

/**
 * The choice of shutter, as a screen of the wizard.
 *
 * `covers` arrives in the order the overview gives it, which is the order the file and the
 * user's own arrangement put them in: this screen does not re-sort a list somebody has
 * already arranged.
 */
export const coverPickerModel = (i18n: I18n, covers: readonly CoverRow[]): ScreenModel => {
  const options: ScreenOption[] = covers.map((cover) => ({
    title: cover.name,
    meta: coverSubtitle(i18n, cover, false),
    chip: originLabel(i18n, cover),
    action: `${COVER}${cover.unique_id}`,
  }));
  return {
    // Not a `panel.…` key: the id names the screen for the event it fires, and the two
    // sentences it draws are asked for explicitly below.
    id: "wizard.pick",
    model: "scelta",
    title: i18n.t("panel.wizard.pick.title"),
    body: i18n.t("panel.wizard.pick.body"),
    options,
    // The way out of a screen nobody has to be on. The wizard's ✕ belongs to a running
    // session and there is none here, so the footer carries the panel's own "Back".
    secondary: [{ label: i18n.t("panel.common.action.back"), action: CLOSE, kind: "text" }],
    announce: i18n.t("panel.wizard.pick.title"),
  };
};
