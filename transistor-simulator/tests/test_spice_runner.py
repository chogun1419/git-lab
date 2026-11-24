"""Tests for the ngspice subprocess wrapper and its output parsers.

The fixtures in ``tests/fixtures/`` are verbatim output from ngspice-47 for the
default reference stage. They were recorded, not written by hand: see
``default-netlist.cir`` for the netlist that produced them.
"""

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from spice_runner import (
    SpiceError,
    find_ngspice,
    parse_ac,
    parse_op,
    parse_transient,
    sample_at,
    simulate,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _completed(returncode=0, stdout=b"", stderr=b""):
    return subprocess.CompletedProcess(
        args=["ngspice_con.exe", "-b", "ce.cir"],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


class TestParseOperatingPoint(unittest.TestCase):
    def setUp(self):
        self.op = parse_op(FIXTURES / "op.txt")

    def test_reads_the_supply(self):
        self.assertAlmostEqual(self.op["vcc_v"], 12.0, places=6)

    def test_reads_the_node_voltages(self):
        self.assertAlmostEqual(self.op["vb_v"], 1.93627438, places=6)
        self.assertAlmostEqual(self.op["ve_v"], 1.27510387, places=6)
        self.assertAlmostEqual(self.op["vc_v"], 9.22254600, places=6)

    def test_reads_the_supply_current(self):
        self.assertAlmostEqual(self.op["i_vcc_a"], -1.36311635e-03, places=9)


class TestParseAc(unittest.TestCase):
    def setUp(self):
        self.ac = parse_ac(FIXTURES / "ac.txt")

    def test_reads_every_sweep_point(self):
        self.assertEqual(len(self.ac["freq_hz"]), 41)
        self.assertEqual(len(self.ac["gain_db"]), 41)
        self.assertEqual(len(self.ac["phase_deg"]), 41)

    def test_reads_the_sweep_ends(self):
        self.assertAlmostEqual(self.ac["freq_hz"][0], 10.0, places=6)
        self.assertAlmostEqual(self.ac["freq_hz"][-1], 1e5, places=3)

    def test_midband_gain_matches_the_known_simulation(self):
        point = sample_at(self.ac, 1_000.0)
        self.assertAlmostEqual(point["gain_db"], 38.79, delta=0.05)

    def test_midband_phase_is_inverted(self):
        point = sample_at(self.ac, 1_000.0)
        self.assertAlmostEqual(abs(point["phase_deg"]), 180.0, delta=15.0)

    def test_phase_is_reported_in_degrees_not_radians(self):
        # Top of the sweep is the flat inverting region: -180 degrees, which
        # would read as -3.14 if the radians were passed through untouched.
        point = sample_at(self.ac, self.ac["freq_hz"][-1])
        self.assertAlmostEqual(point["phase_deg"], -180.0, delta=0.5)

    def test_sample_at_reports_the_frequency_it_used(self):
        point = sample_at(self.ac, 990.0)
        self.assertIn(point["freq_hz"], self.ac["freq_hz"])

    def test_sample_at_rejects_an_empty_sweep(self):
        with self.assertRaises(SpiceError) as caught:
            sample_at({"freq_hz": [], "gain_db": [], "phase_deg": []}, 1_000.0)
        self.assertEqual(caught.exception.kind, "no_data")


class TestParseTransient(unittest.TestCase):
    def setUp(self):
        self.tran = parse_transient(FIXTURES / "tran.txt")

    def test_reads_every_time_step(self):
        self.assertEqual(len(self.tran["time_s"]), 1008)

    def test_starts_at_zero_and_ends_at_five_periods(self):
        self.assertAlmostEqual(self.tran["time_s"][0], 0.0, places=12)
        self.assertAlmostEqual(self.tran["time_s"][-1], 5e-3, places=9)

    def test_input_swing_matches_the_requested_amplitude(self):
        values = self.tran["vin_v"][len(self.tran["time_s"]) // 2:]
        self.assertAlmostEqual(max(values) - min(values), 0.02, delta=1e-4)

    def test_output_swing_agrees_with_the_ac_gain(self):
        half = len(self.tran["time_s"]) // 2
        vout = self.tran["vout_v"][half:]
        vin = self.tran["vin_v"][half:]
        swing_gain = (max(vout) - min(vout)) / (max(vin) - min(vin))
        self.assertAlmostEqual(swing_gain, 86.0, delta=3.0)


class TestParserFailures(unittest.TestCase):
    def test_missing_file_is_reported_as_no_data(self):
        for parser in (parse_op, parse_ac, parse_transient):
            with self.subTest(parser=parser.__name__):
                with self.assertRaises(SpiceError) as caught:
                    parser(FIXTURES / "does-not-exist.txt")
                self.assertEqual(caught.exception.kind, "no_data")

    def test_header_without_rows_is_reported_as_no_data(self):
        with self.assertRaises(SpiceError) as caught:
            parse_op(FIXTURES / "header-only.txt")
        self.assertEqual(caught.exception.kind, "no_data")

    def test_unexpected_columns_are_reported_rather_than_guessed(self):
        with self.assertRaises(SpiceError) as caught:
            parse_ac(FIXTURES / "wrong-columns.txt")
        self.assertEqual(caught.exception.kind, "no_data")


class TestFindNgspice(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="ngspice-lookup-"))
        self.gui = self.tmp / "ngspice.exe"
        self.gui.write_text("", encoding="ascii")
        self.console = self.tmp / "ngspice_con.exe"
        self.console.write_text("", encoding="ascii")

    def test_prefers_the_console_binary(self):
        self.assertEqual(find_ngspice(candidates=[self.gui, self.console]), self.console)

    def test_prefers_the_console_binary_regardless_of_candidate_order(self):
        self.assertEqual(find_ngspice(candidates=[self.console, self.gui]), self.console)

    def test_falls_back_to_the_gui_binary_when_that_is_all_that_exists(self):
        self.assertEqual(find_ngspice(candidates=[self.gui]), self.gui)

    def test_returns_none_when_no_candidate_exists(self):
        missing = self.tmp / "absent.exe"
        self.assertIsNone(find_ngspice(candidates=[missing]))


class TestSimulateFailures(unittest.TestCase):
    def test_missing_binary_is_named_in_the_error(self):
        with self.assertRaises(SpiceError) as caught:
            simulate("* test\n.end\n", binary=Path("C:/nowhere/ngspice_con.exe"))
        self.assertEqual(caught.exception.kind, "missing_binary")
        self.assertIn("ngspice_con.exe", caught.exception.message)

    def test_non_zero_exit_keeps_the_ngspice_text(self):
        with mock.patch("spice_runner.subprocess.run", return_value=_completed(1, b"Error: bad card\n")):
            with self.assertRaises(SpiceError) as caught:
                simulate("* test\n.end\n")
        self.assertEqual(caught.exception.kind, "failed")
        self.assertIn("bad card", caught.exception.detail)

    def test_singular_matrix_is_a_failure_even_with_exit_code_zero(self):
        output = b"Warning: singular matrix:  check node out\n"
        with mock.patch("spice_runner.subprocess.run", return_value=_completed(0, output)):
            with self.assertRaises(SpiceError) as caught:
                simulate("* test\n.end\n")
        self.assertEqual(caught.exception.kind, "failed")
        self.assertIn("singular matrix", caught.exception.detail)

    def test_stepping_failure_is_not_swallowed(self):
        output = b"Note: Starting source stepping\nNote: source stepping failed\n"
        with mock.patch("spice_runner.subprocess.run", return_value=_completed(0, output)):
            with self.assertRaises(SpiceError) as caught:
                simulate("* test\n.end\n")
        self.assertIn("source stepping failed", caught.exception.detail)

    def test_timeout_is_reported_with_the_limit(self):
        expired = subprocess.TimeoutExpired(cmd="ngspice_con.exe", timeout=30)
        with mock.patch("spice_runner.subprocess.run", side_effect=expired):
            with self.assertRaises(SpiceError) as caught:
                simulate("* test\n.end\n")
        self.assertEqual(caught.exception.kind, "timeout")
        self.assertIn("30", caught.exception.message)

    def test_success_without_output_files_is_reported(self):
        with mock.patch("spice_runner.subprocess.run", return_value=_completed(0, b"ok\n")):
            with self.assertRaises(SpiceError) as caught:
                simulate("* test\n.end\n")
        self.assertEqual(caught.exception.kind, "no_data")

    def test_the_netlist_is_written_where_ngspice_runs(self):
        with mock.patch(
            "spice_runner.subprocess.run", return_value=_completed(0, b"ok\n")
        ) as runner:
            with self.assertRaises(SpiceError):
                simulate("* test\n.end\n")
        workdir = Path(runner.call_args.kwargs["cwd"])
        self.assertEqual((workdir / "ce.cir").read_text(encoding="ascii"), "* test\n.end\n")


if __name__ == "__main__":
    unittest.main()
