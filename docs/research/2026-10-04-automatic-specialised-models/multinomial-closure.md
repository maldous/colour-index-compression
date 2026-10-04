# Multinomial helper closure

`runtime/cix_runtime/legacy/multinomial.py` is a dependency closure for the extracted specialist codecs. It is derived verbatim from the original helper span beginning at `vencode` and ending after `decode_type_class_known_n`, with only the standard-library imports required by that span (`math` and `typing.Iterable`).

The retained public and cross-module helper surface is: `vencode`, `vdecode`, `Fenwick`, `multinomial_cardinality`, `_ArithmeticEncoder`, `_ArithmeticDecoder`, `encode_type_class`, `decode_type_class`, `combination_rank_colex`, `combination_unrank_colex`, `_range_encode_type_sequence`, and `TYPECLASS_RANGE`. The closure also retains every private combinatorial, permutation, fixed-width, and arithmetic-range helper transitively called by those functions.

Evidence was collected from every current `runtime/cix_runtime/legacy/*.py` import and module-attribute use. The importers are the chemical/MyISAM, grid/fixed-star, image/volume, and ECOFF transform closures. Their imported symbols are all present in this closure. The focused test covers type-class rank and range encodings plus the shared Fenwick and combinatorial helpers.

Removed code begins with `_context_bucket` in the original `cix/multinomial.py` and runs to end of file. It consists of the CIXM adaptive portfolio stream API: context-model configuration, block selection, stream encoder/decoder, and lazy imports of `wavelet`, `adaptive`, `sparse`, `runs`, `lz`, `bwt`, `ppm`, `expertmix`, `fixedmix`, `transforms`, `numeric`, `record`, `periodic`, `bitplanes`, `chain`, `histogram`, and `stateful`. No extracted runtime module imports or calls those stream APIs; retaining them would leave imports to modules intentionally absent from the specialised closure.

This is a packaging reduction only. It does not change the retained helper algorithms or their framing semantics.
