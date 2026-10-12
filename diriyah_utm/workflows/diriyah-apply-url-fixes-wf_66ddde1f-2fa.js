export const meta = {
  name: 'diriyah-apply-url-fixes',
  description: 'LIVE WRITE (user-approved 11-Oct): apply 146 generator-derived final URLs, URL field only, verify each by re-reading',
  phases: [
    { title: 'Canary', detail: 'first batch: dry-run, apply, verify; stop if systematic failure' },
    { title: 'Apply', detail: 'remaining batches in parallel' },
  ],
}
const P = args.platform
const DIR = args.dir
const GW = { meta: 'meta_native_action', snapchat: 'snapchat_native_action', tiktok: 'tiktok_native_action', google: 'google_ads_native_action', linkedin: 'linkedin_native_action', x: 'x_ads_native_action' }[P]
const COMMON = `
You are applying UTM fixes to LIVE ads through the Whathead MCP server. The user explicitly approved exactly these changes (the 'Changes ready' list) on 11-Oct-2026.
Load tools with ToolSearch, e.g. "select:mcp__Whathed_MCP__${GW},mcp__Whathed_MCP__whathead_tool_help". Use LIST_ACTIONS / DESCRIBE_ACTION to find the exact write action and its required params.

HARD RULES
- Change ONLY the destination URL in the listed slot(s), to the exact "new" string, byte for byte. Do not change status, budget, bids, targeting, names, text, media, CTA type, or anything else. Do not add utm_id. Do not touch any entity not listed in your input file.
- For every item: (1) re-read the live entity; if the slot's current URL is not exactly the "now" value, SKIP it (result "Skipped", detail "changed since inventory: <current>"). (2) Make the write with dry_run:true first and check the preview only changes the URL, then repeat with dry_run:false. If an API requires a full-object PUT, read the full object and send it back unchanged except the URL. (3) Re-read and confirm the slot now equals "new" exactly.
- Do the FIRST item completely (dry-run -> live -> verify) before the others. If it fails for a systemic reason (permission, wrong action shape) and you cannot correct the call, stop and report; do not hammer the API.
- Never delete anything. Never retry a write more than twice.
- Record one JSON line per change (per slot) to the results file (append, python3 or Write tool), fields:
  {"platform":"${P}","account_id":"...","unit":"...","ad_ids":[...],"ad_names":[...],"slot":"...","before":"<now>","after_expected":"<new>","after_live":"<URL read back after the write, or current URL if skipped/failed>","result":"Fixed|Failed|Skipped","new_entity_ids":"<new creative id etc. if one was created>","detail":"<api response summary / error text / review status>"}
`
const HOW = {
  meta: `META: creatives are immutable. Per ad (unit = ad id): GET the ad's creative with all fields needed to recreate it (name, object_story_spec incl. page_id/instagram_user_id/link_data/video_data/child_attachments, asset_feed_spec, url_tags, degrees_of_freedom_spec, contextual_multi_ads, etc.). Create a NEW adcreative on the same ad account that is identical except the listed URL slot(s) are set to "new" (all listed slots of that ad go into one new creative; keep the original creative name). Then update the ad (POST /<ad_id>) with creative={"creative_id":"<new>"}; do not send status. Verify by reading the ad's creative again. The ad may re-enter review: record the ad's effective_status after the update in detail. If Meta refuses for a Page permission reason, record Failed with the exact error.`,
  snapchat: `SNAPCHAT: unit = creative id. GET the creative (and for composite/story, the listed sub-creative). PUT /v1/adaccounts/{ad_account_id}/creatives with the full creative object, only web_view_properties.url changed to "new". This triggers re-review; record the creative review_status after the write in detail.`,
  tiktok: `TIKTOK: unit = ad id. Manual ads (slot ad.landing_page_url): use the ad update action (/v1.3/ad/update/). Check with DESCRIBE_ACTION which fields are required (adgroup_id, creatives[] with ad_id and the creative's existing fields); read the ad with ad/get and send its existing values back unchanged except landing_page_url = "new". If the ad has utm_params, set utm_params so every key/value matches the UTMs in "new" (and contains no utm_id). Upgraded Smart+ ads (slot smart_plus_ad.landing_page_url_list[0].landing_page_url): use the smart_plus ad update action, change only landing_page_url_list[0].landing_page_url (and ad_configuration.utm_params the same way if present). Verify by re-reading (ad/get or smart_plus/ad/get).`,
  google: `GOOGLE ADS: unit = ad id (responsive search ads). Use the AdService mutate (search LIST_ACTIONS for "ad_service" / "mutate_ads") to update resource customers/<account_id>/ads/<ad_id>: final_urls = ["new"], update_mask "final_urls". Do not touch the ad group ad status. Verify with GAQL: SELECT ad_group_ad.ad.final_urls, ad_group_ad.policy_summary.approval_status FROM ad_group_ad WHERE ad_group_ad.ad.id = <id>.`,
  linkedin: `LINKEDIN: units are Message Ad creatives; the URL slot is inMailContent(<urn>).subContent.regular.callToActionLandingPageUrl. Use PARTIAL_UPDATE on /rest/inMailContents/<urn-encoded> with {"patch":{"$set":{"subContent":{"regular":{"callToActionLandingPageUrl":"<new>"}}}}} (check DESCRIBE_ACTION for the exact shape; if the regular subContent requires sibling fields in the $set, read the full content and send them back unchanged). Verify with GET /rest/inMailContents?ids=List(...).`,
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
  const rest = await parallel(args.batches.slice(1).map(f => () => run(f, 'Apply')))
  results.push(...rest)
}
return { platform: P, results }
