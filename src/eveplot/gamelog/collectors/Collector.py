from typing import Sequence, Optional, List, Any, Tuple
from datetime import datetime

from eveplot.gamelog.parsers.LogFileParser import ParsedLogFile, ParsedLogMessage


class Collector(object):
    """
    Base collector class that every other collector should inherit from
    implements some basic features and checks that are usefull everywhere
    """

    def __init__(self, user_name: str, log_files: Sequence[ParsedLogFile], test_server: bool = False,
                 live_server: bool = True,
                 start_date_time: Optional[datetime] = None, end_date_time: Optional[datetime] = None):
        self.testServer: bool = test_server
        self.liveServer: bool = live_server
        self.userName: str = user_name
        self.files: Sequence[ParsedLogFile] = log_files
        self.names: Optional[List[str]] = None
        self.values: Optional[List[int]] = None
        self.start: datetime = start_date_time
        self.end: datetime = end_date_time

    def skipfile(self, file):
        if file.get_character() != self.userName:
            return True
        if file.is_testserver and not self.testServer:
            return True
        if not file.is_testserver and not self.liveServer:
            return True

    def skipmsg(self, msg):
        return (self.start is not None and msg.datetime < self.start) or (
        self.end is not None and msg.datetime > self.end)

    def get_msg_list(self, file):
        return file.get_messages_in_order()

    def get_new_value(self, target: ParsedLogMessage, oldval: int):
        """
        Defines how to get a new value from the old value and a target
        should be overriden by child collectors
        default just does return oldval+1
        """
        return oldval + 1

    def get_label_x(self, names, values) -> str:
        return "Undefined"

    def get_key(self, msg: ParsedLogMessage) -> Any:
        """
        Get the key relevant for this collector from a ParsedLogMessage
        should be overriden by child classes
        :param msg: a ParsedLogMessage to get the key from
        :return: Any key
        """
        return msg.data.source

    def get_data(self) -> Tuple[List[str], List[int]]:
        """
        Get collected data from this collector
        Child classes can but don't need to override this
        it is a generic collection function that uses get_label_x get_key and get_new_value to create data
        :return: tuple of y-axis names and x-axis values
        """
        if self.names is not None and self.values is not None:
            return self.names, self.values

        comdata = dict()
        for file in self.files:
            if (self.skipfile(file)):
                continue

            messageList = self.get_msg_list(file)
            for msg in messageList:
                if (self.skipmsg(msg)):
                    continue
                dmg = None
                key = self.get_key(msg)
                if key not in comdata:
                    dmg = self.get_new_value(msg, 0)
                else:
                    dmg = self.get_new_value(msg, comdata[key])
                comdata[key] = dmg

        values = [int(key) for key in list(comdata.values())]
        names = [x for (_, x) in
                 sorted(zip(values, [str(key) for key in list(comdata.keys())]), key=lambda pair: pair[0])]
        values.sort()

        self.names = names
        self.values = values

        return names, values