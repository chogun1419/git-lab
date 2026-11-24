"""Tests for the server-side SVG chart geometry."""

import math
import unittest

from plots import build_chart


def _points(polyline):
    return [
        (float(x), float(y))
        for x, y in (pair.split(",") for pair in polyline.split())
    ]


class TestBuildChart(unittest.TestCase):
    def setUp(self):
        self.x = [10.0, 100.0, 1_000.0, 10_000.0]
        self.y = [38.0, 38.8, 38.8, 30.0]
        self.chart = build_chart([self.y], self.x, x_scale="log")

    def test_returns_one_polyline_per_series(self):
        chart = build_chart([self.y, [1.0, 2.0, 3.0, 4.0]], self.x, x_scale="log")
        self.assertEqual(len(chart["polylines"]), 2)

    def test_every_point_stays_inside_the_plot_box(self):
        left, top = self.chart["left"], self.chart["top"]
        right = left + self.chart["plot_width"]
        bottom = top + self.chart["plot_height"]
        for x, y in _points(self.chart["polylines"][0]):
            self.assertGreaterEqual(x, left - 1e-6)
            self.assertLessEqual(x, right + 1e-6)
            self.assertGreaterEqual(y, top - 1e-6)
            self.assertLessEqual(y, bottom + 1e-6)

    def test_decades_are_evenly_spaced_on_a_log_axis(self):
        points = _points(self.chart["polylines"][0])
        steps = [b[0] - a[0] for a, b in zip(points, points[1:])]
        for step in steps[1:]:
            self.assertAlmostEqual(step, steps[0], delta=0.02)

    def test_higher_values_sit_higher_on_screen(self):
        points = _points(self.chart["polylines"][0])
        # y grows downwards in SVG, so the larger value must have the smaller y.
        self.assertLess(points[1][1], points[0][1])

    def test_log_axis_ticks_land_on_decades(self):
        values = [tick["value"] for tick in self.chart["x_ticks"]]
        self.assertIn(10.0, values)
        self.assertIn(1_000.0, values)
        for value in values:
            self.assertAlmostEqual(math.log10(value) % 1.0, 0.0, places=6)

    def test_linear_axis_is_supported_for_waveforms(self):
        chart = build_chart([[0.0, 1.0, -1.0]], [0.0, 0.5, 1.0], x_scale="linear")
        points = _points(chart["polylines"][0])
        self.assertAlmostEqual(points[1][0] - points[0][0], points[2][0] - points[1][0], delta=0.02)

    def test_a_flat_series_does_not_divide_by_zero(self):
        chart = build_chart([[5.0, 5.0, 5.0]], [1.0, 2.0, 3.0], x_scale="linear")
        self.assertEqual(len(_points(chart["polylines"][0])), 3)

    def test_y_range_covers_the_data_with_room_to_spare(self):
        self.assertLess(self.chart["y_min"], min(self.y))
        self.assertGreater(self.chart["y_max"], max(self.y))

    def test_empty_series_is_rejected_with_a_clear_error(self):
        with self.assertRaises(ValueError):
            build_chart([[], []], [], x_scale="log")


if __name__ == "__main__":
    unittest.main()
