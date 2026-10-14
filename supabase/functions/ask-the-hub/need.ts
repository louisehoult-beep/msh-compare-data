// "Tell us what you need" (My Hub home screen, 2026-10, spec item 9).
// A member's request for something the Hub should cover. No AI call is made
// for a request: it goes to the same place as a question the Hub could not
// answer (a row in ask_gaps, and one email to the site admin address through
// the WordPress snippet), marked so Lou can tell the two apart.

export const NEED_PREFIX = "Member request: ";
export const NEED_MIN = 4;
export const NEED_MAX = 400;

// The request as it will be stored, or null if it is not a usable request.
export function cleanNeed(raw: unknown): string | null {
  if (typeof raw !== "string") return null;
  const t = raw.replace(/\s+/g, " ").trim();
  if (t.length < NEED_MIN || t.length > NEED_MAX) return null;
  return t;
}

// The text recorded in ask_gaps and emailed: the prefix tells a request
// from an unanswered question in the same inbox and the same table.
export function needQuestion(t: string): string {
  return NEED_PREFIX + t;
}
