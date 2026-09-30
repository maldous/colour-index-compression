# CIX projection research

| Recipe | Priority | Input range | Control bytes | Complete bytes | Δ | Verification | Encode / decode s | Memory lower bound | Decision |
|---|---|---|---:|---:|---:|---|---:|---:|---|
| p1 | p1 priority | 0+4194304 5ba647fec2ba | 799638 | 2216487 | 1416849 | SIZE_REJECTED_UNVERIFIED | 12.489322783891112 / — | 221409280 | size loss; decode skipped |
| p3 | p3 priority | 0+4194304 5ba647fec2ba | 799638 | 2223524 | 1423886 | SIZE_REJECTED_UNVERIFIED | 13.789767529815435 / — | 226095104 | size loss; decode skipped |
| p2 | p2 priority | 0+4194304 5ba647fec2ba | 799638 | 3346456 | 2546818 | SIZE_REJECTED_UNVERIFIED | 14.710759273730218 / — | 214478848 | size loss; decode skipped |
| p1 | p1 priority | 400000000+4194304 a07035d4de76 | 720368 | 2135528 | 1415160 | SIZE_REJECTED_UNVERIFIED | 12.043918280862272 / — | 221224960 | size loss; decode skipped |
| p3 | p3 priority | 400000000+4194304 a07035d4de76 | 720368 | 2140617 | 1420249 | SIZE_REJECTED_UNVERIFIED | 13.645731962285936 / — | 226115584 | size loss; decode skipped |
| p2 | p2 priority | 400000000+4194304 a07035d4de76 | 720368 | 3328507 | 2608139 | SIZE_REJECTED_UNVERIFIED | 14.672664896119386 / — | 214552576 | size loss; decode skipped |
| p1 | p1 priority | 0+37253 dece3fc9570a | 350 | 2519 | 2169 | SHA256_MATCHED_REHASHED | 0.35549920005723834 / 0.31119417026638985 | 25878528 | verified loss |
| p3 | p3 priority | 0+37253 dece3fc9570a | 350 | 3750 | 3400 | SHA256_MATCHED_REHASHED | 0.3752075838856399 / 0.33081316808238626 | 31109120 | verified loss |
| p2 | p2 priority | 0+37253 dece3fc9570a | 350 | 17091 | 16741 | SHA256_MATCHED_REHASHED | 0.4323681127279997 / 0.2969797058030963 | 26755072 | verified loss |

PAQ controls are historical size references only. CIX and PAQ timing measurements are not presented as a matched speed comparison. Program package size is not measured here.
