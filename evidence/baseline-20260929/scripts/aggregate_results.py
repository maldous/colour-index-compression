#!/usr/bin/env python3
"""Summarise every scheduled run; no favourable-repetition selection."""
import argparse
from collections import defaultdict
import csv
import json
from pathlib import Path
import statistics


def summary(values):
    median=statistics.median(values)
    return dict(median=median,minimum=min(values),maximum=max(values),
                MAD=statistics.median(abs(v-median) for v in values),n=len(values))


def aggregate(raw_rows):
    groups=defaultdict(list)
    for row in raw_rows:
        if row.get('smoke_only'):continue
        groups[(row['dataset_id'],row['algorithm'],row['profile'])].append(row)
    output=[]
    for (dataset,algorithm,profile),all_rows in sorted(groups.items()):
        rows=[r for r in all_rows if not r.get('warmup')]
        if not rows:continue
        required=3 if rows[0].get('original_bytes',rows[0]['input_manifest']['obtained_bytes'])<=1<<30 else 1
        verified=[r for r in rows if r['status']=='VERIFIED']
        identity={(r.get('original_sha256'),r.get('original_bytes'),r.get('cix_commit')) for r in verified}
        if len(identity)>1:raise ValueError('Mixed source/commit in one summary')
        result=dict(dataset_id=dataset,algorithm=algorithm,profile=profile,status='INCOMPLETE',
                    required_repetitions=required,repetition_count=len(verified),
                    attempted_repetitions=len(rows),warmup_attempts=len(all_rows)-len(rows),
                    failures=[dict(repetition=r['repetition'],status=r['status'],reason=r.get('failure_reason')) for r in rows if r['status']!='VERIFIED'],
                    warmup_failures=[dict(status=r['status'],reason=r.get('failure_reason')) for r in all_rows if r.get('warmup') and r['status']!='VERIFIED'],
                    raw_result_paths=[r['raw_result_path'] for r in all_rows],
                    cix_commit=rows[0].get('cix_commit'))
        if not verified:
            result['status']=rows[-1]['status'];result['failure_reason']=rows[-1].get('failure_reason')
            output.append(result);continue
        if len(verified)!=required or len(rows)!=required or result['failures']:
            result['failure_reason']='Prescribed measured repetition schedule is incomplete or contains a failed run'
            output.append(result);continue
        assert len({r['repetition'] for r in verified})==required
        first=verified[0];n=first['original_bytes']
        cs=summary([r['compressed_bytes'] for r in verified]);size=cs['median']
        ct=summary([r['compression']['wall_seconds'] for r in verified])
        dt=summary([r['decompression']['wall_seconds'] for r in verified])
        cp=summary([r['compression']['kernel_max_single_process_rss_bytes'] for r in verified])
        dp=summary([r['decompression']['kernel_max_single_process_rss_bytes'] for r in verified])
        assert all(r['original_sha256']==r['decompressed_sha256'] and r['original_bytes']==r['restored_bytes'] for r in verified)
        result.update(status='VERIFIED',original_bytes=n,compressed_bytes=size,
                      original_sha256=first['original_sha256'],decompressed_sha256=first['decompressed_sha256'],
                      compression_seconds=ct['median'],decompression_seconds=dt['median'],
                      compression_peak_rss_bytes=cp['median'],decompression_peak_rss_bytes=dp['median'],
                      compression_MiB_s=n/1048576/ct['median'],decompression_MiB_s=n/1048576/dt['median'],
                      ratio=n/size,compressed_percent=100*size/n,saving_percent=100*(1-size/n),bits_per_input_byte=8*size/n,
                      verification='Every measured repetition restored exact SHA-256 and length',
                      compression_command=first['compression_command'],decompression_command=first['decompression_command'],
                      compressor_identity=first['compressor_identity'],
                      dispersion=dict(compressed_bytes=cs,compression_seconds=ct,decompression_seconds=dt,compression_peak_rss_bytes=cp,decompression_peak_rss_bytes=dp))
        output.append(result)
    return output


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run_directory',type=Path);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    raw=[]
    for file in sorted(args.run_directory.rglob('result.json')):
        row=json.loads(file.read_text());row['raw_result_path']=str(file.absolute());raw.append(row)
    rows=aggregate(raw);args.output.write_text(json.dumps(rows,indent=2)+'\n')
    fields=['dataset_id','algorithm','profile','status','original_bytes','compressed_bytes','ratio','compressed_percent','saving_percent','bits_per_input_byte','compression_seconds','decompression_seconds','compression_MiB_s','decompression_MiB_s','compression_peak_rss_bytes','decompression_peak_rss_bytes','repetition_count','required_repetitions','original_sha256','decompressed_sha256','verification','cix_commit','compression_command','decompression_command','failure_reason']
    with args.output.with_suffix('.csv').open('w',newline='') as stream:
        w=csv.DictWriter(stream,fieldnames=fields,extrasaction='ignore');w.writeheader()
        for row in rows:w.writerow({k:json.dumps(v) if isinstance(v,(list,dict)) else v for k,v in row.items()})
    print(json.dumps(dict(groups=len(rows),verified=sum(r['status']=='VERIFIED' for r in rows))))
