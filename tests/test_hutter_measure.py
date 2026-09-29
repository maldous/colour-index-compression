import sys

from benchmarks.hutter_measure import measure


def test_measure_captures_finished_command_and_temp_peak(tmp_path):
    report = measure([sys.executable, "-c", "open('payload', 'wb').write(b'x' * 4096)"], tmp_path, cpu=None, interval=0.001)
    assert report["completed"] is True
    assert report["exit_code"] == 0
    assert report["peak_temp_bytes"] >= 4096
