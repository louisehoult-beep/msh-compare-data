// deno test supabase/functions/alerts-subscribe/rules_test.ts
import { assertEquals } from "jsr:@std/assert@1";
import { decide, readSub } from "./rules.ts";

const GOOD = {
  endpoint: "https://web.push.apple.com/QExampleEndpoint123",
  p256dh: "B" + "a".repeat(86),
  auth: "c".repeat(22),
  specialities: ["stroke", "urology", "stroke"],
  user_agent: "Mozilla/5.0 (iPhone)",
};

Deno.test("a well-formed subscription is read, duplicates dropped", () => {
  const s = readSub(GOOD);
  assertEquals(typeof s, "object");
  if (typeof s === "object") assertEquals(s.specialities, ["stroke", "urology"]);
});
Deno.test("empty specialities means every speciality and is allowed", () => {
  const s = readSub({ ...GOOD, specialities: [] });
  if (typeof s === "object") assertEquals(s.specialities, []);
  else throw new Error(s);
});
Deno.test("bad endpoints are refused", () => {
  for (const e of ["http://x.example/a", "https://", "javascript:alert(1)", 5, "https://a/" + "x".repeat(1001)]) {
    assertEquals(readSub({ ...GOOD, endpoint: e }), "endpoint");
  }
});
Deno.test("bad keys are refused", () => {
  assertEquals(readSub({ ...GOOD, p256dh: "short" }), "keys");
  assertEquals(readSub({ ...GOOD, auth: "has spaces in it!!!!" }), "keys");
});
Deno.test("bad specialities are refused", () => {
  assertEquals(readSub({ ...GOOD, specialities: ["Stroke"] }), "specialities");
  assertEquals(readSub({ ...GOOD, specialities: "stroke" }), "specialities");
  assertEquals(readSub({ ...GOOD, specialities: ["a'; drop table"] }), "specialities");
});
Deno.test("a valid pass saves, whatever is on file", () => {
  assertEquals(decide(42, undefined), { kind: "save", member_id: 42 });
  assertEquals(decide(42, null), { kind: "save", member_id: 42 });
  assertEquals(decide(42, 7), { kind: "save", member_id: 42 });
});
Deno.test("a verified phone can change its specialities without a pass", () => {
  assertEquals(decide(null, 42), { kind: "update" });
});
Deno.test("no pass and no verified row is refused: the members-only rule", () => {
  assertEquals(decide(null, undefined), { kind: "refuse", why: "member" });
  assertEquals(decide(null, null), { kind: "refuse", why: "member" });
});
