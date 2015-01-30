#!/usr/bin/env python
import sys
import os 
import time
from random import random
sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/../external/lib/python')
from clint.textui import progress
from MTRunner import MTRunner, Algorithm, Data

class GreetingAlgorithm(Algorithm):

    def update_progress(self, progress):
        print '\r[{0}] {1}%'.format('#'*(progress/10), progress)

    def process(self, item):
        #print '%s is sleeping' % item

        bar = progress.Bar(label=item, expected_size=10)

        for i in range(11):
            time.sleep(random() * 1.)
            bar.show(i)

        #print 'wakeup %s!' % item
        return True

class Greeter(MTRunner):

    def __init__(self, numThread, keepAlive):
        MTRunner.__init__(self, name='my_greeter', data=Data(collection=[]), algorithm=GreetingAlgorithm())

        ## specify number of agent threads to be created (i.e. number of parallel threads)
        self.numThread = numThread

        ## specify if the agent threads should be kept alive in the background
        self.keepAlive = keepAlive

    ## a method allow adding new people on demand
    def addNewPerson(self, name):
        self.addDataItem(name)

## here we ask for 10 greeting agents and let the agents alive even there is no data to process
g = Greeter(numThread=2, keepAlive=False)
g.setLogLevel(3)

## add some initial data to be processed (people to be greeted)
g.addNewPerson(name="David")
g.addNewPerson(name="Hellen")

g.start()

g.addNewPerson(name="hahah")

g.join()
