"""Regression coverage for stage-specific acceptance in the ML index."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "dataset_index", Path(__file__).resolve().parents[1] /
    "scripts/analysis/build_dataset_index.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class CompletionEvidenceTests(unittest.TestCase):
    def test_rigid_scf_does_not_require_ionic_optimization(self):
        self.assertTrue(module.is_converged("A", {
            "electronic_converged": True, "job_done": True}))

    def test_normal_exit_without_electronic_convergence_is_rejected(self):
        self.assertFalse(module.is_converged("A", {"job_done": True}))
        self.assertFalse(module.is_converged("A", {
            "electronic_converged": False, "job_done": True,
            "converged": True}))

    def test_relaxation_needs_completed_aligned_optimization(self):
        valid = dict(bfgs_converged=True, end_bfgs=True, job_done=True,
                     alignment_ok=True, maximum_cpu_time_exceeded=False)
        self.assertTrue(module.is_converged("B", valid))
        for field in ("bfgs_converged", "end_bfgs", "job_done", "alignment_ok"):
            self.assertFalse(module.is_converged("B", dict(valid, **{field: False})))
        self.assertFalse(module.is_converged("B", dict(
            valid, maximum_cpu_time_exceeded=True)))

    def test_stage_c_uses_its_independent_projected_convergence_record(self):
        self.assertTrue(module.is_converged("C", {"converged": True}))
        self.assertFalse(module.is_converged("C", {"job_done": True}))


if __name__ == "__main__":
    unittest.main()
