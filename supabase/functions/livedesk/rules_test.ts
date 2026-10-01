// deno test --allow-read supabase/functions/livedesk/rules_test.ts
import { assertEquals } from "jsr:@std/assert@1";
import { fromRevenueCat, HUB_LINK_DAYS, readDevice, status } from "./rules.ts";

const NOW = Date.parse("2026-10-01T09:00:00Z");
const day = 86400_000;

Deno.test("hub link within the window opens access", () => {
  const s = status({ hub_member_id: 7, hub_verified_at: new Date(NOW - 3 * day).toISOString(), store_expires_at: null }, NOW);
  assertEquals([s.access, s.via, s.relink], [true, "hub", false]);
});
Deno.test("stale hub link closes access and asks for a relink", () => {
  const s = status({ hub_member_id: 7, hub_verified_at: new Date(NOW - 40 * day).toISOString(), store_expires_at: null }, NOW);
  assertEquals([s.access, s.relink], [false, true]);
});
Deno.test("store subscription in date opens access", () => {
  const s = status({ hub_member_id: null, hub_verified_at: null, store_expires_at: new Date(NOW + day).toISOString() }, NOW);
  assertEquals([s.access, s.via], [true, "store"]);
});
Deno.test("no row, no access", () => {
  assertEquals(status(null, NOW).access, false);
});
Deno.test("SQL rule uses the same window", async () => {
  const sql = await Deno.readTextFile(new URL("../../migrations/20261001090000_livedesk_app.sql", import.meta.url));
  assertEquals(sql.includes(`interval '${HUB_LINK_DAYS} days'`), true);
});
Deno.test("device: good, bad platform, bad slug", () => {
  const ok = readDevice({ token: "x".repeat(40), platform: "ios", specialities: ["stroke", "stroke"] });
  assertEquals(typeof ok === "object" && ok.specialities, ["stroke"]);
  assertEquals(readDevice({ token: "x".repeat(40), platform: "web" }), "platform");
  assertEquals(readDevice({ token: "x".repeat(40), platform: "ios", specialities: ["Bad Slug"] }), "specialities");
});
Deno.test("revenuecat: renewal sets expiry, anonymous ignored, test ignored", () => {
  const uid = "0b6f3c1e-1111-4a2b-9c3d-123456789abc";
  const r = fromRevenueCat({ type: "RENEWAL", app_user_id: uid, expiration_at_ms: NOW + day, product_id: "livedesk_monthly", store: "APP_STORE" });
  assertEquals(r?.store_expires_at, new Date(NOW + day).toISOString());
  assertEquals(fromRevenueCat({ type: "RENEWAL", app_user_id: "$RCAnonymousID:abc", expiration_at_ms: NOW }), null);
  assertEquals(fromRevenueCat({ type: "TEST", app_user_id: uid }), null);
});
