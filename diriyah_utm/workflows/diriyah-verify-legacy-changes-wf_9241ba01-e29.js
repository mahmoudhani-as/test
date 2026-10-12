export const meta = {
  name: 'diriyah-verify-legacy-changes',
  description: 'Read-only adversarial review of 1,197 proposed legacy/clash UTM changes against the generator and the user rules',
  phases: [{ title: 'Review', detail: '4 independent reviewers, one chunk each' }],
}
const RULES = `
You are an independent, skeptical reviewer. Nothing is written to any ad platform in this task; you only read files.
Generator workbook (the "bible"): ${args.gen}. Read sheets Schema, Mappings, Campaign_Code_Generator, Input_Campaign_Generator, Output_Campaign_Generator with python3 (openpyxl, data_only=True).
Each row in your chunk is a proposed change of one live ad URL from "now" to "new". Rules the user set (11-Oct-2026):
1. Format: utm_campaign = [code_]{campaign name}_{mon}{yy}_{objective}; utm_term = [code_]{ad set name}_{ad set language}; utm_content = [code_]{ad name}_{format}_{ad language}. All lower-case. Objective in awr/cond/conv. Language in ar/en/all/en-ar. Format in Mappings col T.
2. A code may appear ONLY if it is the Campaign_Code_Generator uid for exactly that name (campaign / ad set / ad). Codes not in the generator (ad-id-..., adset-id-..., cam-id-..., XXXXXX, RSA1, macros like {creative}) must be dropped, never carried over. If the generator has the campaign (e.g. manazel-alhadawi-2026 7EBEB0A8) it may be used for that legacy campaign (same year), or when other ads in the same live campaign already carry it.
3. Month/year = the month the ad FIRST SERVED (column first_serving_date), not the campaign name date.
4. Objective from the live campaign name: AWR->awr, CONV->conv, LEAD->conv, TRF->cond, or the words awareness/consideration/conversion.
5. No utm_id, no fbclid. Landing page (host/path/fragment) must not change.
6. Names must be real names taken from the ad's own existing UTM tokens or generator-format entity names - never template placeholders (test_adset_name, adset_name, test_ad_name), never macros, never words that belong to other positions (language, funnel, objective, channel) when that leaves a misleading name.
7. Languages must agree with the evidence: the ad name (EN/AR/English/Arabic), the existing UTM tokens, then the landing page.
8. kva/kvb/kvd creatives are programmatic-only; they must not appear on social/search.
For EVERY row decide: OK, or PROBLEM with a precise reason (which token, what it should be per the evidence, and which rule). Be strict: if a token in "new" cannot be traced to the generator, the ad's names, the existing URL tokens, or the first-serving date, it is a PROBLEM. Do not report style preferences.
Write all PROBLEM rows to the output file as JSON list [{"n":..,"token":"utm_...","problem":"...","suggested":"..."}] and return counts.`
const SCHEMA = { type: 'object', properties: { reviewed: { type: 'integer' }, ok: { type: 'integer' }, problems: { type: 'integer' }, out_file: { type: 'string' }, systemic: { type: 'array', items: { type: 'string' } } }, required: ['reviewed', 'ok', 'problems', 'out_file'] }
const res = await parallel([1, 2, 3, 4].map(i => () => agent(`${RULES}
Your chunk: ${args.dir}/chunk_${i}.json (JSON list). Output file: ${args.dir}/problems_${i}.json. In "systemic", list any pattern that affects many rows.`,
  { label: `review:chunk_${i}`, phase: 'Review', schema: SCHEMA })))
return res
