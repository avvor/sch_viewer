from datetime import datetime
import os
import shutil
from xml.etree.ElementInclude import include
from keywords import *
import pandas as pd

__version__ = '0.1'

class tNavigatorModel(object):
    '''Класс tNavigatorModel: предоставляет свойства и методы для редактирования модели.
    Внутренне представлен в виде словаря { datetime: list of tNavigatorKeyword }
    start: datetime = None - стартовая дата модели. Все последующие даты должны быть больше чем она
    keywords_list: list of tNavigatorKeyword = [] - список ключевых слов, из которых собрается модель
    basepath: str = None - путь к файлу с ключевым словом SCHEDULE'''
    def __init__(self, start: datetime = None, keywords_list: list = [], basepath:str = None) -> None:
        self.__start = start
        self.__sch_data = dict()
        date = start 

        self.schedule_kw = tNavigatorKeyword('SCHEDULE')
        self.schedule_kw.add_line('SCHEDULE')
        self.end_kw = tNavigatorKeyword('END')
        self.end_kw.add_line('END')

        for kw in keywords_list:
            if kw.name == 'SCHEDULE':
                self.schedule_kw = kw
            elif kw.name == 'END':
                self.end_kw = kw
            else:
                if kw.name == 'DATES': 
                    date = kw.get_value()
                # TODO спорный момент, обсудить с Сашей
                if kw.name == 'TSTEP': 
                    date = date + kw.get_value()
                self.add_keyword(date, kw, add_date_kw=False)
        # self.__source_sch = self.schedule_data.copy()
        self.__basepath = basepath

    @staticmethod
    def get_keyword_class(class_name: str):
        '''Получает конкретную реализацию класса tNavigatorKeyword по ключевому слову (оно совпадает с именем класса)
        class_name: str - имя класса/ключевое слово'''
        for subclass in tNavigatorKeyword.__subclasses__():
            if subclass.__name__ == class_name.upper():
                return subclass
        return tNavigatorKeyword

    @property
    def schedule_data(self):
        '''Данные SCHEDULE секции в виде словаря  { datetime : list of tNavigatorKeyword }'''
        return self.__sch_data

    @schedule_data.setter
    def schedule_data(self, sch_data):  
        '''Данные SCHEDULE секции в виде словаря  { datetime : list of tNavigatorKeyword }'''    
        self.__sch_data = sch_data

    # @property
    # def source_sch(self):
    #     '''Исходные данные SCHEDULE секции в виде словаря (неизмененная версия)'''
    #     return self.__source_sch
        
    @property
    def start(self):
        '''Стартовая дата модели'''
        return self.__start

    @start.setter
    def start(self, start):      
        '''Стартовая дата модели'''
        self.__start = start

    def add_keyword(self, date: datetime, keyword: tNavigatorKeyword, add_date_kw: bool = True) -> tNavigatorKeyword:
        '''Добавить ОДНО ключевое слово в модель
        date: datetime - дата
        keyword: tNavigatorKeyword - ключевое слово. Объект класса tNavigatorKeyword должен быть заранее подготовлен
        add_date_kw: bool = True - при добавлении ключевого слова в дату, которой еще нет в модели, сначала добавлять ключевое слово DATES
        replace_empty_include: bool = True - при добавлении ключевого слова с пустым include_path автоматически его определять. Добавляется в самый последний инклюд'''
        if date < self.start:
            raise KeyError (f'Ключевое слово {keyword.name} не может быть добавлено в модель. Дата ключевого слова НЕ должна быть меньше стартовой')
        keyword.__class__ = tNavigatorModel.get_keyword_class(keyword.name)
        if keyword.is_correct():
            if date in self.schedule_data: 
                if keyword.include_path == '' and len(self.schedule_data[date]) > 0:
                    keyword.include_path = self.schedule_data[date][-1].include_path 
                # TODO раскомментировать строки ниже если нужно выводить ЛОГ, при повторном добавлении ключевого слова в дату
                # if keyword.name != 'INCLUDE':
                #     n = len(self.find_keywords(date, keyword.name))
                #     if n>0: 
                #         print(f'Для даты {date} ключевое слово {keyword.name} добавлено {n+1} раз(а)') 
                self.schedule_data[date].append(keyword)
            else: 
                if keyword.include_path == '':
                    prev = [x for x in self.schedule_data.keys() if x < date] 
                    if len(prev) > 0:
                        keyword.include_path = self.schedule_data[prev[-1]][-1].include_path

                if add_date_kw and keyword.name != 'DATES':
                    datekw = DATES(include_path=keyword.include_path)
                    datekw.set_value(date)
                    self.schedule_data[date]=[datekw]
                    self.schedule_data[date].append(keyword)
                else:
                    self.schedule_data[date]=[keyword]
            return keyword
        else:
            raise ValueError (f'Ключевое слово {keyword.name} не может быть добавлено в модель. Проверьте корректность значений')

    def delete_keywords(self, date: datetime, keyword: str = None, comment: str = None) -> list:
        '''Удалить ключевые слова по заданным параметрам
        date: datetime - дата
        keyword: str = None - название ключевого слова
        comment: str = None - коментарий ключевого слова (без --)'''
        if keyword == None and comment == None:
            return self.schedule_data.pop(date, [])
        else:
            deleted = self.find_keywords(date, keyword, comment)
            for item in deleted:
                self.schedule_data[date].remove(item)
            if len(self.schedule_data[date]) == 0:
                self.schedule_data.pop(date)
            return deleted

            
    def find_keywords(self, date: datetime, keyword: str = None, comment: str = None) -> list:
        '''Найти ключевые слова по заданным параметрам
        date: datetime - дата
        keyword: str = None - название ключевого слова
        comment: str = None - коментарий ключевого слова (без --)'''
        if date in self.schedule_data:
            keywords = self.schedule_data[date] 
            if keyword == None and comment == None:
                return keywords
            else:
                return [x for x in keywords if (keyword == None or x.name == keyword) and (comment == None or x.get_comment() == comment)] 
        else: 
            return []
               


    def __str__(self):
        return f"Кол-во: {len(self.schedule_data)}; START: {self.start}"

    

    def save_as(self, path: str, makebackup: bool=False):
        '''Сохранить модель в новом месте. Указывается только путь к файлу *.data
        path: str - путь к файлу
        makebackup: bool=False - сохранять копии старых файлов (к исходным файлам будет дописано расширение .back)'''
        files = dict() # {имя файла: содержание файла}
        inc_path = ''
        for date, ketwords in sorted(self.schedule_data.items()): 
            for kw in ketwords:          
                if kw.include_path not in files:
                    files[kw.include_path] = []
                files[kw.include_path] += kw.body 
                  

        for file, content in files.items():
            src_file = ''
            if self.__basepath != None:
                src_file = os.path.normpath(os.path.join(os.path.dirname(self.__basepath), file)) if file != '/' else self.__basepath
            
            # делаем бекап файла
            if makebackup and self.__basepath != None:
                shutil.copyfile(src_file, src_file + '.back')

            output_file =  os.path.normpath(os.path.join(os.path.dirname(path), file)) if file != '/' else path

            if not os.path.exists(os.path.dirname(output_file)):
                os.makedirs(os.path.dirname(output_file))
            
            # для файла, где прописана секция SCHEDULE, нужно сохранить основное содежание файла, заменить только секцию SCHEDULE
            if file == '/' and self.__basepath != None:                
                content = self.schedule_kw.body + content  + self.end_kw.body                
                #читаем исходный файл и находим индексы ключевых слов SCHEDULE и END 
                with open(src_file, 'r', encoding='utf-8') as file:
                    lines = file.readlines()
                start_i = -1
                end_i = -1
                for i, line in enumerate(lines):
                    if re.match(r"(?i)^\s*SCHEDULE", line): start_i = i
                    # если встречаем уже встретили SCHEDULE и встречает END, то запоминаем индекс строки    
                    if re.match(r"(?i)^\s*END", line) and start_i >=0: end_i = i

                with open(output_file, 'w', encoding='utf-8') as f:
                    f.writelines(lines[:start_i])
                    f.writelines(content)
                    if end_i>=0 and len(lines) > end_i+1:
                        f.writelines(lines[end_i+1:])
            else:
                # для всех остальных, или если не указан базовый файл (напимер, если модель была считана из excel)
                with open(output_file, 'w', encoding='utf-8') as f:
                    #самый первый файл, где должна быть секция schedule, дописываем ключевые слова
                    if file == '/': 
                        content = self.schedule_kw.body + content + self.end_kw.body
                    f.writelines(content)


    def save(self, makebackup: bool=True):
        '''Сохранить изменения в модели. Доступно только для моделей сгенерированных с помощью класса tNavigatorModelParser
        makebackup: bool=False - сохранять копии старых файлов (к исходным файлам будет дописано расширение .back)'''
        if self.__basepath != None:
            self.save_as(self.__basepath, makebackup)
        else:
            raise FileExistsError

    def to_dataframe(self) -> pd.DataFrame:
        '''Конвертировать модель в pandas.DataFrame'''
        list = []
        for key, value in sorted(self.schedule_data.items()):
            for val in value:
                list.append({'date': key, 'keyword': val.name, 'body': val.get_body_text(), 'include': val.include_path})
        return pd.DataFrame.from_dict(list)	

    
    def from_dataframe(self, df: pd.DataFrame):
        '''Получить модель из pandas.DataFrame
        df: pandas.DataFrame - датафрейм, из которого генерируется модель. Должна содерждать колонки usecols=['date', 'keyword', 'body', 'include']'''
        if df.empty:
            raise ValueError('Нельзя построить модель из пустого DataFrame')        
        self.schedule_data.clear()
        if self.start == None:
            self.start = df['date'].min()
        self.schedule_data[self.start]=[]
        self.add_keywords_from_df(df)
    
    def export_to_excel(self, path: str, df: pd.DataFrame = None):
        '''Экспортировать модель в MS Excel
        path: str - путь к файлу. обязательно указывать расширение *.xlsx
        df: pd.DataFrame = None - при значении None экспортируется вся модель, при других значениям экспортируется переданный df ['date', 'keyword', 'body', 'include']'''
        if df is None:
            df = self.to_dataframe()
        writer = pd.ExcelWriter(path)
        df.to_excel(writer, index=False)
        writer.save()

 
    def add_keywords_from_df(self, df: pd.DataFrame):
        '''Добавить ключевые слова из pandas.DataFrame
        df: pd.DataFrame - датафреймс данными. Должен содержать колонки ['date', 'keyword', 'body', 'include']''' 
        for i, row in df.iterrows():
            tNav_kw_class = tNavigatorModel.get_keyword_class(row['keyword'])
            inc = row['include']
            if not isinstance(inc, str): inc = ''
            body = row['body']
            if not isinstance(body, str): body = ''
            kw = tNav_kw_class(row['keyword'], inc)
            kw.set_body_text(body)
            self.add_keyword(row['date'].to_pydatetime(), kw)
     

    def read_from_excel(self, path: str, append: bool=False):
        '''Считать модель/ключевые слова из MS Excel
        path: str - путь к файлу MS Excel. Эксель должен содержать колонки ['date', 'keyword', 'body', 'include'], а лучше быть предварительно создан с помощью этого модуля
        append: bool=False -  True: добавлять считанные ключевые слова в существующую модель, False: перезаписать модель'''
        df = pd.read_excel(path, usecols=['date', 'keyword', 'body', 'include']) 
        if append:
            self.add_keywords_from_df(df)
        else:
            self.from_dataframe(df)


if __name__ == '__main__':
    print(tNavigatorModel.__doc__)
