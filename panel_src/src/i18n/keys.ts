// Every `panel.*` key this bundle asks for, with the English sentence to show when the
// server has not answered.
//
// **The words live in `fallback.json`, and that is deliberate.** They are a copy of the
// English `config_panel` block, key for key, and `tests/test_translations.py` holds them
// to it: `test_the_bundle_asks_only_for_keys_the_files_have` fails if a key here is not in
// `strings.json`, and `test_the_offline_stand_ins_are_the_english_sentences` fails if a
// word drifts. A Python suite that runs with no Node can read JSON exactly; it can only
// guess at a TypeScript object literal with sentences wrapped over three lines in it, and
// a guard that guesses is a guard that is quietly wrong one day.
//
// **Why a stand-in at all.** The standing rule is that a missing key renders as the key,
// so that it looks like the bug it is. It stays the rule for a key the files do not have.
// What this file covers is the other case: the panel paints before `myhome/calibration/
// texts` has answered, and it paints when that call fails, and four screens of dotted
// identifiers is not a better answer than four screens of English. `engine/i18n.ts`
// prefers the server's sentence for every key that has one, so a translated key is never
// shadowed by the word beside it here.
//
// **What is not here.** The five origin phrases
// (`selector.calibration_origin.options.*`), the six value labels
// (`options.step.calibration_edit.data.*`) and the fourteen refusals
// (`exceptions.<key>.message`) are read out of the blocks the same answer carries. The
// panel is forbidden from keeping its own copy of a sentence the guided flow already
// says, and a fallback is a copy.
//
// The list is **exactly what this bundle asks for today** - no key is written ahead of
// the code that reads it, which is the decision of 13 September about dead keys applied
// to this file too. Lots 7 and 8 add their own as they add the screens that need them,
// in `strings.json`, `translations/en.json` and `translations/it.json` first.

import stand_ins from "./fallback.json";

export const FALLBACK_TEXTS: Record<string, string> = stand_ins;

/** The key list itself, for anybody who wants to walk it. */
export const FALLBACK_KEYS: readonly string[] = Object.keys(FALLBACK_TEXTS);
