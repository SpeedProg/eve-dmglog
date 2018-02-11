import io
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
from typing import Optional, List, Dict

import re


class ParsedLogMessage(object):
    """
    Containes parsed data about a log message
    """
    __regLine = re.compile("^\[ (\d{4})\.(\d{2})\.(\d{2}) (\d{2}):(\d{2}):(\d{2}) \] \((\w*)\) (.*)", re.S)

    def __init__(self, text):
        self.type: Optional[str] = None
        self.datetime: Optional[datetime] = None
        self.data: Optional[CombatMessage] = None
        self.parseMessage(text)

    def parseMessage(self, text: str) -> None:
        match_line = self.__regLine.search(text)

        self.datetime = datetime(int(match_line.group(1)), int(match_line.group(2)), int(match_line.group(3)),
                                           int(match_line.group(4)), int(match_line.group(5)), int(match_line.group(6)), 0,
                                            timezone(timedelta(0))
                                            )

        self.type = match_line.group(7)
        msgText = match_line.group(8)
        if self.type == 'combat':
            self.data = CombatMessageParserSimple.parse(msgText)
        else:
            pass
            #print("Type", self.type, " not supported!")

    def __str__(self):
        return self.data

class ParsedLogFile(object):
    __sanshas: Dict[str, None] = {'Deltole Tegmentum': None, 'Renyn Meten': None, 'Tama Cerebellum': None,
                                  'Ostingele Tectum': None, 'Vylade Dien': None, 'Antem Neo': None,
                                  'Eystur Rhomben': None, 'Auga Hypophysis': None,
                                  'True Power Mobile Headquarters': None, 'Outuni Mesen': None, 'Mara Paleo': None,
                                  'Yulai Crus Cerebi': None, 'Romi Thalamus': None, 'Intaki Colliculus': None,
                                  'Uitra Telen': None, 'Schmaeel Medulla': None, 'Arnon Epithalamus': None,
                                  'Sansha\'s Nation Commander': None, 'Sansha Battletower': None}
    "Dict containing all the rats that we should pay attention too"
    __firstLine: str = "-"
    __secondLine: str = "  Gamelog"
    __thridLine: str = "  Listener:"
    __forthLine: str = "  Session Started:"
    __fifthLine: str = "-"
    __msg_start: str = "[ "
    __re_start_time = re.compile("^ {2,2}Session Started: (\d{4})\.(\d{2})\.(\d{2}) (\d{2}):(\d{2}):(\d{2})\r$")
    __re_listener = re.compile("^ {2,2}Listener: (.*)\r$")

    def __init__(self, filepath: str, data: bytes, ignore_none_incursion: bool = True) -> None:
        print(("reading", filepath))
        self.__messages: List[ParsedLogMessage] = []
        self.__status: int = -1
        self.__start_datetime: Optional[datetime] = None
        self.__listener: Optional[str] = None
        self.__filepath: str = filepath
        self.__status = self.__readFile(data)
        print(f"Status {self.__status}")
        self.is_testserver: bool = False
        self.ignore_none_incursion = ignore_none_incursion

    def __readFile(self, data: bytes) -> int:
        """
        Returns __status: 0 = ok, 2 file useless, 1 file invalid
        """
        #file = data.replace(b"\xff\xfe", b"").decode("utf_8")
        file = data.decode("utf_8")
        file = io.StringIO(file)

        current_line = file.readline()
        '''
        Check first line
        '''
        if not "-------" in current_line:
            print(f"startline>>{current_line}<< does not start with >>{self.__firstLine}<<")
            return 1

        current_line = file.readline()
        if not current_line.startswith(self.__secondLine):
            print("typeline>>"+current_line+"<<")
            return 1;

        current_line = file.readline()
        if not current_line.startswith(self.__thridLine):
            # #print("listener>>"+current_line+"<<")
            return 2;
        else:  # extracting character name of the listener
            m = self.__re_listener.match(current_line)
            self.__listener = m.group(1)

        current_line = file.readline()
        if not current_line.startswith(self.__forthLine):
            # #print("session>>"+current_line+"<<")
            return 2;
        else:
            # parse the session start
            m = self.__re_start_time.match(current_line)
            if (m != None):
                self.__start_datetime = datetime(
                    int(m.group(1)), int(m.group(2)), int(m.group(3)),
                    int(m.group(4)), int(m.group(5)), int(m.group(6)), 0,
                    timezone(timedelta(0))
                )

        current_line = file.readline()
        if not current_line.startswith(self.__fifthLine):
            # print("endline>>"+current_line+"<<")
            return 2
        print("Parsed Header, starting with message parsing")
        msg: str = self.__getNextMessage(file)
        if '<h4> Available systems</h4>' in msg:
            self.is_testserver = True
        while msg != '':
            #           print("msg>", msg)
            parsedMessage: ParsedLogMessage = ParsedLogMessage(msg)
            if parsedMessage.data is not None:  # it has a supported type
                # if (parsedMessage.data.target == 'self' and parsedMessage.data.source in self.__sanshas) or parsedMessage.data.target in self.__sanshas:
                self.__addMessage(parsedMessage)

            msg = self.__getNextMessage(file)
            if msg == '':
                print("We are done")
        return 0

    def __getNextMessage(self, file) -> str:
        msg = ""
        line = file.readline()
        #        #print("check msg start:", line)
        if not line.startswith(self.__msg_start):
            #            print('not msg start')
            return ""
        msg += line
        #        #print("start msg>", line)
        '''
        If we land here this line was the msg start
        Now we need to get the current position.
        Read the next line,
        Check for a new message start,
        New Message -> Rewind and return our msg
        No New Message -> Append line to our msg and check next line
        '''
        last_pos = file.tell()
        #        #print(last_pos)
        line = file.readline()
        while line != '' and not line.startswith(self.__msg_start):
            #            #print("next line>", line)
            msg += line
            #            #print(last_pos)
            last_pos = file.tell()
            line = file.readline()

        if line != '' and line.startswith(self.__msg_start):
            #            #print("go back a position to", last_pos)
            file.seek(last_pos)

        # print("Msg", msg)
        return msg

    def __addMessage(self, msg: ParsedLogMessage) -> None:
        # print("Adding to LogFile", msg.type, msg)
        self.__messages.append(msg)  # add message by order

    def print_messages_by_type(self, msg_type: str) -> None:
        msgSByType = self.get_messages_by_type()
        if msg_type in msgSByType:
            for msg in msgSByType[msg_type]:
                print(msg)
                pass
        else:
            print(("No messages of this msg_type=" + msg_type))
            pass

    def get_messages_by_type(self, msg_type=None):
        # sort them into types
        messagesByType = dict()
        if (msg_type == None):
            # sort them all in
            for msg in self.__messages:
                if msg.type not in messagesByType:
                    messagesByType[msg.type] = []
                messagesByType[msg.type].append(msg)
            # done sorting them all in
            return messagesByType

        # else only sort those in that are of this type
        messages_for_type = []
        for msg in self.__messages:
            if msg.type == msg_type:
                messages_for_type.append(msg)

        return messages_for_type

    def get_status(self):
        return self.__status

    def get_character(self):
        return self.__listener

    def get_filepath(self):
        return self.__filepath

    def get_messages_in_order(self):
        return self.__messages


class CombatMessageParserHTML(HTMLParser):
    def __init__(self, *args, **kwargs):
        super(CombatMessageParserHTML, self).__init__(*args, **kwargs)
        self.line = 0
        self.type = None
        self.effect = None
        self.direction = None
        self.source = None
        self.target = None
        self.__re_dmg = re.compile("^\s*(\d*)$")

    def handle_starttag(self, tag, attrs):
        ##print("Encountered a start tag:", tag, attrs)
        pass

    def handle_endtag(self, tag):
        ##print("Encountered an end tag :", tag)
        pass

    # @profile
    def handle_data(self, data):
        #        #print("Encountered some data  :", data)
        self.line += 1
        if self.line == 1:
            '''
            Find the combat type
            '''
            # if it is a number it is a dmg msg
            m = self.__re_dmg.match(data)
            if m != None:
                self.type = 'dmg'
                self.effect = int(m.group(1))
            else:
                # check for warp scramble
                self.type = 'ewar'
                self.effect = data

        elif self.line == 3:
            self.direction = data

        elif self.line == 5:
            self.source = data

        elif self.line == 8:
            self.target = data

    def combat_reset(self):
        self.line = 0
        self.type = None

    def getType(self):
        return self.type

    def getEffect(self):
        return self.effect

    def getDirection(self):
        return self.direction

    def getSource(self):
        return self.source

    def getTarget(self):
        return self.target


class CombatMessage(object):
    """
    Contains data about a single combat message
    """

    def __init__(self) -> None:
        self.type: Optional[str] = None
        self.effect: Optional[str] = None  # "Warp scramble attempt" | ... other dynamic values parsed from msg
        self.direction: Optional[str] = None  # "from" | "to"
        self.source: Optional[str] = None  # name of the guy doing the combat action
        self.target: Optional[str] = None  # name of the guy that is target of the combat action
        self.weapon: Optional[str] = None  # name of the weapon system used e.g. "Gecko"
        self.quality: Optional[str] = None  # name of hit quality e.g. "Smashes"

    def __repr__(self):
        sb = []
        for key in self.__dict__:
            sb.append("{key}={value}".format(key=key, value=self.__dict__[key]))

        return ', '.join(sb)


class CombatMessageParserSimple(object):
    __re_dmg = re.compile("^\s*(\d*)$")
    __re_scram = re.compile(
        "<color=0xffffffff><b>(.*)</b> <color=0x77ffffff><font size=10>from</font> <color=0xffffffff><b>(.*)</b> <color=0x77ffffff><font size=10>to <b><color=0xffffffff></font>(.*)\r")
    __re_dmg_in = re.compile(
        "<color=0xffcc0000><b>(\d*)</b> <color=0x77ffffff><font size=10>from</font> <b><color=0xffffffff>(.*)</b><font size=10><color=0x77ffffff>(.*)\r")
    __re_miss_in = re.compile("(.*) misses you completely\r")
    __re_dmg_out = re.compile(
        "<color=0xff00ffff><b>(?P<dmg>.*)</b> <color=0x77ffffff><font size=10>to</font> <b><color=0xffffffff>(?P<target>.*)</b><font size=10><color=0x77ffffff> - (?P<weapon>.*) - (?P<quality>.*)\r")
    __re_miss_group = re.compile("Your group of (.*) misses (.*) completely - (.*)\r")
    __re_miss_drone = re.compile("Your (.*) misses (.*) completely - (.*)\r")

    @staticmethod
    def parse(txt) -> Optional[CombatMessage]:
        msg = CombatMessage()
        groups = CombatMessageParserSimple.__re_scram.match(txt)
        if groups is not None:
            msg.type = "ewar"
            msg.effect = "Warp scramble attempt"
            msg.direction = "from"
            msg.source = groups.group(2)
            msg.target = groups.group(3)
            if msg.target == 'you!':
                msg.target = 'self'
            msg.weapon = None
            msg.quality = None
            return msg

        groups = CombatMessageParserSimple.__re_dmg_in.match(txt)
        if groups is not None:
            msg.type = "dmg"
            msg.effect = int(groups.group(1))
            msg.direction = "from"
            msg.source = groups.group(2)
            msg.target = "self"
            msg.weapon = None
            msg.quality = None
            return msg

        groups = CombatMessageParserSimple.__re_miss_in.match(txt)
        if groups is not None:
            msg.type = "miss"
            msg.effect = None
            msg.direction = "from"
            msg.source = groups.group(1)
            msg.target = "self"
            msg.weapon = None
            msg.quality = None
            return msg

        groups = CombatMessageParserSimple.__re_dmg_out.match(txt)
        if groups is not None:
            msg.type = "dmg"
            msg.effect = int(groups.group('dmg'))
            msg.direction = "to"
            msg.source = "self"
            msg.target = groups.group('target')
            msg.weapon = groups.group('weapon')
            msg.quality = groups.group('quality')
            return msg

        groups = CombatMessageParserSimple.__re_miss_group.match(txt)
        if groups is not None:
            msg.type = "miss"
            msg.effect = None
            msg.direction = "to"
            msg.source = groups.group(1)
            msg.target = groups.group(2)
            msg.weapon = None
            msg.quality = None
            return msg

        groups = CombatMessageParserSimple.__re_miss_drone.match(txt)
        if groups is not None:
            msg.type = "miss drone"
            msg.effect = 1
            msg.source = groups.group(1)
            msg.target = groups.group(2)
            msg.direction = "to"
            msg.weapon = None
            msg.quality = None
            return msg

        return None