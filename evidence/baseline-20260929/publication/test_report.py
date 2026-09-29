"""Claims must fail closed when only incomplete or inconsistent evidence exists."""
import copy
import unittest
from build_report import CIX_SHA, PROFILE, comparison, validate_local


def verified():
    return dict(dataset_id='D1', algorithm='CIX', profile=PROFILE, status='VERIFIED',
                cix_commit=CIX_SHA, original_bytes=1048576, compressed_bytes=524288,
                original_sha256='a'*64, decompressed_sha256='a'*64,
                compression_seconds=2.0, decompression_seconds=1.0,
                ratio=2.0, compressed_percent=50.0, saving_percent=50.0,
                bits_per_input_byte=4.0, compression_MiB_s=0.5, decompression_MiB_s=1.0,
                repetition_count=3, required_repetitions=3, failures=[])


class Claims(unittest.TestCase):
    def test_partial_corpus_is_not_a_total(self):
        row = verified()
        rendered = comparison(['D1','D2'], {('D1','CIX'):row})
        self.assertIn('NOT MEASURED: 1', rendered)
        self.assertNotIn('524,288', rendered)

    def test_single_normal_repetition_is_not_a_verified_group(self):
        row = verified()
        row['repetition_count'] = 1
        with self.assertRaisesRegex(ValueError, 'repetitions'):
            validate_local([row])

    def test_bad_restore_and_changed_cix_are_rejected(self):
        for changed in ({'decompressed_sha256':'b'*64}, {'cix_commit':'b'*40}):
            row = verified()
            row.update(changed)
            with self.assertRaises((ValueError,AssertionError)):
                validate_local([row])

    def test_unit_error_and_cherry_picked_failure_are_rejected(self):
        for changed in ({'compression_MiB_s':0.524288}, {'failures':[{'status':'TIMEOUT'}]}):
            row = verified()
            row.update(changed)
            with self.assertRaises((ValueError,AssertionError)):
                validate_local([row])

    def test_duplicate_profiles_cannot_replace_a_single_result(self):
        row = verified()
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            validate_local([row,copy.deepcopy(row)])


if __name__ == '__main__':
    unittest.main()
