/** Text helpers shared by the Calibration tab and the calibration wizard. Strings never carry HTML. */
const url = new URL("panel-dom.js", import.meta.url);
url.search = new URL(import.meta.url).search;
const { escapeHtml: esc } = await import(url.href);

/** `{name}` placeholders from `values`; a missing value keeps the placeholder visible to tests. */
export function fill(text, values = {}) {
  return String(text).replace(/\{(\w+)\}/g, (match, key) => values[key] == null ? match : String(values[key]));
}

/** Escaped text with `**bold**` spans and blank-line paragraphs: the only markup the texts use. */
export function rich(text, values) {
  const paragraphs = fill(text, values).split(/\n\s*\n/).map((part) => part.trim()).filter(Boolean);
  return paragraphs.map((part) => `<p>${inline(part)}</p>`).join("");
}

/** One paragraph, without the wrapping `<p>`: line breaks become `<br>`. */
export function inline(text, values) {
  const escaped = esc(fill(text, values));
  // A span may cross a line break (`**text.\n**`): the break stays inside the bold run.
  return escaped.replace(/\*\*([\s\S]+?)\*\*/g, (match, inner) => inner.trim() ? `<strong>${inner.trim()}</strong>` : "")
    .replace(/\*\*/g, "").replace(/\n/g, "<br>");
}

/** A localized number: tenths of a second or centimetre unless `digits` says otherwise. */
export function number(value, language = "en", digits = 1) {
  if (value == null || !Number.isFinite(Number(value))) return "—";
  try {
    return new Intl.NumberFormat(language, { maximumFractionDigits: digits, minimumFractionDigits: 0, useGrouping: false }).format(Number(value));
  } catch {
    return `${Number(Number(value).toFixed(digits))}`;
  }
}

/** A date in the browser's time zone; unknown or invalid dates are left to the caller. */
export function dateText(value, language = "en") {
  if (!value || Number.isNaN(Date.parse(value))) return "";
  try { return new Intl.DateTimeFormat(language, { dateStyle: "medium" }).format(new Date(value)); }
  catch { return new Date(value).toISOString().slice(0, 10); }
}

/** A list of names joined the way the language joins them ("A, B and C"). */
export function names(list, language = "en") {
  try { return new Intl.ListFormat(language, { style: "long", type: "conjunction" }).format(list); }
  catch { return list.join(", "); }
}
