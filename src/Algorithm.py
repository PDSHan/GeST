'''
Copyright 2019 ARM Ltd. and University of Cyprus
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, 
including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, 
and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, 
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

import subprocess
from xml.dom import minidom
from Instruction import Instruction
from Operand import Operand
from Population import Population
from Individual import Individual
import math
import fileinput
from random import Random
import os
import shutil
import sys
from threading import Timer
from threading import Thread
import time
import pickle
import re
import atexit
import datetime
from paramiko import SSHClient, client
import paramiko
import socket
import platform
import visa
from statistics import stdev
from multiprocessing.pool import ThreadPool
from multiprocessing import  TimeoutError
import importlib
import operator
import copy

#import serial

class Algorithm(object):


    UNIFORM_CROSSOVER="0"
    ONEPOINT_CROSSOVER="1"
    WHEEL_SELECTION="1"
    TOURNAMENT_SELECTION="0"
    ORIGINAL_ALGORITHM="0"
    ALPS_ALGORITHM="1"
    Linear_age_func="0"
    Fibonacci_age_func="1"
    Polynomial_age_func="2"
    Exponential_age_func="3"
    

    def __init__(self,configurationFile,rand=Random()): #reads configuration file and initializes the first population        
        '''general initialization'''
        self.general_initialization(configurationFile, rand)
        '''specific initializations'''
        self.__instructions_operands_init__()
        print("End of inputs\n")
            
    def general_initialization(self,configurationFile,rand):
        '''general algorithm and run parameters'''
        self.xmldoc = minidom.parse(configurationFile)
        self.intitializeAlgorithmAndRunParameters(configurationFile, rand)
        '''create results and saved state directories'''
        self.setupDirs(configurationFile) 
        '''print general and run parameters'''
        self.printGeneralInputs()
        
    def intitializeAlgorithmAndRunParameters(self,configurationFile,rand):    
        ##genetic algorithm parameters
        self.algorithmType = self.xmldoc.getElementsByTagName('algorithm_type')[0].attributes['value'].value
        if self.algorithmType == Algorithm.ALPS_ALGORITHM:
            self.alpsNumOfLayers  = int(self.xmldoc.getElementsByTagName('alpsNumOfLayers')[0].attributes['value'].value)
            self.alpsAgeGap     = int(self.xmldoc.getElementsByTagName('alpsAgeGap')[0].attributes['value'].value)
            self.alpsAgeScheme    = self.xmldoc.getElementsByTagName('alpsAgeScheme')[0].attributes['value'].value
            self.alpsMaxIndivsPerLayer = int(self.xmldoc.getElementsByTagName('alpsMaxIndivsPerLayer')[0].attributes['value'].value)
            self.__alps_init__()

        self.populationSize = self.xmldoc.getElementsByTagName('population_size')[0].attributes['value'].value  
        self.mutationRate = self.xmldoc.getElementsByTagName('mutation_rate')[0].attributes['value'].value 
        self.crossoverType = self.xmldoc.getElementsByTagName('crossover_type')[0].attributes['value'].value 
        self.crossoverRate = self.xmldoc.getElementsByTagName('crossover_rate')[0].attributes['value'].value
        self.uniformRate = self.xmldoc.getElementsByTagName('uniform_rate')[0].attributes['value'].value
        self.ellitism = self.xmldoc.getElementsByTagName('ellitism')[0].attributes['value'].value
        self.ellitismSize = int(self.xmldoc.getElementsByTagName('ellitism_size')[0].attributes['value'].value)
        self.selectionMethod=self.xmldoc.getElementsByTagName('selectionMethod')[0].attributes['value'].value#0 wheel,1 tournament
        self.tournamentSize = self.xmldoc.getElementsByTagName('tournament_size')[0].attributes['value'].value  
        self.populationsToRun=  int(self.xmldoc.getElementsByTagName('populations_to_run')[0].attributes['value'].value)
        self.printLog = self.xmldoc.getElementsByTagName('print_log')[0].attributes['value'].value + self.algorithmType + "_" + self.selectionMethod + "_" + self.populationSize + "_" + str(self.populationsToRun) + ".log"
        if os.path.exists(self.printLog):
            os.remove(self.printLog)
        self.bestFitnessHistory = []
        ##compilation and measurement parameters
        self.fitnessClassName = self.xmldoc.getElementsByTagName('fitnessClass')[0].attributes['value'].value 
        
        module= importlib.import_module("Fitness."+self.fitnessClassName)
        self.fitnessClass = getattr(module,self.fitnessClassName) 
        self.fitness = self.fitnessClass()
         
        self.measurementClassName = self.xmldoc.getElementsByTagName('measurementClass')[0].attributes['value'].value 
        self.measurementClassConfFile = self.xmldoc.getElementsByTagName('measurementClassConfFile')[0].attributes['value'].value
        
                
        module= importlib.import_module("Measurement."+self.measurementClassName)
        self.measurementClass = getattr(module,self.measurementClassName) 
        if self.measurementClassConfFile[-4:]!=".xml":
            self.measurementClassConfFile=self.measurementClassConfFile+".xml"
        self.measurement=self.measurementClass("./configurationFiles/measurement/"+self.measurementClassConfFile)
        self.measurement.init()   
        
        self.dirToSaveResults = self.xmldoc.getElementsByTagName('dirToSaveResults')[0].attributes['value'].value
        self.seedDir=self.xmldoc.getElementsByTagName('seedDir')[0].attributes['value'].value  
        self.compilationDir = self.xmldoc.getElementsByTagName('compilationDir')[0].attributes['value'].value
        
        ##make sure that dirs end with /
        self.dirToSaveResults=self.__fixDirEnd__(self.dirToSaveResults)
        self.seedDir=self.__fixDirEnd__(self.seedDir)
        self.compilationDir=self.__fixDirEnd__(self.compilationDir)
                     
        ##some other variable initialization
        
        try:
            self.saveWholeSource=self.xmldoc.getElementsByTagName('save_whole_source')[0].attributes['value'].value  
        except:
            self.saveWholeSource=1
        
        self.population=Population()
        self.rand=rand
        self.populationsExamined=1
        self.bestIndividualUntilNow=None
        self.waitCounter=0
        self.populationsTested=0  

    def fibonacci(i): 
        if i <= 0: 
            return 0 
        elif i == 1: 
            return 1 
        else: 
            a, b = 0, 1 
            for _ in range(2, i + 1): 
                a, b = b, a + b 
            return b

    def __alps_init__(self):
        self.alpsEnvolutions=0
        self.alpsAgeLayersLists = []
        self.alpsAgeLists = []
        for i in range(self.alpsNumOfLayers):
            newList = []
            self.alpsAgeLayersLists.append(newList)
            
        if self.alpsAgeScheme == Algorithm.Linear_age_func:
            for i in range(1, self.alpsNumOfLayers+1):
                self.alpsAgeLists.append(i * self.alpsAgeGap)
        elif self.alpsAgeScheme == Algorithm.Fibonacci_age_func:
            for i in range(1, self.alpsNumOfLayers+1):
                self.alpsAgeLists.append(fibonacci(i) * self.alpsAgeGap)
        elif self.alpsAgeScheme == Algorithm.Polynomial_age_func:
            for i in range(1, self.alpsNumOfLayers+1):
                self.alpsAgeLists.append(i * i * self.alpsAgeGap)
        elif self.alpsAgeScheme == Algorithm.Exponential_age_func:
            for i in range(1, self.alpsNumOfLayers+1):
                self.alpsAgeLists.append(2 ** i * self.alpsAgeGap)
        else:
            print("Unknown ALPS age functions!")
            sys.exit()

    def __fixDirEnd__(self,dir):
        if dir=="":
            return dir
        if dir[-1:]!="/":
            dir=dir+"/"
        return dir
    
    def setupDirs(self,configurationFile):
        '''create the results dirs'''
        if(not os.path.exists(self.dirToSaveResults)):
            os.makedirs(self.dirToSaveResults)
        self.timeStart=datetime.datetime.now().strftime("%y-%m-%d-%H-%M") 
        self.savedStateDir=self.dirToSaveResults+self.timeStart+"/"
        if(not os.path.exists(self.savedStateDir)):
            os.makedirs(self.savedStateDir)#create a dir in results dir named after start time that will be used to save state like population and rand state
        atexit.register(self.saveRandstate) #register a function which will save rand state at exit
        
        ''' save configuration src in the results dir '''
        if os.path.exists(self.savedStateDir+"configuration.xml"):
            os.remove(self.savedStateDir+"configuration.xml")
        shutil.copy(configurationFile,self.savedStateDir+"configuration.xml" )
        
        if os.path.exists(self.savedStateDir+"src"):
            shutil.rmtree(self.savedStateDir+"src", ignore_errors=True)  
        shutil.copytree("./src",self.savedStateDir+"src" )
        
        ''' save measurement configuration '''
        if os.path.exists(self.savedStateDir+"measurement.xml"):
            os.remove(self.savedStateDir+"measurement.xml")  
        shutil.copy("./configurationFiles/measurement/"+self.measurementClassConfFile,self.savedStateDir+"measurement.xml")
        
        '''save assembly compilation in the results dir'''
        if os.path.exists(self.savedStateDir+"assembly_compilation"):
            shutil.rmtree(self.savedStateDir+"assembly_compilation", ignore_errors=True)
        shutil.copytree(self.compilationDir,self.savedStateDir+"assembly_compilation")
        if os.path.exists(self.savedStateDir+"assembly_compilation/main.s"):
            os.remove(self.savedStateDir+"assembly_compilation/main.s") #remove this because they belong to previous run and this can get confusing
            os.makedirs(self.savedStateDir + "assembly_compilation/main.s")
        self.compilationDir=self.savedStateDir+"assembly_compilation/"
        print("New compilationDir is "+self.compilationDir)
        
    def __instructions_operands_init__(self):
        self.loopSize = self.xmldoc.getElementsByTagName('loopSize')[0].attributes['value'].value  
        print ("loop Size: " + self.loopSize)
        self.percentage_clue=self.xmldoc.getElementsByTagName('instruction_percentage_clue')[0].attributes['value'].value      
        print("Percentage clue? :"+self.percentage_clue)
        self.instruction_types={}#a dictionary of instruction type and the amount of each instruction in loop.. Note useful only when percentage clue is True
        self.instructions={} #a dictionay that has for keeps an array of instructions for every instruction type
        self.allInstructionArray=[] #An array which hold all instructions
        self.operands={}
        self.toggleInstructionsList={}
        
        itemList = self.xmldoc.getElementsByTagName("instruction_type")
        for instruction_type in itemList:
            name=instruction_type.attributes["id"].value
            perc= instruction_type.attributes["perc"].value
            self.instruction_types[name]= int (float(perc) * float(self.loopSize)) 
            '''calculate how many of these instructions will be in the loop'''
        if(self.percentage_clue=="True"):
            print("amount per instruction type in the loop:")
            print (self.instruction_types)
            sum=0
            for value in list(self.instruction_types.values()):
                sum+=value
            self.loopSize=sum
            print("actual loop size is "+str(self.loopSize))
        
        itemList = self.xmldoc.getElementsByTagName("operand")
        print("Available operands\n")
        for operandDesc in itemList:  
            ins_type=operandDesc.attributes["type"].value
            if (ins_type=="immediate" or ins_type=="constant" or ins_type=="automatically_incremented_operand"):
                anOperand = Operand(id=operandDesc.attributes["id"].value,type=operandDesc.attributes["type"].value,values=[],min=operandDesc.attributes["min"].value,max=operandDesc.attributes["max"].value,stride=operandDesc.attributes["stride"].value,toggleable=operandDesc.attributes["toggle"].value)        
            #elif ins_type=="branch_label":
                #  anOperand = BranchLabel(id=operandDesc.attributes["id"].value,ins_type=operandDesc.attributes["type"].value,values=operandDesc.attributes["values"].value.split(),min=operandDesc.attributes["min"].value,max=operandDesc.attributes["max"].value,stride=operandDesc.attributes["stride"].value,toggleable=operandDesc.attributes["toggle"].value)
            else:
                anOperand = Operand(id=operandDesc.attributes["id"].value,type=operandDesc.attributes["type"].value,values=operandDesc.attributes["values"].value.split(),toggleable=operandDesc.attributes["toggle"].value)
           
            print("id "+anOperand.id.__str__())
            print ("values ")
            print(anOperand.values)
            print("max "+ anOperand.max.__str__())
            print ("min " + anOperand.min.__str__())
            print("stride "+anOperand.stride.__str__()+"\n")
            self.operands[anOperand.id] = anOperand 
        print("End of available operands\n")
       
        itemList = self.xmldoc.getElementsByTagName("instruction")
        print("Available instructions\n")
        for instructionDesc in itemList:
            name=instructionDesc.attributes["name"].value
            ins_type=instructionDesc.attributes["type"].value
            numOfOperands=instructionDesc.attributes["num_of_operands"].value
            if "format" in instructionDesc.attributes:
                anInstruction = Instruction(name,ins_type,numOfOperands,format=instructionDesc.attributes["format"].value,toggleable=instructionDesc.attributes["toggle"].value)
            else:
                print("Instruction "+name+"doesnt have format specified.. All instructions must have format... Exitting")
                sys.exit()
                #anInstruction = Instruction(name,ins_type,numOfOperands,toggleable=instructionDesc.attributes["toggle"].value)
            
            if(instructionDesc.attributes["toggle"].value=="True"):
                self.toggleInstructionsList[instructionDesc.attributes["name"].value]=1
            
            operands=[]#TODO fix this source of bugs..  It's irritating when the num of operands does not match the operands specified in the xml file. and in general is stupid to how the operands specified and the number of operands at the same time.. this redundancy leads to bugs
            for i in range(1,int(anInstruction.numOfOperands)+1):
                operands.append(self.operands[(instructionDesc.attributes["operand"+i.__str__()].value)].copy())
            anInstruction.setOperands(operands)
            print(anInstruction) ##for debugging
            self.instructions.setdefault(anInstruction.ins_type,[]).append(anInstruction)
        #print (self.instructions)
        print("End of available instructions\n")
        
        for array in list(self.instructions.values()):
            for ins in array:
                self.allInstructionArray.append(ins)
        print("register initialization") 
        #print(self.registerInitStr)
        #sys.exit()
       
        
    def printGeneralInputs(self):
        print("Debug Inputs")
        print ("Population size: " +self.populationSize)
        print ("Mutation Rate: "+self.mutationRate)
        print ("Crossover Rate: "+self.crossoverRate)
        if(self.crossoverType==Algorithm.ONEPOINT_CROSSOVER):
            print("Crossover Type: one point crossover")
        elif(self.crossoverType==Algorithm.UNIFORM_CROSSOVER):
            print("Crossover Type: uniform crossover")
            print ("Uniform Rate: "+self.uniformRate)
        print ("Ellitism: "+self.ellitism)
        if(self.selectionMethod==Algorithm.TOURNAMENT_SELECTION):
            print("Selection Method: Tournament")
            print ("Tournament selection size: "+self.tournamentSize)
        elif(self.selectionMethod==Algorithm.WHEEL_SELECTION):
            print("Selection Method: Wheel Selection")
        #print ("Termination Conditions are: ")
        #print("If for "+self.populationsToRun+" populations there is no more than "+self.fitnessThreshold+" improvement stop")
        print ("ResultsDir: "+self.dirToSaveResults)
        print ("compilationDir: "+self.compilationDir)
        
    
    @staticmethod
    def returnRunType(configurationFile):
        xmldoc = minidom.parse(configurationFile)
        run_type = xmldoc.getElementsByTagName('run_type')[0].attributes['value'].value
        if(run_type==Algorithm.PROFILE_RUN):
            return Algorithm.PROFILE_RUN
        else:
            return Algorithm.INSTRUCTION_RUN 
        
    def saveRandstate(self,postfix=""):
        output=open(self.savedStateDir +"rand_state"+postfix+".pkl","wb")
        pickle.dump(self.rand.getstate(),output)
        output.close()
        
    def loadRandstate(self):
        latest=1
        if(not os.path.exists(self.seedDir+"rand_state.pkl")):
            for root, dirs, filenames in os.walk(self.seedDir):
                for f in filenames:
                    if("rand_state" in f):
                        num=int(f.replace("rand_state","").replace(".pkl",""))
                        if(num>latest):
                            latest=num
            stateToLoad="rand_state"+str(latest)+".pkl"
            input=open(self.seedDir+stateToLoad,"rb")
            self.rand.setstate(pickle.load(input))
            input.close()
        else:
            input=open(self.seedDir+"rand_state.pkl","rb")
            self.rand.setstate(pickle.load(input))
            input.close()
        
    '''def __initializeRegisterValues__ (self):#DEPRECATED DON"T USE THIS ANYMORE AS IT MAY LEAD TO BUGS ##remember this functions expects a clean original copy of main.s 
        for line in fileinput.input(self.compilationDir+"/main.s", inplace=1): #TODO keep in mind that it works with and without /
            print(line,end="")
            if "reg init" in line:
                print(self.registerInitStr)
        fileinput.close()
    
    def __initializeMemory__ (self,core=1): #DEPRECATED DON"T USE THIS ANYMORE AS IT MAY LEAD TO BUGS  ##remember this functions expects a clean original copy of main.s
        for line in fileinput.input(self.compilationDir+"/startup.s", inplace=1):
            if "MemoryInit"+str(core) in line:
                print (line,end="")
                print(self.memoryInitArray[core-1])
            else:
                print(line,end="")
        fileinput.close()'''
        
    def createInitialPopulation (self):
        individuals=[]
        if self.seedDir == "": #random initialization
            for i in range(int(self.populationSize)):
                individuals.append(self.__randomlyCreateIndividual__())
            self.population=Population(individuals)
            
            if self.algorithmType == Algorithm.ALPS_ALGORITHM:
                self.alpsAgeLayersLists[0] = individuals
        else: #initial population based on existing individuals.. Useful for continuing runs that where stopped              
            newerPop=0 ##find which is the newest population      
            for root, dirs, filenames in os.walk(self.seedDir):
                for f in filenames:
                    if((".pkl" in f) and ("rand" not in f)):
                        tokens=re.split('[_.]',f)                
                        popNum=int(tokens[0])
                        if (popNum>newerPop):
                            newerPop=popNum
                input = open(self.seedDir+str(newerPop)+'.pkl',mode="rb") 
                self.population=Population.unpickle(input)
                input.close()

            maxId=0##track the maxId
            for indiv in self.population.individuals:
                if(indiv.myId>maxId):
                    maxId=indiv.myId
            
            Individual.id=maxId #the new indiv will start from maxId
            self.bestIndividualUntilNow=self.population.getFittest() #set the best individual seen until now
            self.loopSize=self.bestIndividualUntilNow.getInstructions().__len__() #ensure that loop Size is correct
            self.populationsExamined=newerPop+1#population will start from the newer population
            self.loadRandstate() #load the previous rand state before evolving pop
            self.evolvePopulation() #immediately evolve population
 
        return
  
    def measurePopulation(self):
        for individual in self.population.individuals:
            ##NOTE Due to fluctuations in measurements is desirable to measure the best individual again
            while True:  #measure until measurement succesful... 
                try:
                    measurements=self.__measureIndividual__(individual)
                    measurement=measurements[0]                  
                    measurement_str="%.6f" % float(measurement)        
                    break
                except (ValueError,IOError):
                    continue
                
            individual.setMeasurementsVector(measurements)
            fitnessArray=self.fitness.getFitness(individual)
            fitnessValue=fitnessArray[0]
            individual.setFitness(fitnessValue)
            measurementStr=""
            
            for measurement in fitnessArray:
                measurement_str=("%.6f" % float(measurement)).replace(".","DOT").strip()+"_"
                measurementStr=measurementStr+measurement_str
            if int(self.saveWholeSource)==1:
                fpath=""
                if(individual.belongsToInitialSeed()): 
                    fpath=self.savedStateDir+str(individual.generation)+"_"+str(individual.currentLayer)+"_"+str(individual.myId)+"_"+measurementStr+"0_0_"+str(individual.age) +".txt"
                else:                
                    fpath=self.savedStateDir+str(individual.generation)+"_"+str(individual.currentLayer)+"_"+str(individual.myId)+"_"+measurementStr+str(individual.parents[0].myId)+"_"+str(individual.parents[1].myId)+"_"+str(individual.age) +".txt"
                shutil.copy(self.compilationDir+"/main.s",fpath)
            else:
                if(individual.belongsToInitialSeed()):
                    f = open(self.dirToSaveResults+str(individual.generation)+"_"+str(individual.currentLayer)+"_"+str(individual.myId)+"_"+measurementStr+"0_0_"+str(individual.age) +".txt",mode="w")  
                else:
                    f = open(self.dirToSaveResults+str(individual.generation)+"_"+str(individual.currentLayer)+"_"+str(individual.myId)+"_"+measurementStr+str(individual.parents[0].myId)+"_"+str(individual.parents[1].myId)+"_"+str(individual.age) +".txt",mode="w")
                f.write(individual.__str__())
                f.close()
            
            
            individual.clearParents()#TODO this is just a cheap hack I do for now in order to avoid the recursive grow in length of .pkl files. This is only okay given that I don't actually need anymore that parents.. fon now is okay  
        ##save a file describing the population so it can be loaded later. useful in case of you want to start a run based on the state of previous runs
        
        output = open(self.savedStateDir+str(self.populationsExamined)+'.pkl','wb')
        self.population.pickle(output)
        output.close()
        
        ##also save the rand_state
        self.saveRandstate(postfix=str(self.populationsExamined))
        self.populationsExamined=self.populationsExamined+1
        self.populationsTested=self.populationsTested+1 
         
    def __measureIndividual__(self,individual):
            #####before each individual bring back the original copy of main and startup    
            self.__bring_back_code_template__()
            ####initialize register values in main.s
            #self.__initializeRegisterValues__()
            ####dump memory initialization in startup.s for each core
            #for core in range(1,int(int(self.cores)+1)):
            #    self.__initializeMemory__(core)
            ##apply toggling on operands
            for key in list(self.toggleInstructionsList.keys()):
                self.toggleInstructionsList[key]=1 #first initialize dictionay
            for ins in individual.getInstructions():
                if(ins.toggleable=="True"):
                    if(int(self.toggleInstructionsList[ins.name])%2==1):
                        ins.toggle(0)
                    else:
                        ins.toggle(1)
                    self.toggleInstructionsList[ins.name]+=1         
            #dump the individual into mail loop of main.s
            for line in fileinput.input(self.compilationDir+"/main.s", inplace=1):
                if "loop_code" in line:     
                    print(individual)
                else:
                    print(line,end="")
            fileinput.close()
            '''at last do the actual measurement'''
            measurements= self.__doTheMeasurement__()
            return measurements
        
    '''def __saveIndiv__(self,individual):
            #####before each individual bring back the original copy of main and startup    
            self.__bring_back_code_template__()
            ####initialize register values in main.s
            #self.__initializeRegisterValues__()
            ####dump memory initialization in startup.s for each core
            #for core in range(1,int(int(self.cores)+1)):
            #    self.__initializeMemory__(core)
            ##apply toggling on operands
            for key in list(self.toggleInstructionsList.keys()):
                self.toggleInstructionsList[key]=1 #first initialize dictionay
            for ins in individual.getInstructions():
                if(ins.toggleable=="True"):
                    if(int(self.toggleInstructionsList[ins.name])%2==1):
                        ins.toggle(0)
                    else:
                        ins.toggle(1)
                    self.toggleInstructionsList[ins.name]+=1         
            #dump the individual into mail loop of main.s
            for line in fileinput.input(self.compilationDir+"/main.s", inplace=1):
                if "loop_code" in line:
                    print(individual)
                else:
                    print(line,end="")
            fileinput.close()'''
  
    def __bring_back_code_template__(self):
        #####before each individual bring back the original copy of main and startup
        if(os.path.exists(self.compilationDir +"main.s")):
            os.remove(self.compilationDir +"main.s")
        shutil.copy(self.compilationDir +"main_original.s", self.compilationDir +"main.s")
        # if(os.path.exists(self.compilationDir +"main.s")):
        #     print(f"{self.compilationDir}")
        #     print("copy success!\n")
        
        
        if(os.path.exists(self.compilationDir +"startup.s")):
            os.remove(self.compilationDir +"startup.s")
        #shutil.copy(self.compilationDir +"startup_original.s", self.compilationDir +"startup.s")
    
    def __doTheMeasurement__(self):
        self.measurement.setSourceFilePath(self.compilationDir+"/main.s")
        return self.measurement.measure() 
        
    def __randomlyCreateIndividual__ (self):
        instruction_sequence=[]
        if self.percentage_clue=="True":
            for ins_type in self.instruction_types.keys():##for each instruction type
                for i in range(self.instruction_types[ins_type]): ##create as many instructions as written in the hash
                        instructions=self.instructions[ins_type]
                        instruction_to_copy=instructions[self.rand.randint(0,instructions.__len__()-1)] #choose random one instruction from the available types
                        instruction=instruction_to_copy.copy()
                        instruction.mutateOperands(self.rand) ##initialize randomy the instruction operands
                        instruction_sequence.append(instruction)
                        #print(instruction)
            self.rand.shuffle(instruction_sequence)
        else:
            for i in range(int(self.loopSize)):
                instruction=self.rand.choice(self.allInstructionArray).copy()
                instruction.mutateOperands(self.rand)
                instruction_sequence.append(instruction)
        newIndividual = Individual (instruction_sequence,self.populationsExamined, 0)
        return newIndividual

    def __alps_replaceInitialLayer__(self, number):
        individuals=[]
        for i in range(number):
            individuals.append(self.__randomlyCreateIndividual__())
        self.alpsAgeLayersLists[0] = individuals
        print(f"Actually after recreated, 0th layer has {len(self.alpsAgeLayersLists[0])} indivs.")

    def areWeDone(self):
        self.waitCounter=self.waitCounter+1
        if int(self.waitCounter) == int(self.populationsToRun):
            return True
        else:
            return False
        '''if self.populationsToRun>0:
            if self.populationsToRun==self.populationsTested:
                self.__saveIndiv__(self.bestIndividualUntilNow)
                return True
        current_population_best=self.population.getFittest()
        
        if(self.bestIndividualUntilNow is None): #only for the first time
            self.bestIndividualUntilNow=current_population_best
            self.waitCounter=0
            return False
        
        if float(self.best_pop_target)>0 and current_population_best.getFitness()>=float(self.best_pop_target):
            #SAVE BEST INDIV SOURCE
            self.__saveIndiv__(current_population_best)
            return True
        
        if float(self.avg_pop_target)>0 and self.population.getAvgFitness()>=float(self.avg_pop_target):
            return True
        
        
        if (float(current_population_best.getFitness()) < float(self.bestIndividualUntilNow.getFitness())):
            self.waitCounter=self.waitCounter+1
        else:
            improvement = float(current_population_best.getFitness()) / self.bestIndividualUntilNow.getFitness()
            if (improvement - 1) < float(self.fitnessThreshold):
                self.waitCounter=self.waitCounter+1
            else:
                self.waitCounter=0
            self.bestIndividualUntilNow=current_population_best'''
        
    def __roulletteWheelSelection__ (self):
        individuals=self.population.individuals
        turn=self.rand.randint(0,individuals[individuals.__len__()-1].cumulativeFitness)
        for indiv in self.population.individuals:
            if(int(indiv.cumulativeFitness)>=turn):
                return indiv #return the first indiv that is equal or bigger to the random generated value
            
    def __tournamentSelection__(self, population):
        tournamentIndiv=[]
        for j in range(0,int(self.tournamentSize)):
            tournamentIndiv.append(population.pickRandomlyAnIndividual(self.rand))
        tournamentPop=Population(tournamentIndiv)
        return tournamentPop.getFittest()
            
    def evolvePopulation (self): 
        #individuals=[0]*int(self.populationSize)
        individuals=[]
        self.bestIndividualUntilNow=self.population.getFittest()
        # print(f"{self.bestIndividualUntilNow.generation}th generation bestIndividual is {self.bestIndividualUntilNow.myId}")
        self.bestFitnessHistory.append(self.bestIndividualUntilNow.getFitness())
        with open(self.printLog, "a") as f:
            print(f"bestFitnessHistory since {self.bestIndividualUntilNow.generation}th generation :", file=f)
            print(self.bestFitnessHistory, file=f)
            print("\n", file=f)
        if self.algorithmType == Algorithm.ORIGINAL_ALGORITHM:
            self.__breeding__(individuals)
        else:#ALPS
            self.__alpsBreeding__()
            self.__checkAgeLayers__()
            for i in range(self.alpsNumOfLayers):
                print(f"Number of self.alpsAgeLayersLists[{i}] is {len(self.alpsAgeLayersLists[i])}")
                individuals+=self.alpsAgeLayersLists[i]
        print(f"Total individuals number is {len(individuals)}")
        self.population = Population(individuals)

    def __alpsBreeding__ (self):#we don't maintain generation of individuals in ALPS.
        self.alpsEnvolutions+=1
        # childsCreated=0
        newAgeLayerLists = []

        for i in range(self.alpsNumOfLayers):
            tmpList = []
            newAgeLayerLists.append(tmpList)

        if self.ellitism=="true": 
            for i in range(self.alpsNumOfLayers):
                sortedList = sorted(self.alpsAgeLayersLists[i], key=operator.attrgetter('fitness'), reverse=True)
                if len(self.alpsAgeLayersLists[i]) >= self.ellitismSize:
                    # childsCreated+=self.ellitismSize
                    for j in range(self.ellitismSize):
                        newAgeLayerLists[i].append(copy.deepcopy(sortedList[j]))
                        newAgeLayerLists[i][j].age += 1
                        newAgeLayerLists[i][j].generation += 1
                elif len(self.alpsAgeLayersLists[i]) < self.ellitismSize and len(self.alpsAgeLayersLists[i]) > 0:
                    newAgeLayerLists[i] = copy.deepcopy(self.alpsAgeLayersLists[i])
                    # childsCreated+=len(self.alpsAgeLayersLists[i])
                    for j in range(len(newAgeLayerLists[i])):
                        newAgeLayerLists[i][j].age += 1
                        newAgeLayerLists[i][j].generation += 1
                else:
                    pass
    
        for i in range(self.alpsNumOfLayers):
            if len(self.alpsAgeLayersLists[i]) > self.ellitismSize:
                prepareForCreate = len(self.alpsAgeLayersLists[i]) - self.ellitismSize
                while prepareForCreate>0:
                    if(self.selectionMethod==Algorithm.WHEEL_SELECTION):
                        print(f"we don't support WHEEL_SELECTION with ALPS until now!")
                        sys.exit()
                    else:#tournament
                        if i==0:
                            ageLayerPopulation = Population(self.alpsAgeLayersLists[i])
                            indiv1=self.__tournamentSelection__(ageLayerPopulation)
                            indiv2=self.__tournamentSelection__(ageLayerPopulation)
                        else:
                            ageLayerPopulation1 = Population(self.alpsAgeLayersLists[i])
                            ageLayerPopulation2 = Population(self.alpsAgeLayersLists[i]+self.alpsAgeLayersLists[i-1])
                            indiv1=self.__tournamentSelection__(ageLayerPopulation1)
                            indiv2=self.__tournamentSelection__(ageLayerPopulation2)
                        maxAgeOfParents = indiv1.age if (indiv1.age>indiv2.age) else indiv2.age
                        if(self.rand.random()<=float(self.crossoverRate)): #According to some sources there should be a slight chance some parents to not change , hence the crossoverRate parameter 
                            if(self.crossoverType==Algorithm.UNIFORM_CROSSOVER):
                                children=self.__uniform_crossover__(indiv1, indiv2)
                            elif (self.crossoverType==Algorithm.ONEPOINT_CROSSOVER):
                                children=self.__onePoint_crossover__(indiv1, indiv2)  
                        else:
                            children=[]
                            children.append(indiv1)
                            children.append(indiv2)

                        for child in children:
                            child.age = maxAgeOfParents + 1
                            child.currentLayer = indiv1.currentLayer
                            self.__mutation__(child) #mutate each child and add it to the list
                            child.fixUnconditionalBranchLabels()##Due to crossover and mutation we must fix any possible duplicate branch labels
                            newAgeLayerLists[i].append(child) #I don't want to waste any child so some populations can be little bigger in number of individuals
                            prepareForCreate-=1
                            # childsCreated+=1
        
        for i in range(self.alpsNumOfLayers):
            self.alpsAgeLayersLists[i]=newAgeLayerLists[i]

    def __checkAgeLayers__(self):
        for i in range(self.alpsNumOfLayers-1):
            self.alpsAgeLayersLists[i].sort(key=operator.attrgetter('age'))
        
        needMovePerLayer = [0] * (self.alpsNumOfLayers - 1)
        for i in range(self.alpsNumOfLayers-1):
            num=0
            for item in self.alpsAgeLayersLists[i]:
                if item.age >= self.alpsAgeLists[i]:
                    num+=1
                else:
                    break
            needMovePerLayer[i]=num
            print(f"The number of individuals praparing to upgrade in {i}th  is {needMovePerLayer[i]}")           
        
        for i in range(self.alpsNumOfLayers-1): #if individual in the highest age layer, it will never move up.
            while needMovePerLayer[i]>0:
                needMoveIndiv = self.alpsAgeLayersLists[i][0]
                self.alpsAgeLayersLists[i].remove(needMoveIndiv)
                self.alpsAgeLayersLists[i+1].append(needMoveIndiv)
                needMovePerLayer[i]-=1
        
        replaceInBottomLayer=len(self.alpsAgeLayersLists[1])-self.alpsMaxIndivsPerLayer
        
        for i in range(1, self.alpsNumOfLayers-1):
            while len(self.alpsAgeLayersLists[i]) > self.alpsMaxIndivsPerLayer:
                weakestIndiv = Population(self.alpsAgeLayersLists[i]).getWeakest()
                self.alpsAgeLayersLists[i].remove(weakestIndiv)
                #TODO try move up weakestIndiv
        
        statisticsMoveup = [0] * (self.alpsNumOfLayers)
        for i in range(1, self.alpsNumOfLayers):
            for item in self.alpsAgeLayersLists[i]:
                if item.currentLayer != i:
                    statisticsMoveup[i]+=1
                    item.currentLayer=i
            print(f"Actually {i}th layer has {statisticsMoveup[i]} new upgrade individual.")
        
        print(f"0th layer should recreate {replaceInBottomLayer} indivs.")
        if self.alpsEnvolutions%self.alpsAgeGap==0:
            self.__alps_replaceInitialLayer__(replaceInBottomLayer)          

    def __breeding__(self, individuals):
        if self.ellitism=="true": 
            if self.ellitismSize==1:
                individuals.append(self.bestIndividualUntilNow)
                self.bestIndividualUntilNow.generation+=1 #For the next measurement the promoted individuals will be recorded as individuals of the next population.. Is just for avoiding confusions when processing the results 
                childsCreated=1
            else:
                goodIndividualsUntilNow = self.population.getGoodFittest(self.ellitismSize)
                for i in range(self.ellitismSize):
                    individuals.append(goodIndividualsUntilNow[i])
                    goodIndividualsUntilNow[i].generation+=1
                childsCreated+=self.ellitismSize
        else:
            childsCreated=0
        if(self.selectionMethod==Algorithm.WHEEL_SELECTION):
            self.population.keepPartBest()##sightly algorithm change apply roullete on best 50%
            self.population.setCumulativeFitness()
        diversity_check = set()
        while childsCreated<int(self.populationSize):
            # print(diversity_check)
            if(self.selectionMethod==Algorithm.WHEEL_SELECTION):
                # Create two children by crossovering two parent selected with the wheel method
                indiv1=self.__roulletteWheelSelection__()
                indiv2=self.__roulletteWheelSelection__()
                #Forbid using the same parents repeatedly or having identical parents.
                while(indiv1==indiv2 or (str(indiv1.myId)+" "+str(indiv2.myId)) in diversity_check or (str(indiv2.myId)+" "+str(indiv1.myId)) in diversity_check):
                    indiv1=self.__roulletteWheelSelection__()
                    indiv2=self.__roulletteWheelSelection__()##the parents must be different TODO check how others do it
                diversity_check.add(str(indiv1.myId)+" "+str(indiv2.myId))

            else:#tournament
                indiv1=self.__tournamentSelection__(self.population)
                indiv2=self.__tournamentSelection__(self.population)
                #Forbid using the same parents repeatedly or having identical parents.
                while(indiv1==indiv2 or (str(indiv1.myId)+" "+str(indiv2.myId)) in diversity_check or (str(indiv2.myId)+" "+str(indiv1.myId)) in diversity_check):
                    indiv1=self.__tournamentSelection__(self.population)
                    indiv2=self.__tournamentSelection__(self.population)
                diversity_check.add(str(indiv1.myId)+" "+str(indiv2.myId))

            if(self.rand.random()<=float(self.crossoverRate)): #According to some sources there should be a slight chance some parents to not change , hence the crossoverRate parameter 
                if(self.crossoverType==Algorithm.UNIFORM_CROSSOVER):
                    children=self.__uniform_crossover__(indiv1, indiv2)
                elif (self.crossoverType==Algorithm.ONEPOINT_CROSSOVER):
                    children=self.__onePoint_crossover__(indiv1, indiv2)
            else:
                children=[]
                children.append(indiv1)
                children.append(indiv2)
            for child in children:
                self.__mutation__(child) #mutate each child and add it to the list
                child.fixUnconditionalBranchLabels()##Due to crossover and mutation we must fix any possible duplicate branch labels
                individuals.append(child) #I don't want to waste any child so some populations can be little bigger in number of individuals
                childsCreated+=1
      
    def __mutation__ (self,individual):##options for mutation whole instructions or instruction's operands
        instructions=individual.getInstructions()
        for i in range(instructions.__len__()):
            if self.rand.random()<=float(self.mutationRate):
                instruction=self.rand.choice(self.allInstructionArray).copy() #choose random one instruction
                instruction.mutateOperands(self.rand) ##initialize randomy the instruction operands
                instructions[i]=instruction
                '''if(self.rand.randint(0,1) ==1): #in this case change the whole instructions
                    instruction=self.rand.choice(self.allInstructionArray).copy() #choose random one instruction
                    instruction.mutateOperands(self.rand) ##initialize randomy the instruction operands
                    instructions[i]=instruction
                else: #in this case just mutate the operands
                    instructions[i].mutateOperands(self.rand)'''
                
    def __uniform_crossover__(self,individual1,individual2):#creates two new individuals
        #newIndiv=Individual() TODO find out this weird bug.. for some reason the newIndiv wasn't reinitializedThis is the default behaviour of python when I use a muttable object for optional parameter
        loop_code1=[]
        loop_code2=[]
        for i in range(int(self.loopSize)):
            if(self.rand.random()<=float(self.uniformRate)): #do crossover
                loop_code1.append(individual2.getInstruction(i).copy())
                loop_code2.append(individual1.getInstruction(i).copy())
            else: #keep instruction as it is
                loop_code1.append(individual1.getInstruction(i).copy())
                loop_code2.append(individual2.getInstruction(i).copy())
        children=[]
        children.append(Individual(sequence=loop_code1,generation=self.populationsExamined))
        children.append(Individual(sequence=loop_code2,generation=self.populationsExamined))
        children[0].setParents(individual1,individual2) ##the first parent is the code that remains the same.. the second parent is the code that came after crossover
        children[1].setParents(individual2,individual1)
        return children 
    
    def __onePoint_crossover__(self,individual1,individual2):#creates two new individuals
        #newIndiv=Individual() TODO find out this weird bug.. for some reason the newIndiv wasn't reinitializedThis is the default behaviour of python when I use a muttable object for optional parameter # Solved look here for the answer http://stackoverflow.com/questions/1132941/least-astonishment-in-python-the-mutable-default-argument
        loop_code1=[]
        loop_code2=[]
        crossover_point = self.rand.choice(range(int(self.loopSize)-1))
        for i in range(int(self.loopSize)):
            if(i>crossover_point):
                #do crossover
                loop_code1.append(individual2.getInstruction(i).copy())
                loop_code2.append(individual1.getInstruction(i).copy())
            else: #keep instruction as it is
                loop_code1.append(individual1.getInstruction(i).copy())
                loop_code2.append(individual2.getInstruction(i).copy())
        children=[]
        children.append(Individual(sequence=loop_code1,generation=self.populationsExamined))
        children.append(Individual(sequence=loop_code2,generation=self.populationsExamined))
        children[0].setParents(individual1,individual2) ##the first parent is the code that remains the same.. the second parent is the code that came after crossover
        children[1].setParents(individual2,individual1)
        return children 
    
    def getFittest(self):
        return self.population.getFittest()
    
