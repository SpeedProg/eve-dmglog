'''
Created on 30.12.2015

@author: SpeedProg
'''
from eveplot.gamelog.GameLogReader import GameLog

if __name__ == '__main__':
    gamelog = GameLog(r"C:\Users\SpeedProg\Documents\EVE\logs\Gamelogs")
    gamelog.load_data_from_logs()
    gamelog.show_graph("Bruce Warhead")
    
    