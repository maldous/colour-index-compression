# RELEASE-PREDICTIVE-1 results

Ideal predictive bits only; no physical archive claim.

Held-out bytes: 49152
Frozen causal choice: bayesian_eta1
HINDSIGHT ORACLE — NON-CAUSAL DIAGNOSTIC ONLY: 137918.797822 bits

| item | ideal bits |
| --- | ---: |
| fixedmix_v1 | 139280.337288 |
| fixedmix_v3_n1 | 139589.911061 |
| fixedmix_v3_n2 | 139592.969828 |
| equal_static | 139430.457037 |
| optimized_static | 139308.075794 |
| bayesian_eta1 | 139267.767730 |
| hedge_eta01 | 139337.778582 |
| fixed_share_1_256 | 139409.889643 |
| fixed_share_001 | 139420.876602 |
| fixedmix_v1 | 139280.337288 |
| fixedmix_v3_n1 | 139589.911061 |
| fixedmix_v3_n2 | 139592.969828 |

Raw native PPM path bits: 155099.386741; paid native valid-mass bits: 0.000000.
Best held-out single native expert: fixedmix_v1 (139280.337288 bits).
Causal gain over best held-out single: 0.000256 b/B; marginal over existing v1: 0.000256 b/B.
v3-N1 marginal over fixedmix-v1: -0.006298 b/B.
v3-N2 marginal over fixedmix-v1: -0.006361 b/B.
Gate (>0.05 b/B and >1% strongest-pool improvement): FAIL.
Duplicate null bits: 139280.337288.
Dirichlet noisy-null bits: dirichlet_eps0.1_seed0=143816.986489, dirichlet_eps0.1_seed1=143832.057109, dirichlet_eps0.1_seed2=143805.847216, dirichlet_eps0.1_seed3=143824.122822, dirichlet_eps0.1_seed4=143840.505457, dirichlet_eps0.2_seed0=150246.190531, dirichlet_eps0.2_seed1=150259.155496, dirichlet_eps0.2_seed2=150248.056737, dirichlet_eps0.2_seed3=150263.595644, dirichlet_eps0.2_seed4=150280.516889.
Redundant uniform-smoothing null bits: 143484.922443.
INVALID alignment-broken diagnostic bits: 139280.337288; it is not a causal forecast.
PPM rows are separate potential-new-model diagnostics; neither native raw PPM nor normalized PPM participates in the oracle, static/online pool, or gate.
This is a narrow omitted-signal screen; the full complementarity/calibration analysis remains CPI1.
These fixed ranges were not used by CPI1, but earlier project research may have exposed them; this is not a pristine corpus-level holdout.
Null oracle controls: {"duplicate": {"best_single_bits": 139280.3372884565, "noncausal_oracle_bits": 139280.3372884565, "oracle_gap_bits": 0.0, "equal_mixture_gain_bits": 0.0}, "smoothing": {"best_single_bits": 139280.3372884565, "noncausal_oracle_bits": 137114.40286399124, "oracle_gap_bits": 2165.9344244652602, "equal_mixture_gain_bits": -1591.8039387397002}, "independent_noise": {"best_single_bits": 139280.3372884565, "noncausal_oracle_bits": 133917.15096684467, "oracle_gap_bits": 5363.186321611836, "equal_mixture_gain_bits": -6432.6672620187455}, "INVALID_alignment_broken_losses": {"best_single_bits": 139280.3372884565, "noncausal_oracle_bits": 53667.00266173752, "oracle_gap_bits": 85613.33462671898, "equal_mixture_gain_bits": 51255.487180925484}}
