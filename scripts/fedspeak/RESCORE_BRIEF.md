# Re-scoring brief: 11-level hawk/dove scale (pilot)

You re-score existing, already-verified statements about US monetary policy. Do NOT browse the web. Use only each record's `quote`, `summary`, `occasion`, `type`, `old_note` and `date`.

Context for 2026 (fixed facts, use them to read the statements):
- Fed cut to 3.50–3.75% in December 2025 and held in January, March, April (April hold with three hawkish dissents against the easing-bias wording, Miran dissented for a cut).
- July 2026: hold, 9–3 (Hammack, Kashkari, Logan dissented for a 25bp hike).
- September 2026: +25bp to 3.75–4.00%, unanimous.
- October 28, 2026: hold, 10–2 (Cook, Hammack dissented for a 25bp hike).
- December 9, 2026 meeting ahead; markets price a hike; Waller floated 50bp.

## Scale (score what the speaker said the Fed should do / intends to do on the policy rate, as of that day)

| score | meaning |
|---|---|
| 10 | wants a hike larger than 25bp soon (50bp, "go big"), or dissent for a larger hike |
| 9 | wants a 25bp hike at the next/this meeting, or dissent for a 25bp hike, or "at least two more hikes" with urgency |
| 8 | more hikes needed soon / policy not restrictive enough, but no specific meeting or size |
| 7 | leans to tightening: open to hiking, inflation risk dominant, "work to do", but conditional |
| 6 | hold with hawkish tilt: patient now, worried about inflation, pushes back on cuts |
| 5 | balanced: hold is right, data dependent, two-sided risks, no lean |
| 4 | hold with dovish tilt: worried about labor/growth/financial conditions, against more hikes soon |
| 3 | hikes should stop / policy restrictive enough / next move could be a cut later |
| 2 | cuts appropriate this year or eventually, no urgency |
| 1 | wants a 25bp cut soon (next meeting), or dissent for a 25bp cut |
| 0 | wants large/rapid cuts (50bp+, "1 point", "rates should be much lower"), or attacks the Fed demanding immediate big cuts |

Rules:
- Use the old 5-level score as a sanity anchor (old −2 ≈ 0–1, −1 ≈ 2–4, 0 ≈ 4–6, +1 ≈ 6–8, +2 ≈ 8–10). Move outside that band only with a clear reason in `note`.
- Politicians and Treasury: same scale, on what they say the Fed should do. "Fed should look forward / patience" without asking for cuts = 3–4. Asking for cuts generally = 1–2. Demanding big or immediate cuts, attacking the chair = 0.
- If torn between two levels, pick the one nearer 5.
- `path_bp`: if the statement states a desired size for the next move or a near-term path in numbers, give it as signed basis points (e.g. +50, +25, −25, −100, or +50 for "two more 25bp hikes"). Otherwise null. Do not infer numbers that are not stated.

## Output
Write ONE JSON object to the output path you were given: `{ "<id>": {"s": <int 0-10>, "path_bp": <int or null>, "note": "<≤20 words, why>"} , ... }`, every input id exactly once, valid JSON, UTF-8. Reply with just the count and the distribution of `s`.
