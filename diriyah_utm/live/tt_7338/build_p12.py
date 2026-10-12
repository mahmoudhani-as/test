import json
COE="https://www.diriyahcompany.sa/ar?utm_source=tiktok&utm_medium=paid-social&utm_campaign=cityofearth-2024-oct-uf-reach-awareness&utm_term=cityofearth-ar-all-mf&utm_content=%s"
def utm(order, src="tiktok", med="paid-social", camp="cityofearth-2024-oct-uf-reach-awareness", content="video"):
    d={"S":["utm_source",src],"M":["utm_medium",med],"C":["utm_campaign",camp],"T":["utm_content",content]}
    return [d[c] for c in order]
A="SMCT"; B="TSMC"; C="MCTS"; D="CTSM"
CA="1813630708433922"; AG="1813630708433938"
pre="Diriyah_Tactical_City of Earth_UF_KSA_Pospecting_AR_Awareness_TikTok_"
coe_rows=[
("1814416245246033","M_DSquare 6s",A,"ENABLE"),
("1814416244966545","M_MudHouse 6s",B,"ENABLE"),
("1814416244961361","M_Hospitality 6s",B,"ENABLE"),
("1814416244956241","M_F&B 6s",B,"ENABLE"),
("1814416244950161","M_Bazar 6s",A,"ENABLE"),
("1814416244943889","M_Green 6s",C,"ENABLE"),
("1814416243821586","M_Football 6s",B,"DISABLE"),
("1814416243790930","M_Hologram 6s",A,"ENABLE"),
("1814414945453073","F_Hospitality 6s",B,"ENABLE"),
("1814414945447953","F_Painter 6s",A,"ENABLE"),
("1814414945441873","F_Culture 6s",A,"ENABLE"),
("1814414945436689","F_Football 6s",B,"DISABLE"),
("1814414945430545","F_MudHouse 6s",A,"ENABLE"),
("1814414945424402","F_F&B 6s",B,"ENABLE"),
("1814414945418258","F_Awards 6s",A,"ENABLE"),
("1814414945412114","F_Home 6s",A,"ENABLE"),
("1814414945405970","F_Bazar 6s",D,"ENABLE"),
("1814414945399954","F_DSquare 6s",B,"ENABLE"),
("1814414944856081","F_Hologram 6s",A,"ENABLE"),
("1814414944850961","F_Green 6s",D,"ENABLE"),
("1814414944844817","F_Social 6s",A,"ENABLE"),
("1814414944838673","M_Home 6s",D,"ENABLE"),
("1814414944832529","M_Painter 6s",C,"ENABLE"),
("1814414942221330","M_Culture 6s",A,"ENABLE"),
("1814414942216210","M_Social 6s",A,"ENABLE"),
("1814414942210066","M_Awards 6s",A,"ENABLE"),
]
out=[]
SEC="AD_STATUS_CAMPAIGN_DISABLE"
for i,n,o,op in coe_rows:
    out.append(dict(ad_id=i,ad_name=pre+n,campaign_id=CA,adgroup_id=AG,ad_format="SINGLE_VIDEO",operation_status=op,secondary_status=SEC,landing_page_url=COE%"video",utm_params=utm(o)))
BT="bujairiterracewinter-2024-oct-lf-conversions"; BTU="bujairiterracewinter-2024-oct-uf/mf-reach-awareness"
def bt(lang,camp,content,site):
    if site=="t": base="https://tickets.bujairi.sa/%s/d/3552/diriyah-access"%lang
    else: base="https://www.diriyah.sa/%s/dine"%lang
    return base+"?utm_source=tiktok&utm_medium=paid-social&utm_campaign=%s&utm_term=bujairiterracewinter-%s-all-mf&utm_content=%s"%(camp,lang,content)
P="Diriyah_Tactical_Bujairi Terrace Winter Campaign_"
rows2=[
("1814339394401298",P+"LW_KSA_Retargeting_EN/AR_Conversion_TIKTOK_Hero Video 30s","1813235175002114","1814339391140914","DISABLE",bt("ar",BT,"phase1-sponsoredpost-ret-ksa","t"),A,BT,"phase1-sponsoredpost-ret-ksa"),
("1814338668422257",P+"LW_KSA_Retargeting_EN_Conversion_TIKTOK_Hero Video 30s","1813235175002114","1814338666550322","DISABLE",bt("en",BT,"heroad-video-ret-ksa","t"),A,BT,"heroad-video-ret-ksa"),
("1814258353756210",P+"UF_KSA_Prospecting_AR_Awareness_TIKTOK_Retail Video 21s","1814258347883569","1814258353754146","ENABLE",bt("ar",BTU,"retailvideo-video-aud-ksa","d"),A,BTU,"retailvideo-video-aud-ksa"),
("1814258351977521",P+"UF_KSA_Prospecting_EN_Awareness_TIKTOK_Retail Video 21s","1814258347883569","1814258347884545","ENABLE",bt("en",BTU,"retailvideo-video-aud-ksa","d"),D,BTU,"retailvideo-video-aud-ksa"),
("1814257738467330",P+"LF_KSA_Prospecting_EN_Conversion_TIKTOK_Retail Video 21s","1814257734712321","1814257738350625","ENABLE",bt("en",BT,"retailvideo-video-aud-ksa","d"),A,BT,"retailvideo-video-aud-ksa"),
("1814257734722577",P+"LF_KSA_Prospecting_AR_Conversion_TIKTOK_Retail Video 21s","1814257734712321","1814257734712353","ENABLE",bt("ar",BT,"retailvideo-video-aud-ksa","d"),A,BT,"retailvideo-video-aud-ksa"),
("1813630708447250",pre+"Female 30s",CA,AG,"DISABLE",COE%"herovideo",B,"cityofearth-2024-oct-uf-reach-awareness","herovideo"),
("1813630708440082",pre+"Male 30s",CA,AG,"ENABLE",COE%"herovideo",A,"cityofearth-2024-oct-uf-reach-awareness","herovideo"),
("1813548516725794",P+"LF_KSA_Prospecting_EN_Conversion_TIKTOK_Hero Video 30s","1813235175002114","1813548516710402","DISABLE",bt("en",BT,"heroad-video-aud-ksa","t"),D,BT,"heroad-video-aud-ksa"),
("1813548319092754",P+"UF_KSA_Prospecting_EN_Awareness_TIKTOK_Hero Video 30s","1813234387592193","1813548318688305","DISABLE",bt("en",BTU,"heroad-video-aud-ksa","t"),A,BTU,"heroad-video-aud-ksa"),
("1813235176424482",P+"LF_KSA_Prospecting_EN/AR_Conversion_TIKTOK_Hero Video 30s","1813235175002114","1813235175002146","DISABLE",bt("ar",BT,"phase1-sponsoredpost-aud-ksa","t"),A,BT,"phase1-sponsoredpost-aud-ksa"),
("1813234387612674",P+"UF_KSA_Prospecting_EN/AR_Awareness_TIKTOK_Hero Video 30s","1813234387592193","1813234387610642","DISABLE",bt("ar",BTU,"phase1-sponsoredpost-aud-ksa","t"),D,BTU,"phase1-sponsoredpost-aud-ksa"),
("1813171053402129",pre+"Male 30s","1813171053383729","1813171053384769","ENABLE",COE%"herovideo",A,"cityofearth-2024-oct-uf-reach-awareness","herovideo"),
("1813171053395985",pre+"Female 30s","1813171053383729","1813171053384769","DISABLE",COE%"herovideo",A,"cityofearth-2024-oct-uf-reach-awareness","herovideo"),
]
for i,n,c,ag,op,lp,o,camp,cont in rows2:
    out.append(dict(ad_id=i,ad_name=n,campaign_id=c,adgroup_id=ag,ad_format="SINGLE_VIDEO",operation_status=op,secondary_status=SEC,landing_page_url=lp,utm_params=utm(o,camp=camp,content=cont)))
for i,n,c,ag in [
("1811804111588369","Diriyah_Tactical_Fortnite_UF_KSA_Prospecting_AR_Awareness_TikTok_Cutdown","1811274912769058","1811274912769074"),
("1811636493854817","Diriyah_Tactical_Fortnite_UF_KSA_Prospecting_EN_Awareness_TikTok_Cutdown","1811274912769058","1811274912769074"),
("1811341015071777","Diriyah_Tactical_Fortnite_UF_KSA_Prospecting_EN/AR_Awareness_TikTok_Video","1811274912769058","1811274912769074"),
("1811274912770082","Diriyah_Tactical_Fortnite_UF_KSA_Prospecting_EN/AR_Awareness_TikTok_Video","1811274912769058","1811274912769074"),
("1810730941902897","Video_Saudi National Day_Generic_RICH_NA_NA_30s","1810725858144305","1810725858145281")]:
    out.append(dict(ad_id=i,ad_name=n,campaign_id=c,adgroup_id=ag,ad_format="SINGLE_VIDEO",operation_status="ENABLE",secondary_status=SEC))
with open('man_s45_p12.jsonl','w') as f:
    for r in out: f.write(json.dumps(r,ensure_ascii=False)+"\n")
print(len(out), len({r['ad_id'] for r in out}))
