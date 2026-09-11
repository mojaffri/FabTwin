# Controller and simulated serial interface

## Transport

FT1 is newline-delimited ASCII with a CRC-16/CCITT-FALSE checksum (polynomial 0x1021, initial value 0xFFFF, no reflection, xorout 0). Compute over the payload before `*`; append four uppercase hexadecimal digits and LF. The known check vector `123456789` gives `29B1`. Frames are bounded to 319 bytes including checksum and newline.

Request payload:

```text
FT1,seq,now_s,sample_s,command,T_C,P_Torr,F_sccm,door_closed,estop,T_set,P_set,F_set,deposition_s
```

Response payload:

```text
FT1,seq,state,fault,heater_fraction,exhaust_fraction,flow_sccm,precursor_gate
```

`seq` is a uint32 incremented modulo 2³². Sample age and successive request gaps must be at most one second. Simulated time must increase and samples may not be from the future. Door/estop/gate are 0 or 1. Commands: 0 tick, 1 start, 2 reset, 3 abort. Recipe values are captured on start; later tick values do not mutate the active recipe. Starting while non-idle is a recipe fault.

| State number | State |
|---|---|
| 0–8 | IDLE, PUMP_DOWN, HEAT, STABILIZE, DEPOSITION, PURGE, COOLDOWN, COMPLETE, FAULT |

| Fault number | Fault |
|---|---|
| 0–11 | NONE, PROTOCOL, STALE, SENSOR, DOOR, ESTOP, OVERTEMP, OVERPRESSURE, TIMEOUT, ABORT, RECIPE, PROCESS_WINDOW |

Packet syntax / CRC failures trip a latched protocol fault. Nonfinite/out-of-range sensor values, door open, emergency stop, >525 °C, >8 Torr, and state timeouts also trip. A frame sequence discontinuity trips the protocol interlock. Malformed replies may contain sequence zero; callers must treat them as errors, not accepted acknowledgments.

During deposition, a deviation exceeding 10 °C, 0.5 Torr, or 10 sccm from the captured recipe for two continuous seconds trips `PROCESS_WINDOW`. Returning to the window clears the debounce timer. These process-integrity limits complement the absolute equipment limits; they do not establish actual film quality. Reset during an active recipe trips `RECIPE` rather than silently cutting output for one tick. Fault/complete reset also requires measured flow below 1 sccm.

## Fault outputs and reset

Every fault commands heater off, precursor gate closed, flow command zero, and exhaust fully open. Those outputs are safe defaults **within this toy vacuum model**, not an assessment of any physical tool. Residual gas and thermal inertia do not disappear at shutdown.

Faults latch; subsequent valid telemetry does not clear them. An explicit reset can clear a fault below 60 °C and 0.3 Torr, with valid sensors, closed door and no estop. To resynchronize after transport loss it also requires measured flow below 1 sccm and a fresh timestamp. This deliberate reset establishes a new sequence origin; normal traffic cannot do so. The first fault cause is retained until reset. Complete recipes require an explicit reset before restart.

The core's `watchdog(now)` must be called independently of incoming frames in any future event-driven adapter. It trips when an active controller has received no new sample for over one second. The host C ABI exposes it as `ft_watchdog`, and an integration test simulates silence. In the synchronous simulator, time only advances when the host advances it; this is not a real-time wall-clock watchdog.

## Portability boundary

`controller.hpp` owns the state machine, PID states and interlocks using fixed-size storage; it has no operating-system calls, heap allocation or transport dependency. The host bridge owns the allocation, ASCII parser and C ABI. Python uses ctypes to pass actual frames to this compiled code. It never implements a duplicate control algorithm.

Float parsing uses the host C locale (decimal point is `.`). The host parser is suitable for protocol demonstrations but may be expensive for a small MCU. The STM32 port should use a bounded receive buffer and an explicitly validated parser. CRC detects accidental corruption, not malicious modification. This is neither SECS/GEM nor an industrial safety protocol.
