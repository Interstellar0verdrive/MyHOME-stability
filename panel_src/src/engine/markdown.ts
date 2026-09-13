// The little bit of Markdown the texts really contain, rendered without a library and
// without ever building HTML from a string.
//
// The translated texts use four things: paragraphs, `**bold**`, simple lists, and - in the
// wizard's descriptions - a leading illustration `![alt](/myhome_static/x.webp)`. That is
// the whole grammar, and it is rendered here into Lit templates. Nothing goes through
// `unsafeHTML`, so a `<script>` or an `<img onerror=…>` that somehow reached a translation
// file arrives on the screen as the literal characters somebody typed, which is both safe
// and a visible bug.
//
// The plan offered `ha-markdown` behind a `customElements.get()` guard instead. It is not
// used, for two reasons: it renders arbitrary HTML out of the text (the exact thing this
// panel must not do with strings it did not write), and a screen that looks one way when
// the element is defined and another way when it is not is a screen nobody can design.
// The guard rule stands for *chrome* - `ha-menu-button` and its like - not for content.
//
// Images are restricted to `/myhome_static/`, the path the integration itself serves. An
// image from anywhere else renders as its alt text: a translation file is not a place from
// which to fetch.

import { html, type TemplateResult } from "lit";

const STATIC_PREFIX = "/myhome_static/";
const IMAGE_LINE = /^!\[([^\]]*)\]\(([^)\s]+)\)$/;
const LEADING_IMAGE = /^!\[[^\]]*\]\([^)\s]*\)\s*\n\s*\n/;

/**
 * The illustration at the head of a description, taken out so the screen can put it in its
 * own slot. The flow dialog keeps it inline because a dialog has nowhere else to put it;
 * the panel has a drawing area, and an image rendered twice is an image rendered wrong.
 */
export const splitLeadingImage = (
  text: string,
): { image: { src: string; alt: string } | null; body: string } => {
  const match = LEADING_IMAGE.exec(text || "");
  if (!match) {
    return { image: null, body: text || "" };
  }
  const line = match[0].trim();
  const parsed = IMAGE_LINE.exec(line);
  if (!parsed || !parsed[2].startsWith(STATIC_PREFIX)) {
    return { image: null, body: text || "" };
  }
  return { image: { alt: parsed[1], src: parsed[2] }, body: (text || "").slice(match[0].length) };
};

/** `**bold**` and nothing else; every other character is text. */
const inline = (text: string): TemplateResult[] => {
  const out: TemplateResult[] = [];
  const parts = text.split("**");
  parts.forEach((part, index) => {
    if (!part) {
      return;
    }
    // Odd segments are the ones between a pair of markers. An unmatched marker leaves an
    // odd number of parts and the tail stays plain, which is what a reader expects from
    // half-typed emphasis.
    out.push(index % 2 === 1 ? html`<strong>${part}</strong>` : html`<span>${part}</span>`);
  });
  return out;
};

const isListItem = (line: string): boolean => /^\s*[-*]\s+/.test(line);

/**
 * `renderMarkdown(text)` - paragraphs, lists, bold, and images from `/myhome_static/`.
 * Everything else is a paragraph of literal text.
 */
export const renderMarkdown = (text: string): TemplateResult => {
  const blocks = (text || "").replace(/\r\n/g, "\n").split(/\n{2,}/);
  const rendered: TemplateResult[] = [];
  for (const raw of blocks) {
    const block = raw.trim();
    if (!block) {
      continue;
    }
    const image = IMAGE_LINE.exec(block);
    if (image) {
      rendered.push(
        image[2].startsWith(STATIC_PREFIX)
          ? html`<img class="md-image" src=${image[2]} alt=${image[1]} />`
          : html`<p>${inline(image[1])}</p>`,
      );
      continue;
    }
    const lines = block.split("\n");
    if (lines.every(isListItem)) {
      rendered.push(
        html`<ul>
          ${lines.map((line) => html`<li>${inline(line.replace(/^\s*[-*]\s+/, ""))}</li>`)}
        </ul>`,
      );
      continue;
    }
    // A single newline inside a paragraph is a line break in every text this panel shows,
    // because the translators write them that way in a spreadsheet cell.
    rendered.push(
      html`<p>
        ${lines.map((line, index) => (index === 0 ? inline(line) : [html`<br />`, ...inline(line)]))}
      </p>`,
    );
  }
  return html`${rendered}`;
};
