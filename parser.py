from .model import tNavigatorModel
from .keywords import *
from . import tnavconstants as tnav

from chardet import detect
from os import listdir
from os.path import basename, splitext, dirname, join, normpath, exists, relpath, isfile
from typing import List, Dict

__version__ = '0.1.1'
 
class ScheduleNotFoundError(Exception):
	def __init__(self):
		self.message = 'Schedule not found'

class tNavigatorModelParser(object):
    '''Класс tNavigatorModelParser: Позволяет парсить данные их файлов ГДМ
    basepath: str полный путь к главному файлу модели (*.data)'''
    def __init__(self) -> None:
        self.basepath = None
        self.duplicate_links=[]
        self.use_pool = False
        self.files={}

    @staticmethod
    def read_lines(path: str) -> List[str]:
        '''Прочитать значения из файла
        path: str - путь к файлу'''
        if exists(path):
            try:
                with open (path, 'r',  encoding='utf-8') as file:
                    lines = file.readlines()
                return lines
            except UnicodeDecodeError:
                # открываем и пересохраняем файл
                print(f'Возникла UnicodeDecodeError файл {path} пробуем пересохранить и считать еще раз')
                with open (path, 'rb') as file:
                    dytes_data = file.read()
                    meta = detect(dytes_data)
                    data = dytes_data.decode(meta['encoding']).replace('\r\n','\n')

                with open(path, 'w', encoding='utf-8') as file:
                    file.write(data)

                return tNavigatorModelParser.read_lines(path)
        else:
            return []
        
    def find_schedule_section(self, path: str) -> Dict[str, List[str]]:
        '''Рекурсивный поиск секции SCHEDULE. Возвращает набор строк секции 
        (используется для определения стартовой даты и файла, в котором начинается секция SCHEDULE)
        path: str - путь к файлу, в котором осуществляется поиск'''
        result = dict()
        lines = tNavigatorModelParser.read_lines(path)
        if len(lines) > 0:
            find_start = False
            find_include = False
            inc_list=[]
            start_i=-1
            end_i=-1
            for i, line in enumerate(lines):
                # ищем стартовую дату (она одна, в файле с расширением *.DATA)
                if re.match(r"(?i)(^\s*START)|(^\s*RESTARTDATE)", line):
                    find_start = True                
                if find_start and re.match(tnav.re_pattern['DATES'], line):
                    start = re.search(tnav.re_pattern['DATES'], line)
                    result['start'] = datetime(int(start.group('year')), 
                                        tnav.months_dict[start.group('month').upper()], 
                                        int(start.group('day')))
                    result['file_with_start_date'] = path
                    find_start = False
                
                # ищем секцию SCHEDULE, она одна, но может быть как в первом файле, так и в INCLUDE любой вложенности (НО ТОЛЬКО ОДИН РАЗ)
                if re.match(r"(?i)^\s*INCLUDE", line): 
                    find_include = True
                # запоминаем встречающиеся инклюды, на случай, если секции SCHEDULE не будет в файле *.DATA
                if find_include and re.match(tnav.re_pattern['INCLUDE'], line):
                    value = re.search(tnav.re_pattern['INCLUDE'], line).group('path')
                    inc_list.append(value)
                    find_include = False

                # если встречаем SCHEDULE, то запоминаем индекс строки
                if re.match(r"(?i)^\s*SCHEDULE", line): start_i = i

                # если встречаем уже встретили SCHEDULE и встречает END, то запоминаем индекс строки    
                if re.match(r"(?i)^\s*END", line) and start_i >=0: end_i = i
                
            if start_i>=0:
                    result['file_with_schedule_section'] = path
                    result['schedule_lines'] = lines[start_i:] if end_i<0 else lines[start_i:end_i+1] 
                    return result    

            # если не встретилась секция в первом фйале, то рекурсивно проходим по всеи INCLUDE, пока не встретиться секция SCHEDULE
            for inc in inc_list:
                sch_lines = self.find_schedule_section(normpath(join(dirname(self.basepath), inc)))
                if sch_lines != None:
                    if 'schedule_lines' in sch_lines:
                        for key in sch_lines.keys():
                            result[key]=sch_lines[key]
                        return result
        # если совсем ничего не найдено - возвращаем пустой список
        return None

    def build_model(self, basepath:str) -> tNavigatorModel:
        '''Строит модель из  SCHEDULE секции указанного в конструкторе файла
        Возвращает класс модели tNavigatorModel
        basepath:str - путь к файлу *.DATA'''
        self.basepath = normpath(basepath)
        schedule = self.find_schedule_section(basepath)
        self.files={}
        if schedule == None:
            raise ScheduleNotFoundError 
        kwlist = self.parse_schedule_section(schedule['schedule_lines']) 
        model = tNavigatorModel(schedule['start'], kwlist, basepath=basepath, schedule_path=schedule['file_with_schedule_section'])  
        return model         
    
    def __get_keywords_list(self, lines: List[str], path: str, abs_path:str, keywords_list: list, index: int = 0, use_recursion:bool = True) -> List[tNavigatorKeyword]:
        '''Получает список ключевых слов. При use_recursion = True Рекурсивно вызывается для секций INCLUDE
        lines: list - список строк, которые парсятся
        path: str - относительный пусть файлу, из которого эти строки ('' -  для первого файла)
        keywords_list: list of tNavigatorKeyword - список объектов ключевых слов'''
        if keywords_list == None:
            keywords_list = []
        tNav_kw = None
        for line in lines:
            re_kw = re.search(tnav.re_pattern['keyword'], line)
            if re_kw:
                kw = re_kw.group('keyword').upper()
                if kw in tnav.keywords:
                    tNav_kw_class = tNavigatorModel.get_keyword_class(kw)
                    tNav_kw = tNav_kw_class(kw, path)
                    # keywords_list.append(tNav_kw)
                    keywords_list.insert(index, tNav_kw)
                    index += 1 
            if tNav_kw != None:
                tNav_kw.add_line(line)

        # проходим по всем инклюдам и рекурсивно выполняем те же действия       
        if use_recursion:
            inc_list = [x for x in keywords_list if x.name == 'INCLUDE' and x.include_path == path]
            for inc in inc_list:
                index = keywords_list.index(inc)
                value = inc.get_value()
                if value != None:
                    inc_path_base = normpath(join(dirname(self.basepath), value))
                    inc_path_curdir = normpath(join(dirname(abs_path), value))
                    inc_file = inc_path_curdir if exists(inc_path_curdir) else inc_path_base
                    if inc_file not in self.files:
                        lines = tNavigatorModelParser.read_lines(inc_file)
                        self.files[inc_file]=lines
                    else:
                        lines = self.files[inc_file]
                    self.__get_keywords_list(lines, value, inc_file, keywords_list, index+1)

    def parse_schedule_section(self, schedule_lines: List[str]) -> List[tNavigatorKeyword]:
        '''Парсинг SCHEDULE секции. Возвращает список объектов ключевых слов lisf of tNavigatorKeyword'''
        keywords_list = []
        self.files[self.basepath] = schedule_lines
        self.__get_keywords_list(schedule_lines, '/', self.basepath, keywords_list, use_recursion=True)
        basedir = dirname(self.basepath)
        modelname = splitext(basename(self.basepath))[0]
        userpath = join(basedir, 'USER')
        if exists(userpath):            
            for item in listdir(userpath):
                userfile = join(userpath, item)
                if isfile(userfile) and item.startswith(f'{modelname}_'): 
                    if userfile not in self.files:
                        lines = tNavigatorModelParser.read_lines(userfile)
                        self.files = lines
                    else:
                        lines = self.files[userfile]
                    # парсим ТОЛЬКО файл пользователя (НЕ рекурсивно), подразумевая, что там нет INCLUDE
                    self.__get_keywords_list(lines, relpath(userfile, basedir), userfile, keywords_list, use_recursion=False)   
        return keywords_list
    
   
    def get_keywords_list(self, path: str) -> List[tNavigatorKeyword]:
        '''Получает список ключевых слов из файла
        paht:str - путь к файлу из которого необходимо получить ключевые слова'''
        lines =  tNavigatorModelParser.read_lines(path)
        keywords_list = []
        self.__get_keywords_list(lines, '', self.basepath, keywords_list, use_recursion=False)
        return keywords_list

if __name__ == '__main__':
    print(tNavigatorModelParser.__doc__)



        