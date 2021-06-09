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
BPF_PERF_ARRAY(cpu_cycles, 12);



struct data {
    u64 pid;
    char comm[TASK_COMM_LEN];
    u64 ts;
    u64 cycle;
    u32 id_cpu;
};

BPF_PERF_OUTPUT(events);

int counter_ipc(struct bpf_perf_event_data *ctx) {
    struct data s = {};

    s.pid = bpf_get_current_pid_tgid();
    s.ts = bpf_ktime_get_ns();
    bpf_get_current_comm(&s.comm, sizeof(s.comm));

    int cpu = bpf_get_smp_processor_id();
    int value = cpu_cycles.perf_read(cpu);
    if ( value<0 ){
        s.cycle=0;
    }
    else s.cycle=value;
    s.id_cpu = cpu;
    events.perf_submit(ctx, &s, sizeof(s));
    return 0;
}
"""

b = BPF(text=code)

try:
    b.attach_perf_event(
        ev_type=PerfType.HARDWARE, ev_config=PerfHWConfig.INSTRUCTIONS,
        fn_name="counter_ipc",cpu=2, sample_period=1000000)

except Exception:
    print("Failed to attach to a hardware event. Is this a virtual machine?")
    exit()
PERF_TYPE_RAW = 4
b["cpu_cycles"].open_perf_event(PERF_TYPE_RAW, 0x0000003C)
start = 0
def print_event(cpu, data, size):
    event = b["events"].event(data)
    global start
    if start == 0:
            start = event.ts
    time_s = (float(event.ts - start)) / 1000000000
    print("t=%6.5f ,cpu=%d, valeur IPC=%d" % (time_s,event.id_cpu ,event.cycle))
b["events"].open_perf_buffer(print_event)
while True:
	try:
    	    b.perf_buffer_poll()
	except KeyboardInterrupt:
            exit()