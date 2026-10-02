/* Generated-bundle launcher; embedded_bundle.inc is produced by package.sh. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <libgen.h>
#include <limits.h>
#include <signal.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>
struct Embedded { const char *name; const unsigned char *data; size_t size; mode_t mode; };
#include "embedded_bundle.inc"
static volatile sig_atomic_t child_pid=-1, received_signal=0;
static void fail(const char *f,...){va_list a;va_start(a,f);fputs("cix9: ",stderr);vfprintf(stderr,f,a);fputc('\n',stderr);va_end(a);}
static void forward_signal(int s){received_signal=s;if(child_pid>0)kill((pid_t)child_pid,s);}
static int join(char *o,size_t n,const char *a,const char *b){int r=snprintf(o,n,"%s/%s",a,b);return r>=0&&(size_t)r<n?0:-1;}
static int write_all(int fd,const unsigned char *p,size_t n){while(n){ssize_t w=write(fd,p,n);if(w<0){if(errno==EINTR)continue;return -1;}if(w==0){errno=EIO;return -1;}p+=(size_t)w;n-=(size_t)w;}return 0;}
static void cleanup(const char *d){for(size_t i=0;i<embedded_files_count;i++){char p[PATH_MAX];if(!join(p,sizeof p,d,embedded_files[i].name))unlink(p);}rmdir(d);}
static int setup(char d[PATH_MAX]){char cwd[PATH_MAX];if(!getcwd(cwd,sizeof cwd)||join(d,PATH_MAX,cwd,".cix9.XXXXXX")||!mkdtemp(d)){fail("cannot create private runtime under current directory: %s",strerror(errno));return -1;}for(size_t i=0;i<embedded_files_count;i++){char p[PATH_MAX];if(join(p,sizeof p,d,embedded_files[i].name)){cleanup(d);return -1;}int fd=open(p,O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC,embedded_files[i].mode);if(fd<0){cleanup(d);return -1;}if(write_all(fd,embedded_files[i].data,embedded_files[i].size)||fsync(fd)){close(fd);cleanup(d);return -1;}if(close(fd)){cleanup(d);return -1;}}return 0;}
static int run(const char *d,char *const a[]){sigset_t block,old;sigemptyset(&block);sigaddset(&block,SIGINT);sigaddset(&block,SIGTERM);if(received_signal)return 128+received_signal;if(sigprocmask(SIG_BLOCK,&block,&old))return -1;if(received_signal){sigprocmask(SIG_SETMASK,&old,0);return 128+received_signal;}pid_t p=fork();if(p<0){sigprocmask(SIG_SETMASK,&old,0);return -1;}if(!p){sigprocmask(SIG_SETMASK,&old,0);unsetenv("LD_PRELOAD");unsetenv("LD_AUDIT");if(setenv("LD_LIBRARY_PATH",d,1))_exit(126);execv(a[0],a);_exit(127);}child_pid=p;sigprocmask(SIG_SETMASK,&old,0);int st;while(waitpid(p,&st,0)<0){if(errno!=EINTR){child_pid=-1;return -1;}}child_pid=-1;return received_signal?128+received_signal:(WIFEXITED(st)?WEXITSTATUS(st):1);}
static int operation(int encode){char d[PATH_MAX],bin[PATH_MAX];if(setup(d))return 1;if(received_signal){cleanup(d);return 128+received_signal;}if(join(bin,sizeof bin,d,"cix")){cleanup(d);return 1;}char *enc[]={bin,"--best","--threads","1","--verbose","-o","archive9.bhm","enwik9",NULL};char *dec[]={bin,"-d","-o","data9","archive9.bhm",NULL};int r=run(d,encode?enc:dec);cleanup(d);return r;}
int main(int argc,char **argv){
if(argc!=1){fail("no options are accepted");return 2;}
struct sigaction sa;memset(&sa,0,sizeof sa);sa.sa_handler=forward_signal;sigemptyset(&sa.sa_mask);sigaction(SIGINT,&sa,0);sigaction(SIGTERM,&sa,0);
char *b=basename(argv[0]);
if(!strcmp(b,"comp9a"))return operation(1);
if(!strcmp(b,"decomp9"))return operation(0);
fail("install as comp9a or decomp9");return 2;
}
