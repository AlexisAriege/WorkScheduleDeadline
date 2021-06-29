#!/usr/bin/python

from bcc import BPF
from time import sleep


# define BPF Program
prog="""
#include <linux/sched.h>

struct stamp_t {
    u64 pid;
    char comm[TASK_COMM_LEN];
    u64 ts;
    u64 end;
};

BPF_RINGBUF_OUTPUT(stamp, 8);

int kretprobe__update_curr_dl(struct pt_regs *ctx)
{
        struct stamp_t s = {};
        struct task_struct *task;
        struct sched_dl_entity *dl_se;
	    task = (struct task_struct *) bpf_get_current_task();
        dl_se = &task->dl;
        if ((*dl_se).dl_throttled && !((*dl_se).dl_yielded)) {

            s.end = 2;
            s.pid = bpf_get_current_pid_tgid();
            s.ts  = bpf_ktime_get_ns();
            bpf_get_current_comm(&s.comm, sizeof(s.comm));
            stamp.ringbuf_output(&s, sizeof(s), BPF_RB_FORCE_WAKEUP);
        }
    return 0;
}

TRACEPOINT_PROBE(syscalls, sys_enter_sched_yield)
{
    struct stamp_t s = {};
    s.end = 1;
    s.pid = bpf_get_current_pid_tgid();
    s.ts  = bpf_ktime_get_ns();
    bpf_get_current_comm(&s.comm, sizeof(s.comm));
    stamp.ringbuf_output(&s, sizeof(s), BPF_RB_FORCE_WAKEUP);
    return 0;
}

TRACEPOINT_PROBE(syscalls, sys_exit_sched_yield)
{
    struct stamp_t s = {};
    s.end = 0;
    s.pid = bpf_get_current_pid_tgid();
    s.ts  = bpf_ktime_get_ns();
    bpf_get_current_comm(&s.comm, sizeof(s.comm));
    stamp.ringbuf_output(&s, sizeof(s), BPF_RB_FORCE_WAKEUP);
    return 0;
}


"""

# load BPF program
b = BPF(text=prog)

# header
print("%-18s %-16s %-6s %s" % ("TIME(s)", "COMM", "PID", "MESSAGE"))

# process event
start = 0
def print_stamp(ctx, data, size):
    global start
    stamp = b['stamp'].event(data)
    if start == 0:
            start = stamp.ts
    time_s = (float(stamp.ts - start)) / 1000000000
    print("%-18.9f %-16s %-6d end %d" % (time_s, stamp.comm, stamp.pid, stamp.end
        ))
# loop with callback to print_event
b['stamp'].open_ring_buffer(print_stamp)
while 1:
    b.ring_buffer_poll()
