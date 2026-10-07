from benchmarks.build_paq_store_state import patch
from benchmarks.paq_store_state_probe import segmentation


def test_nested_segmentation_counts_only_model_leaf_inputs(tmp_path):
    log=tmp_path/'sample.log'
    log.write_text(' 0 | tar | 100 bytes [0 - 99]\n 0-0 | text | 60 bytes [0 - 59]\n 0-1 | zlib | 40 bytes [60 - 99]\n 0-1-0 | text | 80 bytes [0 - 79]\n')
    row=segmentation(log)
    assert row['leaf_blocks']==2 and row['leaf_model_input_bytes']=={'text':140}
    assert row['detected_types']=={'tar':1,'text':2,'zlib':1}


def test_patch_is_confined_to_predictor_free_branch():
    text='    Encoder en(predictorBlock.get(), predictorMain.get(), doEncoding, mode, &archive);'
    out=patch(text)
    assert out.endswith(text) and 'if (!doEncoding)' in out
    assert 'Unexpected probability request in stored mode.' in out
