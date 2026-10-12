def arm(lang, uid, fmt, geo, kv='armanikv1'):
    return (f"https://www.diriyahcompany.sa/{lang}/diriyah-living/armani?utm_source=twitter&utm_medium=paid-social"
            f"&utm_campaign=hs-brandedresidencearmani-2025-apr-lf-conversions&utm_id={uid}"
            f"&utm_term=brandedresidencearmani-{lang}-all-na&utm_content={kv}-{fmt}-{geo}#appointment-form")
def faena(lang, uid, content, camp="hs-brandedresidence-faena-2025-oct-uf-reach-awareness", term_prefix="brandedresidence-faena"):
    return (f"https://www.wadisafar.com/{lang}/residences/faena?utm_source=twitter&utm_medium=paid-social"
            f"&utm_campaign={camp}&utm_id={uid}&utm_term={term_prefix}-{lang}-all-na&utm_content={content}")
def living(lang, mon, uid, content):
    return (f"https://www.diriyahcompany.sa/{lang}/diriyah-living?utm_source=twitter&utm_medium=paid-social"
            f"&utm_campaign=hs-diriyahliving-2025-{mon}-uf-reach-awareness&utm_id={uid}&utm_term=diriyahliving-{lang}-all-na&utm_content={content}")
def hadawi(lang, uid, content, camp="hs-cityscape-2025-dec-lf-conversions", term="cityscape", frag="#register-interest-form"):
    return (f"https://www.diriyahcompany.sa/{lang}/diriyah-living/alhadawi?utm_source=twitter&utm_medium=paid-social"
            f"&utm_campaign={camp}&utm_id={uid}&utm_term={term}-{lang}-all-na&utm_content={content}{frag}")
def manazel(lang, adset, ad, kv):
    return (f"https://www.diriyahcompany.sa/{lang}/diriyah-living/alhadawi?utm_source=x&utm_medium=paid-social"
            f"&utm_campaign=ManazelAlHadawi_Jun2026&utm_term=adset-id-{adset}_manazel-alhadawi_{lang}_all_mf_prospecting"
            f"&utm_content=ad-id-{ad}_manazel-alhadawi-{kv}_display")
def manz(lang, adset, ad, suffix):
    return (f"https://www.diriyahcompany.sa/{lang}/diriyah-living/alhadawi?utm_source=x&utm_medium=paid-social"
            f"&utm_campaign=ManazelAlHadawi_Jun2026&utm_term=adset-id-{adset}_manazel-alhadawi_{lang}_all_mf_prospecting"
            f"&utm_content=ad-id-{ad}_manazel-alhadawi-{suffix}")
def lid(lang, content):
    return (f"https://www.diriyahcompany.sa/{lang}/life-in-diriyah?utm_source=x&utm_medium=paid-social"
            f"&utm_campaign=2c0ef446_diriyah-living_sep26&utm_term=3e71b680_residential_{lang}&utm_content={content}")
def rcsr(lang, content):
    return (f"https://www.diriyahcompany.sa/{lang}/diriyah-living/ritz-carlton-signature?utm_source=x&utm_medium=paid-social"
            f"&utm_campaign=bb1cac08_ritz-carlton-signature_sep26&utm_term=87bde3ee_rcsr_{lang}&utm_content={content}")
