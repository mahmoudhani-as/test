export const meta = {
  name: 'diriyah-review-targets',
  description: 'Read-only adversarial review of proposed UTM target URLs against the generator workbook and the user rules (two lenses per chunk)',
  phases: [{ title: 'Review', detail: 'trace lens + evidence lens per chunk' }],
}
const RULES = `
You are an independent, skeptical reviewer of proposed ad URL changes. Nothing is written to any ad platform in this task; you only read local files. Use python3 for everything.
Generator workbook (the user calls it "the bible"): ${args.gen}. Read sheets Schema, Mappings, Campaign_Code_Generator, Input_Campaign_Generator, Output_Campaign_Generator with openpyxl (data_only=True). Campaign_Code_Generator holds the only valid 8-hex uids (a uid belongs to exactly one campaign / ad set / ad name).
Each row of your chunk is one live ad URL slot changing from "now" to "new". Fields: platform, account, campaign_name, adset_name, ad_id, ad_name, slot, first_serving_date (first day the ad had impressions, account time zone; null if not pulled or never served), kind (generator | legacy | clash | omit | omit-sitelink = which rule built "new"), basis (how each token was sourced), omitted (schema parts deliberately left out).
USER RULES (binding, latest 12-Oct-2026):
1. Schema: utm_campaign = uid_campaign-name_monYY_objective ; utm_term = uid_adset-name_adset-lang ; utm_content = uid_ad-name_format_ad-lang. All lower case. utm_source / utm_medium from the Mappings lists. No utm_id anywhere. Objective (awr / cond / conv) is always added when known.
2. Uids: only Campaign_Code_Generator codes, and only for exactly that name. A name the generator has no code for gets NO code (codes like ad-id-..., adset-id-..., cam-id-..., XXXXXX, RSA1, 2883, macros like {creative} must be dropped, never carried). Manazel: use the generator code if it has one, else drop.
3. Month = month the ad FIRST SERVED (first_serving_date), not the campaign-name date and not the creation date. For sitelinks (no serving date of their own) the month is left out.
4. kva / kvb / kvd creatives are programmatic-only: on social or search the ad token is unknown and is left out.
5. 12-Oct omit rule: "for unknown figures like ad tokens write the utm without them". A schema part that cannot be sourced is LEFT OUT, never invented (no usable name, never served -> no month, kva, sitelinks with no code, a campaign shared by several sitelinks). A whole parameter with no known part is dropped. Leaving a part out is CORRECT when it truly cannot be sourced; it is a PROBLEM only when the evidence in the row clearly gives that part.
6. Ritz Google search content = 78f964bb_rcsr-search_search_{lang}.
7. Landing page (scheme, host, path, fragment) and non-UTM query params must not change; click ids (fbclid, gclid...) are dropped.
PAST MISTAKES to hunt for: audience tags (aud, ret, prospecting, retargeting, lal) copied in as creative/ad names; rsa1 / googlesearch / tactical / search-network words kept as names; wrong format (e.g. display on a video ad, carousel vs display, story); old tokens that name ANOTHER creative or campaign than this ad; language that contradicts the ad name or landing page (/ar/ vs /en/); month not equal to first_serving_date's month; codes that do not belong to the name; template placeholders (test_adset_name, adset_name, test_ad_name); upper case; characters outside a-z0-9_-; "_" inside a name.
For EVERY row decide OK or PROBLEM. Be strict but fair: a PROBLEM must cite the exact token, the evidence that proves it wrong (which field / which generator row), the rule number, and what it should be (or "leave out"). Do not report style preferences or things the rules allow.
Write ALL PROBLEM rows to the output file as a JSON list [{"n":..,"ad_id":"..","slot":"..","token":"utm_...","problem":"...","suggested":"...","severity":"high|low"}] (empty list if none) and return counts. In "systemic", describe any pattern that affects several rows (so it can be fixed at the source).`
const LENS = {
  trace: 'YOUR LENS: TRACEABILITY. For every token in "new", find where it comes from: the generator (uid <-> name pair, Mappings lists), the ad\'s own names (campaign / ad set / ad name), the existing "now" URL tokens, or first_serving_date. Any token you cannot trace is a PROBLEM (invented). Any uid that is not the generator code of exactly that name is a PROBLEM. Any token naming a different creative/campaign than this ad is a PROBLEM.',
  evidence: 'YOUR LENS: EVIDENCE AGREEMENT. Check that month == month of first_serving_date (mmmYY), objective agrees with the campaign name (AWR->awr, CONV/LEAD->conv, TRF->cond, or the generator Input rows for funnel + sub-objective), languages agree with the ad / ad set names and the landing page path, the format word agrees with the ad name / creative type / slot (video vs display vs carousel vs story vs search), source/medium agree with platform and Mappings, and that nothing the evidence clearly provides was left out, and nothing was kept that should have been dropped.',
}
const SCHEMA = { type: 'object', properties: { reviewed: { type: 'integer' }, ok: { type: 'integer' }, problems: { type: 'integer' }, out_file: { type: 'string' }, systemic: { type: 'array', items: { type: 'string' } } }, required: ['reviewed', 'ok', 'problems', 'out_file'] }
const jobs = []
for (const c of args.chunks) for (const l of ['trace', 'evidence']) jobs.push({ c, l })
const res = await parallel(jobs.map(j => () => agent(`${RULES}
${LENS[j.l]}
Your chunk: ${args.dir}/chunk_${j.c}.json (JSON list; review every row). Output file: ${args.dir}/problems_${j.c}_${j.l}.json.`,
  { label: `review:${j.l}:chunk_${j.c}`, phase: 'Review', schema: SCHEMA }).then(r => ({ chunk: j.c, lens: j.l, ...(r || {}) }))))
return res