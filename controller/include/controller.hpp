#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>

namespace fabtwin {
enum class State { IDLE, PUMP_DOWN, HEAT, STABILIZE, DEPOSITION, PURGE, COOLDOWN, COMPLETE, FAULT };
enum class Fault { NONE, PROTOCOL, STALE, SENSOR, DOOR, ESTOP, OVERTEMP, OVERPRESSURE, TIMEOUT, ABORT, RECIPE, PROCESS_WINDOW };
struct Sensor { double t, p, flow; bool door, estop; };
struct Recipe { double t=450, p=3, flow=100, duration=120; };
struct Output { double heater=0, throttle=1, flow=0; bool precursor=false; };

// Derivative on measurement, filtered; conditional integration prevents windup.
struct PID {
    double kp, ki, kd, integral=0, previous=0, derivative=0;
    bool initialized=false;
    void reset() { integral=previous=derivative=0; initialized=false; }
    double step(double setpoint, double value, double dt, double feedforward=0) {
        const double error=setpoint-value;
        double raw=initialized ? -(value-previous)/dt : 0;
        derivative += dt/(1.0+dt)*(raw-derivative);
        previous=value; initialized=true;
        const double proposal=integral+ki*error*dt;
        const double candidate=feedforward+kp*error+proposal+kd*derivative;
        if ((candidate>=0 && candidate<=1) || (candidate>1 && error<0) || (candidate<0 && error>0)) integral=proposal;
        return std::clamp(feedforward+kp*error+integral+kd*derivative,0.0,1.0);
    }
};

class Controller {
public:
    State state=State::IDLE;
    Fault fault=Fault::NONE;
    Recipe recipe;
    Output out;
    PID thermal{0.018,0.0008,0.01}, pressure{0.22,0.06,0.015};
    double previous_time=-1, entered=0, stable_since=-1, excursion_since=-1;
    std::uint32_t last_seq=0;
    bool have_seq=false;

    void trip(Fault f) { if(state!=State::FAULT) fault=f; state=State::FAULT; out={}; }
    // Invoke from an independent scheduler tick even when no frames arrive.
    void watchdog(double now) {
        if(state!=State::IDLE && state!=State::COMPLETE && previous_time>=0
            && (!std::isfinite(now) || now<previous_time || now-previous_time>1.0)) trip(Fault::STALE);
    }
    void transition(State s,double now) { state=s; entered=now; stable_since=-1; excursion_since=-1; }
    bool valid_recipe(const Recipe& r) const {
        return std::isfinite(r.t)&&std::isfinite(r.p)&&std::isfinite(r.flow)&&std::isfinite(r.duration)
          &&r.t>=400&&r.t<=500&&r.p>=1&&r.p<=5&&r.flow>=50&&r.flow<=150&&r.duration>=30&&r.duration<=240;
    }
    void step(std::uint32_t seq,double now,double stamp,int command,const Sensor& s,const Recipe& r) {
        out={};
        if(command<0 || command>3) {trip(Fault::PROTOCOL); return;}
        // A fresh, explicit reset in a safe measured condition may resynchronize
        // a faulted transport after a dropped/corrupted frame or watchdog gap.
        if(command==2 && state==State::FAULT && std::isfinite(now) && std::isfinite(stamp)
            && now>=0 && stamp<=now && now-stamp<=1 && now>previous_time
            && std::isfinite(s.t)&&std::isfinite(s.p)&&std::isfinite(s.flow)
            && s.t>=0&&s.t<60&&s.p>=0&&s.p<0.3&&s.flow>=0&&s.flow<1&&s.door&&!s.estop) {
            previous_time=-1; have_seq=false;
        }
        if(!std::isfinite(now)||!std::isfinite(stamp)||now<0||stamp>now||now-stamp>1.0
            ||(previous_time>=0&&(now<=previous_time||now-previous_time>1.0))) { trip(Fault::STALE); return; }
        if(have_seq && seq!=last_seq+1u) { trip(Fault::PROTOCOL); return; }
        last_seq=seq; have_seq=true;
        double dt=previous_time<0 ? 0.25 : now-previous_time;
        previous_time=now;
        if(!std::isfinite(s.t)||!std::isfinite(s.p)||!std::isfinite(s.flow)||s.t<0||s.t>1000||s.p<0||s.p>20||s.flow<0||s.flow>250) {trip(Fault::SENSOR); return;}
        if(!s.door) {trip(Fault::DOOR); return;}
        if(s.estop) {trip(Fault::ESTOP); return;}
        if(s.t>525) {trip(Fault::OVERTEMP); return;}
        if(s.p>8) {trip(Fault::OVERPRESSURE); return;}
        if(command==3) {trip(Fault::ABORT); return;}
        if(command==2) {
            if(state!=State::FAULT && state!=State::COMPLETE && state!=State::IDLE) {
                trip(Fault::RECIPE); return;
            }
            if((state==State::FAULT||state==State::COMPLETE) && s.t<60 && s.p<0.3 && s.flow<1) {
                fault=Fault::NONE; transition(State::IDLE,now); thermal.reset(); pressure.reset();
            }
            return;
        }
        if(state==State::FAULT) return;
        if(command==1) {
            if(state!=State::IDLE || !valid_recipe(r)) {trip(Fault::RECIPE); return;}
            recipe=r; transition(State::PUMP_DOWN,now);
        }
        if(state==State::IDLE||state==State::COMPLETE) return;
        double elapsed=now-entered;
        double limit=state==State::COOLDOWN ? 600 : (state==State::DEPOSITION ? recipe.duration+2 : 450);
        if(elapsed>limit) {trip(Fault::TIMEOUT); return;}
        switch(state) {
        case State::PUMP_DOWN: if(s.p<0.15) transition(State::HEAT,now); break;
        case State::HEAT: if(std::abs(s.t-recipe.t)<2) transition(State::STABILIZE,now); break;
        case State::STABILIZE:
            if(std::abs(s.t-recipe.t)<2 && std::abs(s.p-recipe.p)<0.08 && std::abs(s.flow-recipe.flow)<3) {
                if(stable_since<0) stable_since=now;
                if(now-stable_since>=10) transition(State::DEPOSITION,now);
            } else stable_since=-1;
            break;
        case State::DEPOSITION:
            // Qualify excursions separately from absolute equipment limits.
            if(std::abs(s.t-recipe.t)>10 || std::abs(s.p-recipe.p)>0.5 || std::abs(s.flow-recipe.flow)>10) {
                if(excursion_since<0) excursion_since=now;
                if(now-excursion_since>=2) {trip(Fault::PROCESS_WINDOW); return;}
            } else excursion_since=-1;
            if(elapsed>=recipe.duration) transition(State::PURGE,now);
            break;
        case State::PURGE: if(elapsed>=10) transition(State::COOLDOWN,now); break;
        case State::COOLDOWN: if(s.t<60 && s.p<0.15) transition(State::COMPLETE,now); break;
        default: break;
        }
        if(state==State::HEAT||state==State::STABILIZE||state==State::DEPOSITION) {
            out.heater=thermal.step(recipe.t,s.t,dt,(recipe.t-25)/950);
            out.flow=recipe.flow;
            // Sign reversal: opening exhaust decreases chamber pressure.
            out.throttle=pressure.step(-recipe.p,-s.p,dt,0.38);
        }
        if(state==State::DEPOSITION) out.precursor=true;
        if(state==State::PURGE) out.flow=100;
    }
};
}
