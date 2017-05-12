import os
import time
from typing import List

from eveplot.gamelog.GameLogReader import GameLog, StatusThread
from eveplot.gamelog.parsers.LogFileParser import ParsedLogFile


class BasicGameLog(GameLog):
    def __init__(self, log_path: str) -> None:
        '''
        Sets the path of the folder that contains the game logs
        to actually load data call
        load_data_from_logs afterwards if this is the invital parse
        or
        load_from_file if parsed logs where saved with save_to_file
        '''
        self.parsedLogFiles: List[ParsedLogFile] = []
        self.logPath: str = log_path

    def __load_logs(self):
        '''
        Load all the logfiles data into memory
        '''

        files = os.listdir(self.logPath)
        files.sort()

        numfiles = len(files)
        print(F"Found {numfiles} files")
        for idx, filename in enumerate(files):

            filepath = os.path.join(self.logPath, filename)
            # print("reading: ", idx, "/", numfiles, "path:", filepath)
            self.__load(filepath)
            if idx % 500 == 0:
                print((idx, "/", numfiles, "loaded"))

    # @profile
    def __load(self, path):
        data: bytes = open(path, "rb").read()
        self.parsedLogFiles.append(ParsedLogFile(data=data, filepath=path))

    def load_data_from_logs(self):
        start = time.time()
        # start a monitor thread
        self.__load_logs()
        end = time.time()
        print(("Took", (end - start)))