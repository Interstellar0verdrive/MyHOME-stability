// The sentences, in the user's language, out of the seven files that already exist.
//
// `myhome/calibration/texts` resolves the fallback chain server-side (`it-CH` -> `it`,
// unknown -> `en`) and answers with the whole `options` / `selector` block of that
// language, plus - from the texts lot on - a top-level `panel` block. Nothing is
// translated here and no sentence is compiled into the bundle: one source of truth,
// already policed by `tests/test_translations.py`, and a language the *user* chose
// rather than the one the server runs in.

import { type HaConnection } from "../types/ha";
import { texts as fetchTexts, type Texts } from "./ws";

export class I18n {
  private _texts: Record<string, unknown> = {};

  /** The language actually served, after the fallback chain. */
  language = "en";

  async load(connection: HaConnection, requested: string): Promise<void> {
    const answer: Texts = await fetchTexts(connection, requested);
    this._texts = answer.texts ?? {};
    this.language = answer.language;
  }

  /**
   * `t("panel.overview.title")` - the sentence, or the key.
   *
   * A missing key renders as the key on purpose: it has to look like a bug, because it
   * is one. `fallback` is the single exception and a temporary one - the panel lot ships
   * before the texts lot writes the `panel.*` block, so the skeleton carries the two or
   * three English words it needs to render at all. Every call that passes a fallback is
   * a call the texts lot deletes.
   */
  t(key: string, fallback?: string): string {
    let node: unknown = this._texts;
    for (const part of key.split(".")) {
      if (node === null || typeof node !== "object") {
        return fallback ?? key;
      }
      node = (node as Record<string, unknown>)[part];
    }
    return typeof node === "string" ? node : (fallback ?? key);
  }
}
