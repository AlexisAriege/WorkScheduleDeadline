#define _GNU_SOURCE
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <linux/unistd.h>
#include <linux/kernel.h>
#include <linux/types.h>
#include <sys/syscall.h>
#include <pthread.h>
#include <signal.h>

 #define gettid() syscall(__NR_gettid)

 #define SCHED_DEADLINE	6
 #define SCHED_FLAG_DL_OVERRUN 0x04

 /* XXX use the proper syscall numbers */
 #ifdef __x86_64__
 #define __NR_sched_setattr		314
 #define __NR_sched_getattr		315
 #endif

 #ifdef __i386__
 #define __NR_sched_setattr		351
 #define __NR_sched_getattr		352
 #endif

 #ifdef __arm__
 #define __NR_sched_setattr		380
 #define __NR_sched_getattr		381
 #endif

static volatile int done;

struct sched_attr {
 __u32 size;

 __u32 sched_policy;
 __u64 sched_flags;

 /* SCHED_NORMAL, SCHED_BATCH */
 __s32 sched_nice;

 /* SCHED_FIFO, SCHED_RR */
 __u32 sched_priority;

 /* SCHED_DEADLINE (nsec) */
 __u64 sched_runtime;
 __u64 sched_deadline;
 __u64 sched_period;
};

int sched_setattr(pid_t pid,
     const struct sched_attr *attr,
     unsigned int flags)
{
 return syscall(__NR_sched_setattr, pid, attr, flags);
}


int sched_getattr(pid_t pid,
     struct sched_attr *attr,
     unsigned int size,
     unsigned int flags)
{
 return syscall(__NR_sched_getattr, pid, attr, size, flags);
}

struct list {
        int *data;
        struct list *next;
};

struct data_thread {
        int *list_label;
        int size;
};

#define number_thread 1

void *function_thread(void *arg) {
        struct data_thread *data;
        data = (struct data_thread*) arg;
        struct list *my_list;
        my_list = (struct list *)malloc(7*sizeof( struct list ));// 7 changeable
        for (int i=0;i<7;i++) {
                my_list[i].data = malloc((data->size)*sizeof( int ));
        }
        //while !donnemes of macros defining constants and labels in enums are capit
        struct list actual;
        actual=my_list[0];
        int i=0;
        struct sched_attr attr;
        int x = 0;
        int ret;
        unsigned int flags = 0;
        printf("deadline thread started [%ld]\n", gettid());
        attr.size = sizeof(attr);
          //attr.sched_flags = SCHED_FLAG_DL_OVERRUN;
        attr.sched_flags = 0;
        attr.sched_nice = 0;
        attr.sched_priority = 0;
        /* This creates a 10ms/30ms reservation */
        attr.sched_policy = SCHED_DEADLINE;
        attr.sched_runtime = 2 *1000* 1000;//runtime
        attr.sched_period = attr.sched_deadline =100* 1000* 1000;// period
        ret = sched_setattr(0, &attr, flags);
        if (ret < 0) {
          done = 0;
          perror("sched_setattr");
          exit(-1);
        }
        while(done == 0){
                //mettre un for ici
                for (int j=0;j<50000;j++) {
                        actual.data[i%(data->size)]=i;
                        actual.next =&my_list[data->list_label[i%(7*3)]];
                        actual=*(actual.next);
                        i++;
                }
                printf("fin \n");
                sched_yield();
        }
        for (int i=0;i<7;i++) {
                free(my_list[i].data);
        }
        free(my_list);
        return NULL;
}

int main(int argc, char *argv[]) {
        // Le role de ce script est de générer X thread qui vont accéder à des listes chainées aléatoirement pour remplir les caches mémoires d'un cpu.
        //int i;
//    application
        done=0;
        int flag_size=0; //size
        int flag_duration=0;
        for (int i=1; i<argc; i++) {
                if (strcmp(argv[i],"--help") == 0) {//rajout de lecture ou ecriture des threads
                        printf("---------- Setting for this application ---------- \n");
                        printf("--size (-s) for the size of data in thread (default = 3MB) \n");
                        printf("--duration (-d) for set the duration of data writting (default = 10s)\n");
                        return 0;
                }
                if ((strcmp(argv[i],"--size") == 0) || (strcmp(argv[i],"-s") == 0)) {
                        flag_size=i;
                }
                if ((strcmp(argv[i],"--duration") == 0) || (strcmp(argv[i],"-d") == 0)) {
                        flag_duration=i;
                }
        }
        int size=3145728; // size par défaut

      //  int number_thread=1;
        int duration_stress=10;
        if (flag_size > 0) {
                if (sscanf(argv[flag_size+1], "%d", &size) != 1) {
                        printf("\n Integer awaited after --size \n");
                        exit(EXIT_FAILURE);
                }
        }
        if (flag_duration > 0) {
                if (sscanf(argv[flag_duration+1], "%d", &duration_stress) != 1) {
                        printf("\n Integer awaited after --duration (s) \n");
                        exit(EXIT_FAILURE);
                }
        }
        pthread_t *thread_data;
        thread_data = malloc(number_thread*sizeof( pthread_t ));
        srand(time(NULL));
        struct data_thread *data_table;
        data_table = (struct data_thread *)malloc(number_thread*sizeof( struct data_thread ));
        for (int i = 0; i < number_thread; i++) {
                data_table[i].list_label = malloc(7*3*sizeof( int ));
                data_table[i].size=size;
                for (int j=0;j<21;j++) {
                        data_table[i].list_label[j]=(rand()%7);
                }
        }
        for (int i=0;i<number_thread;i++) {
                pthread_create(&thread_data[i],NULL,function_thread,&data_table[i]);
        }
        sleep(duration_stress);
        done=1;
        for (int i=0;i<number_thread;i++) {
                pthread_join(thread_data[i], NULL);
        }
        for (int i = 0; i < number_thread; i++){
                free(data_table[i].list_label);
        }
        free(data_table);
        free(thread_data);
        return 0;
}
