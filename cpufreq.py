

from __future__ import print_function
from bcc import BPF
from bcc.utils import printb

# load BPF program
b = BPF(text="""
TRACEPOINT_PROBE(power, cpu_frequency) {
    // args is from /sys/kernel/debug/tracing/events/power/cpu_frequency/format
    bpf_trace_printk("%lu f %lu\\n",args->cpu_id,args->state);
    return 0;
}
""")

# header
print("%-18s %-16s %-6s %s" % ("TIME(s)", "COMM", "PID", "ID + f (Hz)"))

# format output
while 1:
    try:
        (task, pid, cpu, flags, ts, msg) = b.trace_fields()
    except ValueError:
        continue
    except KeyboardInterrupt:
        exit()
    printb(b"%-18.9f %-16s %-6d %s" % (ts, task, pid, msg))
