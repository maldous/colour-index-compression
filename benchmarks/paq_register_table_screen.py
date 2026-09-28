"""Validate the exact integer-table formulation before native physical trials."""
import hashlib
import json
from pathlib import Path
import sys
from benchmarks import paq_register_adaptive_screen as screen, register_log_math as arithmetic


if __name__=='__main__':
    screen.Posterior=arithmetic.TablePosterior
    report=screen.analyze(sys.argv[1]);report['numerical_control']=__doc__
    for path in (Path(__file__),Path(arithmetic.__file__),arithmetic.HEADER):
        report['source_hashes'][str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
    report['posterior']='Q20 relative scores; pinned Q30-log/Q48-exp tables; integer interpolation and coding weights'
    report['limitation']='Exact native integer formulas, still a prediction-only screen. Native archive size, original-trace identity and independent restoration remain required.'
    Path(sys.argv[2]).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['rows'],indent=2))
