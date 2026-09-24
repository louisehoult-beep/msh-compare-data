// deno test supabase/functions/ask-the-hub/pass_test.ts
// Both halves: a real pass is ACCEPTED, and every near-miss is rejected.
// "Rejects the bad pass" and "rejects everyone" look the same from outside.
import { assertEquals } from "jsr:@std/assert@1";
import { makePass, MAX_LIFE, verifyPass } from "./pass.ts";

const S = "k".repeat(48);
const NOW = 1_790_000_000;

Deno.test("a fresh pass from WordPress is accepted", async () => {
  assertEquals(await verifyPass(await makePass(S, 42, NOW + 600), S, NOW), 42);
});
Deno.test("a pass matching the PHP snippet's output byte for byte is accepted", async () => {
  // Produced by the snippet's own code under php -r, secret "k"*48, user 42, expiry NOW+600.
  const php = "eyJ2IjoxLCJ1Ijo0MiwiZSI6MTc5MDAwMDYwMH0.LD0YlN0gmoUGbmB4nR42CBWuuydicxJykP_u7lf5opc";
  assertEquals(await verifyPass(php, S, NOW), 42);
});
Deno.test("expired pass is rejected", async () => {
  assertEquals(await verifyPass(await makePass(S, 42, NOW - 1), S, NOW), null);
});
Deno.test("pass living longer than MAX_LIFE is rejected", async () => {
  assertEquals(await verifyPass(await makePass(S, 42, NOW + MAX_LIFE + 60), S, NOW), null);
});
Deno.test("pass signed with another secret is rejected", async () => {
  assertEquals(await verifyPass(await makePass("x".repeat(48), 42, NOW + 600), S, NOW), null);
});
Deno.test("tampered user id is rejected", async () => {
  const good = await makePass(S, 42, NOW + 600);
  const forged = await makePass(S, 7, NOW + 600);
  assertEquals(await verifyPass(forged.split(".")[0] + "." + good.split(".")[1], S, NOW), null);
});
Deno.test("junk, empty, publishable-key-shaped and missing secret are rejected", async () => {
  for (const p of ["", "abc", "a.b.c", "sb_publishable_xyz", null, 12, "eyJ.eyJ"]) {
    assertEquals(await verifyPass(p, S, NOW), null);
  }
  assertEquals(await verifyPass(await makePass(S, 42, NOW + 600), "", NOW), null);
});
Deno.test("user id must be a positive integer", async () => {
  assertEquals(await verifyPass(await makePass(S, 0, NOW + 600), S, NOW), null);
});
