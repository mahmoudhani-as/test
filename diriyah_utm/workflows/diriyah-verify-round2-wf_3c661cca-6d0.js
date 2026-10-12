export const meta = {
  name: 'diriyah-verify-round2',
  description: 'Read-only second-round adversarial review of a 300-row random sample of the corrected legacy/clash changes',
  phases: [{ title: 'Review', detail: '2 independent reviewers' }],
}
const RULES = `
You are an independent, skeptical reviewer. Read-only: do not call any ad platform. Generator workbook (the bible): ${args.gen} (sheets Schema, Mappings, Campaign_Code_Generator, Input/Output_Campaign_Generator; read with python3 openpyxl data_only=True).
Each row proposes changing a live ad URL from "now" to "new". User rules (11-Oct-2026):
1. utm_campaign = [code_]{campaign name}_{mon}{yy}_{objective}; utm_term = [code_]{ad set name}_{ad set language}; utm_content = [code_]{ad name}_{format}_{ad language}; lower-case; objective awr/cond/conv; language ar/en/all/en-ar; format from Mappings col T.
2. A code only if it is the Campaign_Code_Generator uid for exactly that name. Any other code (ad-id-, adset-id-, cam-id-, XXXXXX, RSA1, macros) dropped. Generator campaign codes may be used for a legacy campaign when the generator has that campaign (same year) or other ads in the same live campaign already carry it; same for ad set codes within the same live ad set.
3. Month/year = month the ad first served (basis line 'MonthYear ... first day the ad served (YYYY-MM-DD ...)'); clash rows use the serving date listed in their basis too.
4. Objective from the live campaign name: AWR->awr, CONV->conv, LEAD->conv, TRF->cond, or awareness/consideration/conversion words.
5. No utm_id, no fbclid; landing page host/path/fragment unchanged.
6. Names come from the ad's generator-format entity names or its own old UTM tokens with dates, codes, placeholders and other-position words (language, funnel, objective, channel, format words like carousel/image) removed; never template placeholders; never a token that belongs to a different campaign/creative; a creative number must agree with the ad name.
7. Ad set language = the ad set name's language (EN/AR/EN-AR incl. 'EN/AR'); ad language = the ad name's language; only if the name has none, the old token, then the landing page.
8. kva/kvb/kvd never on social/search.
For EVERY row decide OK or PROBLEM (exact token, what it should be, which rule). Be strict but do not report style preferences or things the rules allow.
Write PROBLEM rows to the output file as a JSON list [{"n":..,"token":..,"problem":..,"suggested":..}] and return counts.`
const SCHEMA = { type: 'object', properties: { reviewed: { type: 'integer' }, ok: { type: 'integer' }, problems: { type: 'integer' }, out_file: { type: 'string' }, systemic: { type: 'array', items: { type: 'string' } } }, required: ['reviewed', 'ok', 'problems', 'out_file'] }
return await parallel(['a', 'b'].map(x => () => agent(`${RULES}
Your rows: ${args.dir}/round2_${x}.json. Output file: ${args.dir}/round2_problems_${x}.json. For context you may look up any row in ${args.dir}/all_rows_v2.json (all 1,163 proposed changes) and the live inventory JSON Lines files in ${args.live}.`,
  { label: `review2:${x}`, phase: 'Review', schema: SCHEMA })))
