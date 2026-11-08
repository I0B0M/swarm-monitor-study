"""Checks replay/stats.py on reference values that statsmodels 0.15.0 and scipy 1.18.1 reproduce exactly.

Run: python -m unittest discover -s tests
"""
import unittest

from replay import stats as S

class TestStats(unittest.TestCase):
    def test_clopper_pearson_zero(self):
        # For 0/n the exact upper bound is 1 - (alpha/2)^(1/n).
        for n in (6, 50, 54, 60, 100):
            lo, hi = S.clopper_pearson(0, n)
            self.assertEqual(lo, 0.0)
            self.assertAlmostEqual(hi, 1 - 0.025 ** (1 / n), places=9)
    def test_clopper_pearson_known(self):
        # Clopper-Pearson 5/10 = (0.1871, 0.8129); statsmodels proportion_confint(method='beta') agrees.
        lo, hi = S.clopper_pearson(5, 10)
        self.assertAlmostEqual(lo, 0.18709, places=4); self.assertAlmostEqual(hi, 0.81291, places=4)
    def test_wilson_newcombe_1998(self):
        # Newcombe (1998) hybrid score interval, 56/70 vs 48/80 -> 0.2000 (0.0524, 0.3339); statsmodels method='newcomb' agrees.
        d, lo, hi = S.newcombe_diff(56, 70, 48, 80)
        self.assertAlmostEqual(d, 0.2, places=9); self.assertAlmostEqual(lo, 0.0524, places=3); self.assertAlmostEqual(hi, 0.3339, places=3)
    def test_newcombe_zero_cells(self):
        # 0/10 vs 0/20 -> 0 (-0.1611, 0.2775); statsmodels method='newcomb' agrees.
        d, lo, hi = S.newcombe_diff(0, 10, 0, 20)
        self.assertAlmostEqual(lo, -0.1611, places=3); self.assertAlmostEqual(hi, 0.2775, places=3)
    def test_fisher_tea(self):
        # Fisher's tea table [[3,1],[1,3]]: two-sided p = 0.4857; scipy fisher_exact agrees.
        self.assertAlmostEqual(S.fisher_exact(3, 1, 1, 3), 0.48571, places=4)
    def test_fisher_one_sided(self):
        # One-sided tea table: P(X >= 3) = 17/70 = 0.2429; scipy fisher_exact(alternative="greater") agrees.
        self.assertAlmostEqual(S.fisher_one_sided_greater(3, 1, 1, 3), 17 / 70, places=9)

    def test_fisher_extreme(self):
        # [[0,50],[6,54]]: two-sided p = 0.0308 (scipy fisher_exact).
        self.assertAlmostEqual(S.fisher_exact(0, 50, 6, 54), 0.03079, places=4)
    def test_betainc_symmetry(self):
        self.assertAlmostEqual(S.betainc(2.5, 2.5, 0.5), 0.5, places=10)
        self.assertAlmostEqual(S.betainc(1, 1, 0.3), 0.3, places=10)
    def test_jeffreys_matches_beta(self):
        lo, hi = S.jeffreys(0, 54)
        self.assertEqual(lo, 0.0)
        self.assertAlmostEqual(S.betainc(0.5, 54.5, hi), 0.975, places=8)
    def test_cluster_bootstrap_constant(self):
        rows = [{"seed": s, "x": 1} for s in range(10) for _ in range(3)]
        p, lo, hi = S.cluster_bootstrap(rows, lambda r: r["seed"], lambda rs: S.rate(rs, "x"), reps=200)
        self.assertEqual((p, lo, hi), (1.0, 1.0, 1.0))
    def test_tost(self):
        ok, (d, lo, hi) = S.tost_equivalent(0, 50, 0, 60, margin=0.10)
        self.assertTrue(ok)

if __name__ == "__main__":
    unittest.main()
