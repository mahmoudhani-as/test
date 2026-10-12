from urllib.parse import urlsplit
def parts(u):
    s = urlsplit(u)
    q = sorted(s.query.split('&')) if s.query else []
    return (s.scheme, s.netloc, s.path, s.fragment, q)
def equiv(a, b):
    if a is None or b is None: return False
    return parts(a) == parts(b)
