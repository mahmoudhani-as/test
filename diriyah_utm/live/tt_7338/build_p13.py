import json
out=[]
SEC="AD_STATUS_CAMPAIGN_DISABLE"
def u(order,camp,content):
    d={"S":["utm_source","tiktok"],"M":["utm_medium","paid-social"],"C":["utm_campaign",camp],"T":["utm_content",content]}
    return [d[c] for c in order]
B="https://tickets.bujairi.sa/en/g/17/bujairi?utm_source=tiktok&utm_medium=paid-social&utm_campaign=%s&utm_term=btramadan-ar-all-mf&utm_content=%s"
TL="btramadan-2024-mar-lf-traffic-leads"; L="btramadan-2024-mar-lf-leads"
G="1794501968489490"; GA="1794501989414978"; K="1794501336076290"; KA="1794501346130977"
out.append(dict(ad_id="1810725858145329",ad_name="Video_Saudi National Day_Generic_RICH_NA_NA_NA",campaign_id="1810725858144305",adgroup_id="1810725858145281",ad_format="SINGLE_VIDEO",operation_status="ENABLE",secondary_status=SEC))
rows=[
("1795135332598802","Somewhere",G,GA,"ENABLE",TL,"gcc-somewhere","MCTS"),
("1795135332174898","African Lounge",G,GA,"ENABLE",TL,"gcc-africanloungeghabga","TSMC"),
("1795135178993698","Somewhere",K,KA,"ENABLE",L,"ksa-somewhere","CTSM"),
("1795135128169473","African Lounge",K,KA,"ENABLE",L,"ksa-africanloungeghabga","SMCT"),
("1794677585001506","Maiz",G,GA,"ENABLE",TL,"gcc-maiz","TSMC"),
("1794677584997378","Villa Mamas",G,GA,"ENABLE",TL,"gcc-villamamas","SMCT"),
("1794677494109217","Long Chim",G,GA,"DISABLE",TL,"gcc-longchim","SMCT"),
("1794677202574337","Maiz",K,KA,"ENABLE",L,"ksa-maiz","SMCT"),
("1794677202569249","Villa Mamas",K,KA,"ENABLE",L,"ksa-villamamas","TSMC"),
("1794677202564097","Long Chim",K,KA,"DISABLE",L,"ksa-longchim","TSMC"),
("1794501966050337","Ramadan_Main Video",G,GA,"ENABLE",L,"ksa-mainvideo","SMCT"),
("1794501346718738","Main Video",K,KA,"ENABLE",L,"ksa-mainvideo","SMCT"),
]
for i,n,c,ag,op,camp,cont,o in rows:
    out.append(dict(ad_id=i,ad_name=n,campaign_id=c,adgroup_id=ag,ad_format="SINGLE_VIDEO",operation_status=op,secondary_status=SEC,landing_page_url=B%(camp,cont),utm_params=u(o,camp,cont)))
for i,n,c,ag,op in [("1793883217663025","Ramadan_Promoted Post","1793847156078641","1793883203633154","ENABLE"),
("1793882913691650","Ramadan_Promoted Post_Rest of KSA","1793882913686530","1793882913686546","DISABLE"),
("1791600898885650","2024-02-22 15:09:10","1791600894438434","1791600892401682","DISABLE")]:
    out.append(dict(ad_id=i,ad_name=n,campaign_id=c,adgroup_id=ag,ad_format="SINGLE_VIDEO",operation_status=op,secondary_status=SEC))
with open('man_s45_p13.jsonl','w') as f:
    for r in out: f.write(json.dumps(r,ensure_ascii=False)+"\n")
print(len(out))
