export const meta = {
  name: 'diriyah-first-serving-dates',
  description: 'Read-only: exact first day with impressions for each listed ad (per account), for the utm_campaign month token',
  phases: [{ title: 'Serving dates', detail: 'one agent per ad account' }],
}
const GW = { meta: 'meta_native_action', snapchat: 'snapchat_native_action', tiktok: 'tiktok_native_action', google: 'google_ads_native_action', linkedin: 'linkedin_native_action', x: 'x_ads_native_action' }
const HINT = {
  meta: 'Meta: act_<id>/insights level=ad, filtering ad.id IN [batch of <=50 ids] plus impressions GREATER_THAN 0, time_increment=monthly over 2022-01-01..2026-10-11 to find each ad\'s first month, then time_increment=1 inside that month for the exact day. Read the account timezone_name.',
  tiktok: 'TikTok: reporting (report/integrated/get, BASIC, data_level AUCTION_AD, dimensions ad_id + stat_time_day, metric impressions, filter ad_ids). Daily ranges are limited (about 30 days per request): use each ad\'s create_time (ad/get) as the lower bound and walk forward in windows until the first day with impressions > 0. Upgraded Smart+ ad ids (smart_plus_ad_id) may need the Smart+ reporting or the creative child ad ids (see ad/get with smart_plus filters) - the earliest child impression counts. Read the advertiser timezone (advertiser/info).',
  snapchat: 'Snapchat: ad stats (GET /v1/ads/{ad_id}/stats or the ad account stats with breakdown=ad) with granularity=DAY, fields impressions, in windows allowed by the API starting at the ad created_at; find the first day with impressions > 0. Use the ad account timezone for start/end times.',
  x: 'X Ads: use the active_entities endpoint (GET /12/stats/accounts/{account_id}/active_entities, entity=PROMOTED_TWEET, windows up to 90 days) to find the first window where each promoted tweet was active, then synchronous stats (GET /12/stats/accounts/{account_id}, entity=PROMOTED_TWEET, entity_ids, granularity=DAY, metric_groups=ENGAGEMENT, windows of 7 days) to find the first day with impressions > 0. Start from the promoted tweet created_at. Account timezone from the account.',
  google: 'Google Ads: GAQL on ad_group_ad: SELECT ad_group_ad.ad.id, segments.month, metrics.impressions FROM ad_group_ad WHERE ad_group_ad.ad.id IN (...) AND metrics.impressions > 0 (segments.month across all time via segments.date range) to find each ad\'s first month, then segments.date inside that month for the exact day. Account time_zone from customer.',
  linkedin: 'LinkedIn: adAnalytics (q=analytics, pivot=CREATIVE, timeGranularity=DAILY, creatives=List(urn:li:sponsoredCreative:<id>), dateRange from creative createdAt to 2026-10-11, fields impressions,dateRange) and take the first day with impressions > 0.',
}
const SCHEMA = { type: 'object', properties: {
  out_file: { type: 'string' }, ads: { type: 'integer' }, with_date: { type: 'integer' }, never_served: { type: 'integer' }, unknown: { type: 'integer' },
  timezone: { type: 'string' }, errors: { type: 'array', items: { type: 'string' } }, notes: { type: 'string' } },
  required: ['out_file', 'ads', 'with_date', 'never_served', 'unknown'] }
const res = await parallel(args.jobs.map(j => () => agent(`
READ-ONLY task through the Whathead MCP (load with ToolSearch "select:mcp__Whathed_MCP__${GW[j.platform]},mcp__Whathed_MCP__whathead_tool_help"; use LIST_ACTIONS / DESCRIBE_ACTION). Never call any write action and never pass dry_run:false.
For ${j.platform} ad account ${j.account_id} ("${j.account_name}"), find for EVERY ad id listed in ${j.ids_file} (JSON array) the exact first calendar day (in the ad account's own timezone) on which the ad had impressions > 0. The user needs this to be extremely accurate: confirm the day with daily data, not just monthly totals.
${HINT[j.platform]}
MCP results are capped around 65KB: batch ids, project fields, paginate; large outputs are saved to a file path - parse it with python3.
Write a JSON object to ${j.ids_file.replace('serving_in_', 'serving_out_')} mapping each ad id (string) to {"first_date": "YYYY-MM-DD" or null, "first_day_impressions": int or null, "status": "served" | "never_served" | "unknown", "note": "..."}. "never_served" only when you verified zero impressions over the ad's whole life; "unknown" when the API would not answer (put the error in note). Every listed id must be present.`,
  { label: `serving:${j.platform}:${j.account_name}`.slice(0, 80), phase: 'Serving dates', schema: SCHEMA })))
return res
