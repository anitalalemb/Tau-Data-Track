"""Conservative handling of remote completion evidence."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "tracking_inventory", Path(__file__).resolve().parents[1] /
    "scripts/analysis/compare_tracking_inventory.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class RemoteCompletionTests(unittest.TestCase):
    def test_failed_electronics_cannot_be_promoted_by_normal_exit(self):
        record = {"read_status": "OK", "marker_counts": {
            "job_done": 1, "scf_converged": 10, "scf_failed": 1}}
        self.assertFalse(module.completion_markers_ok(record))

    def test_ionic_completion_needs_closed_coordinates_and_no_time_limit(self):
        markers = dict(job_done=1, scf_converged=3, bfgs_converged=1,
                       end_bfgs=1, final_coordinates_begin=1)
        record = {"read_status": "OK", "marker_counts": markers}
        self.assertFalse(module.completion_markers_ok(record, True))
        markers["final_coordinates_end"] = 1
        self.assertTrue(module.completion_markers_ok(record, True))
        markers["time_limit"] = 1
        self.assertFalse(module.completion_markers_ok(record, True))

    def test_active_file_is_not_accepted(self):
        self.assertFalse(module.completion_markers_ok({
            "read_status": "CHANGED_DURING_READ",
            "marker_counts": {"job_done": 1, "scf_converged": 1}}))


if __name__ == "__main__":
    unittest.main()
