#include "controller.hpp"
#include <cstdio>
#include <cstdlib>

// Explicit checks stay active in Release builds (unlike assert with NDEBUG).
static void check(bool condition, const char* message) {
    if(!condition) { std::fprintf(stderr,"FAIL: %s\n",message); std::exit(1); }
}

int main() {
    using namespace fabtwin;
    PID pid{0.02,0.01,0};
    for(int i=0;i<1000;++i) check(pid.step(450,25,0.25)==1,"heater saturates");
    check(std::abs(pid.integral)<1e-9,"anti-windup blocks saturated integration");
    check(pid.step(450,460,0.25)==0,"PID recovers on error reversal");

    Controller c;
    c.transition(State::DEPOSITION,0);
    Sensor nominal{450,3,100,true,false};
    Sensor excursion{450,3.6,100,true,false};
    Recipe recipe;
    c.step(0,0,0,0,nominal,recipe);
    for(unsigned i=1;i<=8;++i) c.step(i,i*.25,i*.25,0,excursion,recipe);
    check(c.state==State::DEPOSITION,"excursion debounce waits full two seconds");
    c.step(9,2.25,2.25,0,nominal,recipe);
    check(c.excursion_since<0,"return to window clears debounce");
    for(unsigned i=10;i<=18;++i) c.step(i,i*.25,i*.25,0,excursion,recipe);
    check(c.fault==Fault::PROCESS_WINDOW,"sustained process deviation trips");
    check(c.out.heater==0 && c.out.flow==0 && !c.out.precursor,"fault commands off");

    Controller stabilize;
    stabilize.transition(State::STABILIZE,0);
    for(unsigned i=0;i<40;++i) stabilize.step(i,i*.25,i*.25,0,nominal,recipe);
    check(stabilize.state==State::STABILIZE,"stability requires ten seconds");
    stabilize.step(40,10,10,0,nominal,recipe);
    check(stabilize.state==State::DEPOSITION,"stable dwell advances recipe");
    stabilize.step(41,10.25,10.25,2,nominal,recipe);
    check(stabilize.fault==Fault::RECIPE,"reset during processing is rejected");
    std::puts("PASS: native PID, excursion debounce, stability dwell, and reset tests");
}
