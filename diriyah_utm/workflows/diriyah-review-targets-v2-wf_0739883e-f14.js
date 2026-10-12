export const meta = {
  name: 'diriyah-review-targets-v2',
  description: 'Read-only adversarial review of rebuilt (v5) UTM target URLs against the generator workbook and the user rules (two lenses per chunk)',
  phases: [{ title: 'Review', detail: 'trace lens + evidence lens per chunk' }],
}
const RULES = `
You are an independent, skeptical reviewer of proposed ad URL changes. Nothing is written to any ad platform in this task; you only read local files. Use python3 for everything.
Generator workbook (the user calls it "the bible"): ${args.gen}. Read sheets Schema, Mappings, Campaign_Code_Generator, Input_Campaign_Generator, Output_Campaign_Generator with openpyxl (data_only=True). Campaign_Code_Generator holds the only valid 8-hex uids (a uid belongs to exactly one campaign / ad set / ad name).
Each row of your chunk is one live ad URL slot changing from "now" (the 11-Oct live URL) to "new". Fields: platform, account, campaign_name, adset_name, ad_id, ad_name, slot, first_serving_date (first day with impressions in the account time zone; null = never served or a sitelink), kind (generator | legacy | clash | omit | omit-sitelink = which rule built "new"), basis (how each token was sourced, incl. sibling and month notes), omitted (parts deliberately left out), sitelink_placements (for sitelinks: every campaign | ad group the asset is linked to).
USER RULES (binding, latest 12-Oct-2026):
1. Schema: utm_campaign = uid_campaign-name_monYY_objective ; utm_term = uid_adset-name_adset-lang ; utm_content = uid_ad-name_format_ad-lang. All lower case. utm_source / utm_medium from the Mappings lists. No utm_id anywhere. Objective (awr / cond / conv) is always added when known.
2. Uids: only Campaign_Code_Generator codes, and only for exactly that name. A name the generator has no code for gets NO code (codes like ad-id-..., adset-id-..., cam-id-..., XXXXXX, RSA1, 2883, macros like {creative} are dropped, never carried). Manazel: use the generator code if it has one, else drop.
3. Month = month the ad FIRST SERVED (first_serving_date), never the campaign-name date. Never served -> month left out. Sitelinks: month left out.
4. kva / kvb / kvd creatives are programmatic-only: on social or search the ad token is unknown and is left out.
5. 12-Oct omit rule: "for unknown figures like ad tokens write the utm without them". A part that cannot be sourced is LEFT OUT, never invented. A whole parameter with no known part is dropped. Leaving out is CORRECT when the part truly cannot be sourced; it is a PROBLEM only when the evidence in the row clearly gives it.
6. Ritz Google search content = 78f964bb_rcsr-search_search_{lang}.
7. Landing page (scheme, host, path, fragment) and non-UTM query params must not change (Google ValueTrack params like {device} outside the utm_ values are fine); click ids are dropped.
AGREED POLICIES (v5, from the first review round - do not flag these as problems by themselves):
a. Names come from the generator, from codes/names sibling ads in the same live campaign / ad set already use, or from the ad's own old UTM token. A live campaign carries one utm_campaign name and a live ad set one utm_term name: a missing or foreign name is taken from the dominant sibling name.
b. Objective from the campaign name: funnel+objective token (_MF_TRF_ -> cond, AWR -> awr, CONV/LEAD -> conv), bare tokens (_Conv_, _lf_conv_), definition words (awareness/consideration/conversion), or sub-objective words whose generator rows all use one objective (reach -> awr, traffic -> cond, leads/sales -> conv). Disagreeing sources -> left out.
c. utm_source follows the campaign name's own channel token when it has one (_Meta_ -> meta, _X_ -> x), as the generator does.
d. Format: the video slot (video_data) means video; carousel has no Mappings format and is written as display.
e. A vocabulary word that leads a numeric name stays (video-2-15s); a duration-only token (45s) or a creative number the ad name does not carry is not a name; a version tag >= 2 in the ad name (_V2, Option 2) is kept on the ad-name part.
f. Sitelinks: a part is kept only when every placement gives the same value (objective from each placement campaign; ad set part from built ads, else the ad group / campaign language; ad language from the sitelink text script and placement names, else the landing page). Assets linked to Search and Demand Gen together are on the user's manual list (not in your chunk).
g. The agency prefix "hs-" carried in legacy campaign tokens is kept (traceable to the old token).
PAST MISTAKES to hunt for: audience tags (aud, ret, prospecting, retargeting, lal) as names; rsa1 / googlesearch / tactical / search-network words kept as names; wrong format; old tokens that name ANOTHER creative or campaign than this ad (e.g. a Ramadan token inside a Summer campaign, a 10s token on a 45s ad); language contradicting the ad name; month != first_serving_date month; codes not belonging to the name; template placeholders (test_adset_name, test_ad_name, campaign-name); broken name fragments; upper case; characters outside a-z0-9_-; "_" inside a name.
For EVERY row decide OK or PROBLEM. Be strict but fair: a PROBLEM must cite the exact token, the evidence that proves it wrong, the rule or policy, and what it should be (or "leave out"). Do not report style preferences or things the rules and policies allow.
Write ALL PROBLEM rows to the output file as a JSON list [{"n":..,"ad_id":"..","slot":"..","token":"utm_...","problem":"...","suggested":"...","severity":"high|low"}] (empty list if none) and return counts. In "systemic", describe any pattern that affects several rows.`
const LENS = {
  trace: 'YOUR LENS: TRACEABILITY. For every token in "new", find where it comes from: the generator (uid <-> name pair, Mappings lists), sibling usage stated in basis, the ad\'s own names, the "now" URL tokens, or first_serving_date. Any token you cannot trace is a PROBLEM (invented). Any uid that is not the generator code of exactly that name is a PROBLEM. Any token naming a different creative / campaign than this ad is a PROBLEM.',
  evidence: 'YOUR LENS: EVIDENCE AGREEMENT. Check month == month of first_serving_date (mmmYY) or left out when null, objective agrees with the campaign name per policy b, languages agree with the ad / ad set names and the landing page, the format word agrees with the ad name / creative type / slot, source/medium agree with platform and Mappings, nothing the evidence clearly provides was left out, and nothing was kept that should have been dropped.',
}
const SCHEMA = { type: 'object', properties: { reviewed: { type: 'integer' }, ok: { type: 'integer' }, problems: { type: 'integer' }, out_file: { type: 'string' }, systemic: { type: 'array', items: { type: 'string' } } }, required: ['reviewed', 'ok', 'problems', 'out_file'] }
const jobs = []
for (const c of args.chunks) for (const l of ['trace', 'evidence']) jobs.push({ c, l })
const res = await parallel(jobs.map(j => () => agent(`${RULES}
${LENS[j.l]}
Your chunk: ${args.dir}/chunk_${j.c}.json (JSON list; review every row). Output file: ${args.dir}/problems_${j.c}_${j.l}.json.`,
  { label: `review2:${j.l}:chunk_${j.c}`, phase: 'Review', schema: SCHEMA }).then(r => ({ chunk: j.c, lens: j.l, ...(r || {}) }))))
return res