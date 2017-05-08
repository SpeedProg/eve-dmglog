'''
Created on 30.12.2015

@author: SpeedProg
'''

import os
import re
import datetime
from html.parser import HTMLParser
from typing import List, Optional, Sequence, Any, Tuple, Dict

import matplotlib.pyplot as plt
import numpy as np
from profilehooks import profile
import threading
from multiprocessing import JoinableQueue, Process
import io
import time, pickle
import json
from matplotlib.cbook import todatetime


def escape_latex(tech):
    tech = tech.replace("\\", "\\textbackslash")
    tech = tech.replace("^", "\\textasciicircum")
    tech = tech.replace("~", "\\textasciitilde")
    escapes = ['&', '%', '$', '#', '_', '{', '}']
    for es in escapes:
        tech = tech.replace(es, '\\'+es)
    return tech


class GameLog(object):
    """
    Represents a folder with game logs
    """
    __an_con_count = 4

    def __init__(self, log_path: str) -> None:
        '''
        Sets the path of the folder that contains the game logs
        to actually load data call
        load_data_from_logs afterwards if this is the invital parse
        or
        load_from_file if parsed logs where saved with save_to_file
        '''
        self.__consumer_threads: List[LogFileCreatorThread] = []

        self.parsedLogFiles: List[ParsedLogFile] = []
        self.rawlogQueue: JoinableQueue = JoinableQueue(maxsize=100)
        self.parsedLogsQueue: JoinableQueue = JoinableQueue(maxsize=100)

        self.logPath: str = log_path

    def load_data_from_logs(self):
        start = time.time()
        self.__init_consumer()
        self.statusThread = StatusThread(self.parsedLogsQueue, self.rawlogQueue)
        self.statusThread.start()
        # start a monitor thread
        self.__load_logs()
        self.__stop_consumer()
        end = time.time()
        print(("Took", (end-start)))

    def __init_consumer(self):
        
        for i in range(self.__an_con_count):
            t = LogFileCreatorThread(self.rawlogQueue, self.parsedLogsQueue, "dec"+str(i))
            t.start()
            self.__consumer_threads.append(t)
            
        t = AppendLogfileThread(self.parsedLogsQueue, self.parsedLogFiles)
        t.start()
        self.__consumer_threads.append(t)
        print("All consumer started!")

    def __stop_consumer(self):
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
            #print("reading: ", idx, "/", numfiles, "path:", filepath)
            self.__load(filepath)
            if idx % 500 == 0:
                print((idx, "/", numfiles, "loaded"))
        
        
    #@profile
    def __load(self, path):
        data: bytes = open(path, "rb").read()
        self.rawlogQueue.put(RawLog(path, data))
    
    def save_to_file(self, path: str) -> None:
        """
        Save data to a pickle file, so we don't need to parse logfiles anymore
        :param path: the path of the pickel file
        :return: None
        """
        with open(path, 'wb') as output:
            pickle.dump(self.parsedLogFiles, output, pickle.HIGHEST_PROTOCOL)
    
    def load_from_file(self, path: str) -> None:
        with open(path, 'rb') as inf:
            self.parsedLogFiles = pickle.load(inf)

    @staticmethod
    def show_graph(self, name: str, aspic: bool = False) -> None:
        """
        Opens a matplotlib graph with graphs for
        DamageIn, DamageOut, EwarIn, EwarOut, EwarOnOthers, MissesIn, MissesOut
        :param name: Name of the Character to show the graphs for
        :param aspic: save as pic instead of opening a window
        :return: None
        """
        collectors = []
        collectors.append(CollectorDamageIn(name, self.parsedLogFiles))
        collectors.append(CollectorDamageOut(name, self.parsedLogFiles))
        collectors.append(CollectorEwarIn(name, self.parsedLogFiles))
        collectors.append(CollectorEwarOut(name, self.parsedLogFiles))
        collectors.append(CollectorEwarOutOthers(name, self.parsedLogFiles))
        collectors.append(CollectorMissIn(name, self.parsedLogFiles))
        collectors.append(CollectorMissOut(name, self.parsedLogFiles))
        
        GameLog.show_graph_for_collectors(collectors, aspic)

    @staticmethod
    def show_graph_for_collectors(collectors: List[Collector], aspic: bool) -> None:
        """
        Display graphs for a list of collectors
        :param collectors: the list of collectors to use
        :param aspic: save as picture instead of opening a window
        :return: None
        """
        graph_count: int = len(collectors)
        plt.switch_backend('TkAgg')
        
        if aspic:
            for idx, collector in enumerate(collectors):
                print((str(idx), collector.__class__.__name__))
                fig, plot = plt.subplots(1)
    
                names, values =  collector.get_data()
                nCount = len(names)
                print(("Enitiy Count", nCount))
                if nCount <= 0:
                    continue
                fig.set_size_inches(350, nCount/10)
                ind = np.arange(nCount)
                for tick in plot.yaxis.get_major_ticks():
                    tick.label.set_fontsize(6)
                rects = plot.barh(ind, values, 0.7, color='r', linewidth=0)
                plot.set_xlabel(collector.get_label_x(names, values))
                plot.set_yticks(ind)
                # filternames bc labels are resticted LaTeX
                names = [escape_latex(name) for name in names]
                plot.set_yticklabels(names)
                for rect in rects:
                    height = rect.get_height()
                    width = rect.get_width()
                    plot.text(width+100, rect.get_y() + height/2.,
                            '%d' % int(width),
                            ha='left', va='center', size='5')

                fig.savefig(collector.__class__.__name__+".png", format="png", dpi=100)
        else:
            fig, plots = plt.subplots(graph_count)
            if graph_count <= 1:
                idx = 0
                plot = plots
    
                collector = collectors[0]
                names, values =  collector.get_data()
                fig.set_size_inches(10, len(values)/2)
                ind = np.arange(len(values))
                for tick in plot.yaxis.get_major_ticks():
                    tick.label.set_fontsize(6)
                rects = plot.barh(ind, values, 0.5, color='r')
                plot.set_xlabel(collector.get_label_x(names, values))
                plot.set_yticks(ind)
                plot.set_yticklabels(names, fontsize=5)
                for rect in rects:
                    height = rect.get_height()
                    width = rect.get_width()
                    plot.text(1.05*width, rect.get_y() + height/2.,
                              f'{width}',
                              ha='left', va='center', size='10')
            else:
                for idx, plot in enumerate(plots):
                    collector = collectors[idx]
                    names, values =  collector.get_data()
                    ind = np.arange(len(values))
                    for tick in plot.yaxis.get_major_ticks():
                        tick.label.set_fontsize(6)
                    rects = plot.barh(ind, values, 0.5, color='r')
                    plot.set_xlabel(collector.get_label_x(names, values))
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
    """
    Thread that creates a ParsedLogfile out of raw log file text
    """
    def __init__(self, tasks: JoinableQueue, results: JoinableQueue, name: str) -> None:
        """
        Initiate the consumer process telling it a queue to get task from and
        one to deliver results too
        and give it a name to identify it
        :param tasks: queue to get tasks from
        :param results:  queue to deliver results to
        :param name: process name
        """
        Process.__init__(self, daemon=True)
        self.__tasks: JoinableQueue = tasks
        self.__results: JoinableQueue = results
        self.name = name
        self.__out_dict = dict()

    def run(self) -> None:
        while True:
            work: RawLog = self.__tasks.get()
            if work is None:
                break
            self.__out_dict = dict()
            logfile = self.createLogfile(work)
            self.__results.put(logfile)
            self.__tasks.task_done()
            #print(self.name, "decoded")
    
    def createLogfile(self, work: RawLog) -> ParsedLogFile:
        f = ParsedLogFile(work.filepath, work.data)
        return f


class DPSCollector(object):
    """
    A collector to display DPS graphs
    this is not finished
    """
    def __init__(self, userName: str, logfiles, testServer = False, liveServer = True, startDateTime = None, endDateTime = None):
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
        return  ((self.start != None and msg.datetime < self.start) or (self.end != None and msg.datetime > self.end))

    def getMsgList(self, file):
        return file.get_messages_in_order()
    
    def getNewValue(self, target, oldval):
        return oldval+1
    
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
        names = [x for (_,x) in sorted(zip(values,[str(key) for key in list(comdata.keys())]), key=lambda pair: pair[0])]
        values.sort()

        self.names = names
        self.values = values

        return names, values


class Collector(object):
    """
    Base collector class that every other collector should inherit from
    implements some basic features and checks that are usefull everywhere
    """
    def __init__(self, user_name: str, log_files: Sequence[ParsedLogFile], test_server: bool = False, live_server: bool = True,
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
        return (self.start is not None and msg.datetime < self.start) or (self.end is not None and msg.datetime > self.end)

    def get_msg_list(self, file):
        return file.get_messages_in_order()
    
    def get_new_value(self, target: ParsedLogMessage, oldval: int):
        """
        Defines how to get a new value from the old value and a target
        should be overriden by child collectors
        default just does return oldval+1
        """
        return oldval+1
    
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
        names = [x for (_,x) in sorted(zip(values,[str(key) for key in list(comdata.keys())]), key=lambda pair: pair[0])]
        values.sort()

        self.names = names
        self.values = values

        return names, values


class CollectorDamageIn(Collector):
    
    def get_key(self, msg):
        return msg.data.source
    
    def get_msg_list(self, file):
        return file.get_messages_by_type('combat')

    def skipmsg(self, msg):
        return Collector.skipmsg(self, msg) or not (msg.data.type == 'dmg' and msg.data.direction == 'from' and msg.data.target == 'self')

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
        return Collector.skipmsg(self, msg) or not (msg.data.type == 'dmg' and msg.data.direction == "to" and msg.data.source == "self")

    def get_new_value(self, target, oldval):
        return oldval + target.data.effect

    def get_label_x(self, names, values):
        total = 0
        for count in values:
            total += count
        return self.userName + " Dealt Damge Total = " + str(total)


class CollectorDamageOutWeapon(Collector):
    
    def __init__(self, userName, weapon, log_files, testServer = False, liveServer = True, startDateTime = None, endDateTime = None):
        Collector.__init__(self, userName, log_files, testServer, liveServer, startDateTime, endDateTime)
        self.weapon = weapon

    def get_key(self, msg):
        return msg.data.target
    
    def get_msg_list(self, file):
        return file.get_messages_by_type('combat')

    def skipmsg(self, msg):
        return Collector.skipmsg(self, msg) or not (msg.data.type == 'dmg' and msg.data.direction == "to" and msg.data.source == "self" and msg.data.weapon == self.weapon)

    def get_new_value(self, target, oldval):
        return oldval + target.data.effect

    def get_label_x(self, names, values):
        total = 0
        for count in values:
            total += count
        return self.userName + " Dealt Damage with " + self.weapon + " Total = " + str(total)


class CollectorDamageOutWeapons(Collector):
    
    def __init__(self, userName, weapons, log_files, testServer = False, liveServer = True, startDateTime = None, endDateTime = None):
        Collector.__init__(self, userName, log_files, testServer, liveServer, startDateTime, endDateTime)
        '''takes weapons seperated by | or "all" to allow all weapons '''
        self.weapons = weapons.split('|')

    def get_key(self, msg):
        return msg.data.target
    
    def get_msg_list(self, file):
        return file.get_messages_by_type('combat')

    def skipmsg(self, msg):
        return Collector.skipmsg(self, msg) or not (msg.data.type == 'dmg' and msg.data.direction == "to" and msg.data.source == "self" and ( "all" in self.weapons or msg.data.weapon in self.weapons ))

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
        return Collector.skipmsg(self, msg) or not (msg.data.type == 'miss' and msg.data.direction == 'from' and msg.data.target == 'self')

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
        return Collector.skipmsg(self, msg) or not (msg.data.type == 'miss' and msg.data.direction == 'to' and msg.data.source == 'self')

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
        return Collector.skipmsg(self, msg) or not (msg.data.type == 'ewar' and msg.data.target != 'self' and msg.data.source != 'self')

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


class StatusThread(threading.Thread):
    def __init__(self, parsedLogQueues: JoinableQueue, rawLogQueue: JoinableQueue):
        threading.Thread.__init__(self, daemon=True)
        self.__parsedLogQueues = parsedLogQueues
        self.__rawLogQueue = rawLogQueue
        self._stop = threading.Event()
        
    def run(self):
        while not self.stopped():
            print(("In rawLogQueue:", self.__rawLogQueue.qsize()))
            print(("In parsedLogQueues:", self.__parsedLogQueues.qsize()))
            time.sleep(1)
    
    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()


class AppendLogfileThread(threading.Thread):
    def __init__(self, tasks: JoinableQueue, results: List[ParsedLogFile]):
        threading.Thread.__init__(self)
        self.__tasks: JoinableQueue = tasks
        self.__results: JoinableQueue = results
    
    def run(self):
        while True:
            work: Optional[ParsedLogFile] = self.__tasks.get()
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
                print(("Final:", self.__out_dict))
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
    """
    Hold the raw log data, as the content as bytes
    and the path as string
    only used as a container to pass on to threads
    """
    def __init__(self, path: str, data: bytes):
        self.filepath: str = path
        self.data: bytes = data


class ParsedLogFile(object):
    __sanshas: Dict[str, None] = {'Deltole Tegmentum' : None, 'Renyn Meten' : None, 'Tama Cerebellum' : None, 'Ostingele Tectum' : None, 'Vylade Dien' : None, 'Antem Neo' : None, 'Eystur Rhomben' : None, 'Auga Hypophysis' : None, 'True Power Mobile Headquarters' : None, 'Outuni Mesen' : None, 'Mara Paleo' : None, 'Yulai Crus Cerebi' : None, 'Romi Thalamus' : None, 'Intaki Colliculus' : None, 'Uitra Telen' : None, 'Schmaeel Medulla' : None, 'Arnon Epithalamus' : None,
                 'Sansha\'s Nation Commander' : None, 'Sansha Battletower' : None }
    "Dict containing all the rats that we should pay attention too"
    __firstLine: str = "-"
    __secondLine: str = "  Gamelog"
    __thridLine: str = "  Listener:"
    __forthLine: str = "  Session Started:"
    __fifthLine: str = "-"
    __msg_start: str = "[ "
    __re_start_time = re.compile("^  Session Started: (\d{4})\.(\d{2})\.(\d{2}) (\d{2}):(\d{2}):(\d{2})\r$")
    __re_listener = re.compile("^  Listener: (.*)\r$")
    
    def __init__(self, filepath: str, data: bytes) -> None:
        print(("reading", filepath))
        self.__messages: List[ParsedLogMessage] = []
        self.__status: int = -1
        self.__start_datetime: Optional[datetime] = None
        self.__listener: Optional[str] = None
        self.__filepath: str = filepath
        self.__status = self.__readFile(data)
        self.is_testserver: bool = False


    def __readFile(self, data: bytes) -> int:
        """
        Returns __status: 0 = ok, 2 file useless, 1 file invalid
        """
        file = data.replace(b"\xff\xfe", b"").decode("utf_8")
        file = io.StringIO(file)

        current_line = file.readline()
        '''
        Check first line
        '''
        if not current_line.startswith(self.__firstLine):

            # #print("startline>>"+current_line+"<<")
            return 1;

        current_line = file.readline()
        if not current_line.startswith(self.__secondLine) :
            # #print("typeline>>"+current_line+"<<")
            return 1;

        current_line = file.readline()
        if not current_line.startswith(self.__thridLine):
            # #print("listener>>"+current_line+"<<")
            return 2;
        else: # extracting character name of the listener
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
                self.__start_datetime = datetime.datetime(
                               int(m.group(1)), int(m.group(2)), int(m.group(3)),
                               int(m.group(4)), int(m.group(5)), int(m.group(6)), 0,
                               datetime.timezone(datetime.timedelta(0))
                               )

        current_line = file.readline()
        if not current_line.startswith(self.__fifthLine):
            #print("endline>>"+current_line+"<<")
            return 2

        msg: str = self.__getNextMessage(file)
        if '<h4> Available systems</h4>' in msg:
            self.is_testserver = True
        while msg != '':
#           print("msg>", msg)
            parsedMessage: ParsedLogMessage = ParsedLogMessage(msg)
            if parsedMessage.data is not None: # it has a supported type
                #if (parsedMessage.data.target == 'self' and parsedMessage.data.source in self.__sanshas) or parsedMessage.data.target in self.__sanshas:
                self.__addMessage(parsedMessage)
            
            msg = self.__getNextMessage(file)
        return 0

    def __getNextMessage(self, file) -> str:
        msg = ""
        line = file.readline()
#        #print("check msg start:", line)
        if not line.startswith(self.__msg_start) :
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

    def __addMessage(self, msg: ParsedLogMessage) -> None:
        #print("Adding to LogFile", msg.type, msg)
        self.__messages.append(msg) # add message by order

    def print_messages_by_type(self, msg_type: str) -> None:
        msgSByType = self.get_messages_by_type()
        if msg_type in msgSByType:
            for msg in msgSByType[msg_type]:
                print(msg)
                pass
        else:
            print(("No messages of this msg_type="+msg_type))
            pass

    def get_messages_by_type(self, msg_type = None):
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

        self.datetime = datetime.datetime(int(match_line.group(1)), int(match_line.group(2)), int(match_line.group(3)),
                                           int(match_line.group(4)), int(match_line.group(5)), int(match_line.group(6)), 0,
                                            datetime.timezone(datetime.timedelta(0))
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
    """
    Contains data about a single combat message
    """
    def __init__(self):
        self.type: Optional[str] = None
        self.effect: Optional[str] = None # "Warp scramble attempt" | ... other dynamic values parsed from msg
        self.direction: Optional[str] = None # "from" | "to"
        self.source: Optional[str] = None # name of the guy doing the combat action
        self.target: Optional[str] = None # name of the guy that is target of the combat action
        self.weapon: Optional[str] = None # name of the weapon system used e.g. "Gecko"
        self.quality: Optional[str] = None # name of hit quality e.g. "Smashes"
        
    def __repr__(self):
        sb = []
        for key in self.__dict__:
            sb.append("{key}={value}".format(key=key, value=self.__dict__[key]))
 
        return ', '.join(sb)


class CombatMessageParserSimple(object):
    __re_dmg = re.compile("^\s*(\d*)$")
    __re_scram = re.compile("<color=0xffffffff><b>(.*)</b> <color=0x77ffffff><font size=10>from</font> <color=0xffffffff><b>(.*)</b> <color=0x77ffffff><font size=10>to <b><color=0xffffffff></font>(.*)\r")
    __re_dmg_in = re.compile("<color=0xffcc0000><b>(\d*)</b> <color=0x77ffffff><font size=10>from</font> <b><color=0xffffffff>(.*)</b><font size=10><color=0x77ffffff>(.*)\r")
    __re_miss_in = re.compile("(.*) misses you completely\r")
    __re_dmg_out = re.compile("<color=0xff00ffff><b>(?P<dmg>.*)</b> <color=0x77ffffff><font size=10>to</font> <b><color=0xffffffff>(?P<target>.*)</b><font size=10><color=0x77ffffff> - (?P<weapon>.*) - (?P<quality>.*)\r")
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


class UtilEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            encoded_object = list(obj.timetuple())[0:7]
        elif isinstance(obj, ParsedLogFile) or isinstance(obj, ParsedLogMessage) or isinstance(obj, CombatMessage):
            return obj.__dict__
        else:
            encoded_object =json.JSONEncoder.default(self, obj)
        return encoded_object