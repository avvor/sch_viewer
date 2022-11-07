from datetime import datetime
from operator import ne
import os
import shutil
from keywords import *
import pandas as pd
import networkx as nx

__version__ = '0.1'

class tNavigatorModel(object):
    '''Класс tNavigatorModel: предоставляет свойства и методы для редактирования модели.
    Внутренне представлен в виде словаря { datetime: list of tNavigatorKeyword }
    start: datetime = None - стартовая дата модели. Все последующие даты должны быть больше чем она
    keywords_list: list of tNavigatorKeyword = [] - список ключевых слов, из которых собрается модель
    basepath: str = None - путь к файлу с ключевым словом SCHEDULE'''
    def __init__(self, start: datetime = None, keywords_list: list = [], basepath: str = None, schedule_path: str=None) -> None:
        self.__start = start
        self.__sch_data = dict()
        self.__basepath = basepath
        self.__schedule_path = schedule_path if schedule_path!=None else basepath
       
        # список файлов, ссылки на которые встречаются более 1 раза
        self.immutable_files={}

        self.schedule_kw = tNavigatorKeyword('SCHEDULE')
        self.schedule_kw.add_line('SCHEDULE')
        self.end_kw = tNavigatorKeyword('END')
        self.end_kw.add_line('END')

        date = self.__start
        for kw in keywords_list:
            if kw.name == 'SCHEDULE':
                self.schedule_kw = kw
            elif kw.name == 'END':
                self.end_kw = kw
            else:
                if kw.name == 'DATES': 
                    date = kw.get_value()
                if kw.name == 'TSTEP': 
                    date = date + kw.get_value()
                self.add_keyword(date, kw, add_date_kw=False)
        self.__source_sch = self.schedule_data.copy()
        

    @property
    def model_name(self):
        if self.__basepath!=None:
            file=os.path.basename(self.__basepath)
            return os.path.splitext(file)[0]
        else:
            return None

    @property
    def model_dirname(self):
        if self.__basepath!=None:
            dir=os.path.dirname(self.__basepath)
            if dir=='':
                return os.getcwd()
        else:
            return os.getcwd()

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

    @property
    def source_sch(self):
        '''Исходные данные SCHEDULE секции в виде словаря (неизмененная версия)'''
        return self.__source_sch
        
    @property
    def start(self):
        '''Стартовая дата модели'''
        return self.__start

    @start.setter
    def start(self, start):      
        '''Стартовая дата модели'''
        self.__start = start

    def add_immutable_file(self, path):
        if path in self.immutable_files:
            self.immutable_files[path]=self.immutable_files[path]+1
        else:
            self.immutable_files[path]=2
        for kw in [x for x in self.find_keywords() if x.include_path==path]:
            kw.immutable = True

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
                
                # проверяем втречалось ли INCLUDE с таким путем, если да, то этот файл изменять нельзя
                if keyword.name == 'INCLUDE':
                    val=keyword.get_value()
                    same_includes = [x for x in self.find_keywords(keyword='INCLUDE') if x.get_value()==val]
                    n = len(same_includes)
                    if n>0: 
                        self.add_immutable_file(val)
                        # TODO раскомментировать, если нужно выводить повторяющиеся ссылки
                        # print(f'{keyword.name} со ссылкой на файл {val} добавлена {n+1} раз(а)')
                # TODO раскомментировать строки ниже если нужно выводить ЛОГ, при повторном добавлении ключевого слова в дату
                # else:
                #     n = len(self.find_keywords(date, keyword.name))
                #     if n>0: 
                #         print(f'Для даты {date} ключевое слово {keyword.name} добавлено {n+1} раз(а)')
               
                keyword.immutable = keyword.include_path in self.immutable_files
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

    def build_include_graph(self):
        graph = nx.DiGraph()
        inc_keywords = self.find_keywords(keyword='INCLUDE')
        for kw in inc_keywords:
            inc_value = kw.get_value()
            graph.add_node(kw.include_path)
            graph.add_node(inc_value)
            graph.add_edge(kw.include_path, inc_value)
        return graph
 
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
                if not item.immutable:
                    self.schedule_data[date].remove(item)
                else:
                    print(f'Ключевое слово {item} не было удалено, так как находится в файле на который несколько ссылок')
            if len(self.schedule_data[date]) == 0:
                self.schedule_data.pop(date)
            return [x for x in deleted if not x.immutable]

            
    def find_keywords(self, date: datetime = None, keyword: str = None, comment: str = None) -> list:
        '''Найти ключевые слова по заданным параметрам (вызов без параметров вернет ВСЕ ключевые слова списком)
        date: datetime = None - дата
        keyword: str = None - название ключевого слова
        comment: str = None - коментарий ключевого слова (без --)'''
        def find(keywords, keyword, comment):
            if keyword == None and comment == None:
                return keywords
            else:
                return [x for x in keywords if (keyword == None or x.name == keyword) and (comment == None or x.get_comment() == comment)] 
        if date == None:
            keywords=[]
            for date, kw in sorted(self.schedule_data.items()): 
                keywords = keywords + find(kw, keyword, comment)
            return keywords
        elif date in self.schedule_data:
            return find(self.schedule_data[date], keyword, comment)
        else: return []
               
    def __str__(self):
        return f"START: {self.start}\nКол-во дат: {len(self.schedule_data)}\nКол-во ключевых слов: {len(self.find_keywords())}"



    def get_changed_files(self) -> dict:
        src_files = self.__get_files(self.source_sch)
        dest_files = self.__get_files(self.schedule_data)
        changed_files = {}
        # выбираем все файл, в которых есть изменения и пользовательские файлы (пока со старыми именами)
        for key, value in dest_files.items():
            if key not in self.immutable_files:
                if key not in src_files or key.upper().startswith('USER'):
                # if key not in src_files:
                    changed_files[key] = value
                elif src_files[key] != value:
                    changed_files[key] = value
        return changed_files

    def __generate_new_file_names(self, new_mname):
        def get_new_name(name):
            if f.startswith('USER'):
                return name.replace(self.model_name, new_mname)
            else:
                f=os.path.splitext(name)
                new_file=f[0]+"_"+new_mname
                if len(f)>1: 
                    new_file+=f[1]
                return new_file 
        # получили файлы в которых изменялись ключевые слова
        changed_files = self.get_changed_files()
        # получили граф инклюдов (для дальнейшего вычисления путей)
        inc_graph = self.build_include_graph()
        # для всех файлов с изменениями меняем имена
        fnames={}
        for key in changed_files:
            includes=sum(nx.all_simple_paths(inc_graph, '/', key), [])
            for f in includes:
                if f!='/' and f not in fnames:
                    fnames[f]=get_new_name(f)
        return fnames

    def save_as(self, new_name:str, makebackup: bool=False):
        # копируем модель во временную переменую 
        temp=self.schedule_data.copy()
        fnames=self.__generate_new_file_names(new_name)
        # изменяем все ссылки на ключевые слова
        inc_kw = self.find_keywords(keyword='INCLUDE')
        for inc in inc_kw:
            name = inc.get_value()
            if name in fnames:
                inc.set_value(fnames[name])
        # получаем новые измененные файлы, именно их мы будем пересохранять
        changed_files = self.get_changed_files()
        now = datetime.now().strftime("%Y%m%d%H%M%S")
        for file, content in changed_files.items():
            if file == '/':
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
                src_file=os.path.join(self.model_dirname, file)
                if makebackup:
                    shutil.copyfile(src_file, f'{src_file}.{now}.back')
                output_file= os.path.normpath(os.path.join(self.model_dirname, fnames[file]))
                with open(output_file, 'w', encoding='utf-8') as f:
                    #самый первый файл, где должна быть секция schedule, дописываем ключевые слова
                    if file == '/': 
                        content = self.schedule_kw.body + content + self.end_kw.body
                    f.writelines(content)


        self.schedule_data=temp

    def __get_files(self, data):
        files = dict() # {имя файла: содержание файла}
        for date, keywords in sorted(data.items()): 
            for kw in keywords:          
                if kw.include_path not in files:
                    files[kw.include_path] = []
                files[kw.include_path] += kw.body 
        return files

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
                note='неизменяемое' if val.immutable else ''
                if len(val.get_body_text())>32767:
                    note='ключевое слово > 32767 символов'
                list.append({'date': key, 'keyword': val.name, 'body': val.get_body_text(), 'include': val.include_path, 'note': note})
                # list.append({'date': key, 'keyword': val.name, 'body': val.get_body_text(), 'include': val.include_path})
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
        df: pd.DataFrame - датафреймс данными. Должен содержать колонки ['date', 'keyword', 'body', 'include', 'note']''' 
        for i, row in df.iterrows():
            tNav_kw_class = tNavigatorModel.get_keyword_class(row['keyword'])
            inc = row['include']
            if not isinstance(inc, str): inc = ''
            body = row['body']
            if not isinstance(body, str): body = ''
            kw = tNav_kw_class(row['keyword'], inc)
            kw.set_body_text(body)
            # kw.immutable = row['immutable']
            self.add_keyword(row['date'].to_pydatetime(), kw)
     

    def read_from_excel(self, path: str, append: bool=False):
        '''Считать модель/ключевые слова из MS Excel
        path: str - путь к файлу MS Excel. Эксель должен содержать колонки ['date', 'keyword', 'body', 'include', 'note'], а лучше быть предварительно создан с помощью этого модуля
        append: bool=False -  True: добавлять считанные ключевые слова в существующую модель, False: перезаписать модель'''
        # df = pd.read_excel(path, usecols=['date', 'keyword', 'body', 'include', 'immutable']) 
        df = pd.read_excel(path, usecols=['date', 'keyword', 'body', 'include']) 
        if append:
            self.add_keywords_from_df(df)
        else:
            self.from_dataframe(df)


if __name__ == '__main__':
    print(tNavigatorModel.__doc__)
