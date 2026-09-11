# Changelog

## 0.2.0 — Portfolio release

- Added a sustained deposition process-window interlock and prevented reset commands from silently interrupting an active recipe.
- Added native C++ tests for anti-windup recovery, stability dwell, excursion debounce and reset semantics; expanded Python tests to 37.
- Added a nominal-kinetics metrology baseline, held-out MAE uncertainty and delayed-metrology residual EWMA with frozen limits.
- Expanded build/test automation to Linux, Windows and macOS; included formatting checks and downloadable demonstration artifacts.
- Made the optional pip-installed Zig compiler discoverable automatically and recorded reproducible reference results.

## 0.1.0 — Local prototype

- Implemented Python chamber dynamics, compiled C++ control, framed serial emulation, DOE, SPC, virtual metrology and six fault cases.
- Produced an initial synthetic reference report; no physical hardware was operated.
