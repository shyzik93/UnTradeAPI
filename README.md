# Модуль для работы с биржами.

Язык: Python 3.4
Поддерживаются биржы Exmo и BTC-e. Цель данного модуля - построение универсального интерфейса для бирж.

# Использование

```
import exchange

config = {'key': '', secret': ''}
exmo = exchange.exchange_exmo(config)
config = {'key': '', secret': ''}
btce = exchange.exchange_exmo(config)
```

Обращаться к API можно двумя способами:
- exmo.do.имяМетода() или exmo.do._имяМетода() - прямое обращение к API биржы. Символ подчёркивания означает метод, использующий авторизацию, без подчёркивания - без авторизации. Полный список методов можно найти в документации соответствующих бирж.
- exmo.имяФункции() - универсальные методы вне зависимости от биржы.

Функции обеих катагорий возвращают три значения: результат, наличие ошибки, список ошибок.

Примеры прямого обращения к биржам:
```
exmo.do._user_info() # запрос информации 
btce.do._getInfo() # то же

btce.do.info(pairs=['usd_rur']) # информация о торгах по валютным парам
exmo.do.order_book(pair='USD_RUB', limit=10) # тоже
```

Функции прямого обращения к API используют разные (хотя и похожие) форматы называния валютных пар. Но универсальные функции - один способ для всех бирж: латнискими буквами, в качестве разделителя валют - знак почёркивания или тире (что проще). Необходимо всё же понимать, что хотя универсальные функции и возвращают результат в одинаковом формате, но одни биржы предоставляют некоторую инфорацию, а другие - нет.

Обращение к API через универсальные функции. Вместо "exmo" можно подставлять любую биржу.

```
exmo.price('btc-usd') # получение цены пары. Для Exmo можно указать второй аргумент - количество значений в "стакане"
id_order = e.new_order('usd-rur', 'sell') # Создание ордера
```

# Подробнее про универсальные функции

data, success, errors = exmo.price('usd-rur') - в качестве data будет возвращён объект Price, имеющего следующие свойства:
- data.sell - цена продажи
- data.buy - цена покупки
- data.glass_sell - "стакан" с ценами продажи (не для всех бирж)
- data.glass_buy - "стакан" с ценами покупки (не для всех бирж)









------------------------------- ещё не сделано :(
e.price('usd_rur', 'buy')
id_order = e.new_order('usd_rur', 'sell')
id_order = e.new_order('usd_rur', 'buy')
e.cancel_order(id_order)