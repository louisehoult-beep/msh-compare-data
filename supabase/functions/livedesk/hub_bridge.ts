// Hub membership bought in the app (plan step D2, 19/11/2026). Pure functions:
// no env reads, no network, so every path is unit-tested (hub_bridge_test.ts).
//
// Flow: the store -> RevenueCat (entitlement "hub") -> livedesk-revenuecat
// webhook -> hubFromRevenueCat() below -> a signed POST to the WordPress
// endpoint /wp-json/msh/v1/livedesk-store (hub/wpcode/livedesk-store-bridge.php),
// which finds or creates the WordPress user by email and starts, renews or ends
// their Paid Member Subscriptions plan to match the store.
//
// The `hub` entitlement includes the Live Desk, so the webhook's existing
// store-columns write (fromRevenueCat) still runs for hub products too.
//
// Signature (both sides must agree; hub_bridge_test.ts and
// test_livedesk_store_bridge.py prove the PHP side matches):
//   header X-MSH-Bridge: t=<unix seconds>,s=<base64url(HMAC-SHA256(secret, t + "." + body))>
// WordPress refuses anything older or newer than BRIDGE_WINDOW seconds.

import { hmac } from "../ask-the-hub/pass.ts";

export const HUB_ENTITLEMENT = "hub";
export const BRIDGE_WINDOW = 300;

/** Store product id -> Paid Member Subscriptions plan id. Filled in when the
 *  products are created in App Store Connect and Play (prices: /join-the-hub/
 *  on that day, nearest store price point; Lou 19/11/2026 "same prices as
 *  website"). Ids not listed here are never sent to WordPress. */
export type ProductMap = Record<string, number>;

export type HubEvent = {
  action: "grant" | "revoke";
  app_user: string;
  email: string | null;
  plan_id: number;
  product: string;
  expires_at: string;
  store: string | null;
  event_id: string | null;
};

const UID = /^[0-9a-f-]{36}$/i;
const EMAIL = /^[^\s@<>"]{1,64}@[^\s@<>"]{1,253}\.[a-z]{2,63}$/i;

const GRANT = new Set(["INITIAL_PURCHASE", "RENEWAL", "PRODUCT_CHANGE", "UNCANCELLATION", "NON_RENEWING_PURCHASE"]);

/** The email RevenueCat holds for the subscriber ($email attribute, set by the
 *  app at purchase: "your membership is tied to your Hub account"). */
export function eventEmail(ev: Record<string, unknown>): string | null {
  const attrs = ev.subscriber_attributes as Record<string, { value?: unknown }> | undefined;
  const v = attrs && attrs["$email"] ? attrs["$email"].value : undefined;
  if (typeof v !== "string") return null;
  const e = v.trim().toLowerCase();
  return EMAIL.test(e) ? e : null;
}

/** RevenueCat event -> what WordPress must do for a Hub membership, or null
 *  when the event is not about Hub membership or changes nothing.
 *  - purchase, renewal, plan change, un-cancel: grant to the new expiry;
 *  - CANCELLATION (auto-renew off): grant to the paid-up expiry, so the member
 *    keeps access to the end of the period, as on the website;
 *  - CANCELLATION for a refund (cancel_reason CUSTOMER_SUPPORT) and EXPIRATION:
 *    revoke now ("Refunds remove access"). */
export function hubFromRevenueCat(ev: Record<string, unknown>, products: ProductMap, now = Date.now()): HubEvent | null {
  const uid = ev.app_user_id;
  if (typeof uid !== "string" || !UID.test(uid)) return null;
  const product = typeof ev.product_id === "string" ? ev.product_id : "";
  const ents = Array.isArray(ev.entitlement_ids) ? ev.entitlement_ids : [];
  const plan = Object.prototype.hasOwnProperty.call(products, product) ? products[product] : undefined;
  // Only products we mapped; an entitlement id alone is not enough to pick a plan.
  if (!plan || !Number.isInteger(plan) || plan <= 0) return null;
  if (ents.length && !ents.includes(HUB_ENTITLEMENT)) return null;

  const type = String(ev.type || "");
  const exp = typeof ev.expiration_at_ms === "number" ? ev.expiration_at_ms : NaN;
  const refund = type === "CANCELLATION" && String(ev.cancel_reason || "") === "CUSTOMER_SUPPORT";
  let action: HubEvent["action"];
  let until: number;
  if (type === "EXPIRATION" || refund) {
    action = "revoke";
    until = now;
  } else if (GRANT.has(type) || type === "CANCELLATION") {
    if (!Number.isFinite(exp)) return null;
    action = exp > now ? "grant" : "revoke";
    until = action === "grant" ? exp : now;
  } else {
    return null; // BILLING_ISSUE, SUBSCRIPTION_PAUSED, TEST, TRANSFER...: expiry events follow
  }
  return {
    action,
    app_user: uid,
    email: eventEmail(ev),
    plan_id: plan,
    product,
    expires_at: new Date(until).toISOString(),
    store: typeof ev.store === "string" ? ev.store : null,
    event_id: typeof ev.id === "string" ? ev.id : null,
  };
}

/** Parse HUB_PRODUCTS ("product_id=plan_id,product_id=plan_id"). Bad entries are dropped. */
export function readProductMap(s: string): ProductMap {
  const out: ProductMap = {};
  for (const part of (s || "").split(",")) {
    const m = part.trim().match(/^([A-Za-z0-9._:-]{3,120})=(\d{1,9})$/);
    if (m) out[m[1]] = Number(m[2]);
  }
  return out;
}

/** The X-MSH-Bridge header for a request body. */
export async function bridgeHeader(secret: string, body: string, t = Math.floor(Date.now() / 1000)): Promise<string> {
  return `t=${t},s=${await hmac(secret, t + "." + body)}`;
}
