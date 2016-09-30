'''
Created on 30.12.2015

@author: SpeedProg
'''

import os
import re
import datetime
from html.parser import HTMLParser
import matplotlib.pyplot as plt
import numpy as np
from profilehooks import profile
import threading
from multiprocessing import JoinableQueue, Process
import io
import time

class GameLog(object):
    '''
    classdocs
    '''
    
    __sanshas = {'Deltole Tegmentum' : None, 'Renyn Meten' : None, 'Tama Cerebellum' : None, 'Ostingele Tectum' : None, 'Vylade Dien' : None, 'Antem Neo' : None, 'Eystur Rhomben' : None, 'Auga Hypophysis' : None, 'True Power Mobile Headquarters' : None, 'Outuni Mesen' : None, 'Mara Paleo' : None, 'Yulai Crus Cerebi' : None, 'Romi Thalamus' : None, 'Intaki Colliculus' : None, 'Uitra Telen' : None, 'Schmaeel Medulla' : None, 'Arnon Epithalamus' : None,
                 'Sansha\'s Nation Commander' : None }
                 
    __an_con_count = 3

    def __init__(self, logPath, charName):
        '''
        Constructor
        '''
        self.__consumer_threads = []

        self.parsedLogFiles = []
        self.rawlogQueue = JoinableQueue(maxsize=100)
        self.parsedLogsQueue = JoinableQueue(maxsize=10)

        self.logPath = os.path.join(logPath, "analyze")
        self.charName = charName
        start = time.time()
        self.initConsumer()
        self.statusThread = StatusThread(self.parsedLogsQueue, self.rawlogQueue)
        self.statusThread.start()
        # start a monitor thread
        self.loadLogs()
        self.stopConsumer()
        end = time.time()
        print("Took", (end-start))

    def initConsumer(self):
        
        for i in range(self.__an_con_count):
            t = LogFileCreatorThread(self.rawlog, self.messageQueue, "dec"+str(i), IncommingSelector())
            t.start()
            self.__consumer_threads.append(t)
            
        t = MessageAddThread(self.messageQueue, self.user)
        t.start()
        self.__consumer_threads.append(t)
        print("All consumer started!")

    def stopConsumer(self):
        self.rawlog.join()
        self.messageQueue.join()
        for _ in range(self.__an_con_count):
            self.rawlog.put(None)
        self.messageQueue.put(None)
        for t in self.__consumer_threads:
            t.join()
        self.statusThread.stop()

    def loadLogs(self):
        '''
        Load all the logfiles data into memory
        '''

        files = os.listdir(self.logPath)
        files.sort()
        ##print(len(files))
        ##print(files)
        numfiles = len(files)
        for idx, filename in enumerate(files):
            
            filepath = os.path.join(self.logPath, filename)
            ##print("opening: ", filepath)
            #print("reading: ", idx, "/", numfiles, "path:", filepath)
            self.load(filepath)
            if idx % 500 == 0:
                print(idx, "/", numfiles, "loaded")
        
            
            ##print("finsished with __status: ", logfile.getStatus())
            '''
            for key in logfile.getTypes():
                #print(key)
            '''
            #self.logfiles.append(logfile)
            #print("appending logfile")
            #print("start analyze")
            #self.addDmgMsg(logfile)
            #print("log file analyzed")


        #for idx, logfile in enumerate(self.logfiles):
        #    print("parsing :", idx, "/", numfiles, "file:", logfile.getFilepath())


        #print(self.user)
        
    #@profile
    def load(self, path):
        data = open(path, "rb").read()
        self.rawlog.put(RawLog(path, data))

    def showGraph(self):
        data = self.user['Bruce Warhead']
        
        filtered_data = dict()
        for shipname in [str(key) for key in self.__sanshas.keys()]:
            if shipname in data:
                filtered_data[shipname] = data[shipname]
        
        data = filtered_data
        
        names = [str(key) for key in data.keys()]
        #print(names)
        ind = np.arange(len(data.values()))

        fig, ax = plt.subplots()
        rects = ax.bar(ind, data.values(), 0.3, color='r')

        ax.set_ylabel("y-l")
        ax.set_xticks(ind+0.3)
        ax.set_xticklabels(names)
    
    
        for rect in rects:
            height = rect.get_height()
            ax.text(rect.get_x() + rect.get_width()/2., 1.05*height,
                    '%d' % int(height),
                    ha='center', va='bottom')
        plt.show()

class LogFileCreatorThread(Process):
    def __init__(self, tasks, results, name, selector):
        Process.__init__(self, daemon=True)
        self.__tasks = tasks
        self.__results = results
        self.__selector = selector
        self.name = name
        self.combat_parser = CombatMessageParserSimple()
        self.__out_dict = dict()

    #@profile
    def run(self):
        while True:
            work = self.__tasks.get()
            if work is None:
                break
            self.__out_dict = dict()
            logfile = self.createLogfile(work)
            self.analyze(logfile)
            self.__tasks.task_done()
            #print(self.name, "decoded")
    
    def createLogfile(self, work):
        file = LogFile(work.filepath, work.data)
        return file
    
    
    def analyze(self, logfile):
        #print(logfile.getMessages('combat'))
        #print(self.name, "analize into", self.__out_dict, "file", logfile.getFilepath())
        combat_parser = self.combat_parser
        combat_msgs = logfile.getMessages('combat')
        #print(self.name, "Combat messages:", len(combat_msgs), "file:", logfile.getFilepath())
        if len(combat_msgs) > 0:
            for msg in combat_msgs:
                #print("parse: ", msg)
                combat_parser.feed(msg)
                msg_parsed = combat_parser.getMsg()
                msg_parsed.username = logfile.getCharacter()
                #print("parsed", msg_parsed)
                self.addToDict(msg_parsed)
                
                #self.__results.put(msg_parsed)
                #print("Put message into final queue")
                combat_parser.combat_reset()
            #print(self.name, "sending out", {logfile.getCharacter(): self.__out_dict})
            self.__results.put({logfile.getCharacter(): self.__out_dict})
    
    
    def addToDict(self, combatmsg):
        if (combatmsg.username == None):
            return
            
        if self.__selector.use(combatmsg):
            name = self.__selector.getName(combatmsg)
            #print(combatmsg.effect, combatmsg.direction, combatmsg.target)
            if name not in self.__out_dict:
                oldDmg = 0
            else:
                oldDmg = self.__out_dict[name]
            self.__out_dict[name] = oldDmg + combatmsg.effect
            #print(self.name, "Changed:", combatmsg.target, self.__out_dict[combatmsg.target])

class OutgoingSelector(object):
    def use(self, target):
        return (target.type == 'dmg' and target.direction == "to" and target.source == "self")

    def getName(self, target):
        return target.target

class IncommingSelector(object):
    def use(self, target):
        return (target.type == 'dmg' and target.direction == "from" and target.target == "self")
    
    def getName(self, target):
        return target.source

class StatusThread(threading.Thread):
    def __init__(self, finishQueue, rawLogQueue):
        threading.Thread.__init__(self, daemon=True)
        self.__finishQueue = finishQueue
        self.__rawLogQueue = rawLogQueue
        self._stop = threading.Event()
        
    def run(self):
        while not self.stopped():
            print("In RawLogQueue:", self.__rawLogQueue.qsize())
            print("In FinishQueue:", self.__finishQueue.qsize())
            time.sleep(1)
    
    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()

class MessageAddThread(threading.Thread):
    def __init__(self, in_dicts, user):
        threading.Thread.__init__(self)
        self.__out_dict = user
        self.__tasks = in_dicts

    def run(self):
        while True:
            work = self.__tasks.get()
            if work is None:
                #print("Final:", self.__out_dict)
                break
            #print("Add to final:", work)
            self.work(work)
            self.__tasks.task_done()
    #@profile
    def work(self, user_dict):
        for user_key in user_dict:
            user_key = str(user_key)
            in_target_data = user_dict[user_key]
            if user_key not in self.__out_dict:
                dest_target_data = dict()
                self.__out_dict[user_key] = dest_target_data
            else:
                dest_target_data = self.__out_dict[user_key]
            
            for target_key in in_target_data:
                target_key = str(target_key)
                if target_key not in dest_target_data:
                    oldDmg = 0
                else:
                    oldDmg = dest_target_data[target_key]
                
                dest_target_data[target_key] = oldDmg + in_target_data[target_key]

class RawLog(object):
    def __init__(self, path, data):
        self.filepath = path
        self.data = data

class LogFile(object):
    __firstLine =   "-"
    __secondLine =  "  Gamelog"
    __thridLine =   "  Listener:"
    __forthLine =   "  Session Started:"
    __fifthLine =   "-"
    __msg_start = "[ "
    _re_start_time = re.compile("^  Session Started: (\d{4})\.(\d{2})\.(\d{2}) (\d{2}):(\d{2}):(\d{2})\r$")
    _re_listener = re.compile("^  Listener: (.*)\r$")

    def __init__(self, filepath, data):
        #print("reading", filepath)
        self.__logdict = dict()
        self.__status = -1
        self.__filepath = ''
        self.__start_datetime = None
        self.__listener = None
        self.__filepath = filepath
        self.__status = self.__readFile(data)

        #print(self)
        #print(self.__logdict)

    def __readFile(self, data):
        '''
        Returns __status: 0 = ok, 2 file useless, 1 file invalid
        '''
        file = data.replace(b"\xff\xfe", b"").decode("utf_8")
        file = io.StringIO(file)

        currentLine = file.readline()
        '''
        Check first line
        '''
        if not currentLine.startswith(self.__firstLine):

            # #print("startline>>"+currentLine+"<<")
            return 1;

        currentLine = file.readline()
        if not currentLine.startswith(self.__secondLine) :
            # #print("typeline>>"+currentLine+"<<")
            return 1;

        currentLine = file.readline()
        if not currentLine.startswith(self.__thridLine):
            # #print("listener>>"+currentLine+"<<")
            return 2;
        else: # extracting character name of the listener
            m = self._re_listener.match(currentLine)
            self.__listener = m.group(1)

        currentLine = file.readline()
        if not currentLine.startswith(self.__forthLine):
            # #print("session>>"+currentLine+"<<")
            return 2;
        else:
            # parse the session start
            m = self._re_start_time.match(currentLine)
            if (m != None):
                self.__start_datetime = datetime.datetime(
                               int(m.group(1)), int(m.group(2)), int(m.group(3)),
                               int(m.group(4)), int(m.group(5)), int(m.group(6)), 0,
                               datetime.timezone(datetime.timedelta(0))
                               )

        currentLine = file.readline()
        if not currentLine.startswith(self.__fifthLine):
            # #print("endline>>"+currentLine+"<<")
            return 2;

        ln = 0
        msg = self.__getNextMessage(file)
        while (msg != ''):
#            #print("msg>", msg)
            ln += 1
            self.__addMessage(LogMessage(ln, msg))
            msg = self.__getNextMessage(file)
#            #print("next msg>", msg)

#        #print("log ended>", msg)

        #file.seek(738)
#        #print(file.readline())

        #print("Contained: " + str(len(self.__logdict)) + " messages")
        #attrs = vars(self)
        # {'kids': 0, 'name': 'Dog', 'color': 'Spotted', 'age': 10, 'legs': 2, 'smell': 'Alot'}
        # now dump this in some way or another
        #print(', '.join("%s: %s" % item for item in attrs.items()))
        return 0

    def __getNextMessage(self, file):
        msg = ""
        line = file.readline()
#        #print("check msg start:", line)
        if not line.startswith(self.__msg_start) :
#            #print('not msg start')
            return "";
        msg += line;
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
        while line != '' and not line.startswith(self.__msg_start) :
#            #print("next line>", line)
            msg += line
#            #print(last_pos)
            last_pos = file.tell()
            line = file.readline()

        if line != '' and line.startswith(self.__msg_start):
#            #print("go back a position to", last_pos)
            file.seek(last_pos)

        #print("Msg", msg)
        return msg

    def __addMessage(self, msg):
        #print("Adding to LogFile", msg.type, msg)
        if msg.type not in self.__logdict:
            self.__logdict[msg.type] = []

        self.__logdict[msg.type].append(msg.msg)

    def printMessages(self, msg_type):
        if msg_type in self.__logdict:
            for msg in self.__logdict[msg_type]:
                print(msg)
                pass
        else:
            print("No messages of this msg_type")
            pass

    def getMessages(self, msg_type):
        if (msg_type == None):
            return self.__logdict
        if msg_type in self.__logdict:
            return self.__logdict[msg_type].copy()
        else:
            #print("Type", msg_type, "none existent", "Existant:", self.__logdict.keys())
            return []

    def getTypes(self):
        return self.__logdict.keys()

    def getStatus(self):
        return self.__status

    def getCharacter(self):
        return self.__listener

    def getFilepath(self):
        return self.__filepath

class LogMessage(object):

    __regLine = re.compile("^\[ (\d{4})\.(\d{2})\.(\d{2}) (\d{2}):(\d{2}):(\d{2}) \] \((\w*)\) (.*)", re.S)


    def __init__(self, number, text):
        self.type = ''
        self.msg = ''
        self.datetime = None
        self.linenumber = number
        self.parseMessage(text)

    def parseMessage(self, text):
        #print(text)
        matchLine = self.__regLine.search(text)

        self.datetime = datetime.datetime(int(matchLine.group(1)), int(matchLine.group(2)), int(matchLine.group(3)),
                                           int(matchLine.group(4)), int(matchLine.group(5)), int(matchLine.group(6)), 0,
                                            datetime.timezone(datetime.timedelta(0))
                                            )

        self.type = matchLine.group(7)
        self.msg = matchLine.group(8)
        if self.type == 'None':
            #print("NoneType>>"+text+"<<")
            pass
        else:
            #print("Add msg with type", self.type)
            pass
    def __str__(self):
        return self.msg

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
    #@profile
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
            else :
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
    def __init__(self):
        self.type = None
        self.effect = None
        self.direction = None
        self.source = None
        self.target = None
        self.username = None
        
    def __repr__(self):
        sb = []
        for key in self.__dict__:
            sb.append("{key}='{value}'".format(key=key, value=self.__dict__[key]))
 
        return ', '.join(sb)
        
class CombatMessageParserSimple(object):

    def __init__(self, *args, **kwargs):
        self.msg = CombatMessage()
        self.__re_dmg = re.compile("^\s*(\d*)$")
        #self.__re_scram = re.compile(" <color=0xffffffff><b>(\w*)</b> <color=0x77ffffff><font size=10>from</font> <color=0xffffffff><b>([^<]*)</b> <color=0x77ffffff><font size=10>to <b><color=0xffffffff></font>([^<]*)")
        self.__re_scram = re.compile("<color=0xffffffff><b>(.*)</b> <color=0x77ffffff><font size=10>from</font> <color=0xffffffff><b>(.*)</b> <color=0x77ffffff><font size=10>to <b><color=0xffffffff></font>(.*)")
        self.__re_dmg_in = re.compile("<color=0xffcc0000><b>(\d*)</b> <color=0x77ffffff><font size=10>from</font> <b><color=0xffffffff>(.*)</b><font size=10><color=0x77ffffff>(.*)")
        self.__re_miss_in = re.compile("(.*) misses you completely");
        self.__re_dmg_out = re.compile("<color=0xff00ffff><b>(.*)</b> <color=0x77ffffff><font size=10>to</font> <b><color=0xffffffff>(.*)</b><font size=10><color=0x77ffffff>(.*)",)
        self.__re_miss_group = re.compile("Your group of (.*) misses (.*) completely - (.*)")
        self.__re_miss_drone = re.compile("Your (.*) misses (.*) completely - (.*)")

    def combat_reset(self):
        self.msg = CombatMessage()

    def getType(self):
        return self.msg.type

    def getEffect(self):
        return self.msg.effect

    def getDirection(self):
        return self.msg.direction

    def getSource(self):
        return self.msg.source

    def getTarget(self):
        return self.msg.target
    
    def getMsg(self):
        return self.msg

    def feed(self, txt):
        groups = self.__re_scram.match(txt)
        if groups != None:
            self.msg.type = "ewar"
            self.msg.effect = "Warp scramble attempt"
            self.msg.direction = "from"
            self.msg.source = groups.group(2)
            self.msg.target = groups.group(3)
            return

        groups = self.__re_dmg_in.match(txt)
        if groups != None:
            self.msg.type = "dmg"
            self.msg.effect = int(groups.group(1))
            self.msg.direction = "from"
            self.msg.source = groups.group(2)
            self.msg.target = "self"
            return

        groups = self.__re_miss_in.match(txt)
        if groups != None:
            self.msg.type = "miss"
            self.msg.effect = None
            self.msg.direction = "from"
            self.msg.source = groups.group(1)
            self.msg.target = "self"
            return

        groups = self.__re_dmg_out.match(txt)
        if groups != None:
            self.msg.type = "dmg"
            self.msg.effect = int(groups.group(1))
            self.msg.direction = "to"
            self.msg.source = "self"
            self.msg.target = groups.group(2)
            return

        groups = self.__re_miss_group.match(txt)
        if groups != None:
            self.msg.type = "miss"
            self.msg.effect = None
            self.msg.direction = "to"
            self.msg.source = groups.group(1)
            self.msg.target = groups.group(2)
            return

        groups = self.__re_miss_drone.match(txt)
        if groups != None:
            self.msg.type = "miss"
            self.msg.effect = None
            self.msg.source = groups.group(1)
            self.msg.target = groups.group(2)
            self.msg.direction = "to"
            return


        print("Add:", txt)
