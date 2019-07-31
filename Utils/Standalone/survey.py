#!/usr/bin/env /Users/zschillaci/Software/miniconda3/envs/pyenv/bin/python
import os
import sys
import collections
import math as mt
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def StrRound(val, floating=2):
    return str(round(val, floating))

def StringtoFlt(string):
    flt = None
    if ("\n" in string):
        string.replace("\n", "")
    if ("=" in string):
        string = string[string.find("=") + 1:]
    try:
        flt = float(string)
    except ValueError:
        print("Cannot convert string to float!")
    return flt

def SetYlim(ylim, yticks):
    #Set y-limits of plot based upon min. and max. of plots
    tick = abs(yticks[0][1] - yticks[0][0])
    low = ylim[0] - 1.55 * tick
    high = ylim[-1] + 1.55 * tick
    return low, high

def SavePlot(path, fname):
    if not os.path.isdir(path):
        os.makedirs(path)
    plt.savefig(path + '/' + fname + '.png')
    plt.close()

def PlotHistogram(placements, corners):
    for dim in placements:
        fig = plt.figure("Histogram - " + dim,(10,10))
        fig.suptitle("Histogram - " + dim, fontsize = 20)
        ax = fig.add_subplot(111)

        bins = np.arange(-55, 55, 10)
        plt.hist(placements[dim], bins=bins, ec='black')
        plt.xlabel('$\Delta$' + dim + ' [$\mu$m]', fontsize=18)
        plt.ylabel('Counts / ' + StrRound(abs(bins[0] - bins[1])) + ' $\mu$m', fontsize=18)
        plt.xticks(np.arange(-50, 55, 10))
        plt.xlim(-55, 55)
        plt.grid()

        _, high = SetYlim(plt.ylim(), plt.yticks())
        plt.ylim(0, high)

        ax.annotate('$\mu$ = ' + StrRound(np.mean(placements[dim])) + ' $\mu$m',xy=(0.995,0.965),xycoords='axes fraction',fontsize=16,horizontalalignment='right',verticalalignment='bottom')
        ax.annotate('$\sigma$ = ' + StrRound(np.std(placements[dim])) + ' $\mu$m',xy=(0.995,0.925),xycoords='axes fraction',fontsize=16,horizontalalignment='right',verticalalignment='bottom')
        SavePlot(RESULTS_FILE, dim + '-Corners' + corners + '-histogram')

class TheSurvey(object):
    def __init__(self, module, stave, infile):
        #Meta-data
        self.module = module
        self.stave = stave
        self.infile = infile
        self.name = 'Module_' + str(module)
        self.infile = self.infile + '/' + self.name + '.txt'
        self.dimensions = ['X', 'Y']
        self.tolerance = 25
       
        #Data
        self.GetLines()
        self.GetCorners()
        self.GetStages()
        self.GetResults()
        self.GetAngles()
        self.GetFlags()

    def Dump(self):
        print('##### SURVEY RESULT #####')
        print('Module:', self.module)
        print('Stave:', self.stave)
        print('File:', self.infile)
        print('')
        self.PrintOverview()

    # reads the file into the "lines" field
    def GetLines(self):
        infile = open(self.infile,"r") # create object to scan the file (r means open file for reading)
        self.lines = infile.readlines() # read the file
        infile.close() # close the scanner

    # gathers information about each corner from self.lines into self.corners (ordered dict)
    def GetCorners(self):
        indA, indB, indC, indD = 0, 0, 0, 0
        for ind, line in enumerate(self.lines): # iterate over self.lines (line) with the counter (ind)
            if ("CornerA" in line): # find line number where information about each corner begins
                indA = ind + 1
            elif ("CornerB" in line):
                indB = ind + 1
            elif ("CornerC" in line):
                indC = ind + 1
            elif ("CornerD" in line):
                indD = ind + 1

        self.corners = collections.OrderedDict()
        self.corners['A'] = self.lines[indA : indB - 2] # save lines after corner A and before corner B in input file into ordered dictionary
        self.corners['B'] = self.lines[indB : indC - 2]
        self.corners['C'] = self.lines[indC : indD - 2]
        self.corners['D'] = self.lines[indD : ]

    def RenameStages(self):
        stages = []
        for stage in self.stages:
            stage = stage.replace(' ', '')
            stage = stage.lower()
            if ('aftergluing' in stage) or ('afterglue' in stage) or ('ag' in stage):
                stage = 'AG'
            elif ('beforebridgeremoval' in stage) or ('bbr' in stage):
                stage = 'BBR'
            elif ('afterbridgeremoval' in stage) or ('abr' in stage):
                stage = 'ABR'
            else:
                stage = stage.capitalize()
            stages.append(stage)
        self.stages = stages

    # get a list the list of stages
    def GetStages(self, rename=False):
        self.stages = []
        for line in self.corners['A']: # go through lines for A
            stage = line[line.find("_") + 1: line.find("=") - 1] # get the stage (when data was taken)
            if (stage not in self.stages): # add to self.stages if not already there
                self.stages.append(stage)
        # self.stages = RenameStages(self.stages)
        return self.stages

    def GetResults(self):
        xdf, ydf = collections.OrderedDict(), collections.OrderedDict()
        for corner, coords in self.corners.items():
            xvals, yvals = [], []
            for i in range(len(self.stages)):
                xvals.append(StringtoFlt(coords[(3 * i)]))
                yvals.append(StringtoFlt(coords[(3 * i) + 1]))
            xdf[corner] = xvals
            ydf[corner] = yvals
        
        self.xdf = pd.DataFrame(xdf, index=self.stages)
        self.ydf = pd.DataFrame(ydf, index=self.stages)
        self.results = {'X' : self.xdf, 'Y' : self.ydf}

    def GetAngle(self, corners, stage):
        c1, c2 = corners
        dx = self.xdf[c1][stage] - self.xdf[c2][stage]
        dy = self.ydf[c1][stage] - self.ydf[c2][stage]
        try:
            angle = 1000 * mt.atan(dy / dx)
        except:
            return -999
        return angle

    def GetAngles(self):
        angles = collections.OrderedDict()
        angles['AB'] = [self.GetAngle('AB', stage) for stage in self.stages]
        angles['CD'] = [self.GetAngle('CD', stage) for stage in self.stages]
        self.angles = pd.DataFrame(angles, index=self.stages)

    def GetRelative(self, df):
        df = pd.DataFrame(df - df.iloc[0])
        df = 1000 * df
        return df

    def GetFlags(self):
        self.passed = True
        self.failures = []        
        for dim in self.dimensions:
            df = self.GetRelative(self.results[dim])
            for corner in self.corners:
                if (abs(df[corner][-1]) >= self.tolerance):
                    self.passed = False
                    self.failures.append(corner + ': delta' + dim + ' = ' + StrRound(df[corner][-1]) + ' um')

    def PrintOverview(self):
        if self.passed:
            print("---> Passed! All surveys within " + StrRound(self.tolerance) + " um tolerance.")
        else:
            print("---> Failed! The following corners are out of " + StrRound(self.tolerance) + " um tolerance: ")
            for failure in self.failures:
                print(failure)
        print('')

    def PopulateHistograms(self, placements, stage, corners='ABCD'):
        for dim in self.dimensions:
            df = self.GetRelative(self.results[dim])
            for corner in self.corners:
                if (corner in corners):
                    placements[dim].append(df[corner][stage])

    def PlotMovement(self, reference='relative', printOut=True):
        fig = plt.figure("Movement - " + reference,(10,10))
        fig.suptitle("Movement - " + reference + " (" + self.stave + ", " + self.name + ")", fontsize = 20)
        for n, dim in enumerate(self.dimensions):
            plt.subplot(211 + n)
            plt.title("Change in " + dim)

            df = self.results[dim]
            if (reference == 'relative'):
                df = self.GetRelative(df)

            for corner in self.corners:
                plt.plot(np.arange(len(df[corner])), df[corner], linestyle='--', marker='o', label=corner)

            units = ('[$\mu$m]' if (reference == 'relative') else '[mm]')
            if printOut:
                print('-----' + dim + ' ' + units + '-----')
                print(df)
                print('--------------------' + '\n')
 
            low, high = SetYlim(plt.ylim(), plt.yticks())
            plt.ylim(low, high)
            plt.ylim(-50.5, 50.5)

            plt.xlabel('Stage in Process')
            plt.xticks(np.arange(len(self.stages)), self.stages)
            plt.ylabel(dim + ' ' + units)
            plt.legend(loc=9, ncol=4)
        SavePlot(RESULTS_FILE, 'position-' + reference + '-' + self.name)

    def PlotAngle(self, reference='relative', printOut=True):
        plt.figure("Angle Movement", (10, 10))
        plt.title("Angle Movement" + " (" + self.stave + ", " + self.name + ")", fontsize = 20)

        df = self.angles
        if (reference == 'relative'):
            df = self.GetRelative(df)
            
        for col in self.angles.columns:
            plt.plot(np.arange(len(df[col])), df[col], linestyle='--', marker='o', label=col)

        units = ('[$\mu$rad]' if (reference == 'relative') else '[mrad]')
        if printOut:
            print('----- Angle ' + units + '-----')
            print(df)
            print('--------------------' + '\n')

        low, high = SetYlim(plt.ylim(), plt.yticks())
        plt.ylim(low, high)

        plt.xlabel('Stage in Process')
        plt.xticks(np.arange(len(self.stages)), self.stages)
        plt.ylabel('Angle ' + units)
        plt.legend(loc=9, ncol=4)
        SavePlot(RESULTS_FILE, 'angle-' + reference + '-' + self.name)

# PARAMETERS #

# Input and output directories
INPUT_FILE = sys.argv[1]
RESULTS_FILE = sys.argv[2]

#Stave name
STAVE = sys.argv[3]

# List of module numbers on the stave (corresponding to survey files in STAVE sub-directory)
MODULES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]

# Plot placement histograms of all modules for specified corners (e.g. ['AB', 'CD', 'AC', 'AD', 'BC', 'BD', 'ABCD'])
CORNERS = 'ABCD'
PLACEMENTS = {'X': [], 'Y': []}

# Plot and printout all survey results, highlighting any failures (placements outside tolerance)
for module in MODULES:
    try:
        survey = TheSurvey(module, STAVE, INPUT_FILE)
        if len(survey.stages) > 1:
            survey.Dump()
            
            survey.PlotMovement(reference='relative', printOut=True)
            survey.PlotAngle(reference='absolute', printOut=True)
        
            survey.PopulateHistograms(PLACEMENTS, survey.stages[-1], CORNERS)
    except:
        print("Error working with module {}".format(module))
PlotHistogram(PLACEMENTS, CORNERS)