# coding: utf-8
# Author: Ra93POL
# E-mail: kostyan_93@mail.ru
# -*- coding: utf-8 -*-
# Date: 25.07.2014   18.08.2015   06.11.2015
import repper, apitools, internettools
import urllib, urllib2, json, hmac, hashlib, os, time

class API(apitools.proto_api):
  exmo_url = "https://api.exmo.com/v1/"
  btce_url = "https://btc-e.com/tapi"
  btce_url2 = "https://btc-e.com/api/3/%s/%s"
  __wait_for_nonce = False # for btce
  def __init__(self, conf):
    self.conf = conf
    self.exmo_it = internettools.InternetTools(geterrors=True)
    self.btce_it = internettools.InternetTools(geterrors=True)

  def exmo_shell(self, api_name, api_params):
    if api_name[0] == '_': # Auth API
      api_name = api_name[1:]
      api_params["nonce"] = str(time.time()).replace('.', '')#split('.')[0]
      post_data = urllib.urlencode(api_params)
      sign = hmac.new(key=self.conf['exmo']['secret'], msg=post_data, digestmod=hashlib.sha512).hexdigest()
      header = {"Key": self.conf['exmo']['key'], "Sign":sign}
      #print header
      answer = self.exmo_it.urlopen(self.exmo_url + api_name, POST=post_data, headers=header)
    else: # Public API
      answer = self.exmo_it.urlopen(self.exmo_url + api_name, GET=api_params, headers={'Accept-Charset': 'utf-8' })
    if answer[0] == None: return json.loads(answer[1])
    else: return answer[0]

  def btce_shell(self, api_name, api_params):
    if self.__wait_for_nonce: time.sleep(1)
    if api_name[0] == '_': # Auth API
      api_name = api_name[1:]
      nonce_v = str(time.time()).split('.')[0]
      api_params['method'] = api_name
      api_params['nonce'] = nonce_v
      api_params = urllib.urlencode(api_params)
      sign = hmac.new(self.conf['btce']['secret'], api_params, digestmod=hashlib.sha512).hexdigest()
      headers = {"Content-type" : "application/x-www-form-urlencoded",
                     "Key" : self.conf['btce']['key'],
                     "Sign" : sign}
      answer = self.btce_it.urlopen(self.btce_url, POST=api_params, headers=headers)
    else: # Public API
      answer = self.btce_it.urlopen(self.btce_url2 % (api_name, api_params['pairs']))
    if answer[0] == None: return json.loads(answer[1])
    else: return answer[0]

  def shell(self, api_name, api_params):
    name, api_name = api_name.split('_', 1)
    return self.__getattribute__(name+'_shell')(api_name, api_params)

  # ########## Высоуровневые функции ############
  def normalize_pair(self, ec_name, pair):
    if ec_name=='exmo': return pair.upper()
    elif ec_name=='btce': return pair.replace('rub', 'rur')

  def denormalize_pair(self, ec_name, pair):
    if ec_name=='exmo': return pair.lower()
    elif ec_name=='btce': return pair.replace('rur', 'rub')

  def Price(self, ec_name, pair, _type):
    ''' Пары пишутся маленькими буквами. Рубль - это rub. '''
    pair = self.normalize_pair(ec_name, pair)
    if ec_name == 'exmo':
      if _type=='buy': _type = 'sell'
      elif _type=='sell': _type = 'buy'
      answer = self.exmo_ticker()
      return float(answer[pair][_type+'_price'])
    elif ec_name == 'btce':
      answer = self.btce_ticker(pairs=pair)
      return float(answer[pair][_type])

  def PairsList(self, ec_name):
    if ec_name == 'exmo': pairs = self.exmo_ticker().keys()
    elif ec_name == 'btce': pairs = self.btce_info(pairs='')['pairs'].keys()
    else: print ec_name, '| Wrong name of exchange!'
    return [self.denormalize_pair(ec_name, pair) for pair in pairs]

  def PairsTradeInfo(self, ec_name):
    if ec_name == 'exmo':
      _pairs = self.exmo_ticker() # список пар с ценами
      return {self.denormalize_pair(ec_name, pair): {'buy': float(data['sell_price']), 'sell': float(data['buy_price'])} for pair, data in _pairs.items()} # sell -> buy - это не ошибка!
    elif ec_name == 'btce':
      _pairs = self.btce_info(pairs='')['pairs'].keys() # список пар с настройками
      _pairs = self.btce_ticker(pairs='-'.join(_pairs)) # передав список, получаем и список, и цены
      for key, value in _pairs.items():
        try: _pairs[key] = float(value)
        except: pass
      return {self.denormalize_pair(ec_name, pair): data for pair, data in _pairs.items()}
