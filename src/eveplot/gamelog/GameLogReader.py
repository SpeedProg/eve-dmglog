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

from eveplot.gamelog.collectors import Collector
from eveplot.gamelog.collectors.Collectors import CollectorDamageIn, CollectorDamageOut, CollectorEwarIn, \
    CollectorEwarOut, CollectorEwarOutOthers, CollectorMissIn, CollectorMissOut
from eveplot.gamelog.parsers.LogFileParser import ParsedLogFile, ParsedLogMessage, CombatMessage

class RawLog(object):
    """
    Hold the raw log data, as the content as bytes
    and the path as string
    only used as a container to pass on to threads
    """
    def __init__(self, path: str, data: bytes):
        self.filepath: str = path
        self.data: bytes = data

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













class UtilEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            encoded_object = list(obj.timetuple())[0:7]
        elif isinstance(obj, ParsedLogFile) or isinstance(obj, ParsedLogMessage) or isinstance(obj, CombatMessage):
            return obj.__dict__
        else:
            encoded_object =json.JSONEncoder.default(self, obj)
        return encoded_object