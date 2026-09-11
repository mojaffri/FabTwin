import pytest

from fabtwin.model import Disturbance, Recipe
from fabtwin.protocol import Controller, frame, unframe
from fabtwin.simulation import simulate


def test_nominal_sequence_and_closed_loop():
    run = simulate()
    assert run.summary["state"] == "COMPLETE"
    assert run.trace.state.drop_duplicates().tolist() == [
        "PUMP_DOWN",
        "HEAT",
        "STABILIZE",
        "DEPOSITION",
        "PURGE",
        "COOLDOWN",
        "COMPLETE",
    ]
    process = run.trace.loc[run.trace.state == "DEPOSITION"]
    assert len(process) * 0.25 == 120
    assert abs(process.temperature_c.mean() - 450) < 1
    assert abs(process.pressure_torr.mean() - 3) < 0.05
    assert 90 < run.summary["truth_thickness_nm"] < 110
    assert run.trace.heater.between(0, 1).all()
    assert not run.trace.loc[run.trace.state != "DEPOSITION", "precursor"].any()
    assert run.trace.truth_thickness_nm.diff().dropna().min() >= 0


@pytest.mark.parametrize(
    "kind,magnitude,expected",
    [
        ("door_open", 0, "DOOR"),
        ("estop", 0, "ESTOP"),
        ("stale", 0, "STALE"),
        ("vacuum_leak", 10, "OVERPRESSURE"),
        ("heater_loss", 0.8, "TIMEOUT"),
    ],
)
def test_faults_cut_energy_and_reactant(kind, magnitude, expected):
    run = simulate(disturbance=Disturbance(kind, 40, magnitude))
    assert run.summary["fault"] == expected
    final = run.trace.iloc[-1]
    assert (
        final.heater == 0
        and final.flow_command == 0
        and not final.precursor
        and final.throttle == 1
    )


@pytest.mark.parametrize(
    "sensor,expected",
    [
        ((float("nan"), 3, 100, 1, 0), "SENSOR"),
        ((450, float("inf"), 100, 1, 0), "SENSOR"),
        ((530, 3, 100, 1, 0), "OVERTEMP"),
        ((450, 9, 100, 1, 0), "OVERPRESSURE"),
    ],
)
def test_sensor_interlocks(sensor, expected):
    with Controller() as c:
        assert c.step(0, sensor, Recipe())["fault"] == expected


def test_latched_fault_requires_safe_explicit_reset():
    with Controller() as c:
        assert c.step(0, (450, 3, 100, 0, 0), Recipe())["fault"] == "DOOR"
        assert c.step(0.25, (450, 3, 100, 1, 0), Recipe())["state"] == "FAULT"
        assert c.step(0.5, (450, 3, 100, 1, 0), Recipe(), command=2)["state"] == "FAULT"
        assert c.step(0.75, (25, 0.02, 0, 1, 0), Recipe(), command=2)["state"] == "IDLE"
        assert c.step(1, (25, 5, 0, 1, 0), Recipe(), command=1)["state"] == "PUMP_DOWN"


@pytest.mark.parametrize(
    "packet",
    [
        b"garbage\n",
        b"X" * 400,
        frame("FT1,0,0,0,0,25,5,0,1,0,450,3,100,120")[:-3] + b"00\n",
        frame("FT1,0,0,0,0,25,5,0,1,0,450,3,100,120,trailing"),
    ],
)
def test_malformed_packet_latches_protocol_fault(packet):
    with Controller() as c:
        fields = unframe(c.exchange(packet)).split(",")
        assert fields[2:4] == ["8", "1"]
        assert float(fields[4]) == 0 and float(fields[6]) == 0 and fields[7] == "0"


def test_duplicate_sequence_and_bad_recipe():
    payload = "FT1,0,0,0,1,25,5,0,1,0,450,3,100,120"
    with Controller() as c:
        c.exchange(frame(payload))
        reply = unframe(c.exchange(frame(payload.replace(",0,0,1,", ",0.25,0.25,1,")))).split(",")
        assert reply[3] == "1"
    with Controller() as c:
        assert unframe(c.exchange(frame(payload.replace(",450,", ",999,")))).split(",")[3] == "10"


def test_crc_known_vector():
    assert frame("123456789") == b"123456789*29B1\n"
    assert unframe(frame("abc")) == "abc"
    with pytest.raises(ValueError):
        unframe(b"abc*0000\n")


def test_silence_watchdog_and_transport_resynchronization():
    with Controller() as c:
        c.step(0, (25, 5, 0, 1, 0), Recipe(), command=1)
        c.watchdog(2)
        assert c.step(2.25, (100, 1, 0, 1, 0), Recipe())["fault"] == "STALE"
        assert c.step(2.5, (25, 0.02, 0, 1, 0), Recipe(), command=2)["state"] == "IDLE"
        assert c.step(2.75, (25, 5, 0, 1, 0), Recipe(), command=1)["state"] == "PUMP_DOWN"


def test_corrupt_frame_recovery_requires_explicit_safe_reset():
    with Controller() as c:
        c.step(0, (25, 5, 0, 1, 0), Recipe(), command=1)
        c.exchange(b"corrupt\n")
        c.seq += 1
        assert c.step(0.25, (25, 0.02, 0, 1, 0), Recipe(), command=2)["state"] == "IDLE"


def test_timestep_convergence_and_reproducibility():
    a = simulate(seed=17)
    b = simulate(seed=17)
    fine = simulate(seed=17, dt=0.125)
    assert a.summary == b.summary
    assert abs(a.summary["truth_thickness_nm"] - fine.summary["truth_thickness_nm"]) < 1


def test_plausible_sensor_bias_is_not_falsely_claimed_detected():
    nominal = simulate(seed=7)
    biased = simulate(seed=7, disturbance=Disturbance("sensor_bias", 150, 8))
    assert biased.summary["fault"] == "NONE"
    assert biased.summary["truth_thickness_nm"] < nominal.summary["truth_thickness_nm"]


def test_deposition_excursion_has_separate_process_fault():
    run = simulate(disturbance=Disturbance("heater_loss", 150, 0.8))
    assert run.summary["fault"] == "PROCESS_WINDOW"
    assert 150 < run.summary["cycle_s"] < 170
    assert not run.trace.iloc[-1].precursor


def test_reset_during_active_recipe_does_not_silently_interrupt_one_tick():
    with Controller() as c:
        c.step(0, (25, 5, 0, 1, 0), Recipe(), command=1)
        assert c.step(0.25, (25, 4, 0, 1, 0), Recipe(), command=2)["fault"] == "RECIPE"


def test_sequence_wraparound():
    with Controller() as c:
        c.seq = 2**32 - 1
        assert c.step(0, (25, 5, 0, 1, 0), Recipe())["fault"] == "NONE"
        assert c.step(0.25, (25, 5, 0, 1, 0), Recipe())["fault"] == "NONE"
