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
        self.repeatedMeasurements = self.tryGetIntValue('repeated_measurements')
    
    def measure(self):  
        super().copyFileOverFTP()
        compilation_command="cd "+self.targetRunDir + " && gcc main.s -o individual"
        execution_command=self.targetRunDir + "individual & perf stat -e instructions,cycles -o " + self.targetRunDir + "tmp -p $! & sleep " + str(self.timeToMeasure) + " && pkill individual"
        output_ins_command="cd " + self.targetRunDir + " && cat tmp | grep insn | awk '{print $1}'"
        output_cycles_command="cd " + self.targetRunDir + " && cat tmp | grep cycles | awk '{print $1}'"
        lines = super().executeSSHcommand(compilation_command)
        lines = super().executeSSHcommand(execution_command)

        # ins = super().executeSSHcommand(output_ins_command)
        # cycles = super().executeSSHcommand(output_cycles_command)
        ipc=0
        ins_total=0
        cycles_total=0
        for i in range(self.repeatedMeasurements):
            ins = super().executeSSHcommand(output_ins_command)
            cycles = super().executeSSHcommand(output_cycles_command)
            while not ins or not cycles:
                super().executeSSHcommand(execution_command)
                ins = super().executeSSHcommand(output_ins_command)
                cycles = super().executeSSHcommand(output_cycles_command)
            try:
                ins_out = float(ins[0].replace(",", "").strip()) ##used for X86 plaform.
                # ins_out = float(ins[0].strip()) #used for ARM plaform.
                # print(f"ins_out is {ins_out}")
                ins_total += ins_out
            except ValueError:
                print ("Exception line not ins")        
            try:
                cycles_out = float(cycles[0].replace(",", "").strip()) ##used for X86 plaform.
                # cycles_out = float(cycles[0].strip()) #used for ARM plaform.
                # print(f"cycles_out is {cycles_out}")
                cycles_total += cycles_out
            except ValueError:
                print ("Exception line not cycles")
        ipc = "%.6f" % float(ins_total/cycles_total)
        
        measurements=[]
        measurements.append(ipc)
        # print(f"measurements is {measurements }")
        return measurements
            #return ipc
