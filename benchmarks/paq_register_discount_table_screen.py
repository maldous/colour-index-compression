"""Check exact pinned-integer discount formulas against the preliminary screen."""
import hashlib
import json
from pathlib import Path
import sys
from benchmarks import paq_register_discount_screen as screen, register_discount_math as oracle


if __name__=='__main__':
    screen.DiscountPosterior=oracle.DiscountPosterior
    report=screen.analyze(sys.argv[1])
    for p in [Path(__file__),Path(oracle.__file__),Path('benchmarks/native/CixDiscountLogMath.hpp'),Path('benchmarks/native/CixLogTables.hpp')]:
        report['source_hashes'][str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
    report['numeric_formulation']='Pinned integer log/exp tables, Q20 scores, explicit nearest-rounded evidence discount. Native profiles use shifts5/7; other shifts remain diagnostics.'
    Path(sys.argv[2]).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['rows'],indent=2))
