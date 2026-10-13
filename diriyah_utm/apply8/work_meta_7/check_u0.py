import json, sys
sys.path.insert(0, '.')
from lib7 import *
sent_body = json.loads('"\\u0645\\u0646\\u0627\\u0632\\u0644 \\u0627\\u0644\\u062f\\u0631\\u0639\\u064a\\u0629.. \\u0645\\u0646\\u0632\\u0644\\u064c \\u064a\\u062c\\u0645\\u0639 \\u0628\\u064a\\u0646 \\u0627\\u0644\\u0645\\u062c\\u062a\\u0645\\u0639\\u060c \\u0648\\u0627\\u0644\\u062b\\u0642\\u0627\\u0641\\u0629\\u060c \\u0648\\u0627\\u0644\\u0637\\u0628\\u064a\\u0639\\u0629\\u060c \\u0648\\u062a\\u0641\\u0627\\u0635\\u064a\\u0644 \\u0627\\u0644\\u062d\\u064a\\u0627\\u0629 \\u0627\\u0644\\u064a\\u0648\\u0645\\u064a\\u0629."')
sent_desc = json.loads('"\\u062a\\u0639\\u0631\\u0651\\u0641 \\u0623\\u0643\\u062b\\u0631"')
sent_title = json.loads('"\\u0645\\u0646\\u0632\\u0644 \\u0641\\u064a \\u0645\\u062f\\u064a\\u0646\\u0629 \\u0635\\u0645\\u0645\\u062a \\u0644\\u0644\\u062d\\u064a\\u0627\\u0629"')
p = json.load(open('payload_120253320122250058.json'))
afs = p['asset_feed_spec']
print('body ', sent_body == afs['bodies'][0]['text'])
print('desc ', sent_desc == afs['descriptions'][0]['text'])
print('title', sent_title == afs['titles'][0]['text'])
