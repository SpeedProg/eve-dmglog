'''
Created on 30.12.2015

@author: SpeedProg
'''
from eveplot.gamelog.GameLogReader import GameLog

if __name__ == '__main__':
    gamelog = GameLog("C:\\Users\\SpeedProg\\Documents\\EVE\\logs", "Bruce Warhead")
    gamelog.showGraph()
    
    