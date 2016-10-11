# *-* coding: utf-8 *-*

'''
Written by Konstantin Polyakov
Date: August, 2016

Thanks to authours of documentation:
-- embeddedpro.ucoz.ru
-- 2150692.ru/faq/47-at-komandy-sim900
-- 2150692.ru/faq/119-gsm-gprs-modul-aithinker-a6-bystryj-zapusk

'''

import os, serial, time, copy

class SMS_PDU_Builder:
    def __init__(self):
        pass

    def _pack_message(message):
        return message

    def _build_absolute_time(self, datetime):
        pass

    def _build_relative_time(self, minutes):
        # vp = 0.. 143
        if minutes <= 60 * 12: vp = (minutes - 5) / 5                 # так как шаг 5 минут, то числа, не кратные 5, округляются в меньшую сторону.
        elif minutes <= 60 * 24: vp = (minutes-12+143*30)/30          # шаг в 30 минут
        elif minutes <= 60 * 24 * 30: vp = minutes/60/24 + 166        # шаг в 1 день
        elif minutes <= 60 * 24 * 7 * 63 : vp = minutes/60/24/7 + 192 # шаг в 1 день
        else: vp = 255

        if vp > 255: vp = 255

        return [int(vp)]


    def _build_address(self, address): # type(addres) = 'str'
        ''' Тип номера - 1 байт.
            7-й бит - всегда 1.
            6 ... 4-й бит - тип номера:
                000 - неизвестный
                001 - интернациональный
                010 - национальный
                011 - принятый в сети
                100 - тип подписчика в сети
                101 - алфавитноцифровой
                110 - сокращённый
                111 - зарезервирован
            3 ... 0-й бит - тип набора:
                0000 - неизвестный
                0001 - ISDN
                0010 - X.121
                0011 - телекс
                1000 - национальный
                1001 - частный
                1010 - ERMES
                1111 - зарезервирован
        '''
        type_of_number = 0x91 # интеенациональный
        # убираем '+'
        _sca = address if not address.startswith('+') else address[1:]
        #_sca = address if address[0] != '+' else address[1:]
        # определили длину (количество полуоктетов (полубайтов, тетрад))
        len_sca = len(_sca)
        # добавили 'F' в конец, если длина нечётная
        if (len_sca % 2 != 0): _sca += 'F'
        # переставляем тетрады местами
        sca = []
        for i in range(0, len(_sca), 2):
            sca.append(int(_sca[i+1] + _sca[i], 16))
        #print('-- SCA: ', sca)
        #print('-- SCA: ', sca2)

        return [len_sca, type_of_number] + sca

    def _build_tpdu(self, address, message, coding, delete_in_minutes, is_flash): # delete_in_minutes = 1 день
        if (isinstance(delete_in_minutes, int)): VPF = '10'
        else: VPF = '11'
        PDU_type = [int(
            '0'  + # Reply Path - запрос ответа от стороны, прин6имающей сообщение
            '0'  + # UDHI - Определяет наличие заголовка в UD (данных пользователя).
                   #     0 - UD содержит только данные, 1 - UD содержит в добавление к данным и заголовок 
            '0'  + # Status Report Request - запрос на получение отчёта. SRR отличается от RP: SRR запрашивает отчёт от сервисного центра, а RP - от получаемой стороны
            VPF + # Validity Period Format - определяет формат поля VP
                   #     00 - поле VP отсутствует
                   #     01 - резерв в Siemens, расширенный формат для SonyErricson
                   #     10 - поле VP использут относительный формат
                   #     11 - поле VP использует абсолютный формат
            '0' +  # Reject Duplicates - говорит сервисному центру о необходимости удалять одинакове сообщения, если они ещё не переданы.
                   #     Одинаковыми считаются сообщения с совпадающими VR (Message Reference) и DA (Destination Address) и поступившие 
                   #     от одного OA (Originator Address)
                   #     0 - не удалять, 1 - удалять
            '01'   # Message Type Indicator.
                   #     Биты | телефон -> серв. центр  |  серв. центр -> телефон
                   #     ------------------------------------------------
                   #     00 - SMS-DELIVER REPORT SMS-DELIVER
                   #     01 - SMS-COMMAND   SMS-STATUS REPORT
                   #     10 - SMS-SUBMIT    SMS-SUBMIT REPORT
                   #     11 - RESERVED
            , 2)]

        # Количество успешно переданных - от 0x00 до 0xff. Устанавливается телефоном. Поэтому при передаче устанавливаем его в 0x00
        MR = [0x00]

        # Адрес приёмника сообщения (номер телефона получателя)
        DA = self._build_address(address)

        # Идентификатор протокола - указывает сервисному центру, как обработать передаваемое сообщение (факс, головосое сообщение и т. д.)
        PID = [0x00]

        # Схема кодирования данных в поле UD
        # Поле DCS представляет собой байт из двух тетрад по 4 бита.
        # Старшая тетрада (с 7 по 4) опаределяет группу кодирования,
        # а младшая ( с 3 по 0 ) - специфичекские данные для группы кодирования
        if is_flash: DCS = '0b0001'
        else: DCS = '0b0000'
        if coding == 'ascii':  DCS += '0000' # )x0
        elif coding == '8bit': DCS += '0100' # 0x4
        elif coding == 'ucs2': DCS += '1000' # 0x8 
        DCS = [int(DCS, 2)]
        '''DCS = [int(
            # 
            '00' +  #
            '' +  #
            '' +  #
            '' +  #
            '' +  #
            '' +  #
            ), 2]'''

        # время жизни сообщения
        if   VPF == '10': VP = self._build_relative_time(delete_in_minutes)
        elif VPF == '11': VP = self._build_absolute_time(delete_in_minutes)
        #if   ((PDU_type[0] && 0b00011000) >> 3) == 0b10: VP = self._build_relative_time(delete_in_minutes)
        #elif ((PDU_type[0] && 0b00011000) >> 3) == 0b11: VP = self._build_absolute_time(delete_in_minutes)

        # 140 байт данных пользователя (для ASCII (GSM) - это 160 символов, а для USC2 (unicode) - это 140 символов)
        if coding == 'ucs2': # unicode
            UD = list(bytearray(message, 'utf-16')) # с маркера (первых двух байт)
        elif coding == '8bit': # utf-8, без кириллицы
            UD = list(bytearray(message, 'utf-8')) # без маркера (первых двух байт)
        elif coding == 'ascii': # ascii "упаклванная" (сжатая)
            UD = self._pack_message(message)

        # Длина поля UD - подсчитываем не кол-во байт, а кол-во символолв.
        UDL = [len(UD)]

        #return PDU_type + MR + DA + PID + DCS + VP + UDL + UD
        #print(PDU_type, MR, DA, PID, DCS, VP, UDL, UD, sep=' -- ')
        return PDU_type + MR + DA + PID + DCS + VP + UDL + UD

    def build_pdu(self, address, message, sms_center_address='nothing', coding='ucs2', delete_in_minutes=1440, is_flash=False):
        ''' Формат PDU осставлен из двух полей:
                - SCA (Service Centre Address)  - адрес сервисного центра рассылки коротких сообщений;
                - TPDU (Transport Protocol Data Unit) - пакет данных транспортного протокола.
            Некоторые модели мобильных телефонов и GSM-модемов не поддеррживают полный формат PDU
            и могут работать только с форматом TPDU. В этом случае SCA берётся из памяти SIM-карты,
            а поле SCA заменяется на 0x00.
        '''
        if sms_center_address == 'zero': sca = [0]
        elif sms_center_address == 'nothing': sca = []
        else: sca = self._build_address(sms_center_address)
        tpdu = self._build_tpdu(address, message, coding, delete_in_minutes, is_flash)
        return bytes(sca), bytes(tpdu)

    def hex2hexString(self, HEX): # принимает байты. bytes([0x0, 0xFF, 0x1A])  -->  '00FF1A'
        HEX = [str(hex(i))[2:] for i in HEX]
        return ''.join([i if len(i)%2==0  else '0'+i for i in HEX])

    def hexString2hex(self, hexs): # '00FF1A' -->  bytes([0x0, 0xFF, 0x1A])
        if len(hexs) % 2 != 0: hexs = '0' + hexs
        HEX = []
        i = 0
        while len(HEX) < len(hexs)/2:
            HEX.append(hexs[i]+hexs[i+1])
            i += 2
        return bytes([int(i, 16) for i in HEX])

'''class Executor:
    def __init__(self, cls, name):
        self.cls = cls
        self.name = name
    def __getattr__(self, name2):
        self.name2 = name2
        return self
    def __call__(self, *args, **kargs):
        return self.cls.__getattribute__(self.name2)(self.cls, *args, **kargs)'''

# Класс работы с GSM-модулем

class _GSM:
    def __autoconnect(self):
        ports = os.listdir('/dev/')
        for port in ports:
            pattern = 'tty'#'ttyUSB'
            # не используем регулярные выражения ради скорости
            if len(port) <= len(pattern) or port[:len(pattern)] != pattern: continue
            try:
                print('Connected to /dev/'+port)
                return serial.Serial(port='/dev/'+port, baudrate=115200)
            except: 
                print(' ===== BAD ======')
        return False

    def __init__(self, show_traffic=True, port=None):
        if port is None:
            self.ser = self.__autoconnect()
            if self.ser == False:
                print('No serial ports to connect')
                exit()
        else: self.ser = serial.Serial(port=port, baudrate=115200)

        time.sleep(3)

        self.show_traffic = show_traffic

        self._write('AT')
        if not self._read(): print(' ===== The device is silent =====')

    def close(self): self.ser.close() 

    def _read(self):
        r_text = bytes()
        while self.ser.inWaiting() > 0:
            r_text += self.ser.read(self.ser.inWaiting())

        if self.show_traffic and len(r_text) != 0:
            print('------ READED AS BYTES: ', r_text)
            print('------- READED AS LIST: ', list(r_text))
            print()

        return r_text

    def _write(self, w_text, endline='\r'):
        if isinstance(endline, str): endline = bytes(endline, 'utf-8')
        if isinstance(w_text, str): w_text = bytes(w_text, 'utf-8')
        w_text = w_text + endline

        if self.show_traffic:
            print('------ WROTE AS BYTES: ', w_text)
            print('------- WROTE AS LIST: ', list(w_text))
            print()

        self.ser.write(w_text)
        time.sleep(0.5)

    def parse(self, s, endline='\r\n'):
        #s = str(s, 'utf-8').strip().split(endline)
        s = s.strip().split(bytes(endline, 'utf-8'))

        if self.echo_isSet: s = s[1:]

        s = [i for i in s if len(i) != 0]

        return s

    '''def __getattr__(self, name):
        return Executor(self, name)'''

class GSM(_GSM):
    def __init__(self, show_traffic=True, port=None, isSetEcho=True):
        _GSM.__init__(self, show_traffic, port)
        self.pdu_builder = SMS_PDU_Builder()
        self.echo_isSet = isSetEcho
        self.echo(isSetEcho)

        self.sets = {
            'sms': {
                'coding': 'ucs2',
                'delete_in_minutes': 10,
                'sms_center_address': 'zero',
                'is_flash': False,
            },
            'echo': 1
        }

    def _get_sets(self, group_name, user_sets):
        sets = copy.deepcopy(self.sets[group_name])
        sets.update(user_sets)

    def read(self, isToParse='simple', isRetEcho=False):
        return self._read()
        '''r_text = self._read()

        if isToParse is True:
            echo, r_text, is_error = self.parse_read(r_text)
            if isRetEcho: return echo, r_text, is_error
            return r_text, is_error
        elif isToParse == 'simple': return self.parse(r_text)
 
        return r_text'''

    def write(self, w_text, endline='\r'):
        self._write(w_text, endline)

    '''
    def parse_read(self, s, endline='\r\n'):
        s = str(s, 'utf-8').strip()

        if not s: return '', '', True

        if self.echo_isSet: echo, answer = s.split(endline, 2)
        else: echo, answer = (None, s)

        ok_msg = 'OK'
        if answer[-len(ok_msg):] == ok_msg:
            answer = answer[:-len(ok_msg)]
            is_error = False
        else: is_error = True

        return echo, answer.strip(), is_error'''

    def set(self, name, data=None, endline='\r'):
        if isinstance(data, (int, float)): data = str(data)
        if data is not None: self.write('AT'+name+'='+data, endline)
        else: self.write('AT'+name, endline)
    def get(self, name, endline='\r'):
        self.write('AT'+name+'?', endline)
    def test(self, name, endline='\r'):
        self.write('AT'+name+'=?', endline)
    def raw(self, name): self.write(name, endline='')

    def parse_test(self, test):
        if test[-1] == bytes('OK', 'utf-8'):
            is_error = False
            values = test[0].split(bytes(' ', 'utf-8'), 1)[1]
            values = values[1:-1].split(bytes(',', 'utf-8'))
            values = [i[1:-1] if i.startswith(bytes('"', 'utf-8')) else i for i in values]
        else:
            is_error = True
            values = test[0]
        return is_error, values

    def parse_get(self, get):
        pass

    def echo(self, isSet=None):
        self.echo_isSet = isSet
        if isSet is None:
            self.write('ATE=?')
            return self.parse(self.read())

        if isSet:
            self.write('ATE1')
            return self.parse(self.read())
        else:
            self.write('ATE0')
            return self.parse(self.read())

    def info(self):
        self.write('ATI')
        return self.parse(self.read())

    def at(self):
        self.write('AT')
        return self.parse(self.read())

    # ---- высокий уровень

    def sms_send(self, message, address, sets={}):
        sets = self._get_sets('sms', sets)
        '''if 'coding' not in sets:             sets['coding'] = 'ucs2'
        if 'delete_in_minutes' not in sets:  sets['delete_in_minutes'] = 10
        if 'sms_center_address' not in sets: sets['sms_center_address'] = 'zero'
        if 'is_flash' not in sets: sets['is_flash'] = False'''

        CONFIRM = bytes([26]) # (SUB) Ctrl-Z
        CANCEL  = bytes([27]) # ESC

        if self.SMS_mode == 'text':
            self.write('AT+CMGS="'+address+'"')
            print(self.parse(self.read()))
            self.write(bytes(message, 'utf-8'), endline=CONFIRM)
            print(self.parse(self.read()))


        elif self.SMS_mode == 'pdu':
            sca, tpdu = self.pdu_builder.build_pdu(address, message, sets['sms_center_address'], sets['coding'], sets['delete_in_minutes'], sets['is_flash'])
            len_tpdu = str(len(tpdu))
            self.write('AT+CMGS='+len_tpdu)
            print(self.parse(self.read()))
            self.write(self.pdu_builder.hex2hexString(sca + tpdu), endline=CONFIRM)
            print(self.parse(self.read()))

    def sms_read(self):
        r_text = bytes()
        while self.ser.inWaiting() > 0:
            r_text += self.ser.read(1)
        return r_text

    def sms_setMode(self, mode):
        ''' Устанавливает режим: текстовый илши PDU '''
        if mode == 'pdu':
            self.write('AT+CMGF=0')
        elif mode == 'text':
            self.write('AT+CMGF=1')
        self.SMS_mode = mode
        print(self.parse(self.read()))

    def setCoding(self, coding):
        ''' Устанавливает кодировку для текстового режима '''
        # кодировка текстового режима. Доступны: GSM, UCS2, HEX
        self.write('AT+CSCS="'+coding+'"')
        print(self.parse(self.read()))

    def TextModeParameters(self, action, value):
        if action=='get':
            self.write('AT+CSDH?')
        elif action=='list':
            self.write('AT+CSDH=?')
        elif action=='exe':
            self.write('AT+CSDH')
        elif action=='set':
            self.write('AT+CSDH='+str(value))
        print(self.parse(self.read()))

#gsm.set.func -  установитиь значение
#gsm.cur.func -  вернуть текущее значение
#gsm.list.func - вернуть список возможных значений
#gsm.exe.func -  выполнить команду

if __name__ == '__main__':

  # Тест GSM

  gsm = GSM(show_traffic=False)
  try:
    #'AT+CUSD=1,"*100#",15\r\n')
    # получаем нолмер сервисного центра
    #gsm.write('AT+CSCA?')

    #gsm.echo(1)
    #print('-- ANSWER: ', gsm.at())
    #gsm.echo(0)
    #print('-- ANSWER: ', gsm.at())

    #print('-- ANSWER: ', gsm.echo())
    #print('-- ANSWER: ', gsm.info())

    '''
    #address = '+79998887766'
    address = '+79615326479'

    gsm.sms_setMode('pdu')
    gsm.sms_send('  Latinica Кирилица Ё', address)
    time.sleep(5)
    #gsm.sms_setMode('text')
    #gsm.sms_send('  Latinica Кирилица Ё', address)'''

    #gsm.write('ATV1')
    #print(gsm.read())

    #gsm.at()
    #gsm.sms_setMode('text')
    #gsm.setCoding('HEX')
    #gsm.write('AT+CUSD=1,"#105#",15')
    #time.sleep(5)
    #raw = gsm.read()
    #print(raw)
    #print(gsm.parse(raw))

    #gsm.showTextModeParameters()

    #gsm.write('AT+CSCS='+data)
    gsm.set('+CSCS', 'GSM')
    print(gsm.parse(gsm.read()))

    #gsm.write('AT+CSCS')
    gsm.set('+CSCS') # gsm.exe
    print(gsm.parse(gsm.read()))

    #gsm.write('AT+CSCS?')
    gsm.get('+CSCS')
    print(gsm.parse(gsm.read()))

    #gsm.write('AT+CSCS=?')
    gsm.test('+CSCS')
    test = gsm.parse(gsm.read())
    print(test)
    print(gsm.parse_test(test))

    gsm.test('+CSCd')
    test = gsm.parse(gsm.read())
    print(test)
    print(gsm.parse_test(test))

    #gsm.write('AT+CSCS='+data)
    #gsm.raw('AT+CSCS='+data)

    while 1:
      w_text = input()
      if w_text == 'exit': break
      if w_text != '': gsm.write(w_text)
      r_text = gsm.read()
      if r_text != '': print(gsm.parse(r_text))

    print('\n\n---------------\nSTOPPED')
  finally:
    gsm.close()
