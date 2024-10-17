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

from Measurement.Measurement import Measurement
import time

class MeasurementIPC(Measurement):
    '''
    classdocs
    '''
    
    def __init__(self,confFile):
        super().__init__(confFile)
     
    
    def init(self):
        super().init()
        self.timeToMeasure = self.tryGetIntValue('time_to_measure')
    
    def measure(self):  
        super().copyFileOverFTP()
        compilation_command="cd "+self.targetRunDir + " && gcc main.s -o individual"
        execution_command=self.targetRunDir + "individual & perf stat -e instructions,cycles -o " + self.targetRunDir + "tmp -p $! & sleep " + str(self.timeToMeasure) + " && pkill individual"
        output_ins_command="cd " + self.targetRunDir + " && cat tmp | grep insn | awk '{print $1}'"
        output_cycles_command="cd " + self.targetRunDir + " && cat tmp | grep cycles | awk '{print $1}'"
        super().executeSSHcommand(compilation_command)
        super().executeSSHcommand(execution_command)
        ins = super().executeSSHcommand(output_ins_command)
        cycles = super().executeSSHcommand(output_cycles_command)
        ipc_old = super().executeSSHcommand("cd " + self.targetRunDir + " && cat tmp | grep insn | awk '{print $4}'")
        print(ipc_old)

        ipc=0
        ins_test=0
        cycles_test=0
        for line in ins:
            try:
                ins_test = float(line.replace(",", ""))     
            except ValueError:
                print ("Exception line not ins")        
        for line in cycles:
            try:
                cycles_test = float(line.replace(",", ""))      
            except ValueError:
                print ("Exception line not cycles")
        ipc = "%.6f" % float(ins_test/cycles_test)
        
        measurements=[]
        measurements.append(ipc)
        print(f"measurements is {measurements }")
        return measurements
            #return ipc
