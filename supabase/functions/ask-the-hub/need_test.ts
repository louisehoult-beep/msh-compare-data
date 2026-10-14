// deno test supabase/functions/ask-the-hub/need_test.ts
import { assertEquals } from "jsr:@std/assert@1";
import { cleanNeed, NEED_MAX, needQuestion } from "./need.ts";

Deno.test("a request is trimmed and its spacing collapsed", () => {
  assertEquals(cleanNeed("  More on   ICB capital\nplans  "), "More on ICB capital plans");
});
Deno.test("too short, too long or not text is refused", () => {
  assertEquals(cleanNeed("abc"), null);
  assertEquals(cleanNeed("x".repeat(NEED_MAX + 1)), null);
  assertEquals(cleanNeed(42), null);
  assertEquals(cleanNeed(undefined), null);
});
Deno.test("the longest allowed request is kept whole", () => {
  assertEquals(cleanNeed("y".repeat(NEED_MAX)), "y".repeat(NEED_MAX));
});
Deno.test("the stored question is marked as a request", () => {
  assertEquals(needQuestion("Wound care formularies"), "Member request: Wound care formularies");
});
