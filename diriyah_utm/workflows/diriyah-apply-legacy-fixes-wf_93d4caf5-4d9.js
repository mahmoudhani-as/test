export const meta = {
  name: 'diriyah-apply-legacy-fixes',
  description: 'LIVE WRITE (user-approved 11-Oct legacy rule): apply rebuilt final URLs, URL field only, verify each by re-reading',
  phases: [
    { title: 'Canary', detail: 'first batch: dry-run, apply, verify; stop if systematic failure' },
    { title: 'Apply', detail: 'remaining batches' },
  ],
}
const P = args.platform
const DIR = args.dir
const GW = { meta: 'meta_native_action', snapchat: 'snapchat_native_action', tiktok: 'tiktok_native_action', google: 'google_ads_native_action', linkedin: 'linkedin_native_action', x: 'x_ads_native_action' }[P]
const COMMON = `
You are applying UTM fixes to LIVE ads through the Whathead MCP server. The user explicitly approved exactly these changes on 11-Oct-2026 (legacy URLs rebuilt to the generator format: codes not in the generator dropped, month = first serving month, objective added, utm_id removed).
Load tools with ToolSearch, e.g. "select:mcp__Whathed_MCP__${GW},mcp__Whathed_MCP__whathead_tool_help". Use LIST_ACTIONS / DESCRIBE_ACTION to find the exact write action and its required params.

HARD RULES
- Change ONLY the destination URL in the listed slot(s), to the exact "new" string, byte for byte. Do not change status, budget, bids, targeting, names, text, media, CTA type, pixels, identity or anything else. Do not add utm_id. Do not touch any entity not listed in your input file.
- Large integer ids (pixel ids, etc.) can lose precision through the gateway (float rounding). When an API needs you to send such a field back, use the exact value as a string from the raw API text, never a rounded number.
- For every item: (1) re-read the live entity; if the slot's current URL is not exactly the "now" value, SKIP it (result "Skipped", detail "changed since inventory: <current>"). (2) Make the write with dry_run:true first and check the preview only changes the URL, then repeat with dry_run:false. If an API requires a full-object PUT, read the full object and send it back unchanged except the URL. (3) Re-read and confirm the slot now equals "new" exactly.
- Do the FIRST item completely (dry-run -> live -> verify) before the others. If it fails for a systemic reason (permission, wrong action shape) and you cannot correct the call, stop and report; do not hammer the API.
- Never delete anything. Never retry a write more than twice.
- Record one JSON line per change (per slot) to the results file (append with the Write/Edit tool or python3), fields:
  {"platform":"${P}","account_id":"...","unit":"...","ad_ids":[...],"ad_names":[...],"slot":"...","before":"<now>","after_expected":"<new>","after_live":"<URL read back after the write, or current URL if skipped/failed>","result":"Fixed|Failed|Skipped","new_entity_ids":"<new creative id etc. if one was created>","detail":"<api response summary / error text / review status>"}
`
const HOW = {
  meta: `META: creatives are immutable. Per ad (unit = ad id): GET the ad's creative with all fields needed to recreate it (name, object_story_spec incl. page_id/instagram_user_id/link_data/video_data/child_attachments, asset_feed_spec, url_tags, degrees_of_freedom_spec, contextual_multi_ads, source_instagram_media_id + call_to_action for boosted IG posts, etc.). Create a NEW adcreative on the same ad account that is identical except the listed URL slot(s) are set to "new" (all listed slots of that ad go into one new creative; keep the original creative name). Then update the ad (POST /<ad_id>) with creative={"creative_id":"<new>"}; do not send status. Verify by reading the ad's creative again. ARCHIVED ads cannot be edited: record Skipped with that reason. If Meta refuses for a Page permission reason, record Failed with the exact error.`,
  snapchat: `SNAPCHAT: unit = creative id. GET the creative. For a WEB_VIEW creative PUT /v1/adaccounts/{ad_account_id}/creatives with the full creative object, only web_view_properties.url changed. For COMPOSITE (story) creatives the slot names the sub-creative id: update that sub-creative the same way. This triggers re-review; record review_status after the write.`,
  tiktok: `TIKTOK: unit = ad id. Manual ads (slot ad.landing_page_url): use ad update (/v1.3/ad/update/) as a full update; read the ad with ad/get and send its existing creative fields back unchanged except landing_page_url = "new". If the ad has utm_params, set utm_params so every key/value matches the UTMs in "new" and contains no utm_id (remove keys not in "new"). Upgraded Smart+ ads (slot smart_plus_ad.landing_page_url_list[0].landing_page_url): use the smart_plus ad update action and change only landing_page_url_list[0].landing_page_url (and ad_configuration.utm_params the same way if present). Verify by re-reading.`,
  google: `GOOGLE ADS: unit = ad id (responsive search ads). AdService mutate: update customers/<account_id>/ads/<ad_id> with final_urls = ["new"], update_mask "final_urls". Do not touch status. Verify with GAQL on ad_group_ad.ad.final_urls.`,
  linkedin: `LINKEDIN: units are Message Ad creatives; slot inMailContent(<urn>).subContent.regular.callToActionLandingPageUrl. POST /rest/inMailContents/<urn-encoded> with X-RestLi-Method PARTIAL_UPDATE and {"patch":{"$set":{"subContent":{"regular":{"callToActionLandingPageUrl":"<new>","callToActionText":"<unchanged live value>"}}}}}. The gateway may report HTTP 204 as BACKEND_ERROR although the write succeeded: verify with GET /rest/inMailContents?ids=List(...) before retrying.`,
  x: `X ADS: unit = tweet id (creative_id). The URL lives on the tweet's card (slot card.components[i].destination.url or card.slides[i][j].destination.url). GET the card (accounts/{account_id}/cards with card_uris or the card id from the tweet). If that card is also used by tweets NOT in your unit list, SKIP with detail "card shared by other tweets". Update the card with the card update action (UPDATE_CARD, PUT accounts/{account_id}/cards/{card_id}) sending the components/slides unchanged except the listed destination url(s) set to "new". Pass account_id via path_params and string-valued query params (top-level account_id with numeric params returned 401 earlier). Slots that are tweet-text links cannot be edited: SKIP them. Verify by re-reading the card.`,
}
const RES = { type: 'object', properties: {
  fixed: { type: 'integer' }, failed: { type: 'integer' }, skipped: { type: 'integer' },
  systemic_error: { type: 'string' }, results_file: { type: 'string' }, notes: { type: 'string' } },
  required: ['fixed', 'failed', 'skipped', 'results_file'] }
const run = (f, ph) => agent(`${COMMON}
${HOW[P]}
Input file (JSON list of edit units with their changes): ${DIR}/${f}
Results file: ${DIR}/${f.replace('in_', 'out_').replace('.json', '.jsonl')}
Process every unit in the input file. Return counts.`, { label: `${ph}:${f}`, phase: ph, schema: RES })
phase('Canary')
const first = await run(args.batches[0], 'Canary')
const results = [first]
if (!first || first.fixed === 0) {
  log(`${P}: canary batch fixed nothing - stopping. ${first ? (first.systemic_error || first.notes || '') : 'agent died'}`)
} else if (args.batches.length > 1) {
  phase('Apply')
  results.push(...await parallel(args.batches.slice(1).map(f => () => run(f, 'Apply'))))
}
return { platform: P, results }
