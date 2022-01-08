# *-* coding: utf-8 *-*

'''
Written by Konstantin Polyakov
Date: August, 2016

Thanks to authours of the documentation:
-- embeddedpro.ucoz.ru
-- 2150692.ru/faq/47-at-komandy-sim900
-- 2150692.ru/faq/119-gsm-gprs-modul-aithinker-a6-bystryj-zapusk

'''

import os
import serial
import time
import copy

class bin_tools():
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

class SMS_PDU_Parser(bin_tools):
    def __init__(self):
        pass

    def parse_pdu(self, pdu):
        cursor = 0

        len_sca = pdu[cursor]
        cursor += 1
        sca = pdu[cursor:len_sca+cursor]

        cursor += len_sca

        pdu_type = pdu[cursor]
        cursor += 1

        print(sca, pdu_type)


'''
 [b'+CMT: ,155', b'07919772929090F340048115810004712022004024218C0B05040B8423F000032302012306246170706C69636174696F6E2F766E642E7761702E6D6D732D6D65737361676500B487AF848C8298583130343330303030303136323131313730323232303030343432303031008D9083687474703A2F2F6D6D7363723A383030322F30343330303030303136323131313730323232303030343432303031008805810302', b'+CIEV: "MESSAGE",1', b'+CMT: ,51', b'07919772929090F36404811581000471202200402421240B05040B8423F00003230202A300890E802B373936S\xa6\xa6M\xa6\xa6&\xd3\x13\xa6&\x13\x13&\xa7PN\x98\x9cE020207', b'\xf9\xff\xff\xff']

'''

r = SMS_PDU_Parser()
pdu = '07919772929090F340048115810004712022004024218C0B05040B8423F000032302012306246170706C69636174696F6E2F766E642E7761702E6D6D732D6D65737361676500B487AF848C8298583130343330303030303136323131313730323232303030343432303031008D9083687474703A2F2F6D6D7363723A383030322F30343330303030303136323131313730323232303030343432303031008805810302'
r.parse_pdu(r.hexString2hex(pdu))
#pdu = '07919772929090F36404811581000471202200402421240B05040B8423F00003230202A300890E802B373936S\xa6\xa6M\xa6\xa6&\xd3\x13\xa6&\x13\x13&\xa7PN\x98\x9cE020207'
#r.parse_pdu(r.hexString2hex(pdu))


#exit()

class SMS_PDU_Builder(bin_tools):
    def __init__(self):
        pass

    def _pack_message(message):
        # необходимо реализовать
        return message

    def _build_absolute_time(self, datetime):
        # необходимо реализовать
        pass

    def _build_relative_time(self, minutes):
        # vp = 0.. 143
        if minutes <= 60 * 12: vp = (minutes - 5) / 5                 # так как шаг 5 минут, то числа, не кратные 5, округляются в меньшую сторону.
        elif minutes <= 60 * 24: vp = (minutes-12+143*30)/30          # шаг в 30 минут
        elif minutes <= 60 * 24 * 30: vp = minutes/60/24 + 166        # шаг в 1 день
        elif minutes <= 60 * 24 * 7 * 63 : vp = minutes/60/24/7 + 192 # шаг в 1 неделю
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
        type_of_number = 0x91 # интернациональный
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
            '0'  + # Reply Path - запрос ответа от стороны, принимающей сообщение
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
        ''' Формат PDU составлен из двух полей:
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

'''class Executor:
    def __init__(self, cls, name):
        self.cls = cls
        self.name = name
    def __getattr__(self, name2):
        self.name2 = name2
        return self
    def __call__(self, *args, **kargs):
        return self.cls.__getattribute__(self.name2)(self.cls, *args, **kargs)'''

# Класс работы с AT-командами

class _AT:
    def __autoconnect(self, baudrate):
        ports = os.listdir('/dev/')
        for port in ports:
            pattern = 'tty'#'ttyUSB'
            # не используем регулярные выражения ради скорости
            if len(port) <= len(pattern) or port[:len(pattern)] != pattern: continue
            print('Connecting to /dev/'+port)
            try:
                ser = serial.Serial(port='/dev/'+port, baudrate=baudrate)
                #self._write('AT', ser=ser)
                #if not self._read(ser=ser): print('--- connected, but didn\'t answer\n-----')
                if not self._send('AT', self.endline, ser, 10): print('--- connected, but didn\'t answer\n-----')
                else:
                    print('--- connected\n------------------------')
                    return ser
            except serial.serialutil.SerialException: 
                print('--- not connected\n--------------------')
        return False

    def __init__(self, baudrate, endline, show_traffic=True, port=None):
        self.show_traffic = show_traffic
        self.endline = endline

        if port is None:
            self.ser = self.__autoconnect(baudrate=baudrate)
            if self.ser == False:
                print('No serial ports to connect')
                exit()
        else: self.ser = serial.Serial(port=port, baudrate=baudrate)

        time.sleep(3)

        print('\n')

    def log(self, data):
        log_file = os.path.join(os.path.dirname(__file__), 'log_gsm.txt')
        Time = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(time.time()-time.altzone))
        text = '\n'#"\n* %s  " % (Time)

        if self.show_traffic != False and len(data) != 0:
            if self.show_traffic == 'file':
                if not os.path.exists(log_file):
                    with open(log_file, 'wb') as f: pass
                with open(log_file, 'ab') as f:
                    f.write(bytes(text, 'utf-8'))
                    f.write(data)
            elif self.show_traffic == True:
                print(data)

    def close(self): self.ser.close() 

    def _read(self, ser=None):
        ser = self.ser if ser is None else ser

        r_text = bytes()
        while ser.inWaiting() > 0:
            r_text += ser.read(ser.inWaiting())

            self.log(bytes('------ READED AS BYTES: ', 'utf-8') + r_text)
            #self.log(bytes('------- READED AS LIST: ', 'utf-8') + list(r_text))

        return r_text

    def _write(self, w_text, endline=None, ser=None):
        if endline is None: endline = self.endline
        if isinstance(endline, str): endline = bytes(endline, 'utf-8')
        if isinstance(w_text, str): w_text = bytes(w_text, 'utf-8')
        w_text = w_text + endline

        self.log(bytes('------ WROTE AS '+str(len(w_text))+'BYTES: ', 'utf-8') + w_text)
        #self.log(bytes('------- WROTE AS LIST: ', 'utf-8') + list(w_text))

        ser = self.ser if ser is None else ser

        ser.write(w_text)
        #time.sleep(0.5)
        return w_text

    def parse(self, r_text, endline='\r\n'):
        #r_text = str(r_text, 'utf-8').strip().split(endline)
        r_text = r_text.strip().split(bytes(endline, 'utf-8'))

        if hasattr(self, 'sets') and self.sets['echo']: r_text = r_text[1:] # удаляем повтор команды из ответа

        r_text = [i for i in r_text if len(i) != 0] # удаляем пустые строки

        self.log(bytes('----- READED AS R_LIST: ', 'utf-8') + bytes(str(r_text), 'utf-8'))

        return r_text # it's r_list now

    def _send(self, command, endline, ser, c):
        command = self._write(command, ser=ser)
        #time.sleep(0.5)
        r = self.parse(self._read(ser=ser))
        rs = []
        x = 0
        step = 1
        while 1:
            if step == 1:
                if r and r[0].strip() == command[:-1].strip():
                    if len(r) == 1:
                        step = 2
                        x = 0
                    else:
                        time.sleep(0.2)
                        return r
            elif step == 2:
                if r:
                    time.sleep(0.2)
                    return r
            #print('2', command, r)
            time.sleep(0.5)
            r = self.parse(self._read(ser=ser))
            rs += r
            x += 1
            if x == c: return rs

    def send(self, command, endline=None, ser=None, c=100, nowait=False):
        while 1 and not nowait:
            r = self._send('AT', endline=endline, ser=ser, c=c)
            if b'busy p...' not in r and b'busy s...' not in r: break
        return self._send(command, endline=endline, ser=ser, c=c)

    def guess_coding(self, message):
        # необходимо реализовать
        coding = ""
        return coding

class AT(_AT):
    def __init__(self, show_traffic=True, port=None, isSetEcho=True, baudrate=115200, endline='\r'):
        _AT.__init__(self, baudrate, endline, show_traffic, port)

    def read(self, isToParse=None):
        r_text = self._read()

        if isToParse in ['simple', 'get', 'list']: r_text = self.parse(r_text)

        if isToParse == 'get': r_text = self.parse_get(r_text)
        elif isToParse == 'list': r_text = self.parse_test(r_text)

        return r_text

    ''' Запись команд в порт '''

    def write(self, w_text, endline=None):
        self._write(w_text, endline)

    def set(self, name, data=None, endline=None, ret=True):
        ''' Устанавливает значение '''
        if isinstance(data, (int, float)): data = str(data)
        if data is not None:
            return self.send('AT'+name+'='+data, endline)
        #if ret: return self.parse(self.read())

    def exe(self, name, data=None, endline=None, ret=True):
        ''' Выполняет команду'''
        return self.send('AT'+name, endline)
        #if ret: return self.parse(self.read())

    def get(self, name, endline=None, ret=True):
        ''' Возвращает текущее значение '''
        return self.send('AT'+name+'?', endline)
        #if ret: return self.parse(self.read())

    def list(self, name, endline=None, ret=True):
        ''' Возвращает список возможных значений '''
        return self.send('AT'+name+'=?', endline)
        #if ret: return self.parse(self.read())

    def raw(self, name, ret=True, nowait=False):
        ''' вручную '''
        return self.send(name, endline='', nowait=nowait)
        #if ret: return self.parse(self.read())

    ''' Разбор ответа '''

    def parse_list(self, r_list):
        if r_list == []: return False, None
        if r_list[-1] == bytes('OK', 'utf-8'):
            is_error = False
            values = r_list[0].split(bytes(' ', 'utf-8'), 1)[1]
            #values = values[1:-1].split(bytes(',', 'utf-8'))
            #values = [i[1:-1] if i.startswith(bytes('"', 'utf-8')) else i for i in values]
        else:
            is_error = True
            values = r_list[0]

        self.log(bytes('----- READED AS R_LIST2: ', 'utf-8') + bytes(str((is_error, values)), 'utf-8'))

        return is_error, values

    def parse_get(self, r_list):
        if r_list == []: return False, None
        if r_list[-1] == bytes('OK', 'utf-8'):
            is_error = False
            value = r_list[0].split(bytes(':', 'utf-8'), 1)[1].strip()
            #value = value[1:-1] if value.startswith(bytes('"', 'utf-8')) else value
        else:
            is_error = True
            value = r_list[0]

        self.log(bytes('----- READED AS R_LIST2: ', 'utf-8') + bytes(str((is_error, value)), 'utf-8'))

        return is_error, value

    ''' Общие для всех устройств команды '''

    def at(self):
        self.write('AT')
        return self.parse(self.read())

    def echo(self, isSet=None):
        self.sets['echo'] = isSet
        if isSet is None:
            self.write('ATE=?')
            return self.parse(self.read())

        if isSet:
            self.write('ATE1')
            return self.parse(self.read())
        else:
            self.write('ATE0')
            return self.parse(self.read())

    '''def build_command(self, action, command, value=''):
        if isinstance(value, (int, float)): value = str(value)

        if action in ['cur', 'get']: # текущее значение
            postfix = '?'
        elif action=='list': # список возможных значений
            postfix = '=?'
        elif action=='exe': # выполнить команду
            postfix = ''
        elif action=='set': # изменить текущее значение
            postfix = '='+str(value)

        return command+postfix'''


# Классы с описанием AT-команд различных устройств

class GSM(AT):
    '''
        - AT+CSDH - Параметры текстового режима СМС
    '''
  
    def __init__(self, show_traffic=True, port=None, isSetEcho=True, baudrate=115200, endline='\r\n'):
        AT.__init__(self, show_traffic, port, isSetEcho, baudrate, endline)

        self.pdu_builder = SMS_PDU_Builder()
        self.pdu_parser = SMS_PDU_Parser()
        
        # настройки по умолчанию
        self.sets = {
            'sms': {
                'coding': 'ucs2',
                'delete_in_minutes': 10,
                'sms_center_address': 'zero',
                'is_flash': False,
            },
            'echo': isSetEcho
        }

        self.echo(isSetEcho)

    def _get_sets(self, group_name, user_sets):
        ''' Возвращает настройки по умолчанию с учётом настроек пользователя '''
        sets = copy.deepcopy(self.sets[group_name])
        sets.update(user_sets)
        return sets

    def info(self):
        return self.exe('I')

    def sms_send(self, message, address, sets={}):
        sets = self._get_sets('sms', sets)

        CONFIRM = bytes([26]) # (SUB) Ctrl-Z
        CANCEL  = bytes([27]) # ESC

        if self.SMS_mode == 'text':
            self.write('AT+CMGS="'+address+'"')
            print(self.parse(self.read()))
            self.write(bytes(message, 'utf-8'), endline=CONFIRM)
            print(self.parse(self.read()))

        elif self.SMS_mode == 'pdu':
            if sets['coding'] == 'auto': sets['coding'] = self.guess_coding(message) # выбор оптимальной кодировки для данного сообщения
            sca, tpdu = self.pdu_builder.build_pdu(address, message, sets['sms_center_address'], sets['coding'], sets['delete_in_minutes'], sets['is_flash'])
            len_tpdu = str(len(tpdu))
            self.write('AT+CMGS='+len_tpdu)
            print(self.parse(self.read()))
            self.write(self.pdu_builder.hex2hexString(sca + tpdu), endline=CONFIRM)
            print(self.parse(self.read()))

    def sms_read_all(self, status):
        '''  -------------------------------------------------------------------------------
             | <status> в текстовом  |  <status>в режиме    |
             |       режиме          |       PDU            |     Пояснение
             -------------------------------------------------------------------------------
             |     REC UNREAD        |           0          | Непрочитанные
             |      REC READ         |           1          | Прочитанные
             |     REC UNSENT        |           2          | Сохранённые неотправленные
             |      REC SENT         |           3          | Сохранённые отправленные
             |        ALL            |           4          | Все сообщения
             -------------------------------------------------------------------------------
        '''

        self.write('AT+CMGL='+str(status))

    def sms_read(self, index):
        self.write('AT+CMGR'+str(index))

    def sms_setMode(self, mode):
        ''' Устанавливает режим: текстовый или PDU '''
        if mode == 'pdu':
            self.write('AT+CMGF=0')
        elif mode == 'text':
            self.write('AT+CMGF=1')
        self.SMS_mode = mode

    def sms_setLogicMemory(self, *message_storages):
        ''' Устанавливает соответствие физических секций памяти логическим.
            Логические:
                - первая - просмотр, чтение и удаление;
                - вторая - сохранение и отправка исходящих сообщений
                - третья - только что полученные сообщения. Обычно, они хранятся в первой секции.
            Физические:
                - SM - память SIM-карты;
                - ME - память модема/телефона
                - MT - общая память модема и SIM-карты
                - BM - память для широковещательных сообщений сети
                - SR - память для отчётов (о доставке и т. п.)
            Любое чтение идёт только из памяти, назначенной для первой логической секции

            Формат команды: AT+CPMS=message_storage1[,message_storage2[,message_storage3]]
            То есть, вторая и третья логическая секция необязательна. '''

        message_storage = ['"'+i+'"' for i in message_storages]
        self.write('AT+CPMS='+",".join(message_storage));

    def setCoding(self, coding):
        ''' Устанавливает кодировку для текстового режима '''
        # кодировка текстового режима. Доступны: GSM, UCS2, HEX
        print(self.set('+CSCS', '"'+coding+'"'))

class WIFI(AT):
    ''' http://www.instructables.com/id/Getting-Started-with-the-ESP8266-ESP-12/
        http://www.ctr-electronics.com/downloads/pdf/4A-ESP8266__AT_Instruction_Set__EN_v0.40.pdf
        
        AT version:0.60.0.0(Jan 29 2016 15:10:17)
        SDK version:1.5.2(7eee54f4)
        Ai-Thinker Technology Co. Ltd.
        May  5 2016 17:30:30
        
        programming:
        https://geektimes.ru/post/241842/
        https://github.com/pfalcon/esp-open-sdk
        http://wikihandbk.com/wiki/ESP8266:%D0%9F%D1%80%D0%BE%D1%88%D0%B8%D0%B2%D0%BA%D0%B8/%D0%9A%D0%B0%D0%BA_%D1%83%D1%81%D1%82%D0%B0%D0%BD%D0%BE%D0%B2%D0%B8%D1%82%D1%8C_%D0%B2_IDE_Arduino_%D0%B0%D0%B4%D0%B4%D0%BE%D0%BD_%D0%B4%D0%BB%D1%8F_ESP8266
        http://wikihandbk.com/wiki/ESP8266:%D0%9F%D1%80%D0%BE%D1%88%D0%B8%D0%B2%D0%BA%D0%B8/Arduino
        "…. stopped with the error ….. error: could not find GNU libtool >= 1.5.26
         just in case for others … this can be solved by: sudo apt-get install libtool-bin"
         
        
        https://habrahabr.ru/post/255135/
        https://habrahabr.ru/search/page2/?q=%5Besp8266%5D&target_type=posts&flow=&order_by=relevance
        https://esp8266.ru/
        
        http://hobbytech.com.ua/%D0%B7%D0%BD%D0%B0%D0%BA%D0%BE%D0%BC%D0%B8%D0%BC%D1%81%D1%8F-%D1%81-%D0%BC%D0%BE%D0%B4%D1%83%D0%BB%D0%B5%D0%BC-esp8266-%D0%BF%D0%BE%D0%B4%D1%80%D0%BE%D0%B1%D0%BD%D0%B5%D0%B5/
        http://hobbytech.com.ua/shop/arduino/shields/esp8266mod/
        
        https://leanpub.com/cart_purchases/euh_7R94pzFyh_QFI95eBg/thankyou
    
        # AT-команды WI-FI-модуля ESP8266-12F компании AI-Thinker

        - AT+GMR - возвращает информацию о молдуле
        - AT+CWMODE - режим модуля. Принимает значения: 1 - клиент, 2 - точка доступа, 3 - WI-FI-клиент и WI-FI-точка доступа одновременно.
        - AT+CWLAP - список найденных точек доступа
        - AT+CWJAP="your_network_name","your_wifi_network_password" - Пождключает модуль к WI-FI точке доступа
        - AT+CIFSR - возвращает IP-адрес модуля как вторую строку и gateway IP-адрес, если устройство подключено.

        - AT+CWQAP - отключится от точки доступа
    '''

    def __init__(self, show_traffic=True, port=None, isSetEcho=True, baudrate=115200, endline='\r\n'):
        AT.__init__(self, show_traffic, port, isSetEcho, baudrate, endline)

    def info(self):
        return self.exe('+GMR')

    def browser_init(self, domain, port=80):
        if isinstance(port, (int, float)): port = str(port)
        print(self.set('+CIPSTART', '"TCP","'+domain+'",'+port))
        self.browser_host = domain
        
    def browser_go(self, method, path):
        data = method +' '+ path + ' HTTP/1.1\nHost: '+self.browser_host+'\n\n' + self.endline
        print(self.set('+CIPSEND', len(data))) # 2 байта символов '\r\n'
        print(self.raw(data, nowait=True))

    def server_start(self):
        print(self.set('+CIPMUX', '1')) # рахрешавем множественные соединения
        print(self.set('+CIPSERVER', '1,80')) # запускаем сервер

    def server_stop(self):
        print(self.set('+CIPSERVER', '0,80'))
        print(self.set('+CIPMUX', '0'))

    def server_send(self, connect_id, data, headers=None):
        if isinstance(connect_id, (int, float)): connect_id = str(connect_id)

        if headers:
            headers = '\n'.join(headers)
            headers = '\n' + headers
        else: headers = ''

        data = "HTTP/1.1 200 OK"+headers+"\n\n"+data+"\n" + self.endline
        print(at.set('+CIPSENDEX', connect_id+','+str(len(data))))
        print(at.raw(data, nowait=True))

if __name__ == '__main__':
  
    import argparse
  
    aparser = argparse.ArgumentParser(description='Module for AT-devi ces (GSM, WIFI, etc)')
    aparser.add_argument('--baudrate', default=None)
    aparser.add_argument('--port', default=None)
    aparser.add_argument('--endline', default=None)

    args = aparser.parse_args()
    _args = {}
    if not (args.port is None): _args['port'] = args.port
    if not (args.endline is None): _args['endline'] = args.endline
    if not (args.baudrate is None): _args['baudrate'] = args.baudrate

    # Тест GSM

    at = GSM(show_traffic='file', **_args)
    try:
        print(at.info())
        
        ''' WIFI '''

        #print(at.exe('+CWLAP'))

        #print(at.set('+CWJAP', '"Name network","password"'))

        '''r = at.parse(at.read())
        while r and r[-1] == 'busy p...':
            time.sleep(1)
            print('c', r)
            r = at.parse(at.read())'''

        #print(at.set('+CWJAP', '"FunMan Network","WNp40p4BcY"'))
        #time.sleep(10);

        #at.browser_init('dosmth.ru')
        #at.browser_go('GET', '/iot.php?temp='+str(time.time()))
        #at.server_start()

        ''' GSM '''
      
        #'AT+CUSD=1,"*100#",15\r\n')
        # получаем нолмер сервисного центра
        #at.write('AT+CSCA?')

        at.echo(1)
        print('-- ANSWER: ', at.at())
        #at.echo(0)
        #print('-- ANSWER: ', at.at())

        #print('-- ANSWER: ', at.echo())
        #print('-- ANSWER: ', at.info())

        #address = '+79998887766'

        at.sms_setMode('pdu')
        print(at.read())
        #at.sms_setLogicMemory('SM', 'ME')
        #print(at.read())

        #at.sms_read_all(4)
        #print(at.read())
        #at.sms_send('  Latinica Кирилица Ё', address)
        #at.sms_send('Пусть каждое утро станет добрым :)\nРаминь!\n\nКонстантин', '+79615151606', {'is_flash':False})
        at.sms_send('Пусть кажд :)\nРаминь!\n\nКонстантин', '+79615151606', {'is_flash':False})
        #at.sms_setLogicMemory("MT")
        #at.list('+CMGL')
        #print(at.read())
        #at.get('+CPMS')
        #print(at.read())

        #time.sleep(5)

        #at.sms_setMode('text')
        #at.sms_send('  Latinica Кирилица Ё', address)

        #at.write('ATV1')
        #print(at.read())

        #at.at()
        #at.sms_setMode('text')
        #at.setCoding('HEX')
        #at.write('AT+CUSD=1,"#105#",15')
        #time.sleep(5)
        #raw = at.read()
        #print(raw)

        #print(at.parse(raw))
        #print(at.exe('+CSDH'))

        #at.write('AT+CSCS='+data)
        '''at.set('+CSCS', 'GSM')
        print(at.parse(at.read()))

        #at.write('AT+CSCS')
        at.set('+CSCS') # at.exe
        print(at.parse(at.read()))

        at.get('+CSCS')
        print(at.read('get'))

        at.list('+CSCS')
        print(at.read('list'))

        at.list('+CSCd') # несуществующая команда
        print(at.read('list'))

        at.list('+CMGL')
        print(at.read('list'))

        at.get('+CMGL')
        print(at.read('get'))

        at.set('+CMGL', 4)
        r_list = at.parse(at.read())
        print(at.parse_list(r_list))'''

        #at.write('AT+CSCS='+data)
        #at.raw('AT+CSCS='+data)

        while 1:
            w_text = input()
            if w_text == 'exit': break
            if w_text != '': print(at.send(w_text, nowait=True))
            r_text = at.read()
            if r_text != '':
                print(at.parse(r_text))
                if b'0,CONNECT' in r_text:
                    at.server_send(0, '<h1>hello to all</h1><br>:-)', ['Content-Type: text/html;'])

        print('\n\n---------------\nSTOPPED')
    finally:
        at.close()