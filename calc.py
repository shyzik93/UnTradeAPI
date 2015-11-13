# coding: utf-8
import repper, conftools
import time, re, os
import exchange

path_conf = os.path.join(os.path.dirname(os.path.abspath('')), 'conf_exchange.txt')
conf = conftools.loadconf(path_conf)
ec = exchange.API(conf)

class calc:
  def __init__(self):
    self.first_price = float(ec.exmo_ticker()['LTC_RUB']['buy_price'])

  def spread(self, ec_name, pair):
    return ec.Price(ec_name, pair, 'buy') - ec.Price(ec_name, pair, 'sell')

  def ex_diff(self, ec_name, _type='buy-sell'):
    _type = _type.split('-')
    ec_name = ec_name.split('-')
    data0 = ec.PairsTradeInfo(ec_name[0])
    data1 = ec.PairsTradeInfo(ec_name[1])
    common_pairs = list(set(data0.keys()) & set(data1.keys()))
    for pair in common_pairs:
      yield pair, data1[pair][_type[1]] - data0[pair][_type[0]]

#print ec.btce_ticker(pairs='btc_rur')
'''print ec.Price('btce', 'btc_rub', 'sell')
print ec.Price('btce', 'btc_rub', 'buy')
print ec.Price('exmo', 'btc_rub', 'sell')
print ec.Price('exmo', 'btc_rub', 'buy'), '\n' '''
c = calc()
#print c.spread('btce', 'btc_rub')
#print c.spread('exmo', 'btc_rub')

#print c.ex_diff('btce-exmo', 'ltc_rub', 'buy-sell')

def show_diff(buy_via, sell_via, convert_to='rub'):
  data = ec.PairsTradeInfo(sell_via)
  print buy_via +' -> '+ sell_via
  for pair, diff in c.ex_diff(buy_via +'-'+ sell_via):
    if diff <= 0: continue
    _pair = pair.split('_')[1]+'_'+convert_to
    if _pair in data: converted = str(data[_pair]['sell'] * diff) +' '+ convert_to
    else: converted = ''
    if pair.split('_')[1] != convert_to: print pair, diff, ' '*(12-len(str(diff))), pair.split('_')[1], '|', converted
    else: print pair, ' '*(12+7), diff, convert_to
  print

while 1:
  show_diff('btce', 'exmo')
  show_diff('exmo', 'btce')
  time.sleep(60)
#print c.ex_diff('btce-exmo', 'btc_eur', 'buy-sell')
#print ec.Price('btce', 'btc_eur', 'buy'), ec.Price('exmo', 'btc_eur', 'sell')

'''#print ec.exmo__order_create(pair=pair, quantity=count[0], price=0, type='market_'+_type)
print ec.exmo__user_info()
print ec.btce_getInfo()

first_price = float(ec.exmo_ticker()['LTC_RUB']['buy_price'])

while 1:
  price = float(ec.exmo_ticker()['LTC_RUB']['buy_price'])
  difference = (first_price - price) * -1
  if difference > 50: signal_bigger(difference)
  elif difference < -50: signal_smaller(difference)
'''
