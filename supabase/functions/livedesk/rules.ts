// Live Desk app rules. Pure functions: no env reads, no network, so every
// accept and reject path is unit-tested (rules_test.ts). Added 01/10/2026.
//
// The access rule lives in SQL too (livedesk_has_access in
// migrations/20261001090000_livedesk_app.sql), for the alert sender's view.
// HUB_LINK_DAYS here and "35 days" there must match; rules_test.ts reads the
// migration to prove they do.

export const HUB_LINK_DAYS = 35;
/** A member pass from the Hub lives 15 minutes; the app uses it within
 *  seconds of the Hub page handing it over, so 10 minutes' grace is plenty. */
export const PASS_GRACE = 10 * 60;

export type Access = {
  hub_member_id: number | null;
  hub_verified_at: string | null;
  store_expires_at: string | null;
};

export type Status = {
  access: boolean;
  via: "hub" | "store" | null;
  /** Hub link older than HUB_LINK_DAYS: the app re-opens the Hub page to renew. */
  relink: boolean;
  hub_until: string | null;
  store_until: string | null;
};

export function status(a: Access | null, now = Date.now()): Status {
  const hubUntil = a && a.hub_member_id && a.hub_verified_at
    ? Date.parse(a.hub_verified_at) + HUB_LINK_DAYS * 86400_000 : NaN;
  const storeUntil = a && a.store_expires_at ? Date.parse(a.store_expires_at) : NaN;
  const hub = hubUntil > now, store = storeUntil > now;
  return {
    access: hub || store,
    via: hub ? "hub" : store ? "store" : null,
    relink: !!(a && a.hub_member_id) && !hub,
    hub_until: Number.isFinite(hubUntil) ? new Date(hubUntil).toISOString() : null,
    store_until: Number.isFinite(storeUntil) ? new Date(storeUntil).toISOString() : null,
  };
}

const SLUG = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

export type Device = { token: string; platform: "ios" | "android"; specialities: string[] };

/** A clean device registration from the request body, or why it is refused. */
export function readDevice(body: Record<string, unknown>): Device | string {
  const token = body.token;
  if (typeof token !== "string" || token.length < 20 || token.length > 4096 || /\s/.test(token)) return "token";
  const platform = body.platform;
  if (platform !== "ios" && platform !== "android") return "platform";
  const specs = body.specialities ?? [];
  if (!Array.isArray(specs) || specs.length > 60) return "specialities";
  const clean: string[] = [];
  for (const s of specs) {
    if (typeof s !== "string" || s.length > 80 || !SLUG.test(s)) return "specialities";
    if (!clean.includes(s)) clean.push(s);
  }
  return { token, platform, specialities: clean };
}

/** RevenueCat webhook event -> the store columns to write, or null to ignore.
 *  app_user_id is the Supabase user id (the app calls Purchases.logIn with it);
 *  anonymous RevenueCat ids ($RCAnonymousID:...) are ignored. */
export function fromRevenueCat(ev: Record<string, unknown>):
  { user_id: string; store_product: string | null; store_expires_at: string | null; store_platform: string | null } | null {
  const uid = ev.app_user_id;
  if (typeof uid !== "string" || !/^[0-9a-f-]{36}$/i.test(uid)) return null;
  const type = String(ev.type || "");
  if (type === "TEST" || type === "TRANSFER" || type === "SUBSCRIBER_ALIAS") return null;
  const exp = typeof ev.expiration_at_ms === "number" ? new Date(ev.expiration_at_ms).toISOString() : null;
  // An EXPIRATION with no time still ends access now.
  const expires = exp ?? (type === "EXPIRATION" ? new Date(0).toISOString() : null);
  if (expires === null) return null;
  return {
    user_id: uid,
    store_product: typeof ev.product_id === "string" ? ev.product_id : null,
    store_expires_at: expires,
    store_platform: typeof ev.store === "string" ? ev.store : null,
  };
}
