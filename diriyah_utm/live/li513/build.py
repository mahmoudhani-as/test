import json, glob, os, collections
D = os.path.dirname(os.path.abspath(__file__))
OUT = "/tmp/claude-0/-home-user-test/c5fcace8-62b1-55a4-9129-dbfe4d94e847/scratchpad/live/linkedin_513006454.jsonl"
ACC_ID, ACC_NAME = "513006454", "Diriyah Company Paid Campaigns"

groups = {}
for l in open(f"{D}/groups.tsv", encoding="utf-8"):
    l = l.rstrip("\n")
    if not l: continue
    i, n, s = l.split("\t")
    groups[i] = (n, s)
camps = {}
for l in open(f"{D}/campaigns.tsv", encoding="utf-8"):
    l = l.rstrip("\n")
    if not l: continue
    i, n, s, g, t, f, o = l.split("\t")
    camps[i] = dict(name=n, status=s, group=g, type=t, format=f, objective=o)
inmail = {}
for l in open(f"{D}/inmail.tsv", encoding="utf-8"):
    l = l.rstrip("\n")
    if not l: continue
    u, url, cta = l.split("\t")
    inmail[u] = (url, cta)
crs = []
for p in sorted(glob.glob(f"{D}/cr_p*.tsv")):
    for l in open(p, encoding="utf-8"):
        l = l.rstrip("\n")
        if not l: continue
        parts = l.split("\t")
        parts += [""] * (8 - len(parts)); assert len(parts) == 8, (p, l)
        crs.append(parts)

print("groups", len(groups), "campaigns", len(camps), "creatives_raw", len(crs))
ids = [c[0] for c in crs]
dups = [k for k, v in collections.Counter(ids).items() if v > 1]
print("dup creative ids:", dups)
missing_c = {c[2] for c in crs if c[2] not in camps}
print("creatives with unknown campaign:", missing_c)
missing_g = {camps[c]["group"] for c in camps if camps[c]["group"] not in groups}
print("campaigns with unknown group:", missing_g)

POST_ERR = ("Posts API read failed: HTTP 403 ACCESS_DENIED 'Not enough permissions to access: partnerApiPostsExternal.GET.20260701' "
            "(GET /rest/posts/{urn}; batch GET /rest/posts?ids=List(...) also 403 'partnerApiPostsExternal.BATCH_GET.20260701'; "
            "legacy GET /v2/ugcPosts 403 'ugcPosts.BATCH_GET.NO_VERSION') - Community Management API not approved for this app, "
            "so the landing page stored on the referenced post cannot be read.")
UTM_NOTE = ("Dynamic UTM (adTrackingParameters) not configured on sampled campaigns 895051873/729004573/877961553 (HTTP 404 'Tracking Parameters resource does not exist'); not checked per campaign.")

removed = []
rows = []
for cid, name, camp, st, serving, ctype, ref, review in crs:
    if st in ("REMOVED", "PENDING_DELETION"):
        removed.append(cid); continue
    c = camps[camp]; g = groups[c["group"]]
    eff = ("SERVING" if serving == "true" else "NOT_SERVING") + (f"; review={review}" if review else "; review=none")
    ad_name = name if name else None
    base = dict(platform="linkedin", account_id=ACC_ID, account_name=ACC_NAME,
                campaign_id=c["group"], campaign_name=g[0], campaign_status=g[1],
                adset_id=camp, adset_name=c["name"], adset_status=c["status"],
                ad_id=cid, ad_name=ad_name, ad_status=st, effective_status=eff,
                creative_id=f"urn:li:sponsoredCreative:{cid}", creative_name=ad_name)
    fmt = f"campaign type={c['type']} format={c['format']} objective={c['objective']}"
    noname = "" if name else " Creative has no name set in API (name null)."
    if ref.startswith("urn:li:adInMailContent:"):
        url, cta = inmail[ref]
        r = dict(base, slot=f"inMailContent({ref}).subContent.regular.callToActionLandingPageUrl",
                 base_url=url, url_tags=None, url=url, tracking_template=None,
                 editable="yes",
                 edit_method=f"POST /rest/inMailContents/{ref} (X-RestLi-Method PARTIAL_UPDATE, $set subContent.regular.callToActionLandingPageUrl) or create new inMailContent + new creative; edits re-enter review",
                 notes=f"Sponsored Message (Message Ad) creative; content.reference={ref}; CTA text '{cta}'; htmlBody has no <a href> links. {fmt}.{noname}")
    else:
        kind = "content.documentAd.reference" if ctype == "documentAd" else "content.reference"
        r = dict(base, slot=f"creative.{kind} -> post {ref} (post content.article.source / CTA landing page)",
                 base_url=None, url_tags=None, url=None, tracking_template=None,
                 editable="unknown",
                 edit_method="Landing URL lives on the referenced post (share/ugcPost), which is immutable once sponsored; change by creating a new post/dark post with new URL and a new creative (POST /rest/creatives), then pause old creative",
                 notes=f"{'Document ad' if ctype=='documentAd' else 'Sponsored Content'} referencing {ref}. {POST_ERR} {UTM_NOTE} {fmt}.{noname}")
    rows.append(r)

with open(OUT, "w", encoding="utf-8") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
print("removed excluded:", len(removed))
print("rows written:", len(rows))
