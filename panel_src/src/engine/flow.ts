// Getting to "Configura" from inside the panel.
//
// Three screens need it and none of them can do the thing themselves: *Misura una
// tapparella* and *Nuovo profilo* on the overview, *Misura di nuovo* and *Correggi…* on
// the detail, *riprendi / termina* on the measuring banner. All five end in the guided
// calibration, which lives in the options flow and stays there for 0.6.0.
//
// There are two ways in, and the plan (§3.7) is explicit about which one is the contract.
//
// **The fallback is the contract.** `/config/integrations/integration/myhome` is an
// ordinary Home Assistant page, reached the ordinary way - `history.pushState` plus the
// frontend's own `location-changed` event, which is how every custom panel navigates. It
// uses no private API, it cannot be renamed out from under us, and the user's next click
// is "Configura". Every one of the five controls works through it.
//
// **The dialog is an optimisation, and it is private frontend API.** HACS opens a flow by
// firing `show-dialog` with `dialogTag: "dialog-data-entry-flow"`, and it can do that
// because it is built against the frontend source: the `dialogParams` that dialog wants
// carry a `flowConfig` object of some twenty callbacks - `createFlow`, `fetchFlow`,
// `handleFlowStep`, `deleteFlow` and a render function per step kind - which is the flow
// dialog's own configuration and not something a panel bundled on its own can construct.
// We do not have it, and writing our own copy of it would be reimplementing the dialog we
// are trying to open.
//
// So this module does exactly what §3.7 asks for and nothing more:
//
// 1. **probe** `customElements.get("dialog-data-entry-flow")`. Undefined - which is what a
//    fresh page load is expected to give, because the frontend loads its dialogs lazily -
//    and the panel navigates at once. No event fired, no half-open state.
// 2. **fire, then watch.** Defined, and the event is fired; 400 ms later the document is
//    asked whether a dialog really attached.
// 3. **fall back.** It did not, and the panel navigates - saying so first, because a
//    silent change of environment is worse than a slow one.
//
// **What is verified and what is not.** Steps 1 and 3 are exercised in the development
// harness and in a browser. Step 2 is not: this repository has no Home Assistant in it,
// and the `flowConfig` the dialog wants is, as above, not ours to build. The honest
// expectation is that on a real installation the dialog path completes only if the
// frontend has been reshaped to want less than it does today, and that the 400 ms
// watchdog is what turns that from a dead button into a slightly slow one.
//
// **Preselecting the cover.** Neither path can. The options flow's `init` step is a menu
// and takes no arguments, so "Correggi… → solo i tempi" lands the user in the menu rather
// than on the path they picked; the panel says as much in `panel.detail.correct.intro`.
// Giving the flow an entry point that names a shutter is a 0.7.0 item, and when it exists
// it is one extra field in `dialogParams` here and one `async_step_*` there.

/** The integration page: the way to "Configura", and the way that always works. */
export const FLOW_URL = "/config/integrations/integration/myhome";

/** How long to wait for the dialog to attach before deciding it never will. */
const WATCHDOG_MS = 400;

/** The frontend's flow dialog, by the name it has had since 2023. */
const DIALOG_TAG = "dialog-data-entry-flow";

/** True when the frontend has that dialog defined in the document the panel lives in. */
export const flowDialogDefined = (): boolean =>
  typeof customElements !== "undefined" && customElements.get(DIALOG_TAG) !== undefined;

/**
 * Move Home Assistant to another of its own pages.
 *
 * `pushState` plus `location-changed` is the frontend's own navigation, and it is what a
 * custom panel has instead of a router: the event tells the shell to render the new URL
 * rather than reloading the document, which would throw away the panel's socket and its
 * pending changes with it. A shell that has stopped listening leaves the URL correct and
 * the page where it was, which a reload fixes - so the last resort is stated too.
 */
export const navigateHomeAssistant = (path: string): void => {
  history.pushState(null, "", path);
  window.dispatchEvent(new CustomEvent("location-changed", { detail: { replace: false } }));
};

export interface OpenFlowRequest {
  /** The element the event is fired from: it has to bubble out of the panel's shadow root. */
  source: HTMLElement;
  /** The gateway whose options flow is wanted. */
  entryId: string | null;
  /**
   * Said out loud and drawn on the screen before the page changes under the user. The
   * panel passes `panel.common.opens_configure`, which is the same sentence the buttons
   * carry as their hint.
   */
  onLeaving: () => void;
}

/**
 * Open the options flow, or go to the page that has the button that opens it.
 *
 * Returns which path it took, so the caller can say something true about what is about to
 * happen rather than guessing. `"dialog"` means the event was fired and a dialog attached
 * within the watchdog; `"page"` means the panel navigated.
 */
export const openOptionsFlow = (request: OpenFlowRequest): "dialog" | "page" | "waiting" => {
  if (!flowDialogDefined()) {
    // Step 1: nothing to fire at. Straight to the page, with no half-open state.
    request.onLeaving();
    navigateHomeAssistant(FLOW_URL);
    return "page";
  }

  // Step 2: fire, and watch. `composed` so the event leaves the panel's shadow root, and
  // `bubbles` so it reaches the frontend's dialog manager at the top of the document.
  request.source.dispatchEvent(
    new CustomEvent("show-dialog", {
      bubbles: true,
      composed: true,
      detail: {
        dialogTag: DIALOG_TAG,
        // The frontend imports its own chunk; we have nothing to import and must not
        // pretend to. A resolved promise is the honest value for "already there".
        dialogImport: () => Promise.resolve(),
        dialogParams: {
          startFlowHandler: request.entryId,
          domain: "myhome",
          // `flowConfig` is missing on purpose - see the head of this file. If a future
          // frontend can build it from the handler alone, this is where it stops being
          // missing, and nothing else here changes.
        },
      },
    }),
  );

  setTimeout(() => {
    if (document.querySelector(DIALOG_TAG)) {
      return;
    }
    // Step 3: it did not open. The page always does.
    request.onLeaving();
    navigateHomeAssistant(FLOW_URL);
  }, WATCHDOG_MS);
  return "waiting";
};
