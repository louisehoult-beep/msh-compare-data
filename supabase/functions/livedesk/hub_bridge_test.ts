// deno test supabase/functions/livedesk/hub_bridge_test.ts
import { assertEquals } from "jsr:@std/assert@1";
import { bridgeHeader, eventEmail, hubFromRevenueCat, readProductMap } from "./hub_bridge.ts";
import { hmac } from "../ask-the-hub/pass.ts";

const NOW = Date.parse("2026-11-19T20:00:00Z");
const DAY = 86400_000;
const UID = "0b6c2f3e-1d2a-4c5b-9e8f-7a6b5c4d3e2f";
const P = { "hub.monthly": 691, "hub.annual": 692 };

function ev(over: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    id: "evt-1", type: "INITIAL_PURCHASE", app_user_id: UID, product_id: "hub.monthly",
    entitlement_ids: ["hub"], expiration_at_ms: NOW + 30 * DAY, store: "APP_STORE",
    subscriber_attributes: { $email: { value: " Member@Example.co.uk " } }, ...over,
  };
}

Deno.test("purchase grants the mapped plan to the new expiry, email cleaned", () => {
  const h = hubFromRevenueCat(ev(), P, NOW)!;
  assertEquals([h.action, h.plan_id, h.email, h.expires_at, h.event_id],
    ["grant", 691, "member@example.co.uk", new Date(NOW + 30 * DAY).toISOString(), "evt-1"]);
});
Deno.test("renewal and plan change grant", () => {
  assertEquals(hubFromRevenueCat(ev({ type: "RENEWAL" }), P, NOW)!.action, "grant");
  assertEquals(hubFromRevenueCat(ev({ type: "PRODUCT_CHANGE", product_id: "hub.annual" }), P, NOW)!.plan_id, 692);
});
Deno.test("auto-renew off keeps access to the paid-up date", () => {
  const h = hubFromRevenueCat(ev({ type: "CANCELLATION", cancel_reason: "UNSUBSCRIBE" }), P, NOW)!;
  assertEquals([h.action, h.expires_at], ["grant", new Date(NOW + 30 * DAY).toISOString()]);
});
Deno.test("refund removes access now", () => {
  const h = hubFromRevenueCat(ev({ type: "CANCELLATION", cancel_reason: "CUSTOMER_SUPPORT" }), P, NOW)!;
  assertEquals([h.action, h.expires_at], ["revoke", new Date(NOW).toISOString()]);
});
Deno.test("expiration revokes", () => {
  assertEquals(hubFromRevenueCat(ev({ type: "EXPIRATION", expiration_at_ms: NOW - DAY }), P, NOW)!.action, "revoke");
});
Deno.test("a grant event already past its expiry revokes", () => {
  assertEquals(hubFromRevenueCat(ev({ type: "RENEWAL", expiration_at_ms: NOW - 1 }), P, NOW)!.action, "revoke");
});
Deno.test("Live Desk products, unmapped products and other entitlements are ignored", () => {
  assertEquals(hubFromRevenueCat(ev({ product_id: "livedesk.annual", entitlement_ids: ["livedesk"] }), P, NOW), null);
  assertEquals(hubFromRevenueCat(ev({ product_id: "hub.weekly" }), P, NOW), null);
  assertEquals(hubFromRevenueCat(ev({ entitlement_ids: ["livedesk"] }), P, NOW), null);
  assertEquals(hubFromRevenueCat(ev(), {}, NOW), null);
});
Deno.test("anonymous RevenueCat ids, billing issues and tests are ignored", () => {
  assertEquals(hubFromRevenueCat(ev({ app_user_id: "$RCAnonymousID:abc" }), P, NOW), null);
  assertEquals(hubFromRevenueCat(ev({ type: "BILLING_ISSUE" }), P, NOW), null);
  assertEquals(hubFromRevenueCat(ev({ type: "TEST" }), P, NOW), null);
  assertEquals(hubFromRevenueCat(ev({ type: "RENEWAL", expiration_at_ms: undefined }), P, NOW), null);
});
Deno.test("bad or missing email gives null email, not a refusal", () => {
  assertEquals(eventEmail(ev({ subscriber_attributes: {} })), null);
  assertEquals(eventEmail(ev({ subscriber_attributes: { $email: { value: "not an email" } } })), null);
  assertEquals(hubFromRevenueCat(ev({ subscriber_attributes: undefined }), P, NOW)!.email, null);
});
Deno.test("product map parsing drops bad entries", () => {
  assertEquals(readProductMap(" hub.monthly=691, hub.annual=692 ,bad, x=0y,=5"), { "hub.monthly": 691, "hub.annual": 692 });
  assertEquals(readProductMap(""), {});
});
Deno.test("bridge header signs t.body", async () => {
  const secret = "s".repeat(40);
  const h = await bridgeHeader(secret, '{"a":1}', 1795000000);
  assertEquals(h, "t=1795000000,s=" + await hmac(secret, '1795000000.{"a":1}'));
});
