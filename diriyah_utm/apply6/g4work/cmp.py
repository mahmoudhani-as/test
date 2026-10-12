import json
from urllib.parse import urlsplit, parse_qsl
def norm(u):
    s = urlsplit(u)
    q = sorted(parse_qsl(s.query, keep_blank_values=True))
    return (s.scheme.lower(), s.netloc.lower(), s.path, s.fragment, tuple(q))
def landing(final_url, suffix):
    if not suffix:
        return final_url
    # append suffix to final url (Google appends with ? or &)
    sep = '&' if '?' in final_url else '?'
    if '#' in final_url:
        base, frag = final_url.split('#',1)
        sep = '&' if '?' in base else '?'
        return base + sep + suffix + '#' + frag
    return final_url + sep + suffix
