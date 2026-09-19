// The signal at the start: a short buzz and a short tone, when the motor really begins.
//
// The presses of the guided calibration are the one place on this panel where a tenth of a
// second is a measurement. The shutter is across the room, the screen is in a hand, and
// between "Start the shutter" and the first thing worth pressing there is a second or two
// of nothing. So the moment the session says the motor has echoed - the transition to
// `awaiting_endpoint`, and nothing the browser worked out - the phone buzzes and beeps
// once, and the user can keep their eyes on the shutter instead of on the screen.
//
// Three rules, all of them about not being clever:
//
// * **nothing here ever throws.** A browser with no vibration, an audio context refused
//   for want of a user gesture, a `localStorage` that is a trap in a private window: each
//   of them is caught and the calibration goes on without the signal. A measurement that
//   failed because a sound could not play would be an absurd way to lose three minutes;
// * **the switch is remembered in this browser and nowhere else.** It is a preference
//   about a room and a phone, not about a shutter, so it does not belong in the session
//   and would be wrong to sync;
// * **`prefers-reduced-motion` silences the animation, not the sound** (SPEC §5.4). Some
//   people turn it on because movement makes them ill; nobody turns it on to be told less
//   about a motor that has started in the next room.

/** Where the switch is remembered, per browser. */
export const CUE_KEY = "myhome-calibration-cue";

/** What the panel holds of `localStorage`, so that nothing here needs a window. */
export interface CueStore {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

const defaultStore = (): CueStore | null => {
  try {
    return (globalThis as { localStorage?: CueStore }).localStorage ?? null;
  } catch {
    // Safari in a private window throws on the property itself, not on the read.
    return null;
  }
};

/** On unless this browser was told otherwise (SPEC decision 23: on by default). */
export const readCue = (store: CueStore | null = defaultStore()): boolean => {
  try {
    return store?.getItem(CUE_KEY) !== "off";
  } catch {
    return true;
  }
};

export const writeCue = (on: boolean, store: CueStore | null = defaultStore()): void => {
  try {
    store?.setItem(CUE_KEY, on ? "on" : "off");
  } catch {
    // Unwritable: the switch works for this page and is forgotten on the next one, which
    // is a smaller loss than a screen that cannot be drawn.
  }
};

type AudioContextLike = new () => {
  createOscillator(): {
    type: string;
    frequency: { value: number };
    connect(to: unknown): void;
    start(): void;
    stop(at: number): void;
  };
  createGain(): { gain: { value: number }; connect(to: unknown): void };
  destination: unknown;
  currentTime: number;
  close(): void;
};

/**
 * 880 Hz for eighty milliseconds: short enough not to be a noise, high enough to carry.
 *
 * It answers whether anything was really played. A browser with no `AudioContext` is not a
 * browser that beeped quietly, and `signalStart` used to report a signal either way.
 */
const tone = (): boolean => {
  const Constructor = (globalThis as { AudioContext?: AudioContextLike }).AudioContext;
  if (!Constructor) {
    return false;
  }
  const audio = new Constructor();
  const oscillator = audio.createOscillator();
  const gain = audio.createGain();
  oscillator.type = "sine";
  oscillator.frequency.value = 880;
  // A quarter of full scale: audible in a room, not a shock in a pocket.
  gain.gain.value = 0.25;
  oscillator.connect(gain);
  gain.connect(audio.destination);
  oscillator.start();
  oscillator.stop(audio.currentTime + 0.08);
  // Closed a moment after the tone has finished; an audio context left open is a tab that
  // goes on showing "playing" in the browser's own chrome.
  setTimeout(() => {
    try {
      audio.close();
    } catch {
      // Already closed, or closing twice: neither is worth a word.
    }
  }, 200);
  return true;
};

/**
 * Buzz and beep, once, if this browser was not told to be quiet.
 *
 * Called from the one place a snapshot says the motor echoed. It answers `true` when it
 * really signalled, which is what `test/wizard-model.test.ts` reads: the alternative would
 * be asserting on a sound.
 */
export const signalStart = (on: boolean): boolean => {
  if (!on) {
    return false;
  }
  let signalled = false;
  try {
    const vibrate = (globalThis as { navigator?: { vibrate?: (pattern: number) => boolean } })
      .navigator?.vibrate;
    if (typeof vibrate === "function") {
      vibrate.call((globalThis as { navigator?: unknown }).navigator, 80);
      signalled = true;
    }
  } catch {
    // A browser that has the method and refuses it: nothing to do and nothing to say.
  }
  try {
    signalled = tone() || signalled;
  } catch {
    // No audio context, or one the browser will not start without a gesture.
  }
  return signalled;
};
