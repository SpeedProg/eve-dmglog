from eveplot.gamelog.collectors.Collector import Collector


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


class DPSCollector(object):
    """
    A collector to display DPS graphs
    this is not finished
    """

    def __init__(self, userName: str, logfiles, testServer=False, liveServer=True, startDateTime=None,
                 endDateTime=None):
        self.testServer = testServer
        self.liveServer = liveServer
        self.userName = userName
        self.files = logfiles
        self.names = None
        self.values = None
        self.start = startDateTime
        self.end = endDateTime
        self.msgStartDate = datetime.datetime.utcnow()
        self.msgEndDate = datetime.datetime.utcnow()

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

    def skipfile(self, file):
        if file.get_character() != self.userName:
            return True
        if file.is_testserver and not self.testServer:
            return True
        if not file.is_testserver and not self.liveServer:
            return True

    def skipmsg(self, msg):
        return ((self.start != None and msg.datetime < self.start) or (self.end != None and msg.datetime > self.end))

    def getMsgList(self, file):
        return file.get_messages_in_order()

    def getNewValue(self, target, oldval):
        return oldval + 1

    def getXLabel(self, names, values):
        return "Undefined"

    def getKey(self, msg):
        return msg.data.source

    def getData(self, fromDateTime, toDateTime):
        if (self.names is not None and self.values is not None):
            return self.names, self.values

        comdata = dict()
        for file in self.files:
            if (self.skipfile(file)):
                continue

            messageList = self.getMsgList(file)
            for msg in messageList:
                if (self.skipmsg(msg)):
                    continue

                dmg = None
                key = self.getKey(msg)
                if key not in comdata:
                    dmg = self.getNewValue(msg, 0)
                else:
                    dmg = self.getNewValue(msg, comdata[key])
                comdata[key] = dmg

        values = [int(key) for key in list(comdata.values())]
        names = [x for (_, x) in
                 sorted(zip(values, [str(key) for key in list(comdata.keys())]), key=lambda pair: pair[0])]
        values.sort()

        self.names = names
        self.values = values

        return names, values