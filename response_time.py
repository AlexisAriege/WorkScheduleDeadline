#!/usr/bin/python

from bcc import BPF
from time import sleep


# define BPF Program
prog="""
#include <linux/sched.h>

// define output data structure in C
struct data_t {
    u32 pid;
    u64 ts;
    char comm[TASK_COMM_LEN];
    unsigned int overrun;
    u64 end;
};

BPF_PERF_OUTPUT(events);

int kretprobe__update_curr_dl(struct pt_regs *ctx)
{
        struct data_t data = {};
        struct task_struct *task;
        struct sched_dl_entity *dl_se;
	    task = (struct task_struct *) bpf_get_current_task();
        dl_se = &task->dl;
        data.end = 0;
        if ((*dl_se).dl_throttled && !((*dl_se).dl_yielded)) {
            data.end = 2;
        }
        else {
	       if ((*dl_se).dl_yielded) {
                data.end = 1;
	        }
        }
    data.pid = bpf_get_current_pid_tgid();
    data.ts  = bpf_ktime_get_ns();
    bpf_get_current_comm(&data.comm, sizeof(data.comm));
    events.perf_submit(ctx, &data, sizeof(data));
    return 0;
}
"""

# load BPF program
b = BPF(text=prog)

# header
print("%-18s %-16s %-6s %s" % ("TIME(s)", "COMM", "PID", "MESSAGE"))

# process event
start = 0
def print_event(cpu, data, size):
    global start
    event = b["events"].event(data)
    if start == 0:
            start = event.ts
    time_s = (float(event.ts - start)) / 1000000000
    print("%-18.9f %-16s %-6d end %d" % (time_s, event.comm, event.pid, event.end
        ))

# loop with callback to print_event
b["events"].open_perf_buffer(print_event)
while 1:
    b.perf_buffer_poll()
