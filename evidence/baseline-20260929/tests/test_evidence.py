import importlib.util
import json
import sys
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))


def module(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/(name+'.py'))
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m


class EvidenceTests(unittest.TestCase):
    def test_weighted_metrics_use_compressed_not_input_size(self):
        m=module('reproduce_nnlcb_metrics')
        rows=[dict(original_bytes=100,compressed_bytes=25,compression_seconds=2,decompression_seconds=1,compression_peak_rss_bytes=100,decompression_peak_rss_bytes=50),
              dict(original_bytes=100,compressed_bytes=75,compression_seconds=4,decompression_seconds=3,compression_peak_rss_bytes=300,decompression_peak_rss_bytes=150)]
        result=m.aggregate(rows)
        self.assertEqual(result['AvgCR'],4)
        self.assertEqual(result['WavgCR'],5)
        self.assertEqual(result['AvgSSP'],50)
        self.assertEqual(result['WavgSSP'],37.5)
        self.assertEqual(result['CRP'],50)
        self.assertEqual(result['TotalCT'],6)
        self.assertEqual(result['AvgCPM'],200)

    def test_incomplete_universe_never_produces_aggregate(self):
        m=module('reproduce_nnlcb_metrics')
        manifest=[dict(dataset_id=f'D{i}',compatibility='NOT EXACTLY REPRODUCED') for i in range(1,29)]
        result=m.qualify(manifest,[])
        self.assertIsNone(result['aggregates'])
        self.assertFalse(result['complete_qualification'])
        self.assertEqual(len(result['matrix']),532)
        self.assertTrue(all(x['status'] and x['explanation'] for x in result['matrix']))

    def test_hash_mismatch_cannot_enter_a_qualified_aggregate(self):
        m=module('reproduce_nnlcb_metrics')
        manifest=[dict(dataset_id=f'D{i}',compatibility='EXACT',sha256='input',obtained_bytes=100) for i in range(1,29)]
        result=dict(dataset_id='D1',algorithm='CIX',status='VERIFIED',original_sha256='input',decompressed_sha256='wrong',original_bytes=100)
        with self.assertRaises(ValueError):m.qualify(manifest,[result])

    def test_synthetic_length_prefixes_and_domain_separation(self):
        m=module('generate_synthetic')
        with tempfile.TemporaryDirectory() as tmp:
            for kind in m.CLASSES:
                first=m.block(kind,0)
                self.assertEqual(len(first),m.BLOCK,kind)
                a=Path(tmp)/(kind+'-a');b=Path(tmp)/(kind+'-b')
                m.generate(kind,65537,a);m.generate(kind,m.BLOCK+17,b)
                self.assertEqual(a.read_bytes(),b.read_bytes()[:65537],kind)
        self.assertNotEqual(m.block('high_entropy',0),m.block('high_entropy',1))
        self.assertNotEqual(m.block('high_entropy',0),m.random_bytes('another-domain',0))

    def test_random_has_no_implausible_gzip_gain(self):
        import gzip,math
        from collections import Counter
        m=module('generate_synthetic');data=m.block('high_entropy',0)
        self.assertGreater(len(gzip.compress(data,compresslevel=9,mtime=0)),len(data))
        entropy=-sum((n/len(data))*math.log2(n/len(data)) for n in Counter(data).values())
        self.assertGreater(entropy,7.99)

    def test_published_CRP_bridge_discrepancy_preserved(self):
        rows=json.loads((ROOT/'tables/nnlcb-reference-reconciliation.json').read_text())
        self.assertEqual(len(rows),16)
        for r in rows:
            if r['algorithm']=='Lstm-compress':
                self.assertGreater(abs(r['reconstructed_AvgCR']-r['published_AvgCR']),0.23)
                self.assertGreater(abs(r['diagnostic_CV_div_sqrt_N']-r['published_CRP']),1)
                continue
            self.assertAlmostEqual(r['diagnostic_CV_div_sqrt_N'],r['published_CRP'],delta=0.002)
            self.assertGreater(r['reconstructed_CRP_equation3'],r['published_CRP']*5)
            self.assertAlmostEqual(r['reconstructed_WavgCR_compressed_weights'],r['published_WavgCR'],delta=0.002)

    def test_failed_warmup_remains_timeout_not_a_skipped_success(self):
        m=module('aggregate_results')
        base=dict(dataset_id='test',algorithm='CIX',profile='high-compression-v1',
                  input_manifest={'obtained_bytes':100},original_bytes=100,raw_result_path='raw')
        rows=[dict(base,repetition=0,warmup=True,status='TIMEOUT',failure_reason='36h phase limit')]
        rows.extend(dict(base,repetition=i,warmup=False,status='NOT RUN',failure_reason='prior timeout') for i in (1,2,3))
        result=m.aggregate(rows)[0]
        self.assertEqual(result['status'],'TIMEOUT')
        self.assertEqual(result['repetition_count'],0)
        self.assertEqual(len(result['failures']),3)
        self.assertNotIn('compression_seconds',result)

    def test_partial_successes_cannot_become_a_three_repetition_median(self):
        m=module('aggregate_results')
        base=dict(dataset_id='test',algorithm='gzip',profile='high-compression-v1',
                  input_manifest={'obtained_bytes':100},original_bytes=100,raw_result_path='raw',
                  original_sha256='same',decompressed_sha256='same',warmup=False)
        rows=[dict(base,repetition=1,status='VERIFIED'),dict(base,repetition=2,status='TIMEOUT')]
        result=m.aggregate(rows)[0]
        self.assertEqual(result['status'],'INCOMPLETE')
        self.assertEqual(result['repetition_count'],1)
        self.assertNotIn('compressed_bytes',result)

    def test_schedule_includes_every_tool_and_rotates_order(self):
        m=module('run_suite')
        jobs=m.schedule_dataset(dict(dataset_id='D1',obtained_bytes=1<<30))
        self.assertEqual(len(jobs),32)
        for i in range(4):
            group=[j for j in jobs if j['repetition']==i]
            self.assertEqual({j['algorithm'] for j in group},set(m.ALGORITHMS))
            self.assertTrue(all(j['warmup']==(i==0) for j in group))
        self.assertNotEqual(m.order('D1',1),m.order('D1',2))
        self.assertEqual(len(m.schedule_dataset(dict(dataset_id='big',obtained_bytes=10<<30))),8)

    def test_killed_inner_timer_does_not_erase_timeout(self):
        m=module('run_benchmark')
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'process-resources.json').write_text('')
            timing={'status':'TIMEOUT','wall_seconds':3600}
            result=m.attach_inner_resources(timing,p)
            self.assertEqual(result['status'],'TIMEOUT')
            self.assertIn('inner_resources_unavailable',result)

    def test_source_rotation_requires_verified_recovery_bytes(self):
        m=module('run_benchmark')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);original=root/'xml';original.write_bytes(b'canonical bytes')
            recovery=root/'source.bz2';recovery.write_bytes(b'recovery source')
            row=dict(dataset_id='WIKIPEDIA-20260901',sha256=m.digest(original),
                source_artifacts=[dict(destination=str(recovery),status='VERIFIED DOWNLOAD',bytes=recovery.stat().st_size,sha256='wrong')])
            with mock.patch.object(m.shutil,'disk_usage',return_value=type('Space',(),{'free':0})()):
                with self.assertRaises(ValueError):m.rotate_source_if_needed(row,original,root,100,{})
                self.assertTrue(original.exists())
                row['source_artifacts'][0]['sha256']=m.digest(recovery)
                result={};self.assertTrue(m.rotate_source_if_needed(row,original,root,100,result))
                self.assertFalse(original.exists());self.assertTrue(recovery.exists())
                self.assertEqual(result['rolling_source_storage']['original_sha256'],row['sha256'])


if __name__=='__main__':unittest.main()
