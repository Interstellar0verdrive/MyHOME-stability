// The sentences, in the user's language, out of the eight files that already exist.
//
// `myhome/calibration/texts` resolves the fallback chain server-side (`it-CH` -> `it`,
// unknown -> `en`) and answers with the whole `options` and `selector` blocks of that
// language, plus the top-level `panel` block the texts lot writes. Nothing is translated
// here: one source of truth, already policed by `tests/test_translations.py`, and a
// language the *user* chose rather than the one the server runs in.
//
// Two things this class does beyond looking a key up.
//
// **Placeholders.** `t("panel.overview.group.measured_on", {cover: "…", date: "…"})`. They
// are named, never positional, because a translator reorders a sentence and a number does
// not survive that.
//
// **An offline English fallback.** The standing rule is that a missing key renders as the
// key. `src/i18n/keys.ts` suspends it for the `panel.*` block only, and for one reason: a
// panel whose `texts` call has not answered yet - or could not - would otherwise be four
// screens of dotted identifiers. Those words are English on purpose and they are the
// English file's own, key for key (`tests/test_translations.py`); the server's answer
// always wins where it has one, so a key that exists is never shadowed by the word beside
// it in that file. A key in neither place still renders as itself.

import { FALLBACK_TEXTS } from "../i18n/keys";
import { type HaConnection } from "../types/ha";
import { renderMarkdown } from "./markdown";
import { texts as fetchTexts, type Texts } from "./ws";
import { type TemplateResult } from "lit";

export type Placeholders = Record<string, string | number>;

const fill = (sentence: string, placeholders?: Placeholders): string => {
  if (!placeholders) {
    return sentence;
  }
  let out = sentence;
  for (const [name, value] of Object.entries(placeholders)) {
    out = out.split(`{${name}}`).join(String(value));
  }
  return out;
};

export class I18n {
  private _texts: Record<string, unknown> = {};
  private _numbers = new Map<number, Intl.NumberFormat>();
  private _dates: Intl.DateTimeFormat | null = null;

  /** The language actually served, after the fallback chain. */
  language = "en";

  /** True once the backend has answered at least once. */
  loaded = false;

  async load(connection: HaConnection, requested: string): Promise<void> {
    const answer: Texts = await fetchTexts(connection, requested);
    this._texts = answer.texts ?? {};
    this.language = answer.language;
    this.loaded = true;
    this._numbers.clear();
    this._dates = null;
  }

  /** `t("panel.overview.title")` - the sentence, the English stand-in, or the key. */
  t(key: string, placeholders?: Placeholders): string {
    const served = this._lookup(key);
    if (served !== null) {
      return fill(served, placeholders);
    }
    const stopgap = FALLBACK_TEXTS[key];
    return fill(stopgap ?? key, placeholders);
  }

  /** The same sentence, rendered as the little Markdown the texts contain. */
  md(key: string, placeholders?: Placeholders): TemplateResult {
    return renderMarkdown(this.t(key, placeholders));
  }

  /**
   * The sentence behind a refusal, which is **not** duplicated under `panel.*` either.
   * Every `send_error` of the panel's API carries `translation_domain: "myhome"` and a
   * `translation_key`, and Home Assistant resolves that pair against the top-level
   * `exceptions` block - `component.myhome.exceptions.<key>.message`. That block travels
   * in the same answer, so the panel says exactly what Home Assistant would say. A key
   * the files do not carry (or a failure with no key at all) falls back to the panel's
   * own sentence about a gateway it could not read.
   */
  refusal(key: string | null | undefined, placeholders?: Placeholders): string {
    const served = key ? this._lookup(`exceptions.${key}.message`) : null;
    if (served !== null) {
      return fill(served, placeholders);
    }
    return this.t("panel.error.not_found");
  }

  /**
   * The origin words, which are **not** duplicated under `panel.*`: they already exist as
   * `selector.calibration_origin.options.*` in all eight files, and they already carry the
   * profile name. The panel renders the server's token, never its own idea of one.
   */
  origin(token: string, profile: string | null): string {
    return this.t(`selector.calibration_origin.options.${token}`, { profile: profile ?? "" });
  }

  /** A number, in the user's language, with the decimals the value deserves. */
  number(value: number, decimals: number): string {
    let formatter = this._numbers.get(decimals);
    if (!formatter) {
      formatter = new Intl.NumberFormat(this.language, {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      });
      this._numbers.set(decimals, formatter);
    }
    return formatter.format(value);
  }

  /** An ISO-8601 instant as a date, in the user's language. Time of day is never the point. */
  date(iso: string): string {
    const when = new Date(iso);
    if (Number.isNaN(when.getTime())) {
      return iso;
    }
    if (!this._dates) {
      this._dates = new Intl.DateTimeFormat(this.language, { dateStyle: "long" });
    }
    return this._dates.format(when);
  }

  private _lookup(key: string): string | null {
    let node: unknown = this._texts;
    for (const part of key.split(".")) {
      if (node === null || typeof node !== "object") {
        return null;
      }
      node = (node as Record<string, unknown>)[part];
    }
    return typeof node === "string" ? node : null;
  }
}
