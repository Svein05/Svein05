import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime
import xml.etree.ElementTree as ET


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + ".py"))
    module = importlib.util.module_from_spec(spec)
    with patch.dict(os.environ, {"METRICS_TOKEN": "test-token"}):
        spec.loader.exec_module(module)
    return module


stars = load("update_stars")
activity = load("update_activity")
NS = {"s": "http://www.w3.org/2000/svg"}


def date(value):
    return datetime.fromisoformat(value).replace(tzinfo=stars.TIMEZONE)


class StarsTests(unittest.TestCase):
    def test_ticks_exact_integer_endpoints(self):
        for low, high in [(0, 0), (3, 4), (3, 8), (128, 500), (4, 7)]:
            ticks = stars.integer_ticks(low, high)
            self.assertEqual((ticks[0], ticks[-1]), (low, high))
            self.assertLessEqual(len(ticks), 5)
            self.assertTrue(all(type(v) is int for v in ticks))

    def test_bootstrap_dates_and_month_baseline(self):
        history = {}
        events = [(date("2026-10-12T12:00"), "A"),
                  (date("2026-11-01T12:00"), "A"),
                  (date("2026-11-14T12:00"), "B")]
        record, most, latest = stars.build_month(history, {"A": 2, "B": 1}, events, date("2026-11-14T23:00"))
        self.assertEqual(record["baseline"], 1)
        self.assertEqual(record["days"]["2026-11-01"], 2)
        self.assertEqual(record["days"]["2026-11-14"], 3)
        self.assertEqual((most, latest), ("A", "B"))

    def test_rollover_preserves_previous_close(self):
        history = {"months": {"2026-12": {"days": {"2026-12-31": 8}}}}
        record, _, _ = stars.build_month(history, {"A": 9}, [(date("2027-01-01T10:00"), "A")], date("2027-01-01T23:00"))
        self.assertEqual(record["baseline"], 8)
        self.assertEqual(record["days"], {"2027-01-01": 9})

    def test_observed_totals_survive_unstars_and_reruns(self):
        history = {}
        stars.build_month(history, {"A": 8}, [], date("2026-11-13T23:00"))
        record, _, _ = stars.build_month(history, {"A": 7}, [], date("2026-11-14T23:00"))
        self.assertEqual(record["baseline"], 8)
        self.assertEqual(record["days"]["2026-11-13"], 8)
        self.assertEqual(record["days"]["2026-11-14"], 7)
        svg = stars.chart_svg(record, "A", "A", date("2026-11-14T23:00"))
        ET.fromstring(svg)
        self.assertIn('>-1</text>', svg)

    def test_points_are_daily_changes_with_aligned_dates(self):
        record = {"baseline": 3, "days": {"2026-11-01": 3, "2026-11-02": 4, "2026-11-03": 4, "2026-11-04": 6}}
        xml = ET.fromstring(stars.chart_svg(record, "A&B", "<B>", date("2026-11-04T23:00")))
        points = xml.findall('s:circle', NS)
        self.assertEqual(len(points), 2)
        texts = xml.findall('s:text', NS)
        self.assertEqual([t.text for t in texts if t.attrib.get("class") == "delta"], ["+1", "+2"])
        for point, day in zip(points, ["02", "04"]):
            tick = next(t for t in texts if t.text == day)
            self.assertEqual(tick.attrib["x"], point.attrib["cx"])
        y_labels = [t.text for t in texts if t.attrib.get("text-anchor") == "end" and t.attrib.get("class") == "axis"]
        self.assertEqual((y_labels[0], y_labels[-1]), ("3", "6"))

    def test_flat_month_has_one_y_tick_and_no_fake_points(self):
        record = {"baseline": 0, "days": {"2028-02-01": 0}}
        svg = stars.chart_svg(record, "—", "—", date("2028-02-01T23:00"))
        self.assertNotIn("nan", svg.lower())
        xml = ET.fromstring(svg)
        self.assertEqual(xml.findall('s:circle', NS), [])
        self.assertIn("No changes this month", svg)

    def test_pagination_collects_all_repositories(self):
        from io import BytesIO
        responses = [BytesIO(json.dumps([{"id": i} for i in range(100)]).encode()), BytesIO(b'[{"id": 100}]')]
        with patch.object(stars.urllib.request, "urlopen", side_effect=responses) as request:
            result = stars.pages("/users/demo/repos?type=owner", "token")
        self.assertEqual(len(result), 101)
        self.assertIn("&per_page=100&page=2", request.call_args.args[0].full_url)

    def test_utc_stars_are_assigned_to_the_chilean_day(self):
        repos = [{"name": "A", "full_name": "Demo/A", "private": False, "stargazers_count": 1}]
        with patch.object(stars, "pages", side_effect=[repos, [{"starred_at": "2026-11-01T01:00:00Z"}]]):
            counts, events = stars.fetch_stars("Demo", None)
        record, _, _ = stars.build_month({}, counts, events, date("2026-11-01T23:00"))
        self.assertEqual(events[0][0].date().isoformat(), "2026-10-31")
        self.assertEqual(record["baseline"], 1)

    def test_leap_day_and_dense_month_are_valid_svg(self):
        for year, month, days in [(2028, 2, 29), (2026, 12, 31)]:
            record = {"baseline": 100, "days": {f"{year}-{month:02d}-{day:02d}": 100 + day for day in range(1, days + 1)}}
            xml = ET.fromstring(stars.chart_svg(record, "A", "B", date(f"{year}-{month:02d}-{days}T23:00")))
            points = xml.findall('s:circle', NS)
            self.assertEqual(len(points), days)
            self.assertEqual(points[-1].attrib["cx"], "696.00")

    def test_api_failure_does_not_write_files(self):
        with patch.object(stars, "fetch_stars", side_effect=RuntimeError("API failure")), patch.object(stars, "get_token", return_value="test"), patch.object(Path, "write_text") as write:
            with self.assertRaises(RuntimeError):
                stars.main()
            write.assert_not_called()


class ActivityTests(unittest.TestCase):
    def test_long_branches_leave_space_for_timestamps(self):
        long_name = "NuvioLatinoSetup:feature/web-performance-accessibility<&>"
        items = [{"icon_type": "commit", "action": "Push", "repo_label": long_name,
                  "detail": "A long branch", "sub": "YESTERDAY"} for _ in range(6)]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "activity.svg"
            activity.generate_svg(items, str(path))
            xml = ET.fromstring(path.read_text(encoding="utf-8"))
        groups = xml.findall('s:g', NS)
        self.assertEqual(len(groups), 6)
        for i, group in enumerate(groups):
            rect = group.find('s:rect', NS)
            end = float(rect.attrib["x"]) + float(rect.attrib["width"])
            self.assertLessEqual(end, (405 if i < 3 else 805) - 82)
            self.assertTrue(group.find('s:text', NS).text.endswith("…"))
            self.assertEqual(group.find('s:title', NS).text, long_name)


if __name__ == "__main__":
    unittest.main()
