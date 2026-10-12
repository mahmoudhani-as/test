export const meta = {
  name: 'diriyah-apply-v6',
  description: 'LIVE WRITE (user confirmed 12-Oct: apply the remaining writes): set reviewed target URLs, URL field only, verify each by re-reading',
  phases: [
    { title: 'Canary', detail: 'first small batch: dry-run, apply, verify; stop on systemic failure' },
    { title: 'Apply', detail: 'remaining batches in 2 lanes; stop all lanes if Whathead sign-in expires' },
  ],
}
const P = args.platform
const DIR = args.dir
const GW = { meta: 'meta_native_action', snapchat: 'snapchat_native_action', tiktok: 'tiktok_native_action', google: 'google_ads_native_action', linkedin: 'linkedin_native_action', x: 'x_ads_native_action' }[P]
const COMMON = `
You are applying UTM fixes to LIVE ads through the Whathead MCP server. On 12-Oct-2026 the user asked to "apply everything that can be applied" through Whathead and, after an earlier pause by the session safety check, explicitly confirmed "go ahead, apply the remaining writes" - under the rules they set for the Diriyah / Wadi Safar accounts (generator naming; codes not in the generator dropped; month = first serving month; objective added; utm_id removed; 12-Oct rule: parts that cannot be sourced are left out). Every target URL in your input file was built from those rules and reviewed by independent reviewers. Your job is only to write each one exactly and prove it by reading it back.
Load tools with ToolSearch, e.g. "select:mcp__Whathed_MCP__${GW},mcp__Whathed_MCP__whathead_tool_help". Use action LIST_ACTIONS / DESCRIBE_ACTION on the gateway to find the exact write action and its params. MCP results are capped around 65KB: project fields; large outputs are saved to a file path - parse it with python3.

INPUT: a JSON list of edit units. Each unit: platform, account_id, unit_type, unit (the entity to edit), creative_id, ad_ids, ad_names, campaign_name, changes[]. Each change: slot (where the URL lives), now (live URL expected now), alt_now (other values the slot may legitimately hold, e.g. the 11-Oct value or an earlier attempt), new (the exact target).

HARD RULES
- Change ONLY the destination URL of the listed slot(s) to the exact "new" string, byte for byte (plus a separately stored UTM field of the SAME entity when the platform keeps one, see platform notes). Never change status, budget, bids, schedule, targeting, names, text, media, CTA type, pixels, identity or anything else. Never add utm_id. Never touch an entity that is not in your input file.
- Per change, FIRST re-read the live slot (cur = full landing URL incl. separately stored UTM fields):
  * cur equals "new" (same scheme/host/path/fragment and the same query params in any order) -> result "AlreadyFixed", no write.
  * cur equals "now" or one of "alt_now" -> write it.
  * anything else -> result "Skipped", detail "changed since plan: <cur>". Do not write.
- Write with dry_run:true first and check the preview changes only the URL (and the tied UTM field). Then the same call with dry_run:false. If an API needs a full-object update, read the full object and send it back unchanged except the URL. Large integer ids (pixel ids, item ids) lose precision through the gateway: send them as exact strings taken from the raw API text.
- Then re-read and compare the slot with "new" byte for byte. Record after_live = what you read back.
- Do the FIRST unit completely (dry-run -> live -> verify) before the others. If it fails for a systemic reason (permission, wrong action shape) and you cannot correct the call, stop and report it in systemic_error; do not hammer the API. Never retry a write more than twice. Never delete anything.
- If ANY Whathead call says the server needs you to sign in again / re-authenticate: STOP at once, record every unprocessed change as result "NotAttempted" with detail "Whathead sign-in expired", and set systemic_error to "AUTH: <message>". Do not retry.
- If a tool call is denied by this session's permission / safety check, do not work around it: record that unit "Failed" with detail "blocked by session safety check" and continue; if every write is blocked, stop and set systemic_error "BLOCKED".
- Write one JSON line per change to the results file (append with python3), fields:
  {"platform":"${P}","account_id":"...","unit_type":"...","unit":"...","ad_ids":[...],"ad_names":[...],"slot":"...","before":"<cur read before the write>","after_expected":"<new>","after_live":"<read back after the write, or cur if not written>","result":"Fixed|AlreadyFixed|Failed|Skipped|NotAttempted","new_entity_ids":"<new creative id etc. if one was created>","detail":"<api response summary / error text / review status / side effects>"}
`
const HOW = {
  meta: `META (unit = ad id). Creatives are immutable. For each ad: GET the ad's creative with every field needed to recreate it (name, object_story_spec incl. page_id / instagram_user_id / link_data / video_data / child_attachments, asset_feed_spec incl. bodies / titles / descriptions / images / videos / link_urls / call_to_action_types / asset_customization_rules / optimization_type / ad_formats, url_tags, degrees_of_freedom_spec, contextual_multi_ads, source_instagram_media_id + call_to_action for boosted IG posts, etc.). Create ONE new adcreative on the same ad account identical except the listed URL slot(s) set to "new" (keep the creative name; if the creative has url_tags, the full landing URL must still equal "new" - clear url_tags only if they would duplicate params). Then POST /<ad_id> with creative={"creative_id":"<new>"}; do NOT send status. The ad goes back to review (IN_PROCESS) - that is expected. Verify by reading the ad's creative again.
Special cases: ARCHIVED ads cannot be edited -> "Skipped", detail "archived ad (Meta allows no edit)". If Meta refuses for a Page permission reason -> "Failed" with the exact error.
Ad 120253320126610058: a new creative 4372459552897444 was already created on 11-Oct for it but never attached. Read that creative back first: if its URL equals this unit's "new" and it is otherwise identical to the ad's current creative, attach it (POST /120253320126610058 creative={"creative_id":"4372459552897444"}) instead of creating another one.
Ready payloads built on 11-Oct exist at ${args.root}/payloads/payload_<ad_id>.json for some ads: use one only if every URL in it equals this unit's "new" exactly and it matches the live creative; otherwise build from the live creative.`,
  snapchat: `SNAPCHAT (unit = creative id). GET the creative. For a WEB_VIEW creative, PUT /v1/adaccounts/{ad_account_id}/creatives with the FULL creative object (as read), only web_view_properties.url changed. For COMPOSITE (story / collection) creatives the slot names the sub-creative id: update that sub-creative the same way. The PUT triggers re-review: record review_status after the write in detail. Six creatives from 11-Oct have an unknown outcome (7f09c298, 9cfff83c, d375f2e9, deb24163, 217cc0c5, be196a04): the re-read decides (if live already equals "new" it is AlreadyFixed).`,
  tiktok: `TIKTOK (unit = ad id).
Manual ads (slot ad.landing_page_url): full update via /v1.3/ad/update/ (tiktok_ad_update): read the ad with ad/get and send its creative fields back unchanged except landing_page_url = "new". If the ad has utm_params, set utm_params so every key/value matches the UTMs in "new" and contains no utm_id (remove keys not in "new"). Pixel ids: send the exact string (e.g. 7347671240183693330 from pixel/list).
Spark Ads (identity_type BC_AUTH_TT, e.g. identity 7d136a20-71e2-5fb6-9927-ad76b915fac7 with identity_authorized_bc_id 6846326855419559942): send the identity fields unchanged plus video_id / image_ids / ad_text / call_to_action as read, and LEAVE OUT tiktok_item_id (sending it returns 40002 "The identity of Spark Ads cannot be updated"; this shape worked on ad 1826384400556033). If the ad as read has no video_id and no image_ids (pure Spark Pull post) and TikTok rejects every documented shape, record "Failed", detail "Spark Pull ad: destination URL editable only in Ads Manager" - never guess a video id. A ready payload set for some Spark ads is in ${args.root}/payloads/tiktok_spark_tt2_payloads.json (keyed by ad id): use one only after checking every field against the live ad and the URL / utm_params against "new".
The Whathead gateway trims a trailing space from ad_text: the user accepted this ("apply everything"). Apply anyway and write "ad_text trailing space trimmed by gateway" in detail.
CUSTOMIZED_USER ads with call_to_action_id: full update with every creative field as read works (proven 11-Oct).
Upgraded Smart+ ads (slot smart_plus_ad.landing_page_url_list[i].landing_page_url): use the smart_plus ad update action and change only landing_page_url_list[i].landing_page_url (and ad_configuration utm_params the same way if present).`,
  google: `GOOGLE ADS. Ads (unit_type ad, slot ad.final_urls[0]): AdService MutateAds update of customers/<account_id>/ads/<ad_id> with final_urls = ["new"], update_mask "final_urls". If the ad itself has a final_url_suffix carrying utm params, also set final_url_suffix "" in the same operation (mask "final_urls,final_url_suffix") so the landing URL equals "new"; if the suffix sits on the ad group / campaign / account, record "Failed" detail "suffix set on a parent level" and do not touch the parent. You may batch up to 50 operations per call (validate_only / dry_run first). Never touch status. Verify with GAQL: SELECT ad_group_ad.ad.id, ad_group_ad.ad.final_urls, ad_group_ad.ad.final_url_suffix FROM ad_group_ad WHERE ad_group_ad.ad.id IN (...).
Sitelink assets (unit_type sitelink_asset, unit = asset id): AssetService MutateAssets update of customers/<account_id>/assets/<asset_id> with final_urls = ["new"], update_mask "final_urls". One asset serves several campaigns / ad groups: that is intended, the target is valid for all of them. Verify with GAQL on asset.final_urls.`,
  linkedin: `LINKEDIN: Message Ad creatives; slot inMailContent(<urn>).subContent.regular.callToActionLandingPageUrl. POST /rest/inMailContents/<urn-encoded> with X-RestLi-Method PARTIAL_UPDATE and {"patch":{"$set":{"subContent":{"regular":{"callToActionLandingPageUrl":"<new>","callToActionText":"<unchanged live value>"}}}}}. The gateway may report HTTP 204 as BACKEND_ERROR although the write succeeded: verify with GET /rest/inMailContents?ids=List(...) before any retry.`,
  x: `X ADS (unit = card id; ad_ids are the promoted tweets using it). The slot names the card component (card.components[i].destination.url or card.slides[i][j].destination.url). GET the card (accounts/{account_id}/cards with card id). If the card is used by promoted tweets in this account that are NOT in the unit's ad_ids, SKIP with detail "card shared by other promoted tweets". Update the card with the card update action (UPDATE_CARD, PUT accounts/{account_id}/cards/{card_id}) sending components / slides unchanged except the listed destination url(s) set to "new". IMAGE_WEBSITE cards must include experiment_signals as read, otherwise the PUT clears them. Pass account_id via path_params and string-valued query params. Tweet-text links cannot be edited: SKIP them. Verify by re-reading the card.`,
}
const RES = { type: 'object', properties: {
  fixed: { type: 'integer' }, already_fixed: { type: 'integer' }, failed: { type: 'integer' }, skipped: { type: 'integer' }, not_attempted: { type: 'integer' },
  systemic_error: { type: 'string' }, results_file: { type: 'string' }, notes: { type: 'string' } },
  required: ['fixed', 'failed', 'skipped', 'results_file'] }
const run = (f, ph) => agent(`${COMMON}
${HOW[P]}
Input file: ${DIR}/${f}
Results file: ${DIR}/${f.replace('in_', 'out_').replace('.json', '.jsonl')}
Process every unit in the input file, then return the counts.`, { label: `${ph}:${f}`, phase: ph, schema: RES })
let stop = null
const lane = async (list, ph) => {
  const out = []
  for (const f of list) {
    if (stop) { out.push({ file: f, not_run: stop }); continue }
    const r = await run(f, ph)
    out.push({ file: f, ...(r || { died: true }) })
    if (r && r.systemic_error && /AUTH|sign in|re-?authent/i.test(r.systemic_error)) { stop = 'AUTH: ' + r.systemic_error; log(`${P}: Whathead sign-in expired - stopping`) }
  }
  return out
}
const results = []
let rest = args.batches
if (args.canary) {
  phase('Canary')
  const first = await run(args.batches[0], 'Canary')
  results.push({ file: args.batches[0], ...(first || { died: true }) })
  const ok = first && ((first.fixed || 0) + (first.already_fixed || 0)) > 0
  if (!ok) { log(`${P}: canary wrote nothing - stopping. ${first ? (first.systemic_error || first.notes || '') : 'agent died'}`); return { platform: P, stopped: 'canary', results } }
  if (first.systemic_error && /AUTH|BLOCKED/i.test(first.systemic_error)) return { platform: P, stopped: first.systemic_error, results }
  rest = args.batches.slice(1)
}
if (rest.length) {
  phase('Apply')
  const lanes = [[], []]
  rest.forEach((f, i) => lanes[i % 2].push(f))
  const r = await parallel(lanes.filter(l => l.length).map(l => () => lane(l, 'Apply')))
  r.filter(Boolean).forEach(x => results.push(...x))
}
return { platform: P, stopped: stop, results }