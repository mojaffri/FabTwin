#include "controller.hpp"
#include <cstdio>
#include <cstring>
#include <new>

#ifdef _WIN32
#define API extern "C" __declspec(dllexport)
#else
#define API extern "C" __attribute__((visibility("default")))
#endif
using namespace fabtwin;
static unsigned crc16(const char* data, size_t n) {
    unsigned crc=0xFFFF;
    for(size_t i=0;i<n;++i) { crc^=static_cast<unsigned char>(data[i])<<8;
        for(int b=0;b<8;++b) crc=((crc&0x8000)?(crc<<1)^0x1021:crc<<1)&0xFFFF;
    }
    return crc;
}
API void* ft_create() { return new(std::nothrow) Controller(); }
API void ft_destroy(void* ptr) { delete static_cast<Controller*>(ptr); }
API void ft_watchdog(void* ptr,double now) { if(ptr) static_cast<Controller*>(ptr)->watchdog(now); }
API int ft_exchange(void* ptr,const char* input,int length,char* output,int capacity) {
    if(!ptr||!input||!output||capacity<160) return -1;
    auto& c=*static_cast<Controller*>(ptr);
    char data[320]{};
    unsigned seq=0,received_crc=0;
    bool valid=length>7 && length<static_cast<int>(sizeof(data));
    if(valid) {
        std::memcpy(data,input,length);
        const char* star=std::strchr(data,'*');
        valid=star && star==data+length-6 && data[length-1]=='\n';
        if(valid) {
            for(int i=1;i<=4;++i) if(!((star[i]>='0'&&star[i]<='9')||(star[i]>='A'&&star[i]<='F'))) valid=false;
            valid=valid && std::sscanf(star+1,"%4x",&received_crc)==1 && received_crc==crc16(data,star-data);
        }
        if(valid) {
            double now,stamp,t,p,flow,rt,rp,rf,rd; int cmd,door,estop,n=0;
            int count=std::sscanf(data,"FT1,%u,%lf,%lf,%d,%lf,%lf,%lf,%d,%d,%lf,%lf,%lf,%lf%n",&seq,&now,&stamp,&cmd,&t,&p,&flow,&door,&estop,&rt,&rp,&rf,&rd,&n);
            valid=count==13 && data+n==star && cmd>=0&&cmd<=3&&(door==0||door==1)&&(estop==0||estop==1);
            if(valid) c.step(seq,now,stamp,cmd,{t,p,flow,door==1,estop==1},{rt,rp,rf,rd});
        }
    }
    if(!valid) c.trip(Fault::PROTOCOL);
    int n=std::snprintf(output,capacity,"FT1,%u,%d,%d,%.8f,%.8f,%.8f,%d",seq,static_cast<int>(c.state),static_cast<int>(c.fault),c.out.heater,c.out.throttle,c.out.flow,c.out.precursor?1:0);
    unsigned checksum=crc16(output,n);
    return n+std::snprintf(output+n,capacity-n,"*%04X\n",checksum);
}
