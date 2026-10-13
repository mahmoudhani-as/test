# usage: python3 -I show.py <payload_file> ... : print payload as one-line JSON, raw Unicode except invisible/special chars escaped
import sys, json
SPECIAL = set(' ​‌‍‎‏﻿  ‪‫‬‭‮⁦⁧⁨⁩؜—–’‘“”')
for f in sys.argv[1:]:
    p = json.load(open(f, encoding='utf-8'))
    s = json.dumps(p, ensure_ascii=False)
    out = ''.join(('\\u%04x' % ord(ch)) if (ch in SPECIAL or (ord(ch) < 32)) else ch for ch in s)
    assert json.loads(out) == p
    print(f.split('/')[-1], ':', out)
    print()
