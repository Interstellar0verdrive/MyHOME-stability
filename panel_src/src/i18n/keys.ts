// Every `panel.*` key this bundle asks for, with the English words to use until the
// translation files have them.
//
// **This file is the texts lot's worklist.** Each key below goes into the new top-level
// `"panel"` block of `custom_components/myhome/strings.json` and of the seven files in
// `translations/`, where `tests/test_translations.py` then holds them key-for-key and
// placeholder-for-placeholder. The naming rules are the plan's: `panel.<view>.<element>`,
// lower snake case, buttons under `<view>.action.<verb>`, errors under
// `<view>.error.<reason>`, placeholders named for what they are and never positional.
//
// **The fallbacks are temporary and they are English on purpose.** The standing rule is
// that a missing key renders as the key, so that it looks like the bug it is; a panel
// shipped before its texts would then be four screens of dotted identifiers, which is
// worse for the one lot between the two. Every entry here is deleted by the texts lot,
// and `i18n.ts` prefers the server's answer for any key that has one, so a translated key
// always wins over the word beside it here.
//
// Origin words are deliberately **absent**: the panel reads
// `selector.calibration_origin.options.{measured,inherited,adjusted,from_the_file,defaults}`,
// which already exist in all eight files and already carry `{profile}`.

export const FALLBACK_TEXTS: Record<string, string> = {
  // --- panel.common: the words every screen uses -------------------------------------
  "panel.common.loading": "Loading…",
  "panel.common.all_rooms": "All rooms",
  "panel.common.search": "Search for a shutter",
  "panel.common.room_filter": "Filter by room",
  "panel.common.travel": "travel {travel} cm",
  "panel.common.travel_unknown": "travel not recorded",
  "panel.common.not_yet": "This screen arrives in a later version. Until then “Configure” does everything it will do.",
  "panel.common.offline": "Not connected to Home Assistant.",
  "panel.common.polling": "Live updates are not available on this version; the page refreshes by itself every 30 seconds.",
  "panel.common.action.menu": "Open the sidebar",
  "panel.common.action.configure": "Open Configure instead",
  "panel.common.action.back": "Back to the overview",
  "panel.common.action.close": "Close",
  "panel.common.action.retry": "Try again",

  // --- panel.overview: the management screen ------------------------------------------
  "panel.overview.title": "Profiles and shutters",
  "panel.overview.gateway": "Gateway {gateway}",
  "panel.overview.intro":
    "A **profile** describes a type of shutter: how long it takes to run, how long the slats take and how the curtain winds onto the roller. Every shutter can follow one, and Home Assistant scales it to that shutter's own travel.",
  "panel.overview.counts": "There are {profiles} profiles and {covers} basic shutters on this gateway.",
  "panel.overview.group_profile": "Profile “{profile}”",
  "panel.overview.group_none": "No profile",
  "panel.overview.group_none_meta":
    "Values from the configuration file, or the defaults. This is not an error: a shutter with measurements of its own is perfectly at home here.",
  "panel.overview.group_values":
    "Reference travel {travel} cm · ascent {up} s · descent {down} s · slats {slat} s",
  "panel.overview.group_values_unknown": "Nobody defines this profile, so it has no values.",
  "panel.overview.group_missing":
    "This profile is not defined any more: the shutters below have quietly fallen back to their own configuration.",
  "panel.overview.group_from_file": "Defined in the configuration file, and read-only from here.",
  "panel.overview.group_empty": "No shutter in this group.",
  "panel.overview.provenance": "Measured on {cover} · {date}",
  "panel.overview.provenance_unknown": "provenance not recorded",
  "panel.overview.provenance_gone": "Measured on a shutter this gateway no longer has · {date}",
  "panel.overview.provenance_follows": "now follows “{profile}”",
  "panel.overview.count_one": "1 shutter",
  "panel.overview.count_other": "{count} shutters",
  "panel.overview.row_profile_missing": "the profile “{profile}” is not defined any more",
  "panel.overview.row_from_file": "assigned by the configuration file",
  // The two short origin words. Everywhere else the panel renders the existing
  // `selector.calibration_origin.options.*`, which name the profile; inside the group of
  // that very profile the name is already in the heading, and the handoff asks for it not
  // to be repeated on every row. These two are the whole of that exception.
  "panel.overview.origin_short_inherited": "Inherited",
  "panel.overview.origin_short_adjusted": "Adjusted",
  "panel.overview.first_run_title": "No profile, for now",
  "panel.overview.first_run_body":
    "A **profile** describes a type of shutter: how long it takes to run, how long the slats take and how the curtain winds onto the roller. Every shutter can follow one, and Home Assistant scales it to that shutter's own travel.",
  "panel.overview.first_run_more":
    "A profile is not written, it is measured. Pick one representative shutter and measure it once with the guided calibration — about three minutes. Similar shutters can then follow it.",
  "panel.overview.measure_hint":
    "The “Configure” dialog opens: that is where the measuring happens. When it is done, the profile appears here.",
  "panel.overview.no_results": "No shutter matches this search.",
  "panel.overview.no_basic_covers":
    "No basic shutter on this gateway. Advanced shutters report their own position, so there is no travel model to measure.",
  "panel.overview.action.measure": "Measure a shutter ↗",
  "panel.overview.action.clear_filters": "Clear the search and the filter",
  "panel.overview.action.open_profile": "Open the profile card",
  "panel.overview.action.open_cover": "Open the details of {cover}",
  "panel.overview.handle_label": "Move {cover} to another group or reorder it",
  "panel.overview.handle_inert": "Assignment and reordering arrive in a later version",

  // --- panel.cover / panel.profile: routed here, built by a later lot -------------------
  "panel.cover.title": "Shutter “{cover}”",
  "panel.cover.unknown": "This gateway has no shutter with that identifier.",
  "panel.profile.title": "Profile “{profile}”",
  "panel.profile.unknown": "No profile of that name is defined or followed here.",

  // --- panel.banner: the states that sit above everything ------------------------------
  "panel.banner.measuring_title": "Measurement in progress",
  "panel.banner.measuring_body":
    "A guided calibration is using “{cover}”. Until that session ends, this page can only be read: nothing is written from here.",
  "panel.banner.action.resume": "Resume the session ↗",
  "panel.banner.action.terminate": "End it ↗",

  // --- panel.screen: the wizard's eight templates, which 0.7.0 fills --------------------
  "panel.screen.phase": "{phase} · {index} of {count}",
  "panel.screen.new_text": "new text — to be translated into seven languages",
  "panel.screen.not_in_this_version":
    "This step belongs to the guided calibration, which moves into the panel in a later version.",
  "panel.screen.motor": "Motor",
  "panel.screen.position": "Estimated position",
  "panel.screen.remaining": "Time remaining ≈ {seconds} s",
  "panel.screen.completed": "Completed",
  "panel.screen.before": "Before",
  "panel.screen.after": "After",
  "panel.screen.action.exit": "Leave the calibration",

  // --- panel.error: one sentence per refusal the backend can send -----------------------
  // The first is the panel's own; the rest are the `translation_key`s of
  // CONTRACT-0.6.0-ws.md §5 and §9.10, rendered as `panel.error.<translation_key>`.
  "panel.error.unreachable": "The panel could not read this gateway.",
  "panel.error.unknown_entry": "That gateway is not there any more.",
  "panel.error.entry_not_loaded": "That gateway is configured but not loaded, so its shutters cannot be read.",
  "panel.error.unknown_cover": "That shutter is not on this gateway.",
  "panel.error.advanced_cover": "That shutter reports its own position: there is no travel model to show.",
  "panel.error.busy_calibrating": "A guided calibration is using “{cover}”: nothing can be written until it ends.",
  "panel.error.write_in_progress": "Another change to this gateway is still being applied.",
  "panel.error.profile_not_editable": "The profile “{profile}” is written in the configuration file, which this integration does not change.",
  "panel.error.unknown_profile": "No profile named “{profile}” is stored here.",
  "panel.error.undo_expired": "That change can no longer be taken back.",
  "panel.error.missing_travel": "The travel of {count} shutters is not known yet.",
  "panel.error.invalid_name": "“{profile}” is not a usable profile name: letters, digits and underscores.",
  "panel.error.name_in_use": "“{profile}” is already taken.",
  "panel.error.out_of_range": "{key} must be between {min} and {max}.",
  "panel.error.not_a_number": "{key} takes a number; decimals with a comma or a dot.",
};

/** The key list itself, for anybody who wants to walk it. */
export const FALLBACK_KEYS: readonly string[] = Object.keys(FALLBACK_TEXTS);
