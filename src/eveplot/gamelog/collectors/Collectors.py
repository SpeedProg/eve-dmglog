import datetime
from typing import List

import numpy as np

from eveplot.gamelog.collectors.Collector import Collector
from eveplot.gamelog.parsers.LogFileParser import ParsedLogMessage


class CollectorDamageIn(Collector):
    def get_key(self, msg):
        return msg.data.source

    def get_msg_list(self, file):
        return file.get_messages_by_type('combat')

    def skipmsg(self, msg):
        return Collector.skipmsg(self, msg) or not (
        msg.data.type == 'dmg' and msg.data.direction == 'from' and msg.data.target == 'self')

    def get_new_value(self, target, oldval):
        return oldval + target.data.effect

    def get_label_x(self, names, values):
        total = 0
        for count in values:
            total += count
        return self.userName + " Received Damge Total = " + str(total)


class CollectorDamageOut(Collector):
    def get_key(self, msg):
        return msg.data.target

    def get_msg_list(self, file):
        return file.get_messages_by_type('combat')

    def skipmsg(self, msg):
        return Collector.skipmsg(self, msg) or not (
        msg.data.type == 'dmg' and msg.data.direction == "to" and msg.data.source == "self")

    def get_new_value(self, target, oldval):
        return oldval + target.data.effect

    def get_label_x(self, names, values):
        total = 0
        for count in values:
            total += count
        return self.userName + " Dealt Damge Total = " + str(total)


class CollectorDamageOutWeapon(Collector):
    def __init__(self, userName, weapon, log_files, testServer=False, liveServer=True, startDateTime=None,
                 endDateTime=None):
        Collector.__init__(self, userName, log_files, testServer, liveServer, startDateTime, endDateTime)
        self.weapon = weapon

    def get_key(self, msg):
        return msg.data.target

    def get_msg_list(self, file):
        return file.get_messages_by_type('combat')

    def skipmsg(self, msg):
        return Collector.skipmsg(self, msg) or not (
        msg.data.type == 'dmg' and msg.data.direction == "to" and msg.data.source == "self" and msg.data.weapon == self.weapon)

    def get_new_value(self, target, oldval):
        return oldval + target.data.effect

    def get_label_x(self, names, values):
        total = 0
        for count in values:
            total += count
        return self.userName + " Dealt Damage with " + self.weapon + " Total = " + str(total)


class CollectorDamageOutWeapons(Collector):
    def __init__(self, userName, weapons, log_files, testServer=False, liveServer=True, startDateTime=None,
                 endDateTime=None):
        Collector.__init__(self, userName, log_files, testServer, liveServer, startDateTime, endDateTime)
        '''takes weapons seperated by | or "all" to allow all weapons '''
        self.weapons = weapons.split('|')

    def get_key(self, msg):
        return msg.data.target

    def get_msg_list(self, file):
        return file.get_messages_by_type('combat')

    def skipmsg(self, msg):
        return Collector.skipmsg(self, msg) or not (
        msg.data.type == 'dmg' and msg.data.direction == "to" and msg.data.source == "self" and (
        "all" in self.weapons or msg.data.weapon in self.weapons))

    def get_new_value(self, target, oldval):
        return oldval + target.data.effect

    def get_label_x(self, names, values):
        total = 0
        for count in values:
            total += count
        return self.userName + " Dealt Damage with " + self.weapon + " Total = " + str(total)


class CollectorMissIn(Collector):
    def get_key(self, msg):
        return msg.data.source

    def get_msg_list(self, file):
        return file.get_messages_by_type('combat')

    def skipmsg(self, msg):
        return Collector.skipmsg(self, msg) or not (
        msg.data.type == 'miss' and msg.data.direction == 'from' and msg.data.target == 'self')

    def get_new_value(self, target, oldval):
        return oldval + 1

    def get_label_x(self, names, values):
        total = 0
        for count in values:
            total += count
        return "Number of Misses On Me Total = " + str(total)


class CollectorMissOut(Collector):
    def get_key(self, msg):
        return msg.data.target

    def get_msg_list(self, file):
        return file.get_messages_by_type('combat')

    def skipmsg(self, msg):
        return Collector.skipmsg(self, msg) or not (
        msg.data.type == 'miss' and msg.data.direction == 'to' and msg.data.source == 'self')

    def get_new_value(self, target, oldval):
        return oldval + 1

    def get_label_x(self, names, values):
        total = 0
        for count in values:
            total += count
        return "Number of Misses By Me Total = " + str(total)


class CollectorEwarOutOthers(Collector):
    def get_key(self, msg):
        return msg.data.source + ' => ' + msg.data.target

    def get_msg_list(self, file):
        return file.get_messages_by_type('combat')

    def skipmsg(self, msg):
        return Collector.skipmsg(self, msg) or not (
        msg.data.type == 'ewar' and msg.data.target != 'self' and msg.data.source != 'self')

    def get_new_value(self, target, oldval):
        return oldval + 1

    def get_label_x(self, names, values):
        total = 0
        for count in values:
            total += count
        return "Ewar attempts done between others total = " + str(total)


class CollectorEwarIn(Collector):
    def get_key(self, msg):
        return msg.data.source

    def get_msg_list(self, file):
        return file.get_messages_by_type('combat')

    def skipmsg(self, msg):
        return Collector.skipmsg(self, msg) or not (msg.data.type == 'ewar' and msg.data.target == 'self')

    def get_new_value(self, target, oldval):
        return oldval + 1

    def get_label_x(self, names, values):
        total = 0
        for count in values:
            total += count
        return "Ewar attempts on me total = " + str(total)


class CollectorEwarOut(Collector):
    def get_key(self, msg):
        return msg.data.target

    def get_msg_list(self, file):
        return file.get_messages_by_type('combat')

    def skipmsg(self, msg):
        return Collector.skipmsg(self, msg) or not (msg.data.type == 'ewar' and msg.data.source == 'self')

    def get_new_value(self, target, oldval):
        return oldval + 1

    def get_label_x(self, names, values):
        total = 0
        for count in values:
            total += count
        return "Ewar attempts by me total = " + str(total)


class DPSCollector(Collector):
    """
    A collector to display DPS graphs
    this is not finished
    """

    def __init__(self, user_name: str, log_files,  test_server=False, live_server=True, start_date_time=None,
                 end_date_time=None, moving_window_size_seconds=20):
        super(DPSCollector, self).__init__(user_name, log_files, test_server, live_server, start_date_time, end_date_time)
        print(f"Gotten {len(self.files)} logfiles")
        self.names = None
        self.values = None
        self.msgStartDate = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone(datetime.timedelta(0)))
        self.msgEndDate = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone(datetime.timedelta(0)))
        self.timewindow = datetime.timedelta(seconds=moving_window_size_seconds)

        # find the min and max date of accepted dmg msgs
        # so we can calculate our x axis from this
        # y will be dps
        for file in self.files:
            if (self.skipfile(file)):
                continue

            messageList = self.getMsgList(file)
            for msg in messageList:
                if self.skipmsg(msg):
                    continue
                if msg.datetime < self.msgStartDate:
                    self.msgStartDate = msg.datetime
                if msg.datetime > self.msgEndDate:
                    self.msgEndDate = msg.datetime
        print(self.msgStartDate)
        print(self.msgEndDate)

    def skipfile(self, file):
        if file.get_character() != self.userName:
            print(f"wrong char {file.get_character()}")
            return True
        if file.is_testserver and not self.testServer:
            print("File is test server")
            return True
        if not file.is_testserver and not self.liveServer:
            return True

    def skipmsg(self, msg):
        return (msg.data.type != "dmg" or (self.start != None and msg.datetime < self.start) or (self.end != None and msg.datetime > self.end))

    def getMsgList(self, file):
        return file.get_messages_in_order()

    def getNewValue(self, target, oldval):
        return oldval + 1

    def get_label_x(self, names, values):
        return "Seconds since first Damage of " + self.userName

    def get_label_y(self, yvalues, xvalues):
        return "Current DPS"

    def is_y_values(self):
        return True

    def get_y_step_size(self, yvalues):
        return int(max(yvalues)/20)

    def get_y_max(self, yvalues):
        return max(yvalues)

    def use_linegraph(self):
        return True

    def get_y_tick_labels(self):
        return np.arange(0, self.get_y_max(self.names), self.get_y_step_size(self.names))

    def getKey(self, msg):
        return msg.data.source

    @staticmethod
    def get_messages_around(point: datetime.datetime, frame: datetime.timedelta, allMessages: List[ParsedLogMessage]) -> List[ParsedLogMessage]:
        foundMsgs: List[ParsedLogMessage] = []
        from_time: datetime.datetime = point-frame
        to_time: datetime.datetime = point+frame
        for msg in allMessages:
            if msg.datetime >= from_time and msg.datetime <= to_time:
                foundMsgs.append(msg)
        return foundMsgs


    def get_data(self):
        if (self.names is not None and self.values is not None):
            return self.names, self.values


        allMessages: List[ParsedLogMessage] = []
        minTime: datetime.datetime = None
        maxTime: datetime.datetime = None

        for file in self.files:
            if (self.skipfile(file)):
                continue
            messageList = self.getMsgList(file)

            for msg in messageList:
                if (self.skipmsg(msg)):
                    continue
                if minTime is None or minTime > msg.datetime:
                    minTime = msg.datetime
                if maxTime is None or maxTime < msg.datetime:
                    maxTime = msg.datetime
                allMessages.append(msg)
        if (maxTime is None or minTime is None):
            print("No messages found for ", self.userName)
            return [], []
        maxSeconds: int = int((maxTime-minTime).total_seconds())
        yvalues = []
        xvalues = []
        for at_second in range(0, maxSeconds, 1):
            point_time = minTime+(datetime.timedelta(seconds=at_second))
            msgs: List[ParsedLogMessage] = DPSCollector.get_messages_around(point_time, self.timewindow, allMessages)
            if len(msgs) > 0:
                dmg = 0
                earliest: datetime.datetime = None
                latest: datetime.datetime = None
                for msg in msgs:
                    if earliest is None or msg.datetime < earliest:
                        earliest = msg.datetime
                    if latest is None or msg.datetime > latest:
                        latest = msg.datetime
                    dmg += msg.data.effect

                dps = (dmg)/20
                # better detect edges of no damage
                if earliest > point_time or latest < point_time:
                    dps = 0
                xvalues.append(at_second)
                yvalues.append(dps)
            else:
                xvalues.append(at_second)
                yvalues.append(0)

        self.names = yvalues
        self.values = xvalues
        return self.names, self.values