# -*- coding: utf-8 -*-
# Author: Konstantin Polyakov
# Date: 25.07.2014, 18.08.2015, 06.11.2015, 18.06.2016

import json, hmac, hashlib, os, time, os
from urllib import request, parse

import requests
import serial # pip3 install pyserial

# Класс для удобного вызова АПИ.

class Doer:
    def __init__(self, classObj):  self.c = classObj
    def __getattr__(self, api_name, *args):
        api_type = 'auth' if api_name.startswith('_') else 'public'
        if api_type == 'auth': api_name = api_name[1:]
        return lambda **args: self.c.shell(api_name, args, api_type)

# Класс  протоАПИ бирж

class ProAPI:
    def __init__(self, conf={}):
      self.conf = conf
      self.do = Doer(self)
    
    #self.opener = request.build_opener(request.HTTPCookieProcessor(cj))

    def urlopen(self, url, POST={}, GET={}, headers={}):
        if POST: r = requests.post(url, params=GET, data=POST, headers=headers)
        else: r = requests.get(url, params=GET, headers=headers)

        if r.status_code == 200:
            return r.text, True, []
        else:
            error = r.status_code +' '+ r.message
            return r.text, False, [error]

    def sign(self, data): # type of data is dict
        ''' Стандартный вариант. Можно переопределять, если алгоритм отличается '''
        data = bytearray(parse.urlencode(data), 'utf-8')
        sign = hmac.new(bytearray(self.conf['secret'], 'utf-8'), msg=data, digestmod=hashlib.sha512).hexdigest()
        return data, sign

    def get_nonce(self, filename):
        file_nonce = os.path.join(os.path.dirname(os.path.abspath('')), 'nonce_'+filename+'.txt')

        if not os.path.exists(file_nonce): nonce = '1'
        else:
            f = open(file_nonce, 'r')
            nonce = f.read()
            f.close()

        if nonce=='': nonce = '1'

        f = open(file_nonce, 'w')
        f.write(str(int(nonce)+1))
        f.close()

        return nonce

    def upair2pair(self, upair, to_reverse=False):
        pair = upair.split('-')
        if to_reverse: pair.reverse()
        return '_'.join(pair).upper()

# Класс цены

class Price:
    def __init__(self, upair, buy, sell):
        self.upair = upair
        self.buy = float(buy)
        self.sell = float(sell)
        self.calc_base_values()
        #self.glass_buy = None
        #self.glass_sell = None
    def calc_base_values(self): # расчёт основных величин
        self.spread = self.buy - self.sell # спрэд
        self.mean = (self.buy + self.sell) / 2 # среднее арифметическое

class Order:
    def __init__(self, ex, upair, action, count, price):
        self.upair = upair
        self.action = action
        self.count = count
        self.price = price

        self.order_id = None

        # расчитываем количество после вычитания комиссии
        percent, success, errors = ex.calc_tax()
        if success: self.real_count = count - (count * percent / 100)
        else: self.real_count = None

    def setId(self, order_id):
        self.order_id = order_id

class Balance:
    def __init__(self, on_order=None, free=None, total=None):
        self.on_order = on_order
        self.free = free
        self.total = total

        # Преобразуем значения во float

        if self.on_order is not None:
            for name, value in self.on_order.items():
                self.on_order[name] = float(self.on_order[name])

        if self.free is not None:
            for name, value in self.free.items():
                self.free[name] = float(self.free[name])

        if self.total is not None:
            for name, value in self.total.items():
                self.total[name] = float(self.total[name])

        # Вычисляем общую сумму

        if on_order is not None and free is not None and total is None:
            self.total = {}
            for name, value in self.on_order.items():
                if name in self.total: self.total[name] += self.on_order[name]
                else: self.total[name] = self.on_order[name]

            for name, value in self.free.items():
                if name in self.total: self.total[name] += self.free[name]
                else: self.total[name] = self.free[name]


    def get_not_null(self, type_balance):
        balance = self.__getattribute__(type_balance)
        new_balance = {}
        for name, value in balance.items():
            if value == 0: continue
            new_balance[name] = value
        return new_balance

# Классы АПИ бирж

class exchange_exmo(ProAPI):
    exmo_url = "https://api.exmo.com/v1/"

    #def sign(self, data):
    #    return hmac.new(key=bytearray(self.conf['secret'], 'utf-8'), msg=data, digestmod=hashlib.sha512).hexdigest()

    def __init__(self, conf):
        ProAPI.__init__(self, conf)

        #pair_settings, success, errs = self.do.pair_settings()
        #if success:
        #    self.pairs = list(pair_settings.keys())
        #else:
        #    self.pairs = {}
        #    print('###', 'Ошибка получения списка валютных пар: ', errs)


        #print('-'*50)
        #print(self.pairs, success, errs)
        #print('-'*50)

    def shell(self, api_name, api_params, api_type):
        if api_type == 'auth': # Auth API
            api_params["nonce"] = int(round(time.time()*1000))#self.get_nonce('exmo_nonce')#str(time.time()).replace('.', '')#split('.')[0]
            api_params, sign = self.sign(api_params)
            header = {"Key": self.conf['key'], "Sign":sign, "Content-type": "application/x-www-form-urlencoded"}
            data, success, errors = self.urlopen(self.exmo_url + api_name, POST=api_params, headers=header)
        else: # Public API
            data, success, errors = self.urlopen(self.exmo_url + api_name, GET=api_params)

        if success:
            data = json.loads(data)
            return (data, True, errors) #if 'error' not in data else (None, False, errors+[data])
        else: return None, False, errors

    '''def upair2pair(self, upair, to_reverse=False):
        pair = upair.replace('-', '_').upper()
        return pair'''

    '''def reverse_pair(self, pair):
        pair = pair.split('_')
        pair.reverse()
        return '_'.join(pair)'''

    def price(self, upair):
        pair = self.upair2pair(upair)

        data, success, errors = self.do.order_book(pair=pair, limit=0)
        if success:
            if pair in data: data = data[pair]
            else: 
                success = False
                errors.append('Нет информации по валютной паре '+pair)
        else: success = False

        if not success: return data, success, errors

        price = Price(upair, data['ask_top'], data['bid_top'])
        #price.glass_sell = data['bid']
        #price.glass_buy = data['ask']

        return price, success, errors

    '''def order(self, upair, data1, data2=None):
        data2 = {} if data2 is None else data2

        pair = self.upair2pair(upair)
        is_reversed = False
        if pair not in self.pairs:
            pair = self.reverse_pair(pair)
            is_reversed = True

        return pair, '', '';'''

    
    '''def order(self, buy, sell):
        upair = buy['name'] + '-' + sell['name']

        pair = self.upair2pair(upair)
        is_reversed = False
        if pair not in self.pairs:
            pair = self.upair2pair(upair, True)
            is_reversed = True

        return pair, '', '';'''

    def order(self, upair, action, count, price):
        pair = self.upair2pair(upair)
        if price == 'market':
            price = 0
            action = 'market_'+ action
        data, success, errors = self.do._order_create(pair=pair, type=action, price=price, quantity=count)

        order = Order(self, pair, action, count, price)

        if success:
            if data['result']:
                order.setId(data['order_id'])
            else:
                success = False
                errors.append(data['error'])

        return order, success, errors

    def cancel_order(self, order_id):
        data, success, errors = self.do._order_cancel(order_id=order_id)
        if success:
            if not data['result']:
                success = False
                errors.append(data['error'])
        return None, success, errors

    def check_order(self, order_id):
        order_data = {'has_done': True, 'count_done':0}

        data, success, errors = self.do._user_open_orders()
        if success:
            for pair in data:
                for order in data[pair]:
                    if int(order['order_id']) == int(order_id):
                        order_data['has_done'] = False
                        break

        return order_data, success, []

        '''data, success, errors = self.do._order_trades(order_id=order_id)
        if success:
            if 'trades' in data:
                count = 0
                trades = data['trades']
                for trade in trades:
                    count += float(trade['amount'])
                    return count, success, errors
            else:
                success = False
                errors.append('Отсутствует значение "reserved" или "balances"')
        return data, success, errors'''

    def balance(self):
        data, success, errors = self.do._user_info()
        if success:
            if 'reserved' in data and 'balances' in data:
                data = Balance(data['reserved'], data['balances'])
            else:
                success = False
                errors.append('Отсутствует значение "reserved" или "balances"')

        return data, success, errors

    def calc_tax(self):
        ''' возвращает процент комиссси за сделку '''
        return 0.2, True, []

class exchange_btce(ProAPI):
    btce_url = "https://btc-e.nz/tapi"
    btce_url2 = "https://btc-e.nz/api/3/%s/%s"
    max_nonce = 4294967294

    def shell(self, api_name, api_params, api_type):
        #if self.__wait_for_nonce: time.sleep(1)
        if api_type == 'auth': # Auth API
            #nonce_v = str(time.time()).split('.')[0]
            api_params['method'] = api_name
            api_params['nonce'] = self.get_nonce('btce')#int(round(time.time()*1000))
            if int(api_params['nonce']) > self.max_nonce: return None, False, ['Значение nonce достигло максимального значения! Пересоздайте ключи в аккаунте биржи btc-e.']
            post_data, sign = self.sign(api_params)
            headers = {"Content-type" : "application/x-www-form-urlencoded",
                       "Key" : self.conf['key'],
                       "Sign" : sign}
            data, success, errors = self.urlopen(self.btce_url, POST=post_data, headers=headers)
        else: # Public API
            api_params = '' if 'pairs' not in api_params else '-'.join(api_params['pairs'])
            data, success, errors = self.urlopen(self.btce_url2 % (api_name, api_params), headers={'Host':'btc-e.nz', 'Accept': 'application/json', 'Accept-Charset': 'utf-8', 'Accept-Encding': 'identity', 'Connection': 'keep-alive'})

        if success:
            data = json.loads(data)
            return (data, True, errors) if 'error' not in data else (None, False, errors+[data])
        else: return None, False, errors

    def upair2pair(self, upair, to_reverse=False):
        pair = upair.replace('rub', 'rur')
        pair = pair.split('-')
        if to_reverse: pair.reverse()
        return '_'.join(pair)

    def price(self, upair=None): # upair is universal pair
        pair = self.upair2pair(upair)

        data, success, errors = self.do.ticker(pairs=[pair])
        if success:
            if pair in data: data = data[pair]
            else:
                success = False
                errors.append('Нет информации по валютной паре '+pair)
        else: success = False

        if not success: return data, success, errors

        price = Price(upair, data['buy'], data['sell'])

        return price, success, errors

    def order(self, upair, action, count, price):
        pair = self.upair2pair(upair)

        data, success, errors = self.do._Trade(pair=pair, type=action, price=price, amount=count)
        order = Order(self, pair, action, count, price)

        if success:
            if data['success'] in ('1', 1):
                order.setId(data['order_id'])
            else: errors.append(data['error'])

        return order, success, errors

    def cancel_order(self, order_id):
        data, success, errors = self.do._CancelOrder(order_id=order_id)
        if success:
            if data['success'] in ('1', 1):
                success = False
                errors.append(data)
        return None, success, errors

    def balance(self):
        data, success, errors = self.do._getInfo()
        if success:
            if 'success' in data:
                if data['success'] in ('1', 1):
                    if 'return' in data:
                        if 'funds' in data['return']:
                            data = Balance(None, data['return']['funds'])
                        else: 
                            success = False
                            errors.append('Отсутствует значение "founds"')
                    else: 
                        success = False
                        errors.append('Отсутствует значение "return"')
                else:
                    success = False
                    errors.append(data)
            else:
                success = False
                errors.append('Отсутствует значение "success"')

        return data, success, errors

    def calc_tax(self):
        ''' возвращает процент комиссси за сделку '''
        return 0, True, []

class exchange_poloniex(ProAPI):
    trade_url =  'https://poloniex.com/tradingApi'
    public_url = 'https://poloniex.com/public'

    def shell(self, api_name, api_params, api_type):
        if api_type == 'auth': # Auth API
            api_params['command'] = api_name
            api_params['nonce'] = int(round(time.time()*1000))
            post_data, sign = self.sign(api_params)
            headers = {"Content-type" : "application/x-www-form-urlencoded",
                       "Key" : self.conf['key'],
                       "Sign" : sign}
            data, success, errors = self.urlopen(self.trade_url, POST=post_data, headers=headers)
        else: # Public API
            api_params['command'] = api_name
            data, success, errors = self.urlopen(self.public_url, GET=api_params)

        if success:
            data = json.loads(data)
            return (data, True, errors) if 'error' not in data else (None, False, errors+[data])
        else: return None, False, errors

    def price(self, upair=None): # upair is universal pair
        pair = self.upair2pair(upair)

        data, success, errors = self.do.returnTicker(pairs=[pair])
        if success:
            if pair in data: data = data[pair]
            else:
              success = False
              errors.append('Нет информации по валютной паре '+pair)
        else: success = False

        if not success: return data, success, errors

        price = Price(upair, data['lowestAsk'], data['highestBid'])

        return price, success, errors

    def order(self, upair, action, count, price):
        pair = self.upair2pair(upair)

        if action == 'buy':
            data, success, errors = self.do._buy(currencyPair=pair, rate=price, amount=count)
        elif action == 'sell':
            data, success, errors = self.do._sell(currencyPair=pair, rate=price, amount=count)

        order = Order(self, pair, action, count, price)
        # если сервер даёт информацию о том, выполнен ли ордер, то её также можно сохранять в класса Order
        print(data)

        if success:
            if 'orderNumber' in data:
                order.setId(data['orderNumber'])
            else: errors.append('Ордер не создан')

        return order, success, errors

    def cancel_order(self, order_id):
        data, success, errors = self.do._cancelOrder(orderNumber=order_id)
        if success:
            if data['success'] != 1:
                success = False
                errors.append('Ошибка отмены ордера')
        return None, success, errors

    def balance(self):
        data, success, errors = self.do._returnCompleteBalances()
        if success:
            free = {}
            on_order = {}
            for name, value in data.items():
                free[name] = value['available']
                on_order[name] = value['onOrders']
            data = Balance(on_order, free)

        return data, success, errors

    def calc_tax(self):
        ''' возвращает процент комиссси за сделку '''
        return 0, True, []

class ExchangeMonitor:

    def __init__(self, exchanges):
        '''
            exchanges = {ИмяБиржи: ОбъектБиржи}
        '''
        self.exchanges = exchanges

    def balance(self):
        r = {}
        for name, exchange in exchanges.items():
            r[name] = exchange.balance()
        return r

    def price(self, upair):
        r = {}
        for name, exchange in exchanges.items():
            r[name] = exchange.price(upair)
        return r

class ExchangeBot:
    def __init__(self, ex):
        self.ex = ex

    def funcByEvent(self, event, func, *args):
        if event['name'] == 'orderDone':
            order = event['data']
            ## проверяем ордер
            count, success, errors = self.ex.check_order(order.order_id)
            ## если выполнен, то ставим следующий ордер
            if count == order.real_count: func(*args)

        event['func'] = func
        event['args'] = args
        event['id'] = event_id

    #def strategySellAfterBuy(upair='btc-rub', count=0.01, priceBuy=65000, priceSell=71000)
    def strategySellAfterBuy(self, upair, count, priceBuy, priceSell):
        ''' После исполнения ордера на покупку выставляет ордер на продажу. '''
        # выставляем ордер
        order, success, errs = self.ex.order(upair, 'buy', count, priceBuy)
        if not success:
            return order, success, errs

        # устанавливаем собвтие на выставление ордера на продажу после исполнения ордера на покупку        
        #return self.funcByEvent({'name':'orderDone', 'data':order}, self.ex.order, upair, 'sell', order.real_count, priceSell)

        ## если выполнен, то ставим следующий ордер
        while 1:
            order_data, success, errors = self.ex.check_order(order.order_id)
            if order_data['has_done']:
                self.ex.order(upair, 'sell', order.real_count, priceSell)
                break
            print("куплено {0} из {1}".format(order_data, order.real_count))
            time.sleep(5)

    def strategyBeFirst(self, upair, action, count, price, extremum):
        ''' Переставляет ордер в стакане так, чтобы он всегда был первым (наверху) '''
        pass


if __name__ == '__main__':

    # Тест бирж

    import configparser
    config = configparser.ConfigParser()
    path_conf = os.path.join(os.path.dirname(os.path.abspath('')), 'conf_exchange.txt')
    config.read(path_conf)

    exmo = exchange_exmo(config['exmo'])
    btce = exchange_btce(config['btce'])
    polo = exchange_poloniex(config['poloniex'])

    monitor = ExchangeMonitor({
        'exmo': exmo,
        'polo': polo,
        'btce': btce
        })

    def fprice(price_float):
        return '{0:<15}'.format(price_float)

    '''----------------------------------------------------------
    -- Баланс пользователя --------------------------------------
    ----------------------------------------------------------'''

    # методы биржи
    print('Методы биржи')

    #print(exmo.do._user_info())
    #print(polo.do._returnCompleteBalances(pairs=[]))
    #print(btce.do._getInfo())

    # универсальные методы
    print('Универсальные методы')

    balance, success, errors = exmo.balance()
    if success: print(balance.get_not_null('total'))
    else: print(balance, errors)

    balance, success, errors = polo.balance()
    if success: print(balance.get_not_null('total'))
    else: print(balance, errors)

    balance, success, errors = btce.balance()
    if success: print(balance.get_not_null('free'))
    else: print(balance, errors)

    '''----------------------------------------------------------
    -- Монитор --------------------------------------------------
    ----------------------------------------------------------'''

    print('-'*60)
    print('     | ', fprice('BUY'), fprice('SELL'), fprice('SPREAD'))
    print('-'*60)

    price, success, errs = exmo.price('btc-usd')
    if success: print('EXMO | ', fprice(price.buy), fprice(price.sell), fprice(price.spread))
    else: print('EXMO | ', errs)

    price, success, errs = btce.price('eth-rub')
    if success: print('BTCE | ', fprice(price.buy), fprice(price.sell), fprice(price.spread))
    else: print('BTCE | ', errs)

    price, success, errs = polo.price('usdt-btc') # usd = dollar, usdt = teather dollar
    if success: print('POLO | ', fprice(price.buy), fprice(price.sell), fprice(price.spread))
    else: print('POLO | ', errs)

    print('-'*60)

    '''----------------------------------------------------------
    -- Ордера ---------------------------------------------------
    ----------------------------------------------------------'''


    #data, success, errs = exmo.order({'name': 'btc', 'count':10, 'price':'market'}, {'name':'usd'})
    '''order, success, errs = exmo.order('ltc-rub', 'buy', 0.1, 100)
    print('\n', order, success, errs)
    if success:
        data, success, errs = exmo.cancel_order(order.order_id)
        print('\n', data, success, errs)'''
    #data, success, errs = exmo.order({'name': 'usd'}, {'name':'btc', 'count':10, 'price':'market'})
    #print('', data, success, errs)

    '''order, success, errs = polo.order('usdt-xmr', 'buy', 0.01, 5)
    print('\n', order, success, errs)
    if success:
        data, success, errs = polo.cancel_order(order.order_id)
        print('\n', data, success, errs)'''


    # разница цен на биржах

    '''price1, success1, errs1 = exmo.price('btc-usd')
    price2, success2, errs2 = polo.price('usdt-btc')
    if success1 and success2:
        print(price2.buy - price1.buy)
    else:
        print(errs1, '\n', errs2)'''

    '''price, success, errs = exmo.price('btc-rub')
    prev_buy = 
    for i in range(5):
        price, success, errs = exmo.price('btc-rub')'''

    '''----------------------------------------------------------
    -- Боты ---------------------------------------------------
    ----------------------------------------------------------'''
    exmo_bot = ExchangeBot(exmo)
    res = exmo_bot.strategySellAfterBuy('btc-rub', 0.005, 54000, 55000)
    print(res)

'''
    exmo.order('ltc-usd', 'buy', 0.1, 100)
    polo.order('ltc-usdt', 'buy', 0.1, 100)
    btce.order('ltc-usd', 'buy', 0.1, 100)

    exmo.cancel_order(order_id)
    polo.cancel_order(order_id)
    btce.cancel_order(order_id)

    exmo.price('ltc-usd')
    polo.price('ltc-usdt')
    btce.price('ltc-usd')
'''