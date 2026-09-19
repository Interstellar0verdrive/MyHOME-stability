// The illustration a step can carry, and the check that keeps it from being an address
// of somebody else's.
//
// It lives beside `engine/screen.ts` rather than inside it for one reason: the rule below
// is the panel's only piece of security-relevant arithmetic that a unit test can reach
// without a DOM. `screen.ts` is a Lit element and registers itself on import; this is
// three regular expressions and a function.

/** The illustration of a step: a path this integration serves, and its description. */
export interface ScreenImage {
  src: string;
  alt: string;
}

// The drawing used to be a `background-image` built by joining strings, and CSS built by
// joining strings is CSS somebody else can add declarations to: a `src` carrying `");`
// would turn the illustration slot into any rule it liked, including a full-screen overlay
// and a request to a host nobody chose. It is an `<img>` now - because a box with a
// background can only ever guess at the shape of what is inside it, and guessing is what
// cropped three of the wizard's drawings (live findings 10, 14 and 19) - but the address
// is still checked here, at the point of use, rather than trusted from wherever the model
// was built. `splitLeadingImage` already refuses an image from outside `/myhome_static/`,
// and this says the same thing again where it cannot be skipped.

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

/**
 * The address the `<img>` is given, or `null` when the step points anywhere else.
 *
 * Nothing about the shape of the drawing is decided here any more. The element is laid out
 * by `.drawing` alone - full width, its own height, `object-fit: contain` - so the picture
 * that arrives is the picture that is shown, whatever its proportions and whatever the
 * width of the column it lands in.
 */
export const drawingSrc = (image: ScreenImage): string | null =>
  servedByUs(image.src) ? image.src : null;
