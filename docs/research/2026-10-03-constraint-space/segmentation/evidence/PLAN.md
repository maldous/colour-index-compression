# Contiguous segmentation baseline — frozen staged screen

Audit and prior-art review precede this implementation. Production source is
unchanged. Stage2/3 only: independent reset segments, one frozen native route
portfolio raw/Huffman/order0adaptive/legacyLZeffort1 from sealed d3a2 rlib.
No history, model sharing, lanes or hierarchy until this baseline completes.

Completecost=17global header(sourceCRC/length/count)+sum(9segmentfields+payload).
DP0=0, DP[j]=min_i(DP[i]+min_route actualedgebytes), tie fewersegments, stablefirstpredecessor; peredge route tieslowestID.
Source<=4096B,segments<=32. Fixedblocks are mandatoryadjacent, notmergeable.
Adaptive scans byte cuts with matchedwindow16/32/64 histogram/repeat changes,
spacing>=8, atmost17points. Costs materialized exactly andcached; estimates only
generatecuts. No globaloptimality claim. Whole/raw always legal. Tiny<=12 DP
crosschecks exhaustivepartitions; allcut reference<=64 has fixedroute exactDP.

Five tiny inputs + four64B controls compareadaptive with allcutreference.
Eight mediuminputs coverhomogeneous,abrupt,gradual,shortalternation,A-B-A,
longcrossboundarydependency,interleavedfields/noise,highentropy. Corresponding
heldout seed/length/ordering variants are frozenbeforeexecution; no boundary
labels passedtoencoder. Newsyntheticbytes only, no acquisition or corpusrun.
All generationparameters/sourcecodehash boundbeforecoding; physicalinputs
hashes recordedin scheduledgeneratorphasebeforefirstencode.

Each medium input compareswhole,fixed64/256/1024,adaptive; currentsealedCIX
DEFAULT andBEST; nativezstd19/xz9e/bzip9/gzipn9 completecontrols. Fresharchiveonly
decode SHA, fulloffsettimeline andall costs recorded. Plain current CIXG2
fixedblock --explain trace is separatediagnostic; not inferredfromflags.

ExistingglobalWaveScheduler leaseCPU8quota1/2GiB/swap0/64MiBactivework,
build120/generator40/batch720seconds,native120/reference120. One observation
perconfig; no averages or comparisontoimportedCPUtimes. No production changes,
Actions, Sites, Hutter, acquisition orfull datasets. Stage4/5remain gated.

Independent partition DP uses emitted measured edge-cost matrix; exhaustive
reference independently enumerates partitions, not the route implementations.
Malformed checks: truncation/trailing, source/segment/payload lengths, segment
count, route ID, CRC and contradictory embedded Huffman length.
