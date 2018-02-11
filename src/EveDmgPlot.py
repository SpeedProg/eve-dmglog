'''
Created on 30.12.2015

@author: SpeedProg
'''
from datetime import datetime, timezone

from eveplot.gamelog.BasicGameLogReader import BasicGameLog
from eveplot.gamelog.GameLogReader import GameLog
from eveplot.gamelog.collectors.Collectors import DPSCollector, CollectorDamageOut, CollectorMissIn

if __name__ == '__main__':
    gamelog = BasicGameLog(r"C:\Users\<windows_user_name>\Documents\EVE\logs\Gamelogs")
    gamelog.load_data_from_logs()
    # don't try this in a 32bit python with a lot of files, you gonna run out of memory
    # i actually run out of memory on 32bit python even just with load_data_from_logs if I have all my evelogs
    #gamelog.save_to_file(r"logsave.pkl")
    #gamelog.load_from_file(r"logsave.pkl")
    start_date_time = datetime(2017, 6, 1, 21, 56, 0, tzinfo=timezone.utc)
    end_date_time = datetime(2017, 6, 2, 5, 0, 0, tzinfo=timezone.utc)
    gamelog.show_graph_for_collectors([
        DPSCollector("Your Character Name", gamelog.parsedLogFiles, moving_window_size_seconds=20),
        CollectorDamageOut("Your Character Name", gamelog.parsedLogFiles, start_date_time=start_date_time, end_date_time=end_date_time),
        CollectorMissIn("Your Character Name", gamelog.parsedLogFiles),
        # etc... thate is a few more collectors in Collectors.*
    ], aspic=False)
