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
import time, pickle
import json

def escapeLaTeX(tech):
    tech = tech.replace("\\", "\\textbackslash")
    tech = tech.replace("^", "\\textasciicircum")
    tech = tech.replace("~", "\\textasciitilde")
    escapes = ['&', '%', '$', '#', '_', '{', '}']
    for es in escapes:
        tech = tech.replace(es, '\\'+es)
    return tech

class GameLog(object):
    '''
    classdocs
    '''
    __an_con_count = 4

    def __init__(self, logPath):
        '''
        Constructor
        '''
        self.__consumer_threads = []

        self.parsedLogFiles = []
        self.rawlogQueue = JoinableQueue(maxsize=100)
        self.parsedLogsQueue = JoinableQueue(maxsize=100)

        self.logPath = logPath

    def loadDataFromLogs(self):
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
            t = LogFileCreatorThread(self.rawlogQueue, self.parsedLogsQueue, "dec"+str(i))
            t.start()
            self.__consumer_threads.append(t)
            
        t = AppendLogfileThread(self.parsedLogsQueue, self.parsedLogFiles)
        t.start()
        self.__consumer_threads.append(t)
        print("All consumer started!")

    def stopConsumer(self):
        print("Trying to join RawLogQueue")
        self.rawlogQueue.join()
        print("Trying to join parsedLogsQueue")
        self.parsedLogsQueue.join()

        for _ in range(self.__an_con_count):
            self.rawlogQueue.put(None)


        self.parsedLogsQueue.put(None)

        print("Waiting for Consumers")

        for t in self.__consumer_threads:
            t.join()

        self.statusThread.stop()

    def loadLogs(self):
        '''
        Load all the logfiles data into memory
        '''

        files = os.listdir(self.logPath)
        files.sort()

        numfiles = len(files)
        for idx, filename in enumerate(files):
            
            filepath = os.path.join(self.logPath, filename)
            #print("reading: ", idx, "/", numfiles, "path:", filepath)
            self.load(filepath)
            if idx % 500 == 0:
                print(idx, "/", numfiles, "loaded")
        
        
    #@profile
    def load(self, path):
        data = open(path, "rb").read()
        self.rawlogQueue.put(RawLog(path, data))
    
    def save_to_file(self, path):
        #with open(path+".json", 'w') as output:
        #    json.dump(self.parsedLogFiles, output, cls=UtilEncoder)
        with open(path, 'wb') as output:
            pickle.dump(self.parsedLogFiles, output, pickle.HIGHEST_PROTOCOL)
    
    def load_from_file(self, path):
        with open(path, 'rb') as inf:
            self.parsedLogFiles = pickle.load(inf)
        

    def showGraph(self, name, aspic = False):
        collectors = []
        collectors.append(CollectorDamageIn(name, self.parsedLogFiles))
        collectors.append(CollectorDamageOut(name, self.parsedLogFiles))
        collectors.append(CollectorEwarIn(name, self.parsedLogFiles))
        collectors.append(CollectorEwarOut(name, self.parsedLogFiles))
        collectors.append(CollectorEwarOutOthers(name, self.parsedLogFiles))
        collectors.append(CollectorMissIn(name, self.parsedLogFiles))
        collectors.append(CollectorMissOut(name, self.parsedLogFiles))
        
        self.showGraphForCollectors(collectors, aspic)

    def showGraphForCollectors(self, collectors, aspic):
        
        graphcount = len(collectors)
        plt.switch_backend('TkAgg')
        
        if (aspic):
            for idx, collector in enumerate(collectors):
                print (str(idx), collector.__class__.__name__)
                fig, plot = plt.subplots(1)
    
                names, values =  collector.getData()
                nCount = len(names)
                print("Enitiy Count", nCount)
                if nCount <= 0:
                    continue
                fig.set_size_inches(350, nCount/10)
                ind = np.arange(nCount)
                for tick in plot.yaxis.get_major_ticks():
                    tick.label.set_fontsize(6)
                rects = plot.barh(ind, values, 0.7, color='r', linewidth=0)
                plot.set_xlabel(collector.getXLabel(names, values))
                plot.set_yticks(ind)
                # filternames bc labels are resticted LaTeX
                names = [escapeLaTeX(name) for name in names]
                plot.set_yticklabels(names)
                for rect in rects:
                    height = rect.get_height()
                    width = rect.get_width()
                    plot.text(width+100, rect.get_y() + height/2.,
                            '%d' % int(width),
                            ha='left', va='center', size='5')

                fig.savefig(collector.__class__.__name__+".png", format="png", dpi=100)
        else:
            fig, plots = plt.subplots(graphcount)
            if graphcount <= 1:
                idx = 0
                plot = plots
    
                collector = collectors[0]
                names, values =  collector.getData()
                fig.set_size_inches(10, len(values)/2)
                ind = np.arange(len(values))
                for tick in plot.yaxis.get_major_ticks():
                    tick.label.set_fontsize(6)
                rects = plot.barh(ind, values, 0.5, color='r')
                plot.set_xlabel(collector.getXLabel(names, values))
                plot.set_yticks(ind)
                plot.set_yticklabels(names, fontsize=5)
                for rect in rects:
                    height = rect.get_height()
                    width = rect.get_width()
                    plot.text(1.05*width, rect.get_y() + height/2.,
                            '%d' % int(width),
                            ha='left', va='center', size='10')
            else:
                for idx, plot in enumerate(plots):
                    collector = collectors[idx]
                    names, values =  collector.getData()
                    ind = np.arange(len(values))
                    for tick in plot.yaxis.get_major_ticks():
                        tick.label.set_fontsize(6)
                    rects = plot.barh(ind, values, 0.5, color='r')
                    plot.set_xlabel(collector.getXLabel(names, values))
                    plot.set_yticks(ind)
                    plot.set_yticklabels(names)
                    for rect in rects:
                        height = rect.get_height()
                        width = rect.get_width()
                        plot.text(1.05*width, rect.get_y() + height/2.,
                                '%d' % int(width),
                                ha='left', va='center', size='10')
            plt.show()

class LogFileCreatorThread(Process):
    def __init__(self, tasks, results, name):
        Process.__init__(self, daemon=True)
        self.__tasks = tasks
        self.__results = results
        self.name = name
        self.__out_dict = dict()

    def run(self):
        while True:
            work = self.__tasks.get()
            if work is None:
                break
            self.__out_dict = dict()
            logfile = self.createLogfile(work)
            self.__results.put(logfile)
            self.__tasks.task_done()
            #print(self.name, "decoded")
    
    def createLogfile(self, work):
        f = ParsedLogFile(work.filepath, work.data)
        return f

class Collector(object):
    def __init__(self, userName, logfiles, testServer = False, liveServer = True, startDateTime = None, endDateTime = None):
        self.testServer = testServer
        self.liveServer = liveServer
        self.userName = userName
        self.files = logfiles
        self.names = None
        self.values = None
        self.start = startDateTime
        self.end = endDateTime
    
    def skipfile(self, file):
        if (file.getCharacter() != self.userName):
            return True
        if file.is_testserver and not self.testServer:
            return True
        if not file.is_testserver and not self.liveServer:
            return True
    
    def skipmsg(self, msg):
        return  ((self.start != None and msg.datetime < self.start) or (self.end != None and msg.datetime > self.end))

    def getMsgList(self, file):
        return file.getMessagesInOrder()
    
    def getNewValue(self, target, oldval):
        return oldval+1
    
    def getXLabel(self, names, values):
        return "Undefined"
    
    def getKey(self, msg):
        return msg.data.source
    
    def getData(self):
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
        
        values = [int(key) for key in comdata.values()]
        names = [x for (_,x) in sorted(zip(values,[str(key) for key in comdata.keys()]), key=lambda pair: pair[0])]
        values.sort()

        self.names = names
        self.values = values

        return names, values

class CollectorDamageIn(Collector):
    
    def getKey(self, msg):
        return msg.data.source
    
    def getMsgList(self, file):
        return file.getMessagesByType('combat')

    def skipmsg(self, msg):
        return Collector.skipmsg(self, msg) or not (msg.data.type == 'dmg' and msg.data.direction == 'from' and msg.data.target == 'self')

    def getNewValue(self, target, oldval):
        return oldval + target.data.effect

    def getXLabel(self, names, values):
        total = 0
        for count in values:
            total += count
        return self.userName + " Received Damge Total = " + str(total)

class CollectorDamageOut(Collector):
    
    def getKey(self, msg):
        return msg.data.target
    
    def getMsgList(self, file):
        return file.getMessagesByType('combat')

    def skipmsg(self, msg):
        return Collector.skipmsg(self, msg) or not (msg.data.type == 'dmg' and msg.data.direction == "to" and msg.data.source == "self")

    def getNewValue(self, target, oldval):
        return oldval + target.data.effect

    def getXLabel(self, names, values):
        total = 0
        for count in values:
            total += count
        return self.userName + " Dealt Damge Total = " + str(total)

class CollectorDamageOutWeapon(Collector):
    
    def __init__(self, userName, weapon, logfiles, testServer = False, liveServer = True, startDateTime = None, endDateTime = None):
        Collector.__init__(self, userName, logfiles, testServer, liveServer, startDateTime, endDateTime)
        self.weapon = weapon

    def getKey(self, msg):
        return msg.data.target
    
    def getMsgList(self, file):
        return file.getMessagesByType('combat')

    def skipmsg(self, msg):
        return Collector.skipmsg(self, msg) or not (msg.data.type == 'dmg' and msg.data.direction == "to" and msg.data.source == "self" and msg.data.weapon == self.weapon)

    def getNewValue(self, target, oldval):
        return oldval + target.data.effect

    def getXLabel(self, names, values):
        total = 0
        for count in values:
            total += count
        return self.userName + " Dealt Damage with " + self.weapon + " Total = " + str(total)

class CollectorDamageOutWeapons(Collector):
    
    def __init__(self, userName, weapons, logfiles, testServer = False, liveServer = True, startDateTime = None, endDateTime = None):
        Collector.__init__(self, userName, logfiles, testServer, liveServer, startDateTime, endDateTime)
        '''takes weapons seperated by | or "all" to allow all weapons '''
        self.weapons = weapons.split('|')

    def getKey(self, msg):
        return msg.data.target
    
    def getMsgList(self, file):
        return file.getMessagesByType('combat')

    def skipmsg(self, msg):
        return Collector.skipmsg(self, msg) or not (msg.data.type == 'dmg' and msg.data.direction == "to" and msg.data.source == "self" and ( "all" in self.weapons or msg.data.weapon in self.weapons ))

    def getNewValue(self, target, oldval):
        return oldval + target.data.effect

    def getXLabel(self, names, values):
        total = 0
        for count in values:
            total += count
        return self.userName + " Dealt Damage with " + self.weapon + " Total = " + str(total)



class CollectorMissIn(Collector):
    
    def getKey(self, msg):
        return msg.data.source
    
    def getMsgList(self, file):
        return file.getMessagesByType('combat')

    def skipmsg(self, msg):
        return Collector.skipmsg(self, msg) or not (msg.data.type == 'miss' and msg.data.direction == 'from' and msg.data.target == 'self')

    def getNewValue(self, target, oldval):
        return oldval + 1

    def getXLabel(self, names, values):
        total = 0
        for count in values:
            total += count
        return "Number of Misses On Me Total = " + str(total)

class CollectorMissOut(Collector):
    
    def getKey(self, msg):
        return msg.data.target
    
    def getMsgList(self, file):
        return file.getMessagesByType('combat')

    def skipmsg(self, msg):
        return Collector.skipmsg(self, msg) or not (msg.data.type == 'miss' and msg.data.direction == 'to' and msg.data.source == 'self')

    def getNewValue(self, target, oldval):
        return oldval + 1

    def getXLabel(self, names, values):
        total = 0
        for count in values:
            total += count
        return "Number of Misses By Me Total = " + str(total)

class CollectorEwarOutOthers(Collector):
    
    def getKey(self, msg):
        return msg.data.source + ' => ' + msg.data.target
    
    def getMsgList(self, file):
        return file.getMessagesByType('combat')

    def skipmsg(self, msg):
        return Collector.skipmsg(self, msg) or not (msg.data.type == 'ewar' and msg.data.target != 'self' and msg.data.source != 'self')

    def getNewValue(self, target, oldval):
        return oldval + 1

    def getXLabel(self, names, values):
        total = 0
        for count in values:
            total += count
        return "Ewar attempts done between others total = " + str(total)

class CollectorEwarIn(Collector):

    def getKey(self, msg):
        return msg.data.source

    def getMsgList(self, file):
        return file.getMessagesByType('combat')

    def skipmsg(self, msg):
        return Collector.skipmsg(self, msg) or not (msg.data.type == 'ewar' and msg.data.target == 'self')

    def getNewValue(self, target, oldval):
        return oldval + 1

    def getXLabel(self, names, values):
        total = 0
        for count in values:
            total += count
        return "Ewar attempts on me total = " + str(total)

class CollectorEwarOut(Collector):

    def getKey(self, msg):
        return msg.data.target

    def getMsgList(self, file):
        return file.getMessagesByType('combat')

    def skipmsg(self, msg):
        return Collector.skipmsg(self, msg) or not (msg.data.type == 'ewar' and msg.data.source == 'self')

    def getNewValue(self, target, oldval):
        return oldval + 1

    def getXLabel(self, names, values):
        total = 0
        for count in values:
            total += count
        return "Ewar attempts by me total = " + str(total)

class StatusThread(threading.Thread):
    def __init__(self, parsedLogQueues, rawLogQueue):
        threading.Thread.__init__(self, daemon=True)
        self.__parsedLogQueues = parsedLogQueues
        self.__rawLogQueue = rawLogQueue
        self._stop = threading.Event()
        
    def run(self):
        while not self.stopped():
            print("In rawLogQueue:", self.__rawLogQueue.qsize())
            print("In parsedLogQueues:", self.__parsedLogQueues.qsize())
            time.sleep(1)
    
    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()

class AppendLogfileThread(threading.Thread):
    def __init__(self, tasks, results):
        threading.Thread.__init__(self)
        self.__tasks = tasks
        self.__results = results
    
    def run(self):
        while True:
            work = self.__tasks.get()
            if work is None:
                print("All Files added")
                break
            self.__results.append(work)
            self.__tasks.task_done()

class MessageAddThread(threading.Thread):
    def __init__(self, in_dicts, user):
        threading.Thread.__init__(self)
        self.__out_dict = user
        self.__tasks = in_dicts

    def run(self):
        while True:
            work = self.__tasks.get()
            if work is None:
                print("Final:", self.__out_dict)
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

class ParsedLogFile(object):
    __sanshas = {'Deltole Tegmentum' : None, 'Renyn Meten' : None, 'Tama Cerebellum' : None, 'Ostingele Tectum' : None, 'Vylade Dien' : None, 'Antem Neo' : None, 'Eystur Rhomben' : None, 'Auga Hypophysis' : None, 'True Power Mobile Headquarters' : None, 'Outuni Mesen' : None, 'Mara Paleo' : None, 'Yulai Crus Cerebi' : None, 'Romi Thalamus' : None, 'Intaki Colliculus' : None, 'Uitra Telen' : None, 'Schmaeel Medulla' : None, 'Arnon Epithalamus' : None,
                 'Sansha\'s Nation Commander' : None, 'Sansha Battletower' : None }
    __firstLine =   "-"
    __secondLine =  "  Gamelog"
    __thridLine =   "  Listener:"
    __forthLine =   "  Session Started:"
    __fifthLine =   "-"
    __msg_start = "[ "
    __re_start_time = re.compile("^  Session Started: (\d{4})\.(\d{2})\.(\d{2}) (\d{2}):(\d{2}):(\d{2})\r$")
    __re_listener = re.compile("^  Listener: (.*)\r$")
    
    def __init__(self, filepath, data):
        print("reading", filepath)
        self.__messages = []
        self.__status = -1
        self.__start_datetime = None
        self.__listener = None
        self.__filepath = filepath
        self.__status = self.__readFile(data)
        self.is_testserver = False


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
            m = self.__re_listener.match(currentLine)
            self.__listener = m.group(1)

        currentLine = file.readline()
        if not currentLine.startswith(self.__forthLine):
            # #print("session>>"+currentLine+"<<")
            return 2;
        else:
            # parse the session start
            m = self.__re_start_time.match(currentLine)
            if (m != None):
                self.__start_datetime = datetime.datetime(
                               int(m.group(1)), int(m.group(2)), int(m.group(3)),
                               int(m.group(4)), int(m.group(5)), int(m.group(6)), 0,
                               datetime.timezone(datetime.timedelta(0))
                               )

        currentLine = file.readline()
        if not currentLine.startswith(self.__fifthLine):
            #print("endline>>"+currentLine+"<<")
            return 2;

        msg = self.__getNextMessage(file)
        if '<h4> Available systems</h4>' in msg:
            self.is_testserver = True
        while (msg != ''):
#           print("msg>", msg)
            parsedMessage = ParsedLogMessage(msg)
            if parsedMessage.data != None: # it has a supported type
                #if (parsedMessage.data.target == 'self' and parsedMessage.data.source in self.__sanshas) or parsedMessage.data.target in self.__sanshas:
                self.__addMessage(parsedMessage)
            
            msg = self.__getNextMessage(file)
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
        self.__messages.append(msg) # add message by order

    def printMessagesByType(self, msg_type):
        msgSByType = self.getMessagesByType()
        if msg_type in msgSByType:
            for msg in msgSByType[msg_type]:
                print(msg)
                pass
        else:
            print("No messages of this msg_type="+msg_type)
            pass

    def getMessagesByType(self, msg_type = None):
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
        messagesForType = []
        for msg in self.__messages:
            if msg.type == msg_type:
                messagesForType.append(msg)
        
        return messagesForType

    def getTypes(self):
        return self.__messagesByType.keys()

    def getStatus(self):
        return self.__status

    def getCharacter(self):
        return self.__listener

    def getFilepath(self):
        return self.__filepath

    def getMessagesInOrder(self):
        return self.__messages

class ParsedLogMessage(object):

    __regLine = re.compile("^\[ (\d{4})\.(\d{2})\.(\d{2}) (\d{2}):(\d{2}):(\d{2}) \] \((\w*)\) (.*)", re.S)

    def __init__(self, text):
        self.type = None
        self.datetime = None
        self.data = None
        self.parseMessage(text)

    def parseMessage(self, text):
        matchLine = self.__regLine.search(text)

        self.datetime = datetime.datetime(int(matchLine.group(1)), int(matchLine.group(2)), int(matchLine.group(3)),
                                           int(matchLine.group(4)), int(matchLine.group(5)), int(matchLine.group(6)), 0,
                                            datetime.timezone(datetime.timedelta(0))
                                            )

        self.type = matchLine.group(7)
        msgText = matchLine.group(8)
        if self.type == 'combat':
            self.data = CombatMessageParserSimple.parse(msgText)
        else:
            pass
            #print("Type", self.type, " not supported!")

    def __str__(self):
        return self.data

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
        self.weapon = None
        self.quality = None
        
    def __repr__(self):
        sb = []
        for key in self.__dict__:
            sb.append("{key}={value}".format(key=key, value=self.__dict__[key]))
 
        return ', '.join(sb)
        
class CombatMessageParserSimple(object):
    __re_dmg = re.compile("^\s*(\d*)$")
    __re_scram = re.compile("<color=0xffffffff><b>(.*)</b> <color=0x77ffffff><font size=10>from</font> <color=0xffffffff><b>(.*)</b> <color=0x77ffffff><font size=10>to <b><color=0xffffffff></font>(.*)\r")
    __re_dmg_in = re.compile("<color=0xffcc0000><b>(\d*)</b> <color=0x77ffffff><font size=10>from</font> <b><color=0xffffffff>(.*)</b><font size=10><color=0x77ffffff>(.*)\r")
    __re_miss_in = re.compile("(.*) misses you completely\r");
    __re_dmg_out = re.compile("<color=0xff00ffff><b>(?P<dmg>.*)</b> <color=0x77ffffff><font size=10>to</font> <b><color=0xffffffff>(?P<target>.*)</b><font size=10><color=0x77ffffff> - (?P<weapon>.*) - (?P<quality>.*)\r")
    __re_miss_group = re.compile("Your group of (.*) misses (.*) completely - (.*)\r")
    __re_miss_drone = re.compile("Your (.*) misses (.*) completely - (.*)\r")

    @staticmethod
    def parse(txt):
        msg = CombatMessage()
        groups = CombatMessageParserSimple.__re_scram.match(txt)
        if groups != None:
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
        if groups != None:
            msg.type = "dmg"
            msg.effect = int(groups.group(1))
            msg.direction = "from"
            msg.source = groups.group(2)
            msg.target = "self"
            msg.weapon = None
            msg.quality = None
            return msg

        groups = CombatMessageParserSimple.__re_miss_in.match(txt)
        if groups != None:
            msg.type = "miss"
            msg.effect = None
            msg.direction = "from"
            msg.source = groups.group(1)
            msg.target = "self"
            msg.weapon = None
            msg.quality = None
            return msg

        groups = CombatMessageParserSimple.__re_dmg_out.match(txt)
        if groups != None:
            msg.type = "dmg"
            msg.effect = int(groups.group('dmg'))
            msg.direction = "to"
            msg.source = "self"
            msg.target = groups.group('target')
            msg.weapon = groups.group('weapon')
            msg.quality = groups.group('quality')
            return msg

        groups = CombatMessageParserSimple.__re_miss_group.match(txt)
        if groups != None:
            msg.type = "miss"
            msg.effect = None
            msg.direction = "to"
            msg.source = groups.group(1)
            msg.target = groups.group(2)
            msg.weapon = None
            msg.quality = None
            return msg

        groups = CombatMessageParserSimple.__re_miss_drone.match(txt)
        if groups != None:
            msg.type = "miss drone"
            msg.effect = 1
            msg.source = groups.group(1)
            msg.target = groups.group(2)
            msg.direction = "to"
            msg.weapon = None
            msg.quality = None
            return msg
        
        return None

class UtilEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            encoded_object = list(obj.timetuple())[0:7]
        elif isinstance(obj, ParsedLogFile) or isinstance(obj, ParsedLogMessage) or isinstance(obj, CombatMessage):
            return obj.__dict__
        else:
            encoded_object =json.JSONEncoder.default(self, obj)
        return encoded_object