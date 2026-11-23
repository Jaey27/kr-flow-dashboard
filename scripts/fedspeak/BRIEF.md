# Fed-speak ledger: collection brief (shared by all collectors)

Today is 2026-11-23. You are collecting public statements about US monetary policy made between **2026-06-01 and 2026-11-23** by the speakers assigned to you. The result feeds a quantitative tone index and a backtest against market-implied Fed pricing, so **dates and quotes must be exact**.

Your own background knowledge of this period is unreliable. Everything must come from pages you actually open in this session.

## Context already verified (do not re-research unless your assignment says so)
- Kevin Warsh became Fed Chair on 2026-05-22. Jerome Powell remains a Governor (voter). Stephen Miran left the Board in May 2026.
- Board (all vote): Warsh (Chair), Jefferson (Vice Chair), Bowman (Vice Chair for Supervision), Waller, Barr, Cook, Powell.
- FOMC meetings in the window: June, July, September, October 28 (next: December 9, then January 27, 2027).
- The FOMC raised the target range by 25bp in September 2026 to 3.75–4.00% and held on October 28 by a 10–2 vote (Cook and Hammack dissented in favor of a hike). Markets currently price a hike in December. So the live question is hike vs. hold, and later a possible pivot.
- 2026 rotating voters are expected to be Cleveland, Philadelphia, Dallas, Minneapolis (plus New York). If a page you open contradicts any of the above, say so in your report.

## What counts as one item
One item = one speaker, one occasion (speech, testimony, press conference, interview, essay, panel Q&A, social media post, client note for sell-side). If one occasion has several distinct policy messages, keep one item and pick the single most decision-relevant quote; put the rest in `summary`.
Include occasions with no monetary-policy content only if they are official speeches (score them `null`) so coverage is auditable. Skip pure ceremonial remarks otherwise.

## Hard rules on evidence
1. Every item needs a `source_url` that you opened and a `quote` that appears **verbatim** on that page (copy-paste, same wording, English). It will be machine-checked by substring match, so do not paraphrase, do not fix typos, do not stitch two sentences with an ellipsis. Keep the quote to one sentence or clause, 30 words or fewer, and it must be the speaker's own words (not the journalist's).
2. Prefer primary sources: the official text or transcript (federalreserve.gov, the regional Fed's site, treasury.gov, whitehouse.gov, the firm's own page, a full interview transcript). Use a news article only when no primary text exists, and then only for a direct quotation inside quotation marks.
3. If you find evidence that a statement happened but cannot open any page containing a direct quote (paywall, video only), do NOT create an item. Put it in the `unverified` list with date, speaker, what you saw, and the URL.
4. Never fill a field from memory or inference. Unknown = `null`.
5. Date = the date the words were spoken or published, US Eastern. If the page only gives the article date, use it and set `date_basis` to `"article"`.

## Scoring rubric (score what the speaker said about the policy rate path on that day)
`score` (hawk positive, to match basis points):
- `+2` explicitly wants a rate increase soon or says more hikes are needed; a dissent in favor of a hike
- `+1` leans tighter: inflation risk dominates, open to hiking, policy may not be restrictive enough, pushes back on cut talk
- `0` balanced: hold is appropriate, data dependent with no lean, two-sided risks
- `-1` leans easier: growth, jobs, or financial-stability risks dominate; says hikes should stop or policy is restrictive enough; opposes further hikes
- `-2` explicitly wants rate cuts soon or says recent hikes were a mistake
- `null` no usable monetary-policy content
For non-Fed speakers (politicians, investors, banks), score what they say the Fed **should do or will do** on the same scale, and set `score_basis` to `"should"` or `"forecast"`. For Fed officials use `"own_stance"`.
Score only from the quote and the surrounding text you read. If torn between two levels, choose the one nearer 0 and say why in `score_note`.

## Tags
- `drivers` (list, the reasons the speaker gives, most important first): `inflation`, `labor`, `growth`, `financial_stability_credit`, `ai_financing`, `fiscal_term_premium`, `tariffs_supply`, `energy`, `political`, `other`
- `ai_financing` applies only if the speaker explicitly links policy or risk to AI capex funding, data-center debt, private credit, neocloud or hyperscaler borrowing, or an AI-driven credit event. If used, also fill `ai_quote` (verbatim, same rule as `quote`, may be from the same page).
- `tool`: `rates`, `balance_sheet`, `both`, `regulation`, `none`

## Output
Write one JSON file to the path given in your assignment (UTF-8, valid JSON, no comments):
```json
{
  "collector": "A1",
  "speakers_covered": ["..."],
  "items": [
    {
      "date": "2026-07-14",
      "time_et": "08:30",
      "date_basis": "event",
      "speaker": "Kevin Warsh",
      "role": "Fed Chair",
      "occasion": "Semiannual Monetary Policy Report, House Financial Services",
      "type": "testimony",
      "source_url": "https://...",
      "source_tier": "official_text",
      "quote": "verbatim sentence from the page",
      "summary": "2-3 plain sentences on what was said about policy, in English",
      "score": 1,
      "score_basis": "own_stance",
      "score_note": "why this level",
      "drivers": ["inflation"],
      "tool": "rates",
      "ai_quote": null
    }
  ],
  "unverified": [
    {"date": "2026-08-02", "speaker": "...", "what": "...", "url": "..."}
  ],
  "coverage_notes": "which months or venues you could not cover, and why"
}
```
`type` is one of: `speech`, `testimony`, `press_conference`, `interview`, `essay`, `panel_qa`, `social_post`, `statement`, `dissent`, `client_note`, `other`.
`source_tier` is one of: `official_text`, `official_transcript`, `full_interview_transcript`, `news_direct_quote`.
`time_et` is `null` unless the page states a time.

## Coverage target
Completeness matters. For each assigned speaker, go month by month from June to November and look for: official speeches and essays on their institution's site, testimony, scheduled interviews (CNBC, Bloomberg, Fox Business, FT, WSJ, Reuters, NPR, podcasts), conference panels, and wire-reported remarks. For Fed officials, expect roughly 2 to 6 policy-relevant occasions per month outside blackout periods; if you find far fewer, search again by month ("<name> Fed <Month> 2026"). Save the file as you go (rewrite the whole file after every 10 or so items) so partial work survives.

## Final report (your reply to me)
Keep it under 200 words: number of items per speaker, number unverified, months with thin coverage, and anything that contradicts the context section above. Do not paste the items.
