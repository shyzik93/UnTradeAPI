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

  def btce_shell(self, method, params):
    if self.__wait_for_nonce: time.sleep(1)
    nonce_v = str(time.time()).split('.')[0]

    params['method'] = method
    params['nonce'] = nonce_v
    params = urllib.urlencode(params)

    sign = hmac.new(self.conf['btce']['secret'], params, digestmod=hashlib.sha512).hexdigest()
    headers = {"Content-type" : "application/x-www-form-urlencoded",
                        "Key" : self.conf['btce']['key'],
                   "Sign" : sign}
    answer = self.btce_it.urlopen("https://btc-e.com/tapi", POST=params, headers=headers)
    if answer[0] == None: return json.loads(answer[1])
    else: return answer[0]

  def shell(self, api_name, api_params):
    name, api_name = api_name.split('_', 1)
    return self.__getattribute__(name+'_shell')(api_name, api_params)

  # ########## Высоуровневые функции ############

  def getPrice(self, pair, _type):
    answer = self.ticker()
    return answer[pair][_type+'_price']
