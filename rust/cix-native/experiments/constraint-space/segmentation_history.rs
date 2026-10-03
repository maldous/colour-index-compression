//! Stage 4 decoded-history segmentation prototype.  It is standalone research:
//! compile it only under a root-owned WaveScheduler lease against the frozen
//! `cix_native` rlib.  It does not alter a production archive or selector.
//!
//! NSCHv1 has a 19-byte header: magic(4), version(1), paid history H(u16),
//! source length(u32), segment count(u32), and source CRC-32(u32).
//! Every segment is route id(u8), decoded length(u32), payload length(u32), and
//! payload.  Only legacy-LZ receives the NSCH header's bounded decoded-prefix
//! history; raw and Huffman are self-contained, and adaptive remains reset
//! order-0 with an empty history.

use cix_native::{adaptive, huffman, legacy_lz};
use std::{
    env,
    fs::{self, File},
    io::Read,
    time::Instant,
};

const MAGIC: &[u8; 4] = b"NSCH";
const VERSION: u8 = 1;
const HEADER_BYTES: usize = 19;
const SEGMENT_METADATA_BYTES: usize = 9;
const MAX_SOURCE: usize = 4096;
const MAX_SEGMENTS: usize = 32;
const MAX_ARCHIVE: usize = 32768;

#[derive(Clone, Copy, Debug, Eq, PartialEq, Ord, PartialOrd)]
enum Route {
    Raw = 0,
    Huffman = 1,
    Adaptive = 2,
    LegacyLz = 3,
}

impl Route {
    fn from_id(id: u8) -> Result<Self, String> {
        match id {
            0 => Ok(Self::Raw),
            1 => Ok(Self::Huffman),
            2 => Ok(Self::Adaptive),
            3 => Ok(Self::LegacyLz),
            _ => Err("unknown NSCHv1 route id".into()),
        }
    }

    fn name(self) -> &'static str {
        match self {
            Self::Raw => "raw",
            Self::Huffman => "huffman",
            Self::Adaptive => "adaptive",
            Self::LegacyLz => "legacy-lz",
        }
    }

    fn coder(self) -> &'static str {
        match self {
            Self::Raw => "identity",
            Self::Huffman => "huffman::encode",
            Self::Adaptive => "adaptive::encode_general(0,8,[],1)",
            Self::LegacyLz => "legacy_lz::encode(decoded-prefix,1)",
        }
    }
}

#[derive(Clone)]
struct Edge {
    start: usize,
    end: usize,
    route: Route,
    payload: Vec<u8>,
}

impl Edge {
    fn total_cost(&self) -> usize {
        SEGMENT_METADATA_BYTES + self.payload.len()
    }
}

#[derive(Clone)]
struct Choice {
    cost: usize,
    segments: usize,
    edges: Vec<Edge>,
}

impl Choice {
    fn empty() -> Self {
        Self { cost: 0, segments: 0, edges: Vec::new() }
    }

    fn append(&self, edge: Edge) -> Result<Self, String> {
        let cost = self.cost.checked_add(edge.total_cost()).ok_or("segment cost overflow")?;
        let segments = self.segments.checked_add(1).ok_or("segment count overflow")?;
        if segments > MAX_SEGMENTS { return Err("segment count exceeds NSCHv1 bound".into()); }
        let mut edges = self.edges.clone();
        edges.push(edge);
        Ok(Self { cost, segments, edges })
    }
}

fn better(left: &Choice, right: &Choice) -> bool {
    (left.cost, left.segments) < (right.cost, right.segments)
}

fn crc32(data: &[u8]) -> u32 {
    let mut value = !0u32;
    for &byte in data {
        value ^= u32::from(byte);
        for _ in 0..8 {
            value = if value & 1 != 0 { (value >> 1) ^ 0xedb8_8320 } else { value >> 1 };
        }
    }
    !value
}

fn bounded_read(path: &str, cap: usize, what: &str) -> Result<Vec<u8>, String> {
    let meta = fs::metadata(path).map_err(|error| format!("{what} metadata: {error}"))?;
    if !meta.is_file() || meta.len() > cap as u64 { return Err(format!("{what} exceeds bound")); }
    let mut file = File::open(path).map_err(|error| format!("{what} open: {error}"))?;
    let mut bytes = Vec::new();
    file.take((cap + 1) as u64).read_to_end(&mut bytes).map_err(|error| format!("{what} read: {error}"))?;
    if bytes.len() > cap { Err(format!("{what} exceeds bound")) } else { Ok(bytes) }
}

fn encode_route(route: Route, input: &[u8], prefix: &[u8]) -> Result<Vec<u8>, String> {
    match route {
        Route::Raw => Ok(input.to_vec()),
        Route::Huffman => huffman::encode(input).map_err(|error| error.to_string()),
        Route::Adaptive => adaptive::encode_general(input, 0, 8, &[], 1),
        Route::LegacyLz => Ok(legacy_lz::encode(input, prefix, 1)?.payload),
    }
}

fn decode_route(route: Route, payload: &[u8], length: usize, prefix: &[u8]) -> Result<Vec<u8>, String> {
    match route {
        Route::Raw => {
            if payload.len() != length { return Err("raw segment length mismatch".into()); }
            Ok(payload.to_vec())
        }
        Route::Huffman => {
            // `huffman::decode` allocates from its embedded u64 decoded length.
            // NSCHv1 supplies the independently bounded segment length, so
            // reject a contradictory header before entering that decoder.
            if payload.len() < 19 || payload[0] != huffman::VERSION {
                return Err("invalid Huffman segment header".into());
            }
            let declared = u64::from_le_bytes(payload[3..11].try_into().map_err(|_| "invalid Huffman decoded length")?);
            if declared != length as u64 { return Err("Huffman embedded decoded length mismatch".into()); }
            huffman::decode(payload).map_err(|error| error.to_string())
        }
        Route::Adaptive => adaptive::decode_general(payload, length, &[], 1),
        Route::LegacyLz => legacy_lz::decode(payload, length, prefix, 4096),
    }
}

/// This cache records the physical best route for every admitted edge among
/// only the four fixed, reset-per-segment routes in this reference.  It makes
/// no claim of global optimality over codecs, parameters, or shared models.
/// A route tie is canonicalized by its stable numeric id; segmentation ties
/// are resolved separately by fewer segments.
fn edge(data: &[u8], start: usize, end: usize, history: usize) -> Result<Edge, String> {
    if start >= end || end > data.len() { return Err("invalid candidate edge".into()); }
    let input = &data[start..end];
    let mut best: Option<Edge> = None;
    for route in [Route::Raw, Route::Huffman, Route::Adaptive, Route::LegacyLz] {
        let prefix = &data[start.saturating_sub(history)..start];
        let candidate = Edge { start, end, route, payload: encode_route(route, input, prefix)? };
        if best.as_ref().map_or(true, |current| {
            (candidate.payload.len(), candidate.route) < (current.payload.len(), current.route)
        }) {
            best = Some(candidate);
        }
    }
    Ok(best.expect("four fixed routes"))
}

fn all_edges(data: &[u8], points: &[usize], history: usize) -> Result<Vec<Vec<Option<Edge>>>, String> {
    let mut cache = vec![vec![None; points.len()]; points.len()];
    for from in 0..points.len() {
        for to in from + 1..points.len() {
            cache[from][to] = Some(edge(data, points[from], points[to], history)?);
        }
    }
    Ok(cache)
}

fn dynamic_program(points: &[usize], cache: &[Vec<Option<Edge>>]) -> Result<Choice, String> {
    if points.first() != Some(&0) || points.last().is_none() { return Err("invalid boundary bank".into()); }
    // Retain one exact state for every endpoint and segment count.  Keeping
    // only a cheapest prefix would be unsound: a cheaper 32-segment prefix can
    // be unable to reach the end while a costlier prefix with fewer segments
    // remains admissible under NSCHv1's 32-segment limit.
    let mut best: Vec<Vec<Option<Choice>>> = vec![vec![None; MAX_SEGMENTS + 1]; points.len()];
    best[0][0] = Some(Choice::empty());
    for to in 1..points.len() {
        for from in 0..to {
            let edge = cache[from][to].as_ref().ok_or("missing edge cache")?.clone();
            for segment_count in 0..MAX_SEGMENTS {
                let Some(previous) = best[from][segment_count].clone() else { continue };
                let candidate = previous.append(edge.clone())?;
                let slot = &mut best[to][segment_count + 1];
                if slot.as_ref().map_or(true, |current| candidate.cost < current.cost) {
                    *slot = Some(candidate);
                }
            }
        }
    }
    let mut selected: Option<Choice> = None;
    for candidate in best.pop().ok_or("missing DP endpoint")?.into_iter().flatten() {
        // States are visited in ascending predecessor and segment-count order.
        // Strict replacement makes an equal-cost/equal-count partition retain
        // that first canonical predecessor; `better` still favours fewer
        // segments when the total physical cost ties.
        if selected.as_ref().map_or(true, |known| better(&candidate, known)) {
            selected = Some(candidate);
        }
    }
    selected.ok_or_else(|| "no segmentation path within 32 segments".into())
}

/// Independent exhaustive partition enumeration for the tiny exact check.
fn exhaustive_tiny(points: &[usize], cache: &[Vec<Option<Edge>>]) -> Result<Choice, String> {
    let internal = points.len().checked_sub(2).ok_or("invalid tiny points")?;
    if internal > 11 { return Err("tiny oracle boundary bound".into()); }
    let mut best: Option<Choice> = None;
    'partitions: for mask in 0usize..(1usize << internal) {
        let mut selected = vec![0usize];
        for bit in 0..internal { if mask & (1 << bit) != 0 { selected.push(bit + 1); } }
        selected.push(points.len() - 1);
        if selected.len() - 1 > MAX_SEGMENTS { continue 'partitions; }
        let mut current = Choice::empty();
        for pair in selected.windows(2) {
            current = current.append(cache[pair[0]][pair[1]].as_ref().ok_or("missing tiny edge")?.clone())?;
        }
        if best.as_ref().map_or(true, |known| better(&current, known)) { best = Some(current); }
    }
    best.ok_or_else(|| "no tiny partition".into())
}

fn fixed_points(length: usize, block: usize) -> Result<Vec<usize>, String> {
    if block == 0 { return Err("fixed block size must be positive".into()); }
    let mut points = vec![0];
    let mut cursor = block;
    while cursor < length { points.push(cursor); cursor = cursor.checked_add(block).ok_or("fixed block overflow")?; }
    if length != 0 { points.push(length); }
    if points.len() - 1 > MAX_SEGMENTS { return Err("fixed segmentation exceeds 32 segments".into()); }
    Ok(points)
}

fn fixed_choice(data: &[u8], points: &[usize], history: usize) -> Result<Choice, String> {
    let mut choice = Choice::empty();
    for pair in points.windows(2) {
        // A fixed control has precisely these adjacent blocks.  It selects a
        // route per block and never admits a coalesced whole-block edge.
        choice = choice.append(edge(data, pair[0], pair[1], history)?)?;
    }
    Ok(choice)
}

fn histogram_distance(left: &[u8], right: &[u8]) -> u64 {
    let mut a = [0u16; 256]; let mut b = [0u16; 256];
    for &byte in left { a[byte as usize] += 1; }
    for &byte in right { b[byte as usize] += 1; }
    a.iter().zip(b.iter()).map(|(&x, &y)| u64::from(x.abs_diff(y))).sum()
}

fn adjacent_repeat_change(left: &[u8], right: &[u8]) -> u64 {
    fn repeats(bytes: &[u8]) -> u64 { bytes.windows(2).filter(|pair| pair[0] == pair[1]).count() as u64 }
    repeats(left).abs_diff(repeats(right))
}

/// The bank is content-only and bounded.  The score is intentionally simple:
/// for each available matched 16/32/64-byte neighbourhood it adds normalized
/// histogram L1 change and normalized adjacent-equality count change.  It is
/// not a parser or format detector, and DP makes no claim outside these stored
/// candidate cuts.
fn adaptive_points(data: &[u8]) -> Vec<usize> {
    let n = data.len();
    if n == 0 { return vec![0]; }
    let mut ranked = Vec::new();
    for cut in 1..n {
        let mut score = 0u64;
        for width in [16usize, 32, 64] {
            let window = width.min(cut).min(n - cut);
            if window >= 8 {
                let left = &data[cut - window..cut];
                let right = &data[cut..cut + window];
                // Scale every matched-window statistic to its 64-byte value
                // so positions near an end are not favoured by unequal input
                // support.  This score only chooses a bounded candidate bank.
                score += histogram_distance(left, right) * 64 / window as u64;
                score += adjacent_repeat_change(left, right) * 16 * 64 / window as u64;
            }
        }
        ranked.push((score, cut));
    }
    ranked.sort_unstable_by(|left, right| right.0.cmp(&left.0).then_with(|| left.1.cmp(&right.1)));
    let mut selected = vec![0usize, n];
    for (_, cut) in ranked {
        if selected.len() == 17 { break; }
        if selected.iter().all(|&known| known.abs_diff(cut) >= 8) { selected.push(cut); }
    }
    selected.sort_unstable();
    selected
}

fn encode_archive(data: &[u8], choice: &Choice, history: usize) -> Result<Vec<u8>, String> {
    if choice.segments != choice.edges.len() || choice.segments > MAX_SEGMENTS { return Err("invalid selected segments".into()); }
    let mut archive = Vec::with_capacity(HEADER_BYTES + choice.cost);
    if history > 4096 { return Err("history exceeds NSCHv1 bound".into()); }
    archive.extend_from_slice(MAGIC); archive.push(VERSION); archive.extend_from_slice(&(history as u16).to_le_bytes());
    archive.extend_from_slice(&(u32::try_from(data.len()).map_err(|_| "source length overflow")?).to_le_bytes());
    archive.extend_from_slice(&(u32::try_from(choice.segments).map_err(|_| "segment count overflow")?).to_le_bytes());
    archive.extend_from_slice(&crc32(data).to_le_bytes());
    let mut cursor = 0usize;
    for edge in &choice.edges {
        if edge.start != cursor || edge.end <= edge.start { return Err("noncanonical selected timeline".into()); }
        let length = edge.end - edge.start;
        archive.push(edge.route as u8);
        archive.extend_from_slice(&(u32::try_from(length).map_err(|_| "segment length overflow")?).to_le_bytes());
        archive.extend_from_slice(&(u32::try_from(edge.payload.len()).map_err(|_| "payload length overflow")?).to_le_bytes());
        archive.extend_from_slice(&edge.payload);
        cursor = edge.end;
    }
    if cursor != data.len() || archive.len() != HEADER_BYTES + choice.cost { return Err("archive accounting mismatch".into()); }
    if archive.len() >= MAX_ARCHIVE { return Err("NSCHv1 archive exceeds exclusive bound".into()); }
    Ok(archive)
}

fn take_u32(bytes: &[u8], position: &mut usize, label: &str) -> Result<usize, String> {
    let end = position.checked_add(4).ok_or("integer position overflow")?;
    let slice = bytes.get(*position..end).ok_or_else(|| format!("truncated {label}"))?;
    *position = end;
    usize::try_from(u32::from_le_bytes(slice.try_into().map_err(|_| "invalid u32")?)).map_err(|_| format!("{label} overflow"))
}

fn take_u16(bytes: &[u8], position: &mut usize, label: &str) -> Result<usize, String> {
    let end = position.checked_add(2).ok_or("integer position overflow")?;
    let slice = bytes.get(*position..end).ok_or_else(|| format!("truncated {label}"))?;
    *position = end;
    Ok(u16::from_le_bytes(slice.try_into().map_err(|_| "invalid u16")?) as usize)
}

fn decode_archive(archive: &[u8]) -> Result<Vec<u8>, String> {
    if archive.len() < HEADER_BYTES || archive.len() >= MAX_ARCHIVE { return Err("NSCHv1 archive length".into()); }
    if &archive[..4] != MAGIC || archive[4] != VERSION { return Err("unsupported NSCHv1 archive".into()); }
    let mut position = 5usize;
    let history = take_u16(archive, &mut position, "history")?;
    let source_length = take_u32(archive, &mut position, "source length")?;
    let segment_count = take_u32(archive, &mut position, "segment count")?;
    let expected_crc = take_u32(archive, &mut position, "source CRC")? as u32;
    if position != HEADER_BYTES || history > 4096 || source_length > MAX_SOURCE || segment_count > MAX_SEGMENTS { return Err("NSCHv1 header bound".into()); }
    if (source_length == 0) != (segment_count == 0) { return Err("invalid empty NSCHv1 layout".into()); }
    let mut output = Vec::with_capacity(source_length);
    for _ in 0..segment_count {
        let route = Route::from_id(*archive.get(position).ok_or("truncated route id")?)?; position += 1;
        let length = take_u32(archive, &mut position, "segment length")?;
        let payload_length = take_u32(archive, &mut position, "payload length")?;
        if length == 0 || length > source_length.saturating_sub(output.len()) { return Err("invalid segment length".into()); }
        let end = position.checked_add(payload_length).ok_or("payload position overflow")?;
        let payload = archive.get(position..end).ok_or("truncated segment payload")?;
        position = end;
        let prefix_start = output.len().saturating_sub(history);
        let decoded = decode_route(route, payload, length, &output[prefix_start..])?;
        if decoded.len() != length { return Err("route decoded length mismatch".into()); }
        output.extend_from_slice(&decoded);
    }
    if position != archive.len() || output.len() != source_length || crc32(&output) != expected_crc { return Err("NSCHv1 canonical length or CRC mismatch".into()); }
    Ok(output)
}

fn json_timeline(choice: &Choice, history: usize) -> String {
    let fields: Vec<String> = choice.edges.iter().map(|edge| format!(
        "{{\"start\":{},\"len\":{},\"route\":\"{}\",\"coder\":\"{}\",\"shared_model\":\"{}\",\"metadata_bytes\":9,\"payload_bytes\":{},\"total_bytes\":{}}}",
        edge.start, edge.end - edge.start, edge.route.name(), edge.route.coder(), if edge.route == Route::LegacyLz { format!("decoded-prefix:{history}") } else { "none".into() }, edge.payload.len(), edge.total_cost()
    )).collect();
    format!("[{}]", fields.join(","))
}

fn json_points(points: &[usize]) -> String {
    format!("[{}]", points.iter().map(usize::to_string).collect::<Vec<_>>().join(","))
}

fn json_edge_cost_matrix(cache: &[Vec<Option<Edge>>]) -> String {
    let rows: Vec<String> = cache.iter().map(|row| {
        let cells: Vec<String> = row.iter().map(|edge| match edge {
            Some(edge) => edge.total_cost().to_string(),
            None => "null".into(),
        }).collect();
        format!("[{}]", cells.join(","))
    }).collect();
    format!("[{}]", rows.join(","))
}

fn admitted_partition_count(points: &[usize]) -> Result<usize, String> {
    if points.len() <= 1 { return Ok(1); }
    let internal = points.len().checked_sub(2).ok_or("invalid partition points")?;
    // Pascal accumulation avoids an overflowing multiply-before-divide in a
    // binomial formula.  For the largest reference (63 internal cuts), the
    // admitted sum through 31 cuts is 2^62 and fits the 64-bit host usize.
    let mut ways = [0usize; MAX_SEGMENTS];
    ways[0] = 1;
    for step in 0..internal {
        let upper = (step + 1).min(MAX_SEGMENTS - 1);
        for selected in (1..=upper).rev() {
            ways[selected] = ways[selected].checked_add(ways[selected - 1]).ok_or("partition count overflow")?;
        }
    }
    let mut total = 0usize;
    for value in ways {
        total = total.checked_add(value).ok_or("partition count overflow")?;
    }
    Ok(total)
}

fn boundary_generation(mode: &str) -> &'static str {
    match mode {
        "whole" => "whole-input",
        "fixed" => "declared-adjacent-blocks",
        "adaptive" => "bounded-content-window-score",
        "tiny-oracle" | "small-reference" => "all-byte-cuts",
        _ => "unknown",
    }
}

fn mode_choice(mode: &str, data: &[u8], fixed_size: Option<usize>, history: usize) -> Result<(Choice, Vec<usize>, Option<usize>, usize, Option<String>), String> {
    match mode {
        "whole" => {
            if data.is_empty() { return Ok((Choice::empty(), vec![0], None, 0, None)); }
            let points = vec![0, data.len()]; let cache = all_edges(data, &points, history)?;
            Ok((dynamic_program(&points, &cache)?, points, None, 1, None))
        }
        "fixed" => {
            let points = fixed_points(data.len(), fixed_size.ok_or("missing fixed size")?)?;
            let edge_count = points.len().saturating_sub(1);
            Ok((fixed_choice(data, &points, history)?, points, None, edge_count, None))
        }
        "adaptive" => {
            let points = adaptive_points(data);
            if data.is_empty() { return Ok((Choice::empty(), points, None, 0, None)); }
            let cache = all_edges(data, &points, history)?;
            let edge_count = points.len() * points.len().saturating_sub(1) / 2;
            Ok((dynamic_program(&points, &cache)?, points, None, edge_count, None))
        }
        "tiny-oracle" => {
            if data.len() > 12 { return Err("tiny oracle source length exceeds 12".into()); }
            if data.is_empty() { return Ok((Choice::empty(), vec![0], Some(0), 0, Some("[[null]]".into()))); }
            let points: Vec<usize> = (0..=data.len()).collect(); let cache = all_edges(data, &points, history)?;
            let dp = dynamic_program(&points, &cache)?;
            let exhaustive = exhaustive_tiny(&points, &cache)?;
            let gap = dp.cost.abs_diff(exhaustive.cost);
            if gap != 0 { return Err("tiny DP disagrees with exhaustive partition enumeration".into()); }
            let edge_count = points.len() * points.len().saturating_sub(1) / 2;
            Ok((dp, points, Some(gap), edge_count, Some(json_edge_cost_matrix(&cache))))
        }
        "small-reference" => {
            if data.len() > 64 { return Err("small reference source length exceeds 64".into()); }
            if data.is_empty() { return Ok((Choice::empty(), vec![0], Some(0), 0, Some("[[null]]".into()))); }
            // All byte cuts are admitted here, so DP is exact for this finite
            // route/reset portfolio.  It is deliberately not an unbounded
            // codec search or a claim about a broader compressor space.
            let points: Vec<usize> = (0..=data.len()).collect();
            let cache = all_edges(data, &points, history)?;
            let dp = dynamic_program(&points, &cache)?;
            let gap = if data.len() <= 12 {
                let exhaustive = exhaustive_tiny(&points, &cache)?;
                let gap = dp.cost.abs_diff(exhaustive.cost);
                if gap != 0 { return Err("small-reference DP disagrees with exhaustive partition enumeration".into()); }
                Some(gap)
            } else {
                None
            };
            let edge_count = points.len() * points.len().saturating_sub(1) / 2;
            Ok((dp, points, gap, edge_count, Some(json_edge_cost_matrix(&cache))))
        }
        _ => Err("unknown segmentation mode".into()),
    }
}

fn encode(mode: &str, fixed_size: Option<usize>, input_path: &str, archive_path: &str, history: usize) -> Result<(), String> {
    let input = bounded_read(input_path, MAX_SOURCE, "source")?;
    if history != 0 && history != 1024 { return Err("history must be 0 or 1024".into()); }
    let started = Instant::now();
    let (choice, points, tiny_gap, edge_count, edge_cost_matrix) = mode_choice(mode, &input, fixed_size, history)?;
    let selection_elapsed = started.elapsed().as_nanos();
    let archive = encode_archive(&input, &choice, history)?;
    // This in-process archive-only validation catches disagreement between
    // selected route metadata and the decoder before retaining the archive.
    // The scheduler's runner performs the separate fresh-process decode.
    if decode_archive(&archive)? != input { return Err("in-process NSCHv1 round trip mismatch".into()); }
    fs::write(archive_path, &archive).map_err(|error| format!("archive write: {error}"))?;
    let partition_count = if mode == "fixed" || mode == "whole" { 1usize } else { admitted_partition_count(&points)? };
    println!(
        "{{\"experiment\":\"segmentation-history-stage4\",\"operation\":\"encode\",\"mode\":\"{}\",\"history_bytes\":{},\"source_bytes\":{},\"source_cap_bytes\":{},\"archive_bytes\":{},\"archive_cap_bytes\":{},\"header_bytes\":19,\"history_header_bytes\":2,\"boundary_generation\":\"{}\",\"boundary_points\":{},\"candidate_boundary_count\":{},\"candidate_edge_count\":{},\"candidate_route_trials\":{},\"candidate_partition_count\":{},\"edge_cost_matrix\":{},\"selection_elapsed_ns\":{},\"complete_encode_and_validation_elapsed_ns\":{},\"exhaustive_partition_gap_bytes\":{},\"decoder_search\":false,\"streaming_lookahead_claim\":false,\"selected_segments\":{}}}",
        mode, history, input.len(), MAX_SOURCE, archive.len(), MAX_ARCHIVE, boundary_generation(mode), json_points(&points), points.len(), edge_count, edge_count * 4,
        partition_count, edge_cost_matrix.unwrap_or_else(|| "null".into()),
        selection_elapsed, started.elapsed().as_nanos(), tiny_gap.map_or("null".into(), |gap| gap.to_string()), json_timeline(&choice, history)
    );
    Ok(())
}

fn decode(input_path: &str, output_path: &str) -> Result<(), String> {
    let started = Instant::now();
    let archive = bounded_read(input_path, MAX_ARCHIVE, "archive")?;
    let output = decode_archive(&archive)?;
    fs::write(output_path, &output).map_err(|error| format!("output write: {error}"))?;
    println!("{{\"experiment\":\"segmentation-history-stage4\",\"operation\":\"decode\",\"archive_bytes\":{},\"restored_bytes\":{},\"decode_elapsed_ns\":{},\"canonical_ids_lengths_sum_crc\":true,\"decoder_search\":false,\"streaming_lookahead_claim\":false}}", archive.len(), output.len(), started.elapsed().as_nanos());
    Ok(())
}

fn run() -> Result<(), String> {
    let mut args: Vec<String> = env::args().skip(1).collect();
    let mut history = 1024usize;
    if args.first().is_some_and(|value| value == "--history") {
        if args.len() < 2 { return Err("missing --history value".into()); }
        history = args[1].parse().map_err(|_| "invalid --history value")?;
        args.drain(..2);
    }
    match args.as_slice() {
        [operation, input, output] if operation == "--whole" => encode("whole", None, input, output, history),
        [operation, size, input, output] if operation == "--fixed" => encode("fixed", Some(size.parse().map_err(|_| "invalid fixed size")?), input, output, history),
        [operation, input, output] if operation == "--adaptive" => encode("adaptive", None, input, output, history),
        [operation, input, output] if operation == "--tiny-oracle" => encode("tiny-oracle", None, input, output, history),
        [operation, input, output] if operation == "--small-reference" => encode("small-reference", None, input, output, history),
        [operation, archive, output] if operation == "decode" => decode(archive, output),
        _ => Err("usage: segmentation_history [--history 0|1024] --whole INPUT ARCHIVE | --fixed SIZE INPUT ARCHIVE | --adaptive INPUT ARCHIVE | --tiny-oracle INPUT ARCHIVE | --small-reference INPUT ARCHIVE | decode ARCHIVE OUT".into()),
    }
}

fn main() {
    if let Err(error) = run() { eprintln!("segmentation_reference: {error}"); std::process::exit(1); }
}
