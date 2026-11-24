from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

import gantry_joint_drive_rk4_screen as rk4_runner


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "gantry-joint-drive-rk4-01-synthetic-config.json"


class TestRK4SyntheticConvergenceScreen(unittest.TestCase):
    def test_config_requires_explicit_synthetic_parameter_provenance(self) -> None:
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        config["provenance"]["parameter_source"] = "machine data"
        with self.assertRaisesRegex(rk4_runner.RK4ScreenError, "synthetic"):
            rk4_runner._validate(config)

    def test_config_requires_exact_12_component_characteristic_scales(self) -> None:
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        del config["metrics"]["state_characteristic_scales"]["current_A"]
        with self.assertRaisesRegex(rk4_runner.RK4ScreenError, "exactly all 12"):
            rk4_runner._validate(config)

    def test_rk4_01_runs_four_smooth_nested_refinements(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = rk4_runner.run(CONFIG_PATH, Path(directory))
            self.assertEqual(result["case_id"], "RK4-01")
            self.assertEqual(result["status"], "COMPLETED_REPORT_ONLY")
            screen = result["numerical_screen"]
            self.assertTrue(screen["finite_states"])
            self.assertTrue(screen["rk4_stage_counts_match"])
            self.assertTrue(screen["all_refinements_smooth_unsaturated"])
            self.assertTrue(screen["adjacent_differences_monotonically_decrease"])
            self.assertTrue(screen["observed_order_screen_pass"])
            self.assertEqual(len(result["pairwise_observed_orders"]), 2)
            self.assertTrue(all(x is not None and x >= 3.0 for x in result["pairwise_observed_orders"]))

            archive = rk4_runner.verify_archive(Path(directory))
            self.assertEqual(archive["archive_status"], "VERIFIED_INTEGRITY_ONLY")
            self.assertEqual(archive["recorded_numerical_status"], "COMPLETED_REPORT_ONLY")

    def test_archive_verifier_rejects_modified_timeseries(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            rk4_runner.run(CONFIG_PATH, output)
            path = output / rk4_runner.TIMESERIES_NAME
            path.write_bytes(path.read_bytes() + b"\n")
            with self.assertRaisesRegex(rk4_runner.RK4ScreenError, "integrity mismatch"):
                rk4_runner.verify_archive(output)

    def test_scale_order_and_units_are_complete_and_stable(self) -> None:
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        validated = rk4_runner._validate(config)
        self.assertEqual(list(validated["scales"]), rk4_runner.STATE_FIELDS)
        self.assertEqual(list(rk4_runner.STATE_UNITS), rk4_runner.STATE_FIELDS)
        self.assertEqual(len(validated["scale_source_ids"]), 1)

    def _rk4_02_config(self) -> dict:
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        config["case_id"] = "RK4-02"
        config["initial_state"]["s_dot_m_s"] = 0.0
        controller = config["controller_and_loads"]
        controller["current_command_model"] = "quintic_pd_current"
        controller["Kp_pos_A_per_m"] = 200.0
        controller["Kd_vel_A_s_per_m"] = 30.0
        controller["path_reference"] = {
            "family": "quintic_rest_to_rest",
            "start_m": 0.72,
            "end_m": 0.735,
            "duration_s": 0.2,
        }
        return config

    def test_rk4_02_requires_positive_free_path_direction(self) -> None:
        config = self._rk4_02_config()
        validated = rk4_runner._validate(config)
        self.assertEqual(validated["case_id"], "RK4-02")
        self.assertEqual(validated["command_spec"]["model"], "quintic_pd_current")
        config["controller_and_loads"]["path_reference"]["end_m"] = 0.70
        with self.assertRaisesRegex(rk4_runner.RK4ScreenError, "positive path displacement"):
            rk4_runner._validate(config)

    def test_rk4_02_runs_positive_smooth_free_path_motion(self) -> None:
        config = self._rk4_02_config()
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "rk4-02-config.json"
            output_dir = Path(directory) / "output"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            result = rk4_runner.run(config_path, output_dir)
            self.assertEqual(result["case_id"], "RK4-02")
            self.assertEqual(result["status"], "COMPLETED_REPORT_ONLY")
            self.assertTrue(result["numerical_screen"]["all_refinements_smooth_unsaturated"])
            self.assertTrue(result["numerical_screen"]["adjacent_differences_monotonically_decrease"])
            self.assertTrue(result["numerical_screen"]["observed_order_screen_pass"])
            with (output_dir / "rk4-02-level-summary.csv").open(encoding="utf-8", newline="") as stream:
                rows = list(__import__("csv").DictReader(stream))
            self.assertEqual(len(rows), 4)
            self.assertTrue(all(int(row["current_reference_saturated_stages"]) == 0 for row in rows))
            self.assertTrue(all(int(row["voltage_saturated_stages"]) == 0 for row in rows))
            self.assertTrue(all(float(row["net_s_displacement_m"]) > 0.0 for row in rows))
            self.assertTrue(all(float(row["requested_current_max_A"]) > 0.0 for row in rows))
            archive = rk4_runner.verify_archive(output_dir)
            self.assertEqual(archive["recorded_numerical_status"], "COMPLETED_REPORT_ONLY")


if __name__ == "__main__":
    unittest.main()
