"""Regression cases for electronic versus optimizer history provenance."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("qe_behavior", Path(__file__).resolve().parents[1] / "scripts/analysis/qe_behavior.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class BehaviorTests(unittest.TestCase):
    def parse(self, text):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "qe.out"
            path.write_text(text)
            return module.parse_output(path)

    def test_restart_number_and_failed_cycle_survive_normal_exit(self):
        r = self.parse("""Program PWSCF
Self-consistent Calculation
iteration # 10
total energy = -10.0 Ry
estimated scf accuracy < 2.0D-4 Ry
convergence NOT achieved after 10 iterations
JOB DONE.
""")
        self.assertEqual(r["electronic_iterations"][0]["qe_iteration"], 10)
        self.assertEqual(r["electronic_iterations"][0]["scf_accuracy_Ry"], 0.0002)
        self.assertEqual(r["cycles"][0]["outcome"], "NOT_CONVERGED")
        self.assertTrue(r["runs"][0]["job_done"])

    def test_high_verbosity_component_forces_do_not_replace_total(self):
        r = self.parse("""Program PWSCF
number of atoms/cell = 1
Self-consistent Calculation
iteration # 1
! total energy = -10.0 Ry
convergence has been achieved in 1 iterations
Forces acting on atoms (cartesian axes, Ry/au):
atom 1 type 1 force = 0.003 0.004 0.0
The non-local contrib. to forces
atom 1 type 1 force = 100.0 0.0 0.0
Total force = 0.005 Total SCF correction = 0.0001
number of bfgs steps = 7
bfgs converged in 9 scf cycles and 8 bfgs steps
""")
        f = r["force_evaluations"][0]
        self.assertAlmostEqual(f["max_printed_atomic_force_eV_A"], 0.005*module.FORCE_FACTOR)
        self.assertEqual(f["reported_bfgs_step_after"], 8)
        self.assertEqual(r["runs"][0]["final_reported_scf_cycles"], 9)
        self.assertEqual(f["energy_Ry"], -10.)

    def test_concatenated_runs_and_scf_cycles_keep_separate_ids(self):
        r = self.parse("""Program PWSCF
Self-consistent Calculation
iteration # 1
total energy = -3.0 Ry
convergence has been achieved in 1 iterations
Self-consistent Calculation
iteration # 1
total energy = -4.0 Ry
JOB DONE.
Program PWSCF
Self-consistent Calculation
iteration # 1
total energy = -5.0 Ry
""")
        self.assertEqual([i["cycle_id"] for i in r["electronic_iterations"]], [1, 2, 3])
        self.assertEqual([i["run_id"] for i in r["electronic_iterations"]], [1, 1, 2])
        self.assertFalse(r["runs"][-1]["job_done"])


if __name__ == "__main__":
    unittest.main()
