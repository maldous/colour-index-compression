import json
import subprocess
import sys
from pathlib import Path

from benchmarks.leaderboard_position import position


def test_position_uses_numeric_totals_not_published_display_order():
    rows = [dict(total_bytes=n, compressor=str(n)) for n in (30, 10, 25, 20, 20)]
    result = position(20, rows)
    assert result['equivalent_position'] == 2
    assert result['published_entries'] == 5
    assert len(result['tied_entries']) == 2
    assert result['nearest_better'][-1]['total_bytes'] == 10
    assert result['nearest_worse'][0]['total_bytes'] == 25


def test_incomplete_cohort_cannot_emit_a_rank(tmp_path):
    published = tmp_path / 'published.json'
    published.write_text(json.dumps(dict(verified_corpus=[dict(name='missing', size=42)])))
    output = tmp_path / 'rank.json'
    script = Path(__file__).resolve().parents[1] / 'benchmarks/leaderboard_position.py'
    result = subprocess.run([sys.executable, str(script), '--published', str(published),
                             '--results', str(tmp_path), '--output', str(output)],
                            capture_output=True,text=True)
    assert result.returncode != 0
    assert 'no rank calculated' in result.stderr
    assert not output.exists()
