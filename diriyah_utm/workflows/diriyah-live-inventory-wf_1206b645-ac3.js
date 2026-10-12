export const meta = {
  name: 'diriyah-live-inventory',
  description: 'Read-only: discover every Diriyah/Wadi ad account on 6 platforms and pull every ad + every final URL slot to JSONL',
  phases: [
    { title: 'Discover', detail: 'find every account whose name contains diriyah or wadi' },
    { title: 'Inventory', detail: 'one agent per account pulls every ad and URL slot' },
  ],
}

const OUT = args.out_dir
const COMMON = `
You are working READ-ONLY against live ad platforms through the Whathead MCP server.
- Load the tools you need with ToolSearch first, e.g. query "select:mcp__Whathed_MCP__whathead_workspace,mcp__Whathed_MCP__whathead_tool_help,mcp__Whathed_MCP__<platform>_native_action".
- NEVER call any create/update/patch/delete/status-change action. NEVER pass dry_run:false. Reads only.
- Use action="LIST_ACTIONS" (with search=...) and action="DESCRIBE_ACTION" (target_action=...) on the platform gateway to find the right endpoint and its params.
- Every MCP result is capped around 65KB: always project fields (fields / result_fields), use compact:true, keep page sizes modest, and PAGINATE UNTIL THE END (aggregate_pages / cursors / next links / page tokens). Never stop at page 1. If a response says it was truncated, re-request smaller.
- Do not guess or invent values. If something cannot be read, record it with a note saying exactly what failed (HTTP code / error text).
`

const RECORD = `
Write results as JSON Lines (one JSON object per line) to the exact file path given, using Bash (python3 or a heredoc) or the Write tool. Overwrite the file if it exists. One line per URL slot per ad; an ad with no URL at all still gets exactly ONE line with "url": null so every ad is counted. Fields (use null when not applicable):
{"platform": "<meta|tiktok|snapchat|linkedin|x|google>",
 "account_id": "...", "account_name": "...",
 "campaign_id": "...", "campaign_name": "...", "campaign_status": "...",
 "adset_id": "...", "adset_name": "...", "adset_status": "...",     // ad set / ad squad / ad group / line item / LinkedIn campaign
 "ad_id": "...", "ad_name": "...", "ad_status": "...", "effective_status": "...",
 "creative_id": "...", "creative_name": "...",
 "slot": "<exact place the URL lives, e.g. creative.object_story_spec.link_data.link, child_attachments[2].link, web_view_properties.url, card.components[0].destination.url, ad.final_urls[0], sitelink asset 123>",
 "base_url": "<URL as stored in that slot>",
 "url_tags": "<separately stored tracking params, e.g. Meta creative.url_tags, Google effective final_url_suffix, TikTok utm_params rendered as k=v&k=v; else null>",
 "url": "<the FULL final URL a user lands on = base_url plus url_tags/suffix appended with ? or &; null if none>",
 "tracking_template": "<Google tracking_url_template or similar, else null>",
 "editable": "<yes|no|unknown>", "edit_method": "<how this slot would be changed, e.g. 'new creative + ad update', 'PUT creatives', 'ad/update', 'card update', 'ad_group_ad mutate'>",
 "notes": "<anything relevant: boosted post, lead form, Smart+, API error text, etc.>"}
Include EVERY ad that is not deleted/removed, in ANY status (active, paused, archived, disapproved, campaign off, etc.).
`

const PLATFORM_HINTS = {
  meta: `Meta (meta_native_action). Pull from the ads edge of act_<id> with fields like id,name,status,effective_status,campaign{id,name,status},adset{id,name,status},creative{id,name,url_tags,object_story_spec,asset_feed_spec,object_story_id,effective_object_story_id,link_url,object_type}. Meta hides ARCHIVED ads unless you filter effective_status explicitly — include ACTIVE,PAUSED,CAMPAIGN_PAUSED,ADSET_PAUSED,ARCHIVED,DISAPPROVED,PENDING_REVIEW,WITH_ISSUES,IN_PROCESS,PREAPPROVED. URL slots: object_story_spec.link_data.link, link_data.child_attachments[i].link (one slot each), video_data.call_to_action.value.link, template_data.link, asset_feed_spec.link_urls[i].website_url; final url = base + creative.url_tags. For ads that only reference an existing page post (object_story_id / effective_object_story_id, i.e. boosted posts), try reading the post's link (GET <post_id> fields call_to_action,attachments{url,unshimmed_url,target}; pass page_id so a page token can be used); if unreadable record url null, editable "no", note why. Lead-form ads: note the lead form. Creatives are immutable: edit_method "new creative + ad update".`,
  tiktok: `TikTok (tiktok_native_action). Pull regular ads via the ad/get endpoint (all statuses except deleted; set filtering primary_status to STATUS_ALL or equivalent) with fields such as ad_id, ad_name, adgroup_id, adgroup_name, campaign_id, campaign_name, operation_status, secondary_status, landing_page_url, landing_page_urls, utm_params, creative_type. ALSO pull Smart+ / Upgraded Smart+ (SPC) campaigns and ads via their own endpoints (search LIST_ACTIONS for "smart_plus" / "spc"), capturing every landing page URL per ad (landing_page_url_list etc.). If utm_params is set, TikTok appends it to the landing page: render it into url_tags and merge into url. Get campaign/adgroup names via campaign/get and adgroup/get if the ad response lacks them.`,
  snapchat: `Snapchat (snapchat_native_action). List campaigns, ad squads, ads and creatives for the ad account (aggregate_pages:true). Join ad.creative_id -> creative, ad.ad_squad_id -> squad -> campaign. URL fields on a creative: web_view_properties.url, deep_link_properties.deep_link_uri / web_view_fallback_url, collection / interaction-zone / composite (story) sub-creatives (follow them), lead_generation_properties (no URL). One slot per URL. edit_method "PUT creatives (triggers re-review)".`,
  x: `X Ads (x_ads_native_action). For the account pull campaigns, line_items, promoted_tweets (not deleted), then the tweets behind them (Ads API tweets endpoint for the account, with tweet ids; include tweet "name" which is the ad name in Ads Manager, the card_uri and expanded URLs in the text), then the cards (cards endpoint filtered by card_uris / card ids) and read each website/destination URL (components[].destination.url or website_url; one slot per carousel component). Ad name = tweet name (null if empty). Card destination: edit_method "card update" if the card API allows; tweet text links: editable "no".`,
  linkedin: `LinkedIn (linkedin_native_action). Pull campaign groups (= campaign), campaigns (= ad set), creatives (= ad; ad name = creative name) for the ad account. For each creative read content.reference (share / ugcPost / post URN) and try the Posts API to read the landing page (article source / CTA landing page); text ads carry destination URLs directly. Earlier runs got HTTP 403 on posts (Community Management API not approved): if so, still record every creative with url null, editable "unknown", and the exact error in notes.`,
  google: `Google Ads (google_ads_native_action, GoogleAdsService search / searchStream with GAQL). Pull: customer.tracking_url_template, customer.final_url_suffix; campaign id,name,status,advertising_channel_type,tracking_url_template,final_url_suffix; ad_group id,name,status,tracking_url_template,final_url_suffix; ad_group_ad ad.id, ad.name, ad.type, ad.final_urls, ad.final_mobile_urls, ad.final_url_suffix, ad.tracking_url_template, ad_group_ad.status, ad_group_ad.policy_summary.approval_status (status != REMOVED). ALSO pull assets that carry final URLs (sitelinks etc. via campaign_asset / ad_group_asset / customer_asset with asset.final_urls, asset.final_url_suffix) and Performance Max asset_group.final_urls if any — each as its own row (ad_id = asset id / asset group id, ad_name = sitelink text / asset group name, slot says which). Effective suffix = the lowest level that sets final_url_suffix (ad > ad group > campaign > account); url = final_url + effective suffix.`,
}

const DISCOVER_HINTS = {
  meta: `Call whathead_workspace list_accounts with {"platform":"meta","include_inactive":true}. Known so far: 2194833637927644 Diriyah Co; 1033388761412991 Diriyah Gate - Billed to MS KSA; 1198625455580757 Diriyah Company - Visit Diriyah Billed to MS KSA.`,
  tiktok: `Call whathead_workspace list_accounts with {"platform":"tiktok","include_inactive":true}. Known so far: 7338074303931449345 H&S - DGCL - Diriyah Gate; 7280828159585468418 Diriyah Gate - Billed to MS KSA; 7338057963233443842 H&S - DGCL - Visit Diriyah.`,
  snapchat: `The workspace list_accounts result for snapchat is TRUNCATED (~393 accounts, only ~200 come back). Get the complete list another way: snapchat_native_action — list the organizations the user belongs to (search LIST_ACTIONS for "organization", e.g. GET /v1/me/organizations) and then snapchat_account_list per organization_id (aggregate_pages true), and check names. Known so far: ebe8d66e-0e3e-4b71-9d37-5c53118d6481 Diriyah Company (org 697c66f1-f8db-4e58-84ff-cddb36877c27); 377f9c96-632a-45b8-b1bc-7ceb96f186a6 Diriyah Company (org da946722-0631-474c-aa4e-2e1c010f2ba3); 189a5ada-5348-4beb-868a-27c79e504666 Diriyah Company Self Service.`,
  x: `Call whathead_workspace list_accounts with {"platform":"x","include_inactive":true}. Known so far: 18ce55o46ul H&S-DiriyahCo; 18ce55o46uh H&S-VisitDiriyah.`,
  linkedin: `Call whathead_workspace list_accounts with {"platform":"linkedin","include_inactive":true}. Known so far: 513006454 Diriyah Company Paid Campaigns; 512278713 Diriyah Gate - Billed to MS KSA; 549801147 Wadi Safar -WPP BM Ad Account.`,
  google: `The workspace list_accounts result for google is TRUNCATED (~858 accounts). Find the complete set another way with google_ads_native_action: e.g. CustomerService ListAccessibleCustomers, and GAQL on manager accounts: SELECT customer_client.id, customer_client.descriptive_name, customer_client.status, customer_client.manager FROM customer_client WHERE customer_client.descriptive_name LIKE '%iriyah%' (repeat for '%Wadi%' / '%wadi%' / '%DIRIYAH%'; LIKE is case-sensitive so cover case variants) on each relevant MCC. Known so far: 9282725829 (928-272-5829, Diriyah Gate) under MS KSA MCC 3766972920. Return only non-manager (client) accounts, but mention matching manager accounts in caveats.`,
}

const ACCOUNTS_SCHEMA = {
  type: 'object',
  properties: {
    platform: { type: 'string' },
    accounts: { type: 'array', items: { type: 'object', properties: {
      account_id: { type: 'string' }, account_name: { type: 'string' }, status: { type: 'string' }, notes: { type: 'string' } },
      required: ['account_id', 'account_name'] } },
    complete: { type: 'boolean' },
    method: { type: 'string' },
    caveats: { type: 'string' },
  },
  required: ['platform', 'accounts', 'complete', 'method'],
}

const INV_SCHEMA = {
  type: 'object',
  properties: {
    platform: { type: 'string' }, account_id: { type: 'string' }, account_name: { type: 'string' },
    file: { type: 'string' },
    ads_total: { type: 'integer' }, ads_with_url: { type: 'integer' }, ads_without_url: { type: 'integer' }, url_rows: { type: 'integer' },
    complete: { type: 'boolean' },
    errors: { type: 'array', items: { type: 'string' } },
    notes: { type: 'string' },
  },
  required: ['platform', 'account_id', 'file', 'ads_total', 'url_rows', 'complete'],
}

const PLATFORMS = ['meta', 'tiktok', 'snapchat', 'x', 'linkedin', 'google']

const results = await pipeline(
  PLATFORMS,
  p => agent(`${COMMON}
TASK: find EVERY ${p} ad account accessible through Whathead whose account NAME contains "diriyah" or "wadi" (case-insensitive substring), including inactive / paused / disabled accounts.
${DISCOVER_HINTS[p]}
Return every matching account (dedupe by id). Set complete=false and explain in caveats if you could not see the full account list.`,
    { label: `discover:${p}`, phase: 'Discover', schema: ACCOUNTS_SCHEMA }),
  (disc, p) => {
    if (!disc || !disc.accounts.length) { log(`${p}: no accounts discovered`); return [] }
    log(`${p}: ${disc.accounts.length} account(s): ${disc.accounts.map(a => a.account_name).join(' | ')}`)
    return parallel(disc.accounts.map(acc => () => agent(`${COMMON}
TASK: pull EVERY ad and EVERY final-URL slot from ${p} ad account ${acc.account_id} ("${acc.account_name}").
${PLATFORM_HINTS[p]}
${RECORD}
Output file: ${OUT}/${p}_${acc.account_id.replace(/[^A-Za-z0-9_-]/g, '')}.jsonl
When done, re-open the file with python3 and count lines / distinct ad_id to fill ads_total, ads_with_url, ads_without_url, url_rows. Set complete=false if any page or entity could not be read, and list each failure in errors.`,
      { label: `inventory:${p}:${acc.account_name}`.slice(0, 80), phase: 'Inventory', schema: INV_SCHEMA })
      .then(r => ({ discovery: acc, result: r }))))
      .then(rs => ({ platform: p, discovery: disc, accounts: rs }))
  },
)
return results
