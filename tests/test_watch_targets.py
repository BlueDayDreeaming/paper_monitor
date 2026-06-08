from __future__ import annotations

import unittest

from ssrn_monitor.watch_targets import load_watch_targets


class WatchTargetsTest(unittest.TestCase):
    def test_embedded_targets_have_expected_shape(self) -> None:
        targets = load_watch_targets()
        self.assertEqual(len(targets), 200)
        self.assertEqual(targets[0].name, "Xu Jiang")
        self.assertEqual(targets[0].school, "Duke University")
        self.assertEqual(targets[-1].name, "Wei Cai")
        self.assertEqual(targets[-1].rank, 200)


if __name__ == "__main__":
    unittest.main()
