# Optional STM32 software-to-hardware extension

**Planned, not implemented or tested on a board.** The current library is built and executed on the computer. Owning a Nucleo does not make this release hardware-in-the-loop. No hardware purchase is needed for the current project.

Use the existing Nucleo only after identifying its exact board / MCU and available ST-LINK virtual COM-port wiring. UART pins, clocks, available RAM and flashing settings depend on that board. No board-specific pinout is assumed here. The Arduino Uno is optional and is not required for this design.

1. Create an STM32CubeIDE C++ project for the exact board. Add `controller/include/controller.hpp`. Allocate one static `fabtwin::Controller`; the host `new/delete` bridge is not firmware.
2. Create a fixed-length UART/USB receive buffer. Reject overflow, partial-frame timeout and invalid CRC before dispatch. Keep parsing out of interrupt context. Convert validated frame fields to typed `Sensor` and `Recipe` values.
3. Use a monotonic board clock for scheduling and watchdogs. Establish a timestamp mapping for host telemetry; do not blindly compare unsynchronized host and board clocks.
4. At a 250 ms task period, call `step` on a new valid sample. Call `watchdog` independently even with no input. On boot, communication failure or parser overflow, hold safe simulation outputs. Add a hardware independent watchdog for firmware hangs.
5. Replace the Python in-memory transport with a serial adapter that handles timeout, buffering, CRC, sequence validation, disconnect and reconnect. The Python chamber still supplies all sensor values; actuator values only drive the simulated model.
6. Replay nominal and injected-fault cases. Record round-trip timing, deadline misses, resets, corrupted-packet response and host/board trace comparisons. Check compile warnings, memory footprint and floating-point behavior on the selected MCU.

Acceptance evidence before using an HIL resume claim: board identification, firmware source/build configuration, flash log, photo of the USB-only setup, saved host/board protocol transcript, timing measurements, and repeated safe fault tests. Do not attach real heaters, gases, vacuum pumps or process equipment to this educational controller.

Good later extensions are measured scheduling jitter, a UART disconnect test, binary framing, and a software regression replay against the host controller. A board port should be a separate milestone with its own tests and evidence, not an unverified checkbox.
