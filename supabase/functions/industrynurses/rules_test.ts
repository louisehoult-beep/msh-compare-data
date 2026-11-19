import { assert, assertEquals, assertMatch } from "jsr:@std/assert@1";
import { checkSignup, ics } from "./rules.ts";

const good = { email: " A@Example.com ", name: "Test Nurse", nmc_pin: "12a3456e", role_category: "Clinical educator", employer_type: "Medical device company", consent: true };

Deno.test("signup is cleaned and accepted", () => {
  const c = checkSignup(good);
  assert(c.ok);
  if (c.ok) { assertEquals(c.value.email, "a@example.com"); assertEquals(c.value.nmc_pin, "12A3456E"); }
});
Deno.test("signup rejects a bad PIN, missing consent, unknown role", () => {
  assertEquals(checkSignup({ ...good, nmc_pin: "bad" }).ok, false);
  assertEquals(checkSignup({ ...good, consent: false }).ok, false);
  assertEquals(checkSignup({ ...good, role_category: "Astronaut" }).ok, false);
  assertEquals(checkSignup({ ...good, email: "nope" }).ok, false);
});
Deno.test("calendar file spans the end date inclusively", () => {
  const f = ics({ id: 3, title: "Nursing Live, 2026", venue: "NEC", detail: "x", source_url: "https://a.b", start_date: "2026-11-09", end_date: "2026-11-10" }, new Date("2026-10-26T00:00:00Z"));
  assertMatch(f, /DTSTART;VALUE=DATE:20261109/);
  assertMatch(f, /DTEND;VALUE=DATE:20261111/);
  assertMatch(f, /SUMMARY:Nursing Live\\, 2026/);
});
