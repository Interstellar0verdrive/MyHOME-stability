// Typed wrappers over the three read commands of `custom_components/myhome/websocket_api.py`.
//
// The shapes below are `custom_components/myhome/panel_schemas.py` restated in
// TypeScript, and that file says so in its own words: it is the frozen contract, and a
// change to either is a change to both. Nothing here re-derives anything the server
// already answered - not a cover's origin, not a rescaled profile value. That is the
// parity invariant: the panel and the `Calibration source` attribute must never disagree,
// and the only way to guarantee it is that one function computes it, on the server.

import { type HaConnection } from "../types/ha";

export interface EntrySummary {
  entry_id: string;
  title: string;
  mac: string;
  loaded: boolean;
}

export interface ProfileRow {
  name: string;
  source: "store" | "yaml" | null;
  editable: boolean;
  values: Record<string, number>;
  reference_height: number | null;
  measured_on: string | null;
  measured_on_name: string | null;
  measured_at: string | null;
  followers: string[];
  followers_from_file: string[];
  missing: boolean;
}

export interface CoverRow {
  unique_id: string;
  entity_id: string | null;
  name: string;
  area_id: string | null;
  area: string | null;
  height: number | null;
  profile: string | null;
  profile_from_file: boolean;
  profile_missing: boolean;
  origin: string;
  source: string;
  values: Record<string, number>;
  has_own: string[];
  level: string | null;
  verify_note: number | null;
  measured_at: string | null;
  calibrating: boolean;
  order_index: number;
}

export interface Overview {
  entries: EntrySummary[];
  entry_id: string;
  measuring: { cover_unique_id: string; name: string } | null;
  profiles: ProfileRow[];
  covers: CoverRow[];
  order: string[];
  no_basic_covers: boolean;
}

export interface Texts {
  language: string;
  requested: string;
  fallback: boolean;
  texts: Record<string, unknown>;
}

/**
 * A refusal from the backend, kept whole.
 *
 * `translation_key` is the interesting half: the backend never sends a sentence a user
 * should read, it sends the key of one, and the panel renders it out of the same seven
 * files the guided dialog reads. `message` is the English fallback that travels beside
 * it so that a key the texts lot has not written yet still says something.
 */
export interface WsError {
  code: string;
  message: string;
  translation_key?: string;
  translation_placeholders?: Record<string, string>;
}

export const asWsError = (error: unknown): WsError => {
  if (error && typeof error === "object" && "code" in error) {
    return error as WsError;
  }
  return { code: "unknown_error", message: String(error) };
};

export const overview = (connection: HaConnection, entryId?: string): Promise<Overview> =>
  connection.sendMessagePromise<Overview>({
    type: "myhome/calibration/overview",
    ...(entryId ? { entry_id: entryId } : {}),
  });

export const texts = (connection: HaConnection, language: string): Promise<Texts> =>
  connection.sendMessagePromise<Texts>({
    type: "myhome/calibration/texts",
    language,
  });
