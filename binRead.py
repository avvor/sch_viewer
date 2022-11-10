import struct
import pandas as pd
from typing import List
from datetime import datetime
from os import listdir
from os.path import splitext, basename, dirname, abspath
import re

class MySmspec:
    @staticmethod
    def __byteToInt(b):
        return int.from_bytes(b,'big')

    @staticmethod
    def __byteToStr(b):
        return str(b,'cp1256').strip()

    @staticmethod
    def __byteToREAL(b):
        return struct.unpack('>f', b)[0]

    @staticmethod
    def __byteToDoub(b):
        return struct.unpack('>d', b)[0]

    @staticmethod
    def __Block(file, pos):
        with open(file,"rb") as f:
            f.seek(pos)
            f.read(4)
            fieldName = MySmspec.__byteToStr(f.read(8)) ## имя записи
            cntRec = MySmspec.__byteToInt(f.read(4)) ## количество записей
            typeRec = MySmspec.__byteToStr(f.read(4))## тип записи
            typeBytes = int(typeRec[2:4]) if typeRec[0:2] == "C0" else {'CHAR':8,'INTE':4,'REAL':4,'DOUB':8, 'LOGI':4, 'MESS':0}[typeRec]
            f.read(4)
            data = []
            while len(data) != cntRec:
                cntOfBytes = MySmspec.__byteToInt(f.read(4))
                for i in range(int(cntOfBytes / typeBytes)):
                    data.append(f.read(typeBytes))
                f.read(4)
            if typeRec == "CHAR" or typeRec[0:2] == "C0":
                data = list(map(MySmspec.__byteToStr, data))
            elif typeRec == "INTE":
                data = list(map(MySmspec.__byteToInt, data))
            elif typeRec == "REAL":
                data = list(map(MySmspec.__byteToREAL, data))
            elif typeRec == "DOUB":
                data = list(map(MySmspec.__byteToDoub, data))
            return data, fieldName, f.tell()
        
    def __init__(self, SMSPECFile:str): 
        f = open(SMSPECFile,"rb")
        curPos = 0
        self.__df = pd.DataFrame() 
        while (f.read(4)):
            block, blockName, curPos = self.__Block(SMSPECFile, curPos)
            if (blockName == "KEYWORDS" or blockName == "WGNAMES" or blockName == "UNITS" or blockName == "NUMS"):
                self.__df[blockName] = block
            f.seek(curPos)
        f.close()
        fname = splitext(basename(SMSPECFile))
        fpath = dirname(abspath(SMSPECFile))
        s00 = [fpath + "\\" + file for file in listdir(fpath) if re.fullmatch(fname[0] + r"\.([sS]\d+|UNSMRY|unsmry)", basename(file))]
        i = 0
        for s in s00:
            f = open(s,"rb")
            curPos = 0
            while (f.read(4)):
                block, blockName, curPos = self.__Block(s, curPos)
                if (blockName == "PARAMS"):
                    i += 1
                    self.__df["PARAMS" + str(i)] = block
                f.seek(curPos)
            f.close()
            
    @property
    def get_data(self)->pd.DataFrame:
        return self.__df
    
    def get_main(self, keywords:List[str], wgnames:List[str])->pd.DataFrame: 
        df = self.__df.loc[self.__df["KEYWORDS"].isin(keywords) & self.__df["WGNAMES"].isin(wgnames)]
        return pd.DataFrame(
                    [[df[col][ind] for ind in df.index] for col in df.columns[4:]],
                    columns = ["{0}: {1}({2})".format(df["WGNAMES"][i], df["KEYWORDS"][i], df["UNITS"][i]) for i in df.index],
                    index = self.get_all_dates
                    )

    @property
    def get_all_dates(self)->List[pd.Timestamp]:
        return list(pd.to_datetime(
            [datetime(
                int(self.__df.loc[self.__df["KEYWORDS"]=="YEAR", col]),
                int(self.__df.loc[self.__df["KEYWORDS"]=="MONTH", col]),
                int(self.__df.loc[self.__df["KEYWORDS"]=="DAY", col])
                )
             for col in self.__df.columns[4:]]
            ))

    @property
    def get_all_keywords(self)->List[str]:
        return list(set(self.__df["KEYWORDS"]))
        
    @property
    def get_all_regions(self)->List[str]:
        return ["REGION {0}".format(num) for num in list(set(self.__df.loc[self.__df["KEYWORDS"].str.startswith('R')]["NUMS"]))]
        
    @property
    def get_all_wells(self)->List[str]:
        return list(set(self.__df.loc[self.__df["KEYWORDS"].str.startswith('W') & (self.__df["WGNAMES"] != ":+:+:+:+")]["WGNAMES"]))
        
    @property
    def get_all_aquifers(self)->List[str]:
        return ["AQUIFER {0}".format(num) for num in list(set(self.__df.loc[self.__df["KEYWORDS"].str.startswith('A')]["NUMS"]))]
    
    @property
    def get_all_groups(self)->List[str]:
        return list(set(self.__df.loc[self.__df["KEYWORDS"].str.startswith('G') & (self.__df["WGNAMES"] != ":+:+:+:+")]["WGNAMES"]))
       
if __name__ == "__main__":
    sm = MySmspec(r'model_1\PREDICT_445_11_2VAR_VELO_PICK.SMSPEC') #относительный путь к SMSPEC, файлы типа .S0001 и .UNSMRY подгружаются автоматически из той же папки
    sm1 = MySmspec(r'C:\Users\I_Badryzlov\Desktop\BinReader\model_2\NETWORK_DEMO.SMSPEC') #абсолютный путь также работает
    pd.set_option('display.width', 1000)
    pd.set_option('display.max_columns',10)

    #get_data возвращает датафрейм со всеми данными
    print(sm.get_data) 
    print("="*150)
    
    #get_main возвращает датафрейм пересечения списка KEYWORDS со списком WGNAMES
    print(sm.get_main(['WGPR'], ['1011','1012'])) 
    print("="*150)
    print(sm.get_main(['GPR','GGPR','FGPR'],['FIELD','DKS1','DKS2']))

    dates = sm.get_all_dates #список всех дат
    keywords = sm.get_all_keywords #список всех уникальных KEYWORDS
    regions = sm.get_all_regions #список всех уникальных регионов
    wells = sm.get_all_wells #список всех уникальных скважин
    aquifers = sm.get_all_aquifers #список всех уникальных аквиферов
    groups = sm.get_all_groups #список всех уникальных групп
    
