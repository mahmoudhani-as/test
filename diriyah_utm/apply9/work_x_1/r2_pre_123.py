import json
IN='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply9/in_x_1.json'
W='/tmp/claude-0/-home-user-test/5e42174a-3db2-542f-afff-62945df1761d/scratchpad/diriyah_utm/apply9/work_x_1'
U=json.load(open(IN))
# live reads (copied from GET_CARD responses of this agent)
reads={
 1:{'tweet':'2095131822749524008','card':'2095131819687464963','get_req':'ec14fb83-e9b9-4344-9d4c-3830d42656fb','card_type':'IMAGE_CAROUSEL_WEBSITE','title':'Manazel AlHadawi',
    'url':'https://www.diriyahcompany.sa/en/diriyah-living/alhadawi?utm_source=x&utm_medium=paid-social&utm_campaign=ManazelAlHadawi_Jun2026&utm_term=adset-id-E1A001_manazel-alhadawi_en_all_mf_prospecting&utm_content=ad-id-AD1001_manazel-alhadawi-CR2'},
 2:{'tweet':'2095139956872167629','card':'2095139954829447168','get_req':'410581a1-1b40-4ff0-ad04-03f0380363df','card_type':'IMAGE_CAROUSEL_WEBSITE','title':'منازل الحداوي',
    'url':'https://www.diriyahcompany.sa/ar/diriyah-living/alhadawi?utm_source=x&utm_medium=paid-social&utm_campaign=ManazelAlHadawi_Jun2026&utm_term=adset-id-A1A002_manazel-alhadawi_ar_all_mf_prospecting&utm_content=ad-id-AD1003_manazel-alhadawi-CR3'},
 3:{'tweet':'2095139958206177684','card':'2095139954837917698','get_req':'1c1be482-5105-4d1c-b674-b733925205ba','card_type':'IMAGE_CAROUSEL_WEBSITE','title':'Manazel AlHadawi',
    'url':'https://www.diriyahcompany.sa/en/diriyah-living/alhadawi?utm_source=x&utm_medium=paid-social&utm_campaign=ManazelAlHadawi_Jun2026&utm_term=adset-id-E1A001_manazel-alhadawi_en_all_mf_prospecting&utm_content=ad-id-AD1001_manazel-alhadawi-CR3'},
}
for i,r in reads.items():
    u=U[i]; ch=u['changes'][0]
    assert u['unit']==r['tweet']
    print(i, u['unit'], u['ad_ids'], '-> card', r['card'], '| slot', ch['slot'])
    print('   cur==now', r['url']==ch['now'], '| cur in alt_now', r['url'] in ch['alt_now'], '| cur==new', r['url']==ch['new'])
    r['cur_eq_now']=r['url']==ch['now']; r['cur_eq_new']=r['url']==ch['new']
json.dump(reads, open(W+'/r2_pre_123.json','w'), ensure_ascii=False, indent=1)
