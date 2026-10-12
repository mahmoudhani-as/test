export const meta = {
  name: 'diriyah-review-targets-v3',
  description: 'Read-only final review of the v6 UTM target URLs (one combined trace + evidence reviewer per chunk)',
  phases: [{ title: 'Review', detail: 'one combined reviewer per chunk' }],
}
const RULES = `
You are an independent, skeptical reviewer of proposed ad URL changes. Nothing is written to any ad platform in this task; you only read local files. Use python3 for everything.
Generator workbook (the user calls it "the bible"): ${args.gen}. Read sheets Schema, Mappings, Campaign_Code_Generator, Input_Campaign_Generator, Output_Campaign_Generator with openpyxl (data_only=True). Campaign_Code_Generator holds the only valid 8-hex uids (a uid belongs to exactly one campaign / ad set / ad name).
Each row of your chunk is one live ad URL slot changing from "now" (the 11-Oct live URL) to "new". Fields: platform, account, campaign_name, adset_name, ad_id, ad_name, slot, creative_notes (live inventory notes incl. creative / card type), first_serving_date (first day with impressions, account time zone; null = never served or a sitelink), kind (which rule built "new"), basis (how each token was sourced), omitted (parts deliberately left out), sitelink_placements (for sitelinks: EVERY campaign | ad group the asset is linked to).
USER RULES (binding, latest 12-Oct-2026):
1. Schema: utm_campaign = uid_campaign-name_monYY_objective ; utm_term = uid_adset-name_adset-lang ; utm_content = uid_ad-name_format_ad-lang. All lower case. No utm_id. Objective (awr / cond / conv) always added when known.
2. Uids: only Campaign_Code_Generator codes, only for exactly that name; otherwise no code. Manazel: use the generator code if it has one.
3. Month = month the ad FIRST SERVED (first_serving_date); never served -> left out; sitelinks -> left out.
4. kva / kvb / kvd: programmatic-only, ad token left out on social / search.
5. 12-Oct omit rule: a part that cannot be sourced is LEFT OUT, never invented; a parameter with no known part is dropped. Leaving out is a PROBLEM only when the evidence in the row clearly gives the part.
6. Ritz-Carlton Signature Google search content = 78f964bb_rcsr-search_search_{lang}.
7. Landing page (scheme, host, path, fragment) and non-UTM query params unchanged (Google ValueTrack params outside utm_ values are fine); click ids dropped.
AGREED POLICIES (v6 - not problems by themselves):
a. Names from the generator (also when a generator name is exactly in the live ad / ad set name), from names sibling ads in the same live campaign / ad set use, or from the ad's own old UTM token. One utm_campaign name per live campaign, one utm_term name per live ad set. Old generator-layout tokens (agency_unit_asset_type_NAME_...) contribute only their NAME field (e.g. visitor-diriyah-coe).
b. Objective from the campaign name (funnel+objective tokens, bare tokens, awareness/consideration/conversion, sub-objective words reach->awr, traffic->cond, leads/sales->conv); if the campaign name gives none, from the ad's own old token.
c. utm_source follows the campaign name's channel token when present. utm_medium = the generator's medium for the source (google -> paid-search; social -> paid-social); Demand Gen (gadg) has no generator row, so its medium is left out.
d. Format: video slot / creative type (SINGLE_VIDEO, VIDEO_WEBSITE) -> video; link_data image / IMAGE_WEBSITE / carousel -> display; else the ad name; template placeholder tokens are no evidence.
e. Language: ad / ad set name, then the campaign's EN/AR token, then the landing page.
f. Sitelinks: a part is kept only when every placement gives the same value.
g. The agency prefix "hs-" in legacy campaign tokens is kept.
PAST MISTAKES to hunt for: audience / targeting / country / KPI words as names; macros or placeholders as names (campaign-name, creative, test_*); old tokens naming ANOTHER campaign, season or creative than this ad; wrong format; language contradicting the ad; month != first_serving_date month; codes not belonging to the name; broken fragments; upper case; characters outside a-z0-9_-; "_" inside a name; any malformed URL (spaces, empty keys).
Check BOTH traceability (every token traces to the generator, a sibling, the ad's names, the old token or first_serving_date) AND evidence agreement (month, objective, language, format, source/medium). For EVERY row decide OK or PROBLEM; a PROBLEM must cite the exact token, the evidence, the rule / policy, and the fix (or "leave out"). Do not report style preferences or anything the rules and policies allow.
Write ALL PROBLEM rows to the output file as a JSON list [{"n":..,"ad_id":"..","slot":"..","token":"utm_...","problem":"...","suggested":"...","severity":"high|low"}] (empty list if none) and return counts. In "systemic", describe any pattern that affects several rows.`
const SCHEMA = { type: 'object', properties: { reviewed: { type: 'integer' }, ok: { type: 'integer' }, problems: { type: 'integer' }, out_file: { type: 'string' }, systemic: { type: 'array', items: { type: 'string' } } }, required: ['reviewed', 'ok', 'problems', 'out_file'] }
const res = await parallel(args.chunks.map(c => () => agent(`${RULES}
Your chunk: ${args.dir}/chunk_${c}.json (JSON list; review every row). Output file: ${args.dir}/problems_${c}.json.`,
  { label: `review3:chunk_${c}`, phase: 'Review', schema: SCHEMA }).then(r => ({ chunk: c, ...(r || {}) }))))
return res