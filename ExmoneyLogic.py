# coding: utf-8
import time, ExmoneyAPI as E, socket

#sock = socket.socket()
#sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, server.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR) | 1)

f = open('config.txt', 'r')
conf = f.read().split('\n')
f.close()
E.api_key = conf[0].split(': ')[1]
E.api_secret = conf[1].split(': ')[1]
pair = conf[2].split(': ')[1]
limit = int(conf[3].split(': ')[1])

def change_limit(limit, profit):
  new_limit = limit + profit/2.0
  f = open('config.txt', 'w')
  f.write('api_key: ' + api_key + '\n')
  f.write('api_secret: ' + api_secret + '\n')
  f.write('pair: ' + pair + '\n')
  f.write('limit: ' + new_limit)
  f.close()
  return new_limit

#------------------------------------------------------------------------#

balance = None # баланс перед покупкой (начальный)
new_balance = None # баланс после продажи
profit = None

balance = E.getBalance(pair[4:])
print u'Начальный баланс: ', balance

price = 23493
#price = E.getPrice(pair, 'sell')
#order_id = E.BuySell(pair, 'buy', 0.0015, price)
#while E.checkOrder(order_id, pair):
#  time.sleep(0.1)
#print u'Куплено по цене ', price, ' ', pair[4:], u'. Баланс: ', E.getBalance(pair[4:])

while balance > limit:
  new_price = E.getPrice(pair, 'buy')
  if new_price >= price+150:
    order_id = E.BuySell(pair, 'sell', 0.0015, new_price)
    price = new_price
    x = 0
    while E.checkOrder(order_id, pair):
      time.sleep(0.1)
      #if x == 20: 
      x += 1
    new_balance = E.getBalance(pair[4:])
    profit = new_balance-balance
    balance = new_balance
    limit = change_limit(limit, profit)
    print u'Продано по цене ', price, ' ', pair[4:], u'. Баланс: ', new_balance
    print u'    Прибыль: ', profit, ' ', pair[4:], u'. Новый лимит: ', limit
    while 1:
      new_price = E.getPrice(pair, 'sell')
      if new_price <= price-150:
        order_id = E.BuySell(pair, 'buy', 0.0015, new_price)
        while E.checkOrder(order_id, pair):
          time.sleep(0.1)
        new_balance = E.getBalance(pair[4:])
        print u'Куплено по цене ', price, ' ', pair[4:], u'. Баланс: ', E.getBalance(pair[4:])
        break
