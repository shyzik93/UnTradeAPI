# coding: utf-8
import repper, conftools
import win32api, time, re, os
import exchange

path_conf = os.path.join(os.path.dirname(os.path.abspath('')), 'conf_exchange.txt')

conf = conftools.loadconf(path_conf)

ec = exchange.API(conf) #conf[0].split(': ')[1], api_secret = conf[1].split(': ')[1])

# Отслеживание
# - скачков/спадов цен
# - разниц цен на разных биржах

def process_count(number):
  if number[-1] == '%': pass
  elif number[0] == '.': number = '0' + number
  return float(number)

def send_query(_type, count, pair):
  if None in count and count.index(None) == 1: # покупка/продажа по рынку 2 LTC RUR
    #print ec.exmo__order_create(pair=pair, quantity=count[0], price=0, type='market_'+_type)
    print ec.exmo__user_info()
    print ec.btce_getInfo()

def parse_strquery(query):
  query = query.split()
  _type = query.pop(0)
  count = [None, None]
  pair = '_'+query.pop(-1)

  if re.findall(r'[0-9%]+', query[-1]): count[1] = query.pop(-1)
  pair = query.pop(-1) + pair
  if query: count[0] = query.pop(0)

  return _type, count, pair.upper()

def prepare_query(queries):
  queries = re.sub(r'--.*', '', queries)
  queries = queries.strip().lower().split(';')
  queries = [q for q in queries if q]
  return queries

def do_query(queries):
  queries = prepare_query(queries.strip())
  print queries
  for query in queries:
    _type, count, pair = parse_strquery(query.strip())
    send_query(_type, count, pair)

'''query = ''''''
BUY  2 LTC RUB; -- по рынку
SELL 2 LTC RUB; -- по рынку
BUY  LTC 440 RUB; -- по рынку
SELL LTC 440 RUB; -- по рынку
BUY  2 LTC 240 RUB; -- по лимиту
SELL 2 LTC 240 RUB; -- по лимиту
'''
query = '''
SELL 0.25 LTC RUB; -- по рынку
'''

do_query(query)

stop

def signal_bigger():
  print difference
  for i in range(3):
    win32api.Beep(512, 125)
    time.sleep(0.125)

def signal_smaller():
  print difference
  for i in range(3):
    win32api.Beep(2048, 125)
    time.sleep(0.25)

first_price= float(ec.exmo_ticker()['LTC_RUB']['buy_price'])

while 1:
  price = float(ec.exmo_ticker()['LTC_RUB']['buy_price'])
  difference = (first_price - price) * -1
  if difference > 50: signal_bigger(difference)
  elif difference < -50: signal_smaller(difference)
  if difference not in [0.0, 0]: print 'difference:', difference
  
  #print
  time.sleep(10)
