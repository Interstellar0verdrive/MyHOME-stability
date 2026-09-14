// The illustration a step can carry, and the check that keeps it from being a stylesheet.
//
// It lives beside `engine/screen.ts` rather than inside it for one reason: the rule below
// is the panel's only piece of security-relevant arithmetic that a unit test can reach
// without a DOM. `screen.ts` is a Lit element and registers itself on import; this is
// three regular expressions and a function.

/** The illustration of a step: a path this integration serves, and how to lay it out. */
export interface ScreenImage {
  src: string;
  alt: string;
  size?: string;
  pos?: string;
}

// The drawing is the one place a step's model reaches CSS, and CSS built by joining
// strings is CSS somebody else can add declarations to: a `src` carrying `");` would turn
// the illustration slot into any rule it liked, including a full-screen overlay and a
// request to a host nobody chose. So the three values are checked here, at the point of
// use, rather than trusted from wherever the model was built - `splitLeadingImage` already
// refuses an image from outside `/myhome_static/`, and this says the same thing again where
// it cannot be skipped. They are then set through `styleMap`, which writes one property at
// a time and cannot grow a second declaration.

/** A path this integration serves, and nothing else: no scheme, no host, no quoting. */
const SAFE_SRC = /^\/myhome_static\/[A-Za-z0-9._~\-/]+$/;
/** ...and no climbing back out of it with dot segments. */
const DOT_SEGMENT = /(^|\/)\.\.?(\/|$)/;

/**
 * True for a path the integration itself serves and that stays inside it.
 *
 * The prefix on its own is not enough, and that is the whole reason this is one function
 * rather than a `startsWith` in each of the three places that need it: a browser resolves
 * `/myhome_static/../../anything` before it asks for it, so a prefix test would let a
 * translation file fetch any address on the Home Assistant host as an image - and say
 * whether it exists by whether the drawing appeared.
 */
export const servedByUs = (src: string): boolean =>
  SAFE_SRC.test(src) && !DOT_SEGMENT.test(src);
/** `background-size` / `background-position`: lengths, percentages and the CSS keywords. */
const SAFE_VALUE = /^[A-Za-z0-9 %.,\-]+$/;

export const drawingStyle = (image: ScreenImage): Record<string, string> | null => {
  if (!servedByUs(image.src)) {
    return null;
  }
  const size = image.size && SAFE_VALUE.test(image.size) ? image.size : "100% auto";
  const position = image.pos && SAFE_VALUE.test(image.pos) ? image.pos : "50% 60%";
  return {
    backgroundImage: `url("${image.src}")`,
    backgroundSize: size,
    backgroundPosition: position,
  };
};
