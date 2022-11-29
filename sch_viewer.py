from parser import *
from model import *
from keywords import * 
from constants import * 

__version__ = '0.1'

if __name__ == '__main__':
    parser = tNavigatorModelParser()
    path=r'C:\WORK\tNav\tNav_models\initial_model_full\initial_model\NETWORK_DEMO.DATA'
    model=parser.build_model(path)
    print(model)


