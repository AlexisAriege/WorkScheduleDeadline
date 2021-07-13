#!/usr/bin/python
# IPC - Instructions Per Cycles using Perf Events and
# uprobes
# 24-Apr-2020	Saleem Ahmad	Created this.

from __future__ import print_function
import argparse
from bcc import BPF, PerfType, PerfHWConfig
import signal
from time import sleep

# load BPF program



code="""
#include <uapi/linux/ptrace.h>
#include <uapi/linux/perf_event.h>
#include <linux/sched.h>

//associé
BPF_PERF_ARRAY(cpu_instructions, 12);
BPF_PERF_ARRAY(cpu_cycles, 12);

BPF_HISTOGRAM(dist);
BPF_HASH(last);

BPF_PERF_OUTPUT(events);

int counter_ipc(struct bpf_perf_event_data *ctx) {
    u64 key_instruction = 0;
    u64 key_cycle = 1;
    u64 *result_instruction;
    u64 *result_cycle;
    int flag_cycle=0;
    int flag_instruction=0;

    u64 cycle;
    u64 instruction;
    u64 cycle_intervalle;
    u64 instruction_intervalle;

    int cpu = bpf_get_smp_processor_id();
    key_instruction=(u64)cpu+12;//car 12 coeur donc map de taille de 24
    key_cycle=(u64)cpu;

    result_instruction = last.lookup(&key_instruction);
    result_cycle = last.lookup(&key_cycle);
    if (result_instruction != NULL) {
        flag_instruction=1;
    }
    if (result_cycle != NULL) {
        flag_cycle=1;
    }
    //ts = bpf_ktime_get_ns();

//bloc mesure des cycles et instructions
    u64 value = cpu_cycles.perf_read(cpu);
    if ( (s64)value<0 ){
        cycle=0;
    }
    else cycle=value;

    u64 value_instructions = cpu_instructions.perf_read(cpu);
    if ( (s64)value_instructions<0 ){
        instruction=0;
    }
    else instruction=value_instructions;


//bloc affectation des IPC
    if ((flag_instruction==1) && (flag_cycle==1)) {

        last.delete(&key_instruction);
        last.delete(&key_cycle);

        cycle_intervalle=cycle-*result_cycle;
        instruction_intervalle=instruction-*result_instruction;
        float ipc;
        ipc = (float)instruction_intervalle/cycle_intervalle;
        //dist.increment(ipc);
    }
    last.update(&key_instruction, &instruction);
    last.update(&key_cycle, &cycle);
    return 0;
}
"""

b = BPF(text=code)

try:
    b.attach_perf_event(
        ev_type=PerfType.HARDWARE, ev_config=PerfHWConfig.INSTRUCTIONS,
        fn_name="counter_ipc",sample_period=50000000) #, sample_freq=1



except Exception:
    print("Failed to attach to a hardware event. Is this a virtual machine?")
    exit()
PERF_TYPE_RAW = 4
b["cpu_cycles"].open_perf_event(PERF_TYPE_RAW, 0x0000003C)
#Instruction
b["cpu_instructions"].open_perf_event(PERF_TYPE_RAW, 0x000000C0)
#b["cpu_cycles"].open_perf_event(b["cpu_cycles"].HW_CPU_CYCLES)
#start = 0
#file_result_ipc = open("file_result_ipc.txt", "w")
#def print_event(cpu, data, size):
    #event = b["events"].event(data)
    #global start
    #if start == 0:
    #        start = event.ts
    #time_s = (float(event.ts - start)) / 1000000000
    #file_result_ipc.write("t=%6.5f ;%d;%d;%d \n" % (time_s,event.id_cpu ,event.cycle, event.instruction))
    #print("t=%6.5f ,cpu=%d, valeur cycle=%d, instruction=%d" % (time_s,event.id_cpu ,event.cycle, event.instruction))
#b["events"].open_perf_buffer(print_event)
while True:
	try:
    	    #b.perf_buffer_poll()
            a=1
	except KeyboardInterrupt:
            b["dist"].print_linear_hist("usecs")
            b["dist"].clear()
            #file_result_ipc.close()
            exit()
