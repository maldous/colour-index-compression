use flate2::{write::DeflateEncoder, Compression, Decompress, FlushDecompress, Status};
use sha2::{Digest, Sha256};
use std::sync::atomic::{AtomicBool, Ordering};
use std::{
    env,
    fs::{self, File, OpenOptions},
    io::{self, Read, Seek, SeekFrom, Write},
    path::Path,
    process,
    time::{SystemTime, UNIX_EPOCH},
};

mod adaptive;
mod external;
mod fixedmix;
mod ppm;
mod rank;

const MAGIC: &[u8; 5] = b"CIXG1";
const HEADER: usize = 13;
const END: u8 = 255;
const MAX_BLOCK: u32 = 65536;
static INTERRUPTED: AtomicBool = AtomicBool::new(false);
fn check_interrupted() -> Result<(), String> {
    if INTERRUPTED.load(Ordering::Relaxed) {
        Err("interrupted".into())
    } else {
        Ok(())
    }
}
fn read_poll<R: Read>(
    src: &mut R,
    buffer: &mut [u8],
    fd: i32,
    timeout: Option<std::time::Duration>,
) -> Result<Option<usize>, String> {
    loop {
        check_interrupted()?;
        #[cfg(unix)]
        {
            if fd >= 0 {
                let slice = std::time::Duration::from_millis(250);
                let wait = timeout.map(|t| t.min(slice)).unwrap_or(slice);
                if !wait_input(fd, wait).map_err(|e| {
                    if INTERRUPTED.load(Ordering::Relaxed) {
                        "interrupted".to_string()
                    } else {
                        ioerr(e)
                    }
                })? {
                    return Ok(None);
                }
            }
        }
        match src.read(buffer) {
            Ok(n) => return Ok(Some(n)),
            Err(e) if e.kind() == io::ErrorKind::Interrupted => continue,
            Err(e) => {
                return Err(if INTERRUPTED.load(Ordering::Relaxed) {
                    "interrupted".into()
                } else {
                    ioerr(e)
                })
            }
        }
    }
}
fn read_exact_poll<R: Read>(src: &mut R, mut buffer: &mut [u8], fd: i32) -> Result<(), String> {
    while !buffer.is_empty() {
        match read_poll(src, buffer, fd, None)? {
            Some(0) => return Err("truncated archive".into()),
            Some(n) => {
                let (_, rest) = buffer.split_at_mut(n);
                buffer = rest;
            }
            None => continue,
        }
    }
    Ok(())
}
#[derive(Default)]
struct Opt {
    decode: bool,
    stdout: bool,
    keep: bool,
    force: bool,
    test: bool,
    list: bool,
    level: u8,
    threads: usize,
    memory: usize,
    input: String,
    output: Option<String>,
    route: Option<String>,
    backend: String,
    external_backend: Option<String>,
    profile: String,
    profile_set: bool,
    portfolio: Option<String>,
    format: String,
    block: Option<u32>,
    stream: bool,
    history: usize,
    independent_blocks: bool,
    flush_interval: Option<std::time::Duration>,
}
fn usage() {
    println!("CIX (pronounced six) native stream compressor (CIXG1; not ZIP/gzip)\nUsage: cix [--external gzip|bzip2|xz|zstd|brotli --profile fast|current|size | --portfolio fast|current|size] [--format cixg1|cixm6] [--backend cix|deflate|hybrid|range|count-range] [--stream] [--block-size SIZE] [--memory SIZE] [--threads N] [--history SIZE] [--independent-blocks] [--flush-interval DURATION] [-1..-9] [-c] [-k] [-f] [--route auto|raw|runs|composition|lz|predictor|bwt|stride|phrases|ppm|mixture|deflate] [-o FILE] FILE...\n       uncix [--stream] [-d|-c|-t|-l] [-k] [-f] [-o FILE] FILE...\n       cixcat FILE...\nUse '-' for standard input/output. Supported stream routes: raw, runs, exact-rank composition, LZ, predictor, PPM, fixed mixer, BWT/MTF, stride transforms, phrases and raw DEFLATE. Adaptive-range and count-range coding are available with the predictor route's --backend option. --external writes bounded CIXB1 (max 16 MiB); `--format cixm6` writes bounded raw/multinomial CIXM6 blocks and `--format cixf1` adds the source basename wrapper; ordinary operation writes CIXG1. CIXG1 frames are limited to 65536 bytes.");
}
fn parse() -> Result<Opt, String> {
    let mut o = Opt {
        level: 6,
        threads: 1,
        memory: 512 * 1024 * 1024,
        backend: "hybrid".into(),
        profile: "current".into(),
        format: "cixg1".into(),
        ..Opt::default()
    };
    let args: Vec<String> = env::args().collect();
    let prog = Path::new(args.first().map(String::as_str).unwrap_or("cix"))
        .file_name()
        .unwrap_or_default()
        .to_string_lossy();
    o.decode = prog == "uncix" || prog == "unsix" || prog == "cixcat";
    o.stdout = prog == "cixcat";
    let mut files = vec![];
    let mut i = 1;
    while i < args.len() {
        let a = &args[i];
        if a == "--help" || a == "-h" {
            usage();
            process::exit(0)
        } else if a == "--version" {
            println!(
                "cix-native {} (CIXG1/CIXM6/CIXF1)",
                env!("CARGO_PKG_VERSION")
            );
            process::exit(0)
        } else if a == "-d" {
            o.decode = true
        } else if a == "-c" {
            o.stdout = true
        } else if a == "-k" {
            o.keep = true
        } else if a == "-f" {
            o.force = true
        } else if a == "-t" {
            o.test = true;
            o.decode = true
        } else if a == "-l" {
            o.list = true;
            o.decode = true
        } else if a == "-1"
            || a == "-2"
            || a == "-3"
            || a == "-4"
            || a == "-5"
            || a == "-6"
            || a == "-7"
            || a == "-8"
            || a == "-9"
        {
            o.level = a[1..].parse().unwrap()
        } else if a == "--stream" {
            o.stream = true
        } else if a == "--independent-blocks" {
            o.independent_blocks = true
        } else if a == "--threads"
            || a == "--memory"
            || a == "-o"
            || a == "--output"
            || a == "--route"
            || a == "--backend"
            || a == "--external"
            || a == "--profile"
            || a == "--portfolio"
            || a == "--format"
            || a == "--block"
            || a == "--block-size"
            || a == "--history"
            || a == "--flush-interval"
        {
            i += 1;
            if i == args.len() {
                return Err(format!("{a} requires a value"));
            }
            match a.as_str() {
                "--threads" => o.threads = args[i].parse().map_err(|_| "invalid thread count")?,
                "--memory" => o.memory = parse_size(&args[i])?,
                "--route" => o.route = Some(args[i].clone()),
                "--backend" => {
                    o.backend = args[i].clone();
                    if !matches!(
                        o.backend.as_str(),
                        "cix" | "deflate" | "hybrid" | "range" | "count-range"
                    ) {
                        return Err("unsupported backend".into());
                    }
                }
                "--external" => o.external_backend = Some(args[i].clone()),
                "--profile" => {
                    o.profile = args[i].clone();
                    o.profile_set = true;
                }
                "--portfolio" => o.portfolio = Some(args[i].clone()),
                "--format" => o.format = args[i].clone(),
                "--block" => o.block = Some(args[i].parse().map_err(|_| "invalid block size")?),
                "--block-size" => {
                    o.block = Some(
                        parse_size(&args[i])?
                            .try_into()
                            .map_err(|_| "block size overflows")?,
                    )
                }
                "--history" => o.history = parse_size(&args[i])?,
                "--flush-interval" => o.flush_interval = Some(parse_duration(&args[i])?),
                _ => o.output = Some(args[i].clone()),
            }
        } else if a.starts_with('-') && a != "-" {
            return Err(format!("unsupported option: {a}"));
        } else {
            files.push(a.clone())
        }
        i += 1
    }
    if files.is_empty() {
        return Err("missing input file".into());
    }
    if files.len() != 1 {
        return Err("this build accepts one input at a time".into());
    }
    o.input = files.remove(0);
    if o.threads == 0 {
        return Err("--threads must be positive".into());
    }
    Ok(o)
}
fn parse_size(s: &str) -> Result<usize, String> {
    let (n, m) = s.split_at(s.find(|c: char| !c.is_ascii_digit()).unwrap_or(s.len()));
    let v: usize = n.parse().map_err(|_| "invalid memory size")?;
    let mul = match m.to_ascii_lowercase().as_str() {
        "" | "b" => 1,
        "k" | "kb" | "kib" => 1024,
        "m" | "mb" | "mib" => 1024 * 1024,
        "g" | "gb" | "gib" => 1024 * 1024 * 1024,
        _ => return Err("size accepts bytes, KiB, MiB or GiB".into()),
    };
    v.checked_mul(mul)
        .ok_or_else(|| "memory size overflow".into())
}
fn parse_duration(s: &str) -> Result<std::time::Duration, String> {
    let (n, unit) = s.split_at(s.find(|c: char| !c.is_ascii_digit()).unwrap_or(s.len()));
    let value: u64 = n.parse().map_err(|_| "invalid flush interval")?;
    let millis = match unit.to_ascii_lowercase().as_str() {
        "ms" => value,
        "" | "s" | "sec" | "secs" => value.checked_mul(1000).ok_or("flush interval overflow")?,
        "m" | "min" | "mins" => value.checked_mul(60_000).ok_or("flush interval overflow")?,
        _ => return Err("flush interval accepts ms, seconds or minutes".into()),
    };
    if millis == 0 {
        return Err("flush interval must be positive".into());
    }
    Ok(std::time::Duration::from_millis(millis))
}
fn put_frame<W: Write>(w: &mut W, r: u8, n: u32, s: u32, h: &[u8; 32]) -> io::Result<()> {
    w.write_all(&[r])?;
    w.write_all(&n.to_le_bytes())?;
    w.write_all(&s.to_le_bytes())?;
    w.write_all(h)
}
fn read_u32<R: Read>(r: &mut R, fd: i32) -> Result<u32, String> {
    let mut b = [0; 4];
    read_exact_poll(r, &mut b, fd)?;
    Ok(u32::from_le_bytes(b))
}
#[cfg(unix)]
fn open_input(path: &str) -> Result<File, String> {
    if path != "-" {
        return File::open(path).map_err(ioerr);
    }
    use std::os::fd::FromRawFd;
    let fd = unsafe { libc::dup(libc::STDIN_FILENO) };
    if fd < 0 {
        return Err(ioerr(io::Error::last_os_error()));
    }
    Ok(unsafe { File::from_raw_fd(fd) })
}
#[cfg(not(unix))]
fn open_input(path: &str) -> Result<File, String> {
    if path == "-" {
        return Err("stdin streaming is not implemented on this platform".into());
    }
    File::open(path).map_err(ioerr)
}
#[cfg(unix)]
fn wait_input(fd: std::os::fd::RawFd, timeout: std::time::Duration) -> io::Result<bool> {
    let mut descriptor = libc::pollfd {
        fd,
        events: libc::POLLIN,
        revents: 0,
    };
    let milliseconds = timeout.as_millis().min(i32::MAX as u128) as i32;
    loop {
        let ready = unsafe { libc::poll(&mut descriptor, 1, milliseconds) };
        if ready >= 0 {
            return Ok(ready != 0);
        }
        let error = io::Error::last_os_error();
        if INTERRUPTED.load(Ordering::Relaxed) {
            return Err(io::Error::new(io::ErrorKind::Interrupted, "interrupted"));
        }
        if error.kind() != io::ErrorKind::Interrupted {
            return Err(error);
        }
    }
}
#[cfg(not(unix))]
fn wait_input(_fd: i32, _timeout: std::time::Duration) -> io::Result<bool> {
    Err(io::Error::new(
        io::ErrorKind::Unsupported,
        "timed pipe reads require Unix poll",
    ))
}
#[cfg(unix)]
fn input_fd(file: &File) -> i32 {
    use std::os::fd::AsRawFd;
    file.as_raw_fd()
}
#[cfg(not(unix))]
fn input_fd(_file: &File) -> i32 {
    -1
}
fn rle(b: &[u8]) -> Vec<u8> {
    let mut o = Vec::new();
    let mut i = 0;
    while i < b.len() {
        let mut j = i + 1;
        while j < b.len() && b[j] == b[i] {
            j += 1
        }
        o.push(b[i]);
        let mut n = (j - i) as u64;
        while n >= 128 {
            o.push((n as u8 & 127) | 128);
            n >>= 7
        }
        o.push(n as u8);
        i = j
    }
    o
}
fn unvar(b: &[u8], p: &mut usize) -> Result<usize, String> {
    let mut v = 0usize;
    for sh in (0..35).step_by(7) {
        if *p >= b.len() {
            return Err("truncated run varint".into());
        }
        let x = b[*p];
        *p += 1;
        v |= ((x & 127) as usize) << sh;
        if x < 128 {
            return Ok(v);
        }
    }
    Err("oversized run varint".into())
}
fn unrle(b: &[u8], n: usize) -> Result<Vec<u8>, String> {
    let (mut p, mut o) = (0, Vec::with_capacity(n));
    while p < b.len() {
        let c = b[p];
        p += 1;
        let k = unvar(b, &mut p)?;
        if k == 0 || o.len().checked_add(k).filter(|&x| x <= n).is_none() {
            return Err("invalid run length".into());
        }
        o.resize(o.len() + k, c)
    }
    if o.len() != n {
        return Err("run output length mismatch".into());
    }
    Ok(o)
}
fn deflate(b: &[u8], level: u8) -> io::Result<Vec<u8>> {
    let mut e = DeflateEncoder::new(Vec::new(), Compression::new(level as u32));
    e.write_all(b)?;
    e.finish()
}
fn entropy(b: &[u8]) -> f64 {
    if b.is_empty() {
        return 0.0;
    }
    let mut counts = [0usize; 256];
    let mut order = Vec::new();
    for &x in b {
        let c = &mut counts[x as usize];
        if *c == 0 {
            order.push(x as usize);
        }
        *c += 1;
    }
    let n = b.len() as f64;
    n.log2()
        - order
            .into_iter()
            .map(|i| counts[i] as f64 * (counts[i] as f64).log2())
            .sum::<f64>()
            / n
}

fn stream_payload(data: &[u8], level: u8, backend: &str) -> Result<(u8, Vec<u8>), String> {
    let mut candidates: Vec<(u8, Vec<u8>)> = vec![(0, data.to_vec()), (1, rle(data))];
    if matches!(backend, "cix" | "hybrid") && entropy(&data[..data.len().min(8192)]) < 7.5 {
        candidates.push((2, rank::encode_composition_tiles(data)?));
    }
    if matches!(backend, "deflate" | "hybrid") {
        let compressed = deflate(data, level).map_err(ioerr)?;
        candidates.push((3, compressed));
    }
    if backend == "range" {
        candidates.push((4, adaptive::encode(data)));
    }
    if backend == "count-range" {
        candidates.push((5, rank::encode_count_range(data)?));
    }
    // Python min() keeps the first equal-sized candidate; preserve its order.
    candidates
        .into_iter()
        .min_by_key(|(_, payload)| payload.len())
        .ok_or_else(|| "no CIX substream candidates".into())
}

fn streams_encode(parts: &[&[u8]], level: u8, backend: &str) -> Result<Vec<u8>, String> {
    if parts.is_empty() || parts.len() > 8 {
        return Err("CIX stream count must be from 1 to 8".into());
    }
    let mut out = Vec::new();
    out.push(parts.len() as u8);
    for part in parts {
        let (coder, payload) = stream_payload(part, level, backend)?;
        out.push(coder);
        out.extend_from_slice(&(part.len() as u32).to_le_bytes());
        out.extend_from_slice(&(payload.len() as u32).to_le_bytes());
        out.extend_from_slice(&payload);
    }
    Ok(out)
}

fn streams_decode(blob: &[u8], limit: usize) -> Result<Vec<Vec<u8>>, String> {
    if blob.is_empty() || blob[0] == 0 || blob[0] > 8 {
        return Err("invalid CIX substream count".into());
    }
    let mut pos = 1usize;
    let mut total = 0usize;
    let mut parts = Vec::with_capacity(blob[0] as usize);
    for _ in 0..blob[0] {
        if pos + 9 > blob.len() {
            return Err("truncated CIX substream descriptor".into());
        }
        let coder = blob[pos];
        let n = u32::from_le_bytes(blob[pos + 1..pos + 5].try_into().unwrap()) as usize;
        let size = u32::from_le_bytes(blob[pos + 5..pos + 9].try_into().unwrap()) as usize;
        pos += 9;
        total = total
            .checked_add(n)
            .ok_or("CIX substream length overflow")?;
        let end = pos
            .checked_add(size)
            .ok_or("CIX substream payload overflow")?;
        if total > limit || end > blob.len() {
            return Err("CIX substream resource/truncation limit".into());
        }
        let payload = &blob[pos..end];
        let decoded = match coder {
            0 => {
                if size != n {
                    return Err("raw substream size mismatch".into());
                }
                payload.to_vec()
            }
            1 => unrle(payload, n)?,
            2 => rank::decode_composition_tiles(payload, n)?,
            3 => inflate(payload, n)?,
            4 => adaptive::decode(payload, n)?,
            5 => rank::decode_composition_tiles(payload, n)?,
            _ => return Err(format!("unsupported CIX substream coder {coder}")),
        };
        parts.push(decoded);
        pos = end;
    }
    if pos != blob.len() {
        return Err("trailing CIX substream bytes".into());
    }
    Ok(parts)
}

fn stream_encode(data: &[u8], level: u8, backend: &str) -> Result<Vec<u8>, String> {
    streams_encode(&[data], level, backend)
}

fn stream_decode(blob: &[u8], expected: usize) -> Result<Vec<u8>, String> {
    let mut parts = streams_decode(blob, expected)?;
    if parts.len() != 1 || parts[0].len() != expected {
        return Err("expected exactly one CIX byte substream".into());
    }
    Ok(parts.remove(0))
}

fn predictor_residual(data: &[u8], inverse: bool) -> Vec<u8> {
    let mut values = vec![0u8; 65536];
    let mut valid = vec![false; 65536];
    let mut scores = [0u32; 3];
    let mut out = Vec::with_capacity(data.len());
    for (i, &value) in data.iter().enumerate() {
        let past = if inverse { out.as_slice() } else { data };
        let context = if i >= 2 {
            past[i - 2] as usize * 256 + past[i - 1] as usize
        } else {
            0
        };
        let predictions = [
            if i > 0 { past[i - 1] } else { 0 },
            if i >= 4 { past[i - 4] } else { 0 },
            if i >= 2 && valid[context] {
                values[context]
            } else {
                0
            },
        ];
        let mut winner = 0;
        for k in 1..3 {
            if scores[k] > scores[winner] {
                winner = k;
            }
        }
        let actual = if inverse {
            value ^ predictions[winner]
        } else {
            value
        };
        out.push(if inverse {
            actual
        } else {
            value ^ predictions[winner]
        });
        for k in 0..3 {
            scores[k] += u32::from(predictions[k] == actual);
        }
        if i >= 2 {
            values[context] = actual;
            valid[context] = true;
        }
        if (i + 1) % 256 == 0 {
            for score in &mut scores {
                *score /= 2;
            }
        }
    }
    out
}

fn read_word(bytes: &[u8], endian_le: bool) -> u64 {
    let mut word = [0u8; 8];
    if endian_le {
        word[..bytes.len()].copy_from_slice(bytes);
        u64::from_le_bytes(word)
    } else {
        word[8 - bytes.len()..].copy_from_slice(bytes);
        u64::from_be_bytes(word)
    }
}

fn write_word(word: u64, width: usize, endian_le: bool, output: &mut Vec<u8>) {
    let bytes = if endian_le {
        word.to_le_bytes()
    } else {
        word.to_be_bytes()
    };
    if endian_le {
        output.extend_from_slice(&bytes[..width]);
    } else {
        output.extend_from_slice(&bytes[8 - width..]);
    }
}

fn stride_spec(id: u8) -> Result<(usize, bool, bool), String> {
    match id {
        4 => Ok((1, true, false)),
        6 => Ok((4, true, true)),
        7 => Ok((8, true, true)),
        9 => Ok((4, false, true)),
        17 => Ok((4, true, false)),
        18 => Ok((8, true, false)),
        _ => Err(format!("unsupported stride transform {id}")),
    }
}

fn apply_stride(data: &[u8], id: u8) -> Result<Vec<u8>, String> {
    let (width, little, delta) = stride_spec(id)?;
    if width == 1 {
        let mut out = data.to_vec();
        for i in (1..out.len()).rev() {
            out[i] = out[i].wrapping_sub(out[i - 1]);
        }
        return Ok(out);
    }
    let usable = data.len() / width * width;
    let words: Vec<u64> = data[..usable]
        .chunks_exact(width)
        .map(|chunk| read_word(chunk, little))
        .collect();
    let mask = if width == 8 {
        u64::MAX
    } else {
        (1u64 << (width * 8)) - 1
    };
    let mut transformed = Vec::with_capacity(data.len());
    let mut previous = 0u64;
    for (i, &word) in words.iter().enumerate() {
        let value = if i == 0 {
            word
        } else if delta {
            word.wrapping_sub(previous) & mask
        } else {
            word ^ previous
        };
        write_word(value, width, little, &mut transformed);
        previous = word;
    }
    transformed.extend_from_slice(&data[usable..]);
    let usable = transformed.len() / width * width;
    let mut shuffled = Vec::with_capacity(transformed.len());
    for lane in 0..width {
        for index in (lane..usable).step_by(width) {
            shuffled.push(transformed[index]);
        }
    }
    shuffled.extend_from_slice(&transformed[usable..]);
    Ok(shuffled)
}

fn invert_stride(data: &[u8], id: u8) -> Result<Vec<u8>, String> {
    let (width, little, delta) = stride_spec(id)?;
    if width == 1 {
        let mut out = data.to_vec();
        for i in 1..out.len() {
            out[i] = out[i].wrapping_add(out[i - 1]);
        }
        return Ok(out);
    }
    let usable = data.len() / width * width;
    let words = usable / width;
    let mut unshuffled = vec![0u8; usable];
    for lane in 0..width {
        for word in 0..words {
            unshuffled[lane + word * width] = data[lane * words + word];
        }
    }
    unshuffled.extend_from_slice(&data[usable..]);
    let raw_usable = unshuffled.len() / width * width;
    let encoded_words: Vec<u64> = unshuffled[..raw_usable]
        .chunks_exact(width)
        .map(|chunk| read_word(chunk, little))
        .collect();
    let mask = if width == 8 {
        u64::MAX
    } else {
        (1u64 << (width * 8)) - 1
    };
    let mut restored = Vec::with_capacity(data.len());
    let mut previous = 0u64;
    for (i, &encoded) in encoded_words.iter().enumerate() {
        let value = if i == 0 {
            encoded
        } else if delta {
            previous.wrapping_add(encoded) & mask
        } else {
            previous ^ encoded
        };
        write_word(value, width, little, &mut restored);
        previous = value;
    }
    restored.extend_from_slice(&unshuffled[raw_usable..]);
    Ok(restored)
}

fn select_stride(sample: &[u8]) -> Result<u8, String> {
    let mut best = None;
    for id in [4u8, 6, 7, 9, 17, 18] {
        let transformed = apply_stride(sample, id)?;
        let score = entropy(&transformed);
        if best.map_or(true, |(_, old)| score < old) {
            best = Some((id, score));
        }
    }
    best.map(|(id, _)| id)
        .ok_or("empty stride candidate set".into())
}

fn phrase_encode(data: &[u8], level: u8) -> Result<Vec<u8>, String> {
    use std::collections::HashMap;
    let mut counts: HashMap<[u8; 2], (usize, usize)> = HashMap::new();
    for i in 0..data.len().saturating_sub(1) {
        let key = [data[i], data[i + 1]];
        let entry = counts.entry(key).or_insert((0, i));
        entry.0 += 1;
    }
    let mut dictionary: Vec<([u8; 2], usize, usize)> = counts
        .into_iter()
        .map(|(key, (count, first))| (key, count, first))
        .collect();
    dictionary.sort_by_key(|(_, count, first)| (std::cmp::Reverse(*count), *first));
    let dictionary: Vec<[u8; 2]> = dictionary
        .into_iter()
        .take(32)
        .filter_map(|(key, count, _)| (count >= 8).then_some(key))
        .collect();
    let mut lookup = HashMap::new();
    for (index, &key) in dictionary.iter().enumerate() {
        lookup.insert(key, index as u8);
    }
    let mut tags = Vec::new();
    let mut literals = Vec::new();
    let mut indices = Vec::new();
    let mut i = 0;
    while i < data.len() {
        if i + 1 < data.len() {
            if let Some(&index) = lookup.get(&[data[i], data[i + 1]]) {
                tags.push(1);
                indices.push(index);
                i += 2;
                continue;
            }
        }
        tags.push(0);
        literals.push(data[i]);
        i += 1;
    }
    let owned = vec![tags, literals, indices];
    let refs: Vec<&[u8]> = owned.iter().map(Vec::as_slice).collect();
    let streams = streams_encode(&refs, level, "hybrid")?;
    let mut out = Vec::with_capacity(1 + 2 * dictionary.len() + streams.len());
    out.push(dictionary.len() as u8);
    for key in dictionary {
        out.extend_from_slice(&key);
    }
    out.extend_from_slice(&streams);
    Ok(out)
}

fn phrase_decode(blob: &[u8], n: usize) -> Result<Vec<u8>, String> {
    if blob.is_empty() || blob[0] > 32 {
        return Err("invalid phrase dictionary size".into());
    }
    let count = blob[0] as usize;
    let start = 1 + count * 2;
    if start > blob.len() {
        return Err("truncated phrase dictionary".into());
    }
    let dictionary: Vec<[u8; 2]> = blob[1..start]
        .chunks_exact(2)
        .map(|p| [p[0], p[1]])
        .collect();
    let parts = streams_decode(&blob[start..], n.saturating_mul(2))?;
    if parts.len() != 3 {
        return Err("phrase stream count mismatch".into());
    }
    let (tags, literals, indices) = (&parts[0], &parts[1], &parts[2]);
    let (mut a, mut b) = (0usize, 0usize);
    let mut out = Vec::with_capacity(n);
    for &tag in tags {
        match tag {
            0 if a < literals.len() => {
                out.push(literals[a]);
                a += 1;
            }
            1 if b < indices.len() && (indices[b] as usize) < dictionary.len() => {
                out.extend_from_slice(&dictionary[indices[b] as usize]);
                b += 1;
            }
            _ => return Err("invalid phrase tag/index".into()),
        }
        if out.len() > n {
            return Err("phrase output overflow".into());
        }
    }
    if out.len() != n || a != literals.len() || b != indices.len() {
        return Err("phrase stream lengths mismatch".into());
    }
    Ok(out)
}

fn stride_encode(data: &[u8], level: u8) -> Result<Vec<u8>, String> {
    let id = select_stride(&data[..data.len().min(4096)])?;
    let transformed = apply_stride(data, id)?;
    let (width, _, _) = stride_spec(id)?;
    let plane = transformed.len() / width;
    let mut owned = Vec::with_capacity(width);
    for lane in 0..width - 1 {
        owned.push(transformed[lane * plane..(lane + 1) * plane].to_vec());
    }
    owned.push(transformed[(width - 1) * plane..].to_vec());
    let refs: Vec<&[u8]> = owned.iter().map(Vec::as_slice).collect();
    let streams = streams_encode(&refs, level, "hybrid")?;
    let mut out = Vec::with_capacity(1 + streams.len());
    out.push(id);
    out.extend_from_slice(&streams);
    Ok(out)
}

fn join_streams(blob: &[u8], limit: usize) -> Result<Vec<u8>, String> {
    let parts = streams_decode(blob, limit)?;
    let total = parts.iter().map(Vec::len).sum();
    if total > limit {
        return Err("decoded CIX stream length exceeds limit".into());
    }
    let mut out = Vec::with_capacity(total);
    for part in parts {
        out.extend_from_slice(&part);
    }
    Ok(out)
}

fn encode_route(route: u8, data: &[u8], level: u8, backend: &str) -> Result<Vec<u8>, String> {
    match route {
        0 => Ok(data.to_vec()),
        1 => Ok(rle(data)),
        2 => stream_encode(data, level, "cix"),
        3 => lz_encode(data, level),
        4 => stream_encode(&predictor_residual(data, false), level, backend),
        5 => bwt_encode(data, level),
        6 => stride_encode(data, level),
        7 => phrase_encode(data, level),
        8 => ppm::encode(data, 3),
        9 => Ok(fixedmix::encode(data)),
        10 => stream_encode(data, level, "deflate"),
        _ => Err(format!("unsupported native route ID {route}")),
    }
}

fn bwt_transform(data: &[u8]) -> Result<(usize, Vec<u8>), String> {
    let n = data.len();
    if n == 0 {
        return Ok((0, Vec::new()));
    }
    let mut suffixes: Vec<usize> = (0..n).collect();
    let mut ranks: Vec<i64> = data.iter().map(|&b| b as i64).collect();
    let mut width = 1usize;
    loop {
        suffixes.sort_unstable_by_key(|&i| {
            (ranks[i], if i + width < n { ranks[i + width] } else { -1 })
        });
        let mut next = vec![0i64; n];
        let mut class = 0i64;
        let mut previous: Option<(i64, i64)> = None;
        for &i in &suffixes {
            let pair = (ranks[i], if i + width < n { ranks[i + width] } else { -1 });
            if previous.is_some() && previous != Some(pair) {
                class += 1;
            }
            next[i] = class;
            previous = Some(pair);
        }
        ranks = next;
        if class as usize == n - 1 {
            break;
        }
        width = width.checked_mul(2).ok_or("BWT suffix width overflow")?;
    }
    let primary = suffixes
        .iter()
        .position(|&i| i == 0)
        .ok_or("BWT suffix array omitted source start")?
        + 1;
    let mut transformed = Vec::with_capacity(n);
    transformed.push(data[n - 1]);
    for &i in &suffixes {
        if i > 0 {
            transformed.push(data[i - 1]);
        }
    }
    if transformed.len() != n {
        return Err("invalid BWT transform size".into());
    }
    Ok((primary, transformed))
}

fn mtf_encode(data: &[u8]) -> Vec<u8> {
    let mut symbols: Vec<u8> = (0..=255).collect();
    let mut positions: Vec<usize> = (0..256).collect();
    let mut out = Vec::with_capacity(data.len());
    for &byte in data {
        let index = positions[byte as usize];
        out.push(index as u8);
        if index > 0 {
            let moved = symbols[index];
            for pos in (1..=index).rev() {
                symbols[pos] = symbols[pos - 1];
                positions[symbols[pos] as usize] = pos;
            }
            symbols[0] = moved;
            positions[moved as usize] = 0;
        }
    }
    out
}

fn mtf_decode(data: &[u8]) -> Vec<u8> {
    let mut symbols: Vec<u8> = (0..=255).collect();
    let mut out = Vec::with_capacity(data.len());
    for &index in data {
        let index = index as usize;
        let symbol = symbols[index];
        out.push(symbol);
        if index > 0 {
            symbols.copy_within(0..index, 1);
            symbols[0] = symbol;
        }
    }
    out
}

fn put_varint(mut value: usize, out: &mut Vec<u8>) {
    while value >= 128 {
        out.push((value as u8 & 0x7f) | 0x80);
        value >>= 7;
    }
    out.push(value as u8);
}

fn mtf_runs(data: &[u8]) -> (Vec<u8>, Vec<u8>, Vec<u8>) {
    let mtf = mtf_encode(data);
    let mut tags = Vec::new();
    let mut literals = Vec::new();
    let mut lengths = Vec::new();
    let mut i = 0;
    while i < mtf.len() {
        if mtf[i] == 0 {
            let start = i;
            i += 1;
            while i < mtf.len() && mtf[i] == 0 {
                i += 1;
            }
            tags.push(1);
            put_varint(i - start, &mut lengths);
        } else {
            tags.push(0);
            literals.push(mtf[i]);
            i += 1;
        }
    }
    (tags, literals, lengths)
}

fn unmtf_runs(parts: &[Vec<u8>], n: usize) -> Result<Vec<u8>, String> {
    if parts.len() != 3 {
        return Err("MTF substream count mismatch".into());
    }
    let (tags, literals, lengths) = (&parts[0], &parts[1], &parts[2]);
    let (mut literal_pos, mut length_pos) = (0usize, 0usize);
    let mut mtf = Vec::with_capacity(n);
    for &tag in tags {
        match tag {
            0 if literal_pos < literals.len() => {
                mtf.push(literals[literal_pos]);
                literal_pos += 1;
            }
            1 => {
                let count = unvar(lengths, &mut length_pos)?;
                if count == 0 || mtf.len().checked_add(count).filter(|&v| v <= n).is_none() {
                    return Err("invalid MTF zero run".into());
                }
                mtf.resize(mtf.len() + count, 0);
            }
            _ => return Err("invalid MTF tag/literal".into()),
        }
    }
    if mtf.len() != n || literal_pos != literals.len() || length_pos != lengths.len() {
        return Err("MTF stream lengths mismatch".into());
    }
    Ok(mtf_decode(&mtf))
}

fn bwt_inverse(primary: usize, transformed: &[u8]) -> Result<Vec<u8>, String> {
    let n = transformed.len();
    if n == 0 {
        return if primary <= 1 {
            Ok(Vec::new())
        } else {
            Err("invalid empty BWT index".into())
        };
    }
    if primary == 0 || primary > n {
        return Err("invalid BWT primary index".into());
    }
    let last: Vec<(u8, usize)> = transformed
        .iter()
        .copied()
        .enumerate()
        .map(|(i, b)| (b, i))
        .collect();
    let mut first = last.clone();
    first.sort_unstable();
    let mut inverse_last = vec![0usize; n];
    for (index, &item) in last.iter().enumerate() {
        inverse_last[item.1] = index + usize::from(index >= primary);
    }
    let mut current = first[primary - 1];
    let mut out = Vec::with_capacity(n);
    for _ in 0..n {
        out.push(current.0);
        let mapped = inverse_last[current.1];
        let index = if mapped == 0 { n - 1 } else { mapped - 1 };
        current = first[index];
    }
    Ok(out)
}

fn bwt_encode(data: &[u8], level: u8) -> Result<Vec<u8>, String> {
    let (primary, transformed) = bwt_transform(data)?;
    let (tags, literals, lengths) = mtf_runs(&transformed);
    let owned = vec![tags, literals, lengths];
    let refs: Vec<&[u8]> = owned.iter().map(Vec::as_slice).collect();
    let streams = streams_encode(&refs, level, "hybrid")?;
    let mut out = Vec::with_capacity(4 + streams.len());
    out.extend_from_slice(&(primary as u32).to_le_bytes());
    out.extend_from_slice(&streams);
    Ok(out)
}

fn lz_insert(table: &mut std::collections::HashMap<[u8; 4], Vec<usize>>, data: &[u8], pos: usize) {
    if pos + 4 > data.len() {
        return;
    }
    let key = [data[pos], data[pos + 1], data[pos + 2], data[pos + 3]];
    let candidates = table.entry(key).or_default();
    candidates.push(pos);
    if candidates.len() > 8 {
        candidates.remove(0);
    }
}

fn lz_encode(data: &[u8], level: u8) -> Result<Vec<u8>, String> {
    use std::collections::HashMap;
    let mut table: HashMap<[u8; 4], Vec<usize>> = HashMap::new();
    let mut tags = Vec::new();
    let mut literals = Vec::new();
    let mut lengths = Vec::new();
    let mut distances = Vec::new();
    let mut position = 0usize;
    while position < data.len() {
        let mut best_length = 0usize;
        let mut best_distance = 0usize;
        if position + 4 <= data.len() {
            let key = [
                data[position],
                data[position + 1],
                data[position + 2],
                data[position + 3],
            ];
            if let Some(candidates) = table.get(&key) {
                let limit = 65535.min(data.len() - position);
                let mut best_score = i64::MIN;
                for &candidate in candidates.iter().rev().take(8) {
                    let distance = position - candidate;
                    if distance == 0 || distance > 65536 {
                        continue;
                    }
                    let mut length = 4usize;
                    while length < limit
                        && data[position - distance + length] == data[position + length]
                    {
                        length += 1;
                    }
                    if length < 4 {
                        continue;
                    }
                    let score = (length * 8) as i64
                        - (usize::BITS - distance.leading_zeros()) as i64
                        - (usize::BITS - length.leading_zeros()) as i64
                        - 3;
                    if score > best_score || (score == best_score && length > best_length) {
                        best_score = score;
                        best_length = length;
                        best_distance = distance;
                    }
                }
            }
        }
        if best_length >= 4 {
            tags.push(1);
            put_varint(best_length - 4, &mut lengths);
            put_varint(best_distance, &mut distances);
            let stop = data.len().min(position + best_length);
            for p in position..stop {
                lz_insert(&mut table, data, p);
            }
            position += best_length;
        } else {
            tags.push(0);
            literals.push(data[position]);
            lz_insert(&mut table, data, position);
            position += 1;
        }
    }
    let owned = vec![tags, literals, lengths, distances];
    let refs: Vec<&[u8]> = owned.iter().map(Vec::as_slice).collect();
    streams_encode(&refs, level, "hybrid")
}

fn lz_decode(blob: &[u8], n: usize) -> Result<Vec<u8>, String> {
    let parts = streams_decode(blob, n.saturating_mul(4))?;
    if parts.len() != 4 {
        return Err("LZ stream count mismatch".into());
    }
    let (tags, literals, lengths, distances) = (&parts[0], &parts[1], &parts[2], &parts[3]);
    let (mut literal_pos, mut length_pos, mut distance_pos) = (0usize, 0usize, 0usize);
    let mut out = Vec::with_capacity(n);
    for &tag in tags {
        match tag {
            0 if literal_pos < literals.len() => {
                out.push(literals[literal_pos]);
                literal_pos += 1;
            }
            1 => {
                let length = unvar(lengths, &mut length_pos)?
                    .checked_add(4)
                    .ok_or("LZ match length overflow")?;
                let distance = unvar(distances, &mut distance_pos)?;
                if distance == 0
                    || distance > out.len().min(65536)
                    || out.len().checked_add(length).filter(|&v| v <= n).is_none()
                {
                    return Err("invalid LZ match descriptor".into());
                }
                for _ in 0..length {
                    let byte = out[out.len() - distance];
                    out.push(byte);
                }
            }
            _ => return Err("invalid LZ tag/literal".into()),
        }
        if out.len() > n {
            return Err("LZ output overflow".into());
        }
    }
    if out.len() != n
        || literal_pos != literals.len()
        || length_pos != lengths.len()
        || distance_pos != distances.len()
    {
        return Err("LZ stream lengths mismatch".into());
    }
    Ok(out)
}
fn inflate(b: &[u8], n: usize) -> Result<Vec<u8>, String> {
    let mut d = Decompress::new(false);
    let mut out = Vec::with_capacity(n.saturating_add(1));
    let status = d
        .decompress_vec(b, &mut out, FlushDecompress::Finish)
        .map_err(|e| format!("DEFLATE: {e}"))?;
    if status != Status::StreamEnd || d.total_in() != b.len() as u64 || out.len() != n {
        return Err("DEFLATE framing/size mismatch".into());
    }
    Ok(out)
}
fn encode<R: Read, W: Write>(
    mut src: R,
    mut dst: W,
    block: u32,
    level: u8,
    forced: Option<&str>,
    backend: &str,
    input_fd: i32,
    flush_interval: Option<std::time::Duration>,
) -> Result<(), String> {
    dst.write_all(MAGIC).map_err(ioerr)?;
    dst.write_all(&block.to_le_bytes()).map_err(ioerr)?;
    dst.write_all(&0u32.to_le_bytes()).map_err(ioerr)?;
    let mut whole = Sha256::new();
    let mut total_bytes = 0u64;
    let mut buf = vec![0; block as usize];
    let mut eof = false;
    loop {
        let mut got = 0;
        let mut symbol_counts = [0u32; 256];
        let mut buffered_since: Option<std::time::Instant> = None;
        while got < buf.len() {
            let timeout = match (flush_interval, buffered_since) {
                (Some(interval), Some(since)) => {
                    let elapsed = since.elapsed();
                    if elapsed >= interval {
                        break;
                    }
                    Some(interval - elapsed)
                }
                _ => None,
            };
            let n = match read_poll(&mut src, &mut buf[got..], input_fd, timeout)? {
                Some(n) => n,
                None => continue,
            };
            if n == 0 {
                eof = true;
                break;
            }
            for &byte in &buf[got..got + n] {
                symbol_counts[byte as usize] += 1;
            }
            got += n;
            if buffered_since.is_none() {
                buffered_since = Some(std::time::Instant::now());
            }
        }
        if got == 0 {
            if eof {
                break;
            }
            continue;
        }
        if symbol_counts.iter().sum::<u32>() != got as u32 {
            return Err("internal block symbol count mismatch".into());
        }
        total_bytes = total_bytes
            .checked_add(got as u64)
            .ok_or("input length overflow")?;
        let data = &buf[..got];
        let rh: [u8; 32] = Sha256::digest(data).into();
        whole.update(data);
        let (route, payload) = if let Some(f) = forced {
            let id = match f {
                "raw" => 0,
                "runs" => 1,
                "composition" => 2,
                "lz" => 3,
                "bwt" => 5,
                "predictor" => 4,
                "stride" => 6,
                "phrases" => 7,
                "ppm" => 8,
                "mixture" => 9,
                "deflate" => 10,
                _ => return Err(format!("unsupported route: {f}")),
            };
            (id, encode_route(id, data, level, backend)?)
        } else {
            let mut candidates = vec![(0u8, data.to_vec()), (1, rle(data))];
            candidates.push((2, encode_route(2, data, level, backend)?));
            candidates.push((10, encode_route(10, data, level, backend)?));
            candidates.sort_by_key(|x| x.1.len());
            candidates.remove(0)
        };
        put_frame(&mut dst, route, got as u32, payload.len() as u32, &rh).map_err(ioerr)?;
        dst.write_all(&payload).map_err(ioerr)?;
        dst.flush().map_err(ioerr)?;
        if eof {
            break;
        }
    }
    let h: [u8; 32] = whole.finalize().into();
    put_frame(&mut dst, END, 0, 0, &h).map_err(ioerr)?;
    dst.flush().map_err(ioerr)?;
    Ok(())
}

fn encode_m6<R: Read, W: Write>(
    mut src: R,
    mut dst: W,
    block_size: usize,
    file_name: Option<&str>,
) -> Result<(), String> {
    dst.write_all(b"CIXM6").map_err(ioerr)?;
    let mut header = Vec::new();
    put_varint(1 << 20, &mut header);
    dst.write_all(&header).map_err(ioerr)?;
    let mut whole = 0usize;
    let mut crc = crc32fast::Hasher::new();
    let mut block = vec![0u8; block_size.min(MAX_BLOCK as usize).max(1)];
    loop {
        let mut got = 0;
        while got < block.len() {
            check_interrupted()?;
            let n = match src.read(&mut block[got..]) {
                Ok(n) => n,
                Err(e) if e.kind() == io::ErrorKind::Interrupted => continue,
                Err(e) => return Err(ioerr(e)),
            };
            if n == 0 {
                break;
            }
            got += n;
        }
        if got == 0 {
            break;
        }
        let data = &block[..got];
        let coded = rank::encode_type_class(data)?;
        let coded_cost = 1 + varint_len(got) + varint_len(coded.len()) + coded.len();
        let raw_cost = 1 + varint_len(got) + varint_len(got) + got;
        let (mode, payload) = if coded_cost < raw_cost {
            (1, coded.as_slice())
        } else {
            (0, data)
        };
        let mut frame = vec![mode];
        put_varint(got, &mut frame);
        put_varint(payload.len(), &mut frame);
        dst.write_all(&frame).map_err(ioerr)?;
        dst.write_all(payload).map_err(ioerr)?;
        dst.flush().map_err(ioerr)?;
        crc.update(data);
        whole = whole
            .checked_add(got)
            .ok_or("CIXM6 stream length overflow")?;
        if got < block.len() {
            break;
        }
    }
    let mut footer = vec![255];
    put_varint(whole, &mut footer);
    footer.extend_from_slice(&crc.finalize().to_le_bytes());
    dst.write_all(&footer).map_err(ioerr)?;
    if let Some(name) = file_name {
        let bytes = name.as_bytes();
        let name_len = u32::try_from(bytes.len()).map_err(|_| "CIXF1 filename is too long")?;
        dst.write_all(bytes).map_err(ioerr)?;
        dst.write_all(&name_len.to_le_bytes()).map_err(ioerr)?;
        dst.write_all(b"CIXF1").map_err(ioerr)?;
    }
    dst.flush().map_err(ioerr)
}

fn varint_len(mut value: usize) -> usize {
    let mut n = 1;
    while value >= 128 {
        value >>= 7;
        n += 1;
    }
    n
}

fn cixg_candidate(data: &[u8], route: Option<u8>, level: u8) -> Result<Vec<u8>, String> {
    let mut out = Vec::new();
    out.extend_from_slice(MAGIC);
    out.extend_from_slice(&MAX_BLOCK.to_le_bytes());
    out.extend_from_slice(&0u32.to_le_bytes());
    let mut whole = Sha256::new();
    for block in data.chunks(MAX_BLOCK as usize) {
        let (selected, payload) = if let Some(id) = route {
            (id, encode_route(id, block, level, "hybrid")?)
        } else {
            let candidates = [
                (0, block.to_vec()),
                (1, rle(block)),
                (2, encode_route(2, block, level, "hybrid")?),
                (10, encode_route(10, block, level, "hybrid")?),
            ];
            candidates.into_iter().min_by_key(|(_, p)| p.len()).unwrap()
        };
        let digest: [u8; 32] = Sha256::digest(block).into();
        put_frame(
            &mut out,
            selected,
            block.len() as u32,
            payload.len() as u32,
            &digest,
        )
        .map_err(ioerr)?;
        out.extend_from_slice(&payload);
        whole.update(block);
    }
    let digest: [u8; 32] = whole.finalize().into();
    put_frame(&mut out, END, 0, 0, &digest).map_err(ioerr)?;
    Ok(out)
}

fn encode_portfolio<R: Read, W: Write>(
    src: R,
    mut dst: W,
    profile: &str,
    memory: usize,
) -> Result<(), String> {
    if !matches!(profile, "fast" | "current" | "size") {
        return Err("--portfolio accepts fast, current or size".into());
    }
    let required = if profile == "size" {
        384 * 1024 * 1024
    } else {
        128 * 1024 * 1024
    };
    if memory < required {
        return Err(format!(
            "{profile} portfolio requires --memory of at least {} MiB",
            required / (1024 * 1024)
        ));
    }
    let mut data = Vec::with_capacity(external::MAX_INPUT);
    src.take((external::MAX_INPUT + 1) as u64)
        .read_to_end(&mut data)
        .map_err(ioerr)?;
    if data.len() > external::MAX_INPUT {
        return Err("native portfolio input exceeds 16 MiB".into());
    }
    let level = match profile {
        "fast" => 1,
        "current" => 5,
        _ => 9,
    };
    let mut winner = cixg_candidate(&data, None, level)?;
    let mut winner_name = "cix-adaptive".to_string();
    let backends: &[&str] = if profile == "fast" {
        &["gzip", "zstd", "brotli"]
    } else {
        &["gzip", "bzip2", "xz", "zstd"]
    };
    for backend in backends {
        check_interrupted()?;
        let candidate = external::encode(backend, profile, &data)?;
        if candidate.len() < winner.len() {
            winner = candidate;
            winner_name = format!("{backend}:direct");
        }
    }
    if profile == "size" {
        for route in 0u8..=10 {
            check_interrupted()?;
            let candidate = cixg_candidate(&data, Some(route), level)?;
            if candidate.len() < winner.len() {
                winner = candidate;
                winner_name = format!("cix-route:{route}");
            }
        }
    }
    dst.write_all(&winner).map_err(ioerr)?;
    dst.flush().map_err(ioerr)?;
    eprintln!(
        "cix: portfolio profile={profile}, selected={winner_name}, archive_bytes={}",
        winner.len()
    );
    Ok(())
}

fn encode_external<R: Read, W: Write>(
    src: R,
    mut dst: W,
    backend: &str,
    profile: &str,
    memory: usize,
) -> Result<(), String> {
    let required = external::MAX_INPUT
        .saturating_mul(2)
        .saturating_add(external::MAX_PAYLOAD)
        .saturating_add(47);
    if memory < required {
        return Err(format!(
            "CIXB1 external encoding requires about {required} bytes of --memory"
        ));
    }
    let mut data = Vec::with_capacity(external::MAX_INPUT);
    src.take((external::MAX_INPUT + 1) as u64)
        .read_to_end(&mut data)
        .map_err(ioerr)?;
    if data.len() > external::MAX_INPUT {
        return Err("CIXB1 external input exceeds 16 MiB".into());
    }
    let archive = external::encode(backend, profile, &data)?;
    dst.write_all(&archive).map_err(ioerr)?;
    dst.flush().map_err(ioerr)
}
fn read_stream_varint<R: Read>(src: &mut R, fd: i32) -> Result<usize, String> {
    let mut value = 0usize;
    for shift in (0..usize::BITS as usize).step_by(7) {
        let mut b = [0u8; 1];
        read_exact_poll(src, &mut b, fd)?;
        let low = (b[0] & 0x7f) as usize;
        if shift + 7 > usize::BITS as usize && low > (usize::MAX >> shift) {
            return Err("CIXM6 varint overflow".into());
        }
        let part = low
            .checked_shl(shift as u32)
            .ok_or("CIXM6 varint overflow")?;
        value = value.checked_add(part).ok_or("CIXM6 varint overflow")?;
        if b[0] & 0x80 == 0 {
            return Ok(value);
        }
    }
    Err("oversized CIXM6 varint".into())
}

fn m6_read_bits(data: &[u8], bitpos: &mut usize, count: usize) -> Result<usize, String> {
    if count >= usize::BITS as usize || bitpos.saturating_add(count) > data.len() * 8 {
        return Err("truncated CIXM6 bitstream".into());
    }
    let mut value = 0usize;
    for _ in 0..count {
        value = (value << 1) | (((data[*bitpos / 8] >> (7 - (*bitpos % 8))) & 1) as usize);
        *bitpos += 1;
    }
    Ok(value)
}
fn m6_decode_bytes(blob: &[u8], count: usize, model_limit: usize) -> Result<Vec<u8>, String> {
    if blob.is_empty() {
        return Err("empty CIXM6 byte substream".into());
    }
    let mut pos = 1;
    let mut out = Vec::with_capacity(count);
    match blob[0] {
        0 => {
            let values = rank::decode_type_class(blob, &mut pos, count)?;
            if pos != blob.len() {
                return Err("trailing CIXM6 static bytes".into());
            }
            Ok(values)
        }
        2 => adaptive::decode_general(&blob[1..], count, &[], model_limit),
        3 => {
            if blob.len() < 2 || !matches!(blob[1], 1 | 2) {
                return Err("invalid CIXM6 byte context order".into());
            }
            adaptive::decode_general(&blob[2..], count, &[], model_limit)
        }
        1 => {
            let chunk = unvar(blob, &mut pos)?;
            if chunk == 0 {
                return Err("invalid CIXM6 byte chunk size".into());
            }
            while out.len() < count {
                let n = chunk.min(count - out.len());
                out.extend(rank::decode_type_class(blob, &mut pos, n)?);
            }
            if pos != blob.len() {
                return Err("trailing CIXM6 chunk bytes".into());
            }
            Ok(out)
        }
        mode => Err(format!("unsupported CIXM6 byte substream mode {mode}")),
    }
}
fn m6_decode_uints(blob: &[u8], count: usize, model_limit: usize) -> Result<Vec<usize>, String> {
    if count == 0 {
        return Ok(Vec::new());
    }
    let mode = *blob.first().ok_or("empty CIXM6 integer stream")?;
    let mut pos = 1;
    match mode {
        0 => {
            let mut out = Vec::with_capacity(count);
            for _ in 0..count {
                out.push(unvar(blob, &mut pos)?);
            }
            if pos != blob.len() {
                return Err("trailing CIXM6 varints".into());
            }
            Ok(out)
        }
        1 => {
            let k = *blob.get(pos).ok_or("missing CIXM6 Rice parameter")? as usize;
            pos += 1;
            let bits = &blob[pos..];
            let mut bp = 0;
            let mut out = Vec::with_capacity(count);
            for _ in 0..count {
                let mut q = 0usize;
                while m6_read_bits(bits, &mut bp, 1)? != 0 {
                    q = q.checked_add(1).ok_or("Rice quotient overflow")?;
                }
                let low = m6_read_bits(bits, &mut bp, k)?;
                out.push(q.checked_shl(k as u32).ok_or("Rice value overflow")? | low);
            }
            Ok(out)
        }
        2 | 3 => {
            let class_len = unvar(blob, &mut pos)?;
            let end = pos.checked_add(class_len).ok_or("class length overflow")?;
            if end > blob.len() {
                return Err("truncated CIXM6 integer classes".into());
            }
            let classes = if mode == 2 {
                let mut cp = 0;
                let v = rank::decode_type_class(&blob[pos..end], &mut cp, count)?;
                if cp != class_len {
                    return Err("trailing CIXM6 integer classes".into());
                }
                v
            } else {
                m6_decode_bytes(&blob[pos..end], count, model_limit)?
            };
            let bits = &blob[end..];
            let mut bp = 0;
            let mut out = Vec::with_capacity(count);
            for class in classes {
                let width = class as usize;
                if width >= usize::BITS as usize {
                    return Err("CIXM6 integer class too wide".into());
                }
                let low = m6_read_bits(bits, &mut bp, width)?;
                out.push(
                    (1usize << width)
                        .checked_add(low)
                        .and_then(|v| v.checked_sub(1))
                        .ok_or("CIXM6 integer overflow")?,
                );
            }
            Ok(out)
        }
        other => Err(format!("unsupported CIXM6 integer stream mode {other}")),
    }
}
fn m6_decode_runs(blob: &[u8], source_len: usize, model_limit: usize) -> Result<Vec<u8>, String> {
    if blob.first() != Some(&1) {
        return Err("unsupported CIXM6 run block version".into());
    }
    let mut pos = 1;
    let run_count = unvar(blob, &mut pos)?;
    if run_count == 0 || run_count > source_len {
        return Err("invalid CIXM6 run count".into());
    }
    let symbol_len = unvar(blob, &mut pos)?;
    let end = pos
        .checked_add(symbol_len)
        .ok_or("run symbol length overflow")?;
    if end > blob.len() {
        return Err("truncated CIXM6 run symbols".into());
    }
    let mut symbol_pos = 0;
    let symbols = rank::decode_type_class(&blob[pos..end], &mut symbol_pos, run_count)?;
    if symbol_pos != symbol_len {
        return Err("unused CIXM6 run-symbol bytes".into());
    }
    let lengths = m6_decode_uints(&blob[end..], run_count, model_limit)?;
    let mut out = Vec::with_capacity(source_len);
    for (symbol, minus_one) in symbols.into_iter().zip(lengths) {
        let n = minus_one.checked_add(1).ok_or("run length overflow")?;
        if out
            .len()
            .checked_add(n)
            .filter(|&v| v <= source_len)
            .is_none()
        {
            return Err("CIXM6 runs exceed source length".into());
        }
        out.resize(out.len() + n, symbol);
    }
    if out.len() != source_len {
        return Err("CIXM6 run source length mismatch".into());
    }
    Ok(out)
}

fn decode_m6<R: Read, W: Write>(
    mut src: R,
    mut dst: W,
    _magic: &[u8; 5],
    fd: i32,
    memory: usize,
    verify_only: bool,
) -> Result<(), String> {
    let history_limit = read_stream_varint(&mut src, fd)?;
    if history_limit == 0 || history_limit > 16 * 1024 * 1024 {
        return Err("invalid CIXM6 history window".into());
    }
    let mut total = 0usize;
    let mut crc = crc32fast::Hasher::new();
    if history_limit > memory {
        return Err("CIXM6 history exceeds --memory".into());
    }
    let mut history: Vec<u8> = Vec::with_capacity(history_limit);
    let mut recent: Vec<Vec<u8>> = Vec::new();
    let mut recent_bytes = 0usize;
    let reference_budget = memory.saturating_div(8).min(16 * 1024 * 1024).max(1);
    loop {
        let mut mode = [0u8; 1];
        read_exact_poll(&mut src, &mut mode, fd)?;
        if mode[0] == 255 {
            let expected = read_stream_varint(&mut src, fd)?;
            let mut checksum = [0u8; 4];
            read_exact_poll(&mut src, &mut checksum, fd)?;
            if expected != total || u32::from_le_bytes(checksum) != crc.clone().finalize() {
                return Err("CIXM6 length or CRC32 checksum mismatch".into());
            }
            let mut tail = Vec::new();
            src.take((1024 * 1024 + 10) as u64)
                .read_to_end(&mut tail)
                .map_err(ioerr)?;
            if tail.len() > 1024 * 1024 + 9 {
                return Err("CIXF1 filename footer exceeds limit".into());
            }
            if !tail.is_empty() {
                if tail.len() < 9 || &tail[tail.len() - 5..] != b"CIXF1" {
                    return Err("trailing bytes after CIXM6 stream".into());
                }
                let name_len =
                    u32::from_le_bytes(tail[tail.len() - 9..tail.len() - 5].try_into().unwrap())
                        as usize;
                if name_len != tail.len() - 9 || std::str::from_utf8(&tail[..name_len]).is_err() {
                    return Err("invalid CIXF1 filename footer".into());
                }
            }
            break;
        }
        let source_len = read_stream_varint(&mut src, fd)?;
        let payload_len = read_stream_varint(&mut src, fd)?;
        let model_budget = match mode[0] {
            10 => source_len.saturating_mul(64),
            16 => source_len.saturating_mul(128),
            19 => source_len.saturating_mul(1024),
            _ => 0,
        };
        if source_len == 0
            || source_len > 1024 * 1024
            || payload_len > 8 * source_len + 4096
            || source_len
                .saturating_add(payload_len)
                .saturating_add(history_limit)
                .saturating_add(reference_budget)
                .saturating_add(model_budget)
                > memory
        {
            return Err("CIXM6 block exceeds memory or format limit".into());
        }
        let mut payload = vec![0u8; payload_len];
        read_exact_poll(&mut src, &mut payload, fd)?;
        let block = match mode[0] {
            0 => {
                if payload.len() != source_len {
                    return Err("CIXM6 raw block length mismatch".into());
                }
                payload
            }
            1 => {
                let mut pos = 0;
                let out = rank::decode_type_class(&payload, &mut pos, source_len)?;
                if pos != payload.len() {
                    return Err("unused CIXM6 multinomial bytes".into());
                }
                out
            }
            10 => adaptive::decode_general(&payload, source_len, &history, memory / 4096)?,
            11 => rank::decode_sparse_blob(&payload, source_len)?,
            12 => m6_decode_runs(&payload, source_len, memory / 4096)?,
            16 => ppm::decode_with_history(&payload, source_len, &history)?,
            19 => fixedmix::decode_with_history(&payload, source_len, &history)?,
            9 => {
                let mut pos = 0;
                let distance = unvar(&payload, &mut pos)?;
                if pos != payload.len() || distance == 0 || distance > recent.len() {
                    return Err("invalid CIXM6 block reference".into());
                }
                let out = recent[recent.len() - distance].clone();
                if out.len() != source_len {
                    return Err("CIXM6 reference length mismatch".into());
                }
                out
            }
            other => return Err(format!("unsupported CIXM6 block mode {other}")),
        };
        if block.len() != source_len {
            return Err("CIXM6 decoded block length mismatch".into());
        }
        crc.update(&block);
        history.extend_from_slice(&block);
        if history.len() > history_limit {
            history.drain(..history.len() - history_limit);
        }
        total = total
            .checked_add(block.len())
            .ok_or("CIXM6 output length overflow")?;
        if !verify_only {
            dst.write_all(&block).map_err(ioerr)?;
            dst.flush().map_err(ioerr)?;
        }
        recent_bytes = recent_bytes.saturating_add(block.len());
        recent.push(block);
        while recent.len() > 4096 || recent_bytes > reference_budget {
            recent_bytes = recent_bytes.saturating_sub(recent.remove(0).len());
        }
    }
    Ok(())
}

fn decode<R: Read, W: Write>(
    mut src: R,
    mut dst: W,
    verify_only: bool,
    list: bool,
    input_fd: i32,
    memory: usize,
) -> Result<(), String> {
    let mut archive_magic = [0u8; 5];
    read_exact_poll(&mut src, &mut archive_magic, input_fd)?;
    if &archive_magic == b"CIXM6" || &archive_magic == b"CIXM5" {
        return decode_m6(src, dst, &archive_magic, input_fd, memory, verify_only);
    }
    if &archive_magic == b"CIXB1" {
        let mut fields = [0u8; 42];
        read_exact_poll(&mut src, &mut fields, input_fd)?;
        let payload_size = u32::from_le_bytes(fields[6..10].try_into().unwrap()) as usize;
        let expected = u32::from_le_bytes(fields[2..6].try_into().unwrap()) as usize;
        if payload_size > external::MAX_PAYLOAD
            || expected > external::MAX_INPUT
            || HEADER.saturating_add(expected).saturating_add(payload_size) > memory
        {
            return Err("CIXB1 archive exceeds --memory or format limit".into());
        }
        let mut archive = Vec::with_capacity(47 + payload_size);
        archive.extend_from_slice(&archive_magic);
        archive.extend_from_slice(&fields);
        archive.resize(47 + payload_size, 0);
        read_exact_poll(&mut src, &mut archive[47..], input_fd)?;
        let data = external::decode(&archive, memory)?;
        loop {
            let mut extra = [0u8; 1];
            match read_poll(&mut src, &mut extra, input_fd, None)? {
                Some(0) => break,
                Some(_) => return Err("trailing bytes after CIXB1 archive".into()),
                None => continue,
            }
        }
        if list {
            eprintln!(
                "CIXB1 stream: backend={}, profile={}, decoded {} bytes",
                archive[5],
                archive[6],
                data.len()
            );
        }
        if !verify_only {
            dst.write_all(&data).map_err(ioerr)?;
            dst.flush().map_err(ioerr)?;
        }
        return Ok(());
    }
    let mut h = [0; HEADER];
    h[..5].copy_from_slice(&archive_magic);
    read_exact_poll(&mut src, &mut h[5..], input_fd)?;
    if &h[..5] != MAGIC {
        return Err("unsupported archive (expected CIXG1)".into());
    }
    let block = u32::from_le_bytes(h[5..9].try_into().unwrap());
    let hist = u32::from_le_bytes(h[9..13].try_into().unwrap());
    if block == 0 || block > MAX_BLOCK || hist != 0 && hist != 65536 {
        return Err("invalid CIXG1 header".into());
    }
    let estimated_decode_working = block as usize * 8 + 65536;
    if estimated_decode_working > memory {
        return Err(format!("archive frame needs about {estimated_decode_working} bytes working memory; raise --memory"));
    }
    let mut whole = Sha256::new();
    let mut total_bytes = 0u64;
    loop {
        let mut r = [0; 1];
        read_exact_poll(&mut src, &mut r, input_fd)?;
        let n = read_u32(&mut src, input_fd)?;
        let s = read_u32(&mut src, input_fd)?;
        let mut sum = [0; 32];
        read_exact_poll(&mut src, &mut sum, input_fd)?;
        if r[0] == END {
            if n != 0 || s != 0 || sum != <[u8; 32]>::from(whole.clone().finalize()) {
                return Err("archive checksum/terminator mismatch".into());
            }
            let mut x = [0];
            loop {
                match read_poll(&mut src, &mut x, input_fd, None)? {
                    Some(0) => break,
                    Some(_) => return Err("trailing archive bytes".into()),
                    None => continue,
                }
            }
            if !verify_only {
                dst.flush().map_err(ioerr)?;
            }
            if list {
                eprintln!("CIXG1 stream: {} decoded bytes", total_bytes);
            }
            return Ok(());
        }
        if n == 0 || n > block || s as u64 > 8 * n as u64 + 4096 {
            return Err("invalid block descriptor".into());
        }
        if r[0] == 8 && memory < 64 * 1024 * 1024 {
            return Err("decoding this PPM block requires --memory of at least 64 MiB".into());
        }
        let mut b = vec![0; s as usize];
        read_exact_poll(&mut src, &mut b, input_fd)?;
        let data = match r[0] {
            0 => {
                if b.len() != n as usize {
                    return Err("raw size mismatch".into());
                }
                b
            }
            1 => unrle(&b, n as usize)?,
            2 => stream_decode(&b, n as usize)?,
            3 => lz_decode(&b, n as usize)?,
            4 => {
                let residual = stream_decode(&b, n as usize)?;
                predictor_residual(&residual, true)
            }
            5 => {
                if b.len() < 4 {
                    return Err("truncated BWT primary index".into());
                }
                let primary = u32::from_le_bytes(b[..4].try_into().unwrap()) as usize;
                let parts = streams_decode(&b[4..], (n as usize).saturating_mul(4))?;
                let transformed = unmtf_runs(&parts, n as usize)?;
                bwt_inverse(primary, &transformed)?
            }
            6 => {
                if b.is_empty() {
                    return Err("truncated stride descriptor".into());
                }
                let transformed = join_streams(&b[1..], n as usize)?;
                let restored = invert_stride(&transformed, b[0])?;
                if restored.len() != n as usize {
                    return Err("stride output size mismatch".into());
                }
                restored
            }
            7 => phrase_decode(&b, n as usize)?,
            8 => ppm::decode(&b, n as usize)?,
            9 => {
                let need = (n as usize)
                    .saturating_mul(4096)
                    .saturating_add(8 * 1024 * 1024);
                if need > memory {
                    return Err("decoding this mixture block exceeds --memory budget".into());
                }
                fixedmix::decode(&b, n as usize)?
            }
            10 => stream_decode(&b, n as usize)?,
            _ => return Err(format!("unsupported CIXG1 route ID {}", r[0])),
        };
        if <[u8; 32]>::from(Sha256::digest(&data)) != sum {
            return Err("block checksum mismatch".into());
        }
        whole.update(&data);
        total_bytes = total_bytes
            .checked_add(data.len() as u64)
            .ok_or("decoded length overflow")?;
        if list {
            eprintln!(
                "CIXG1 block: route={}, source={} bytes, payload={} bytes",
                r[0], n, s
            )
        }
        if !verify_only {
            dst.write_all(&data).map_err(ioerr)?;
            dst.flush().map_err(ioerr)?;
        }
    }
}

type SquashRead = unsafe extern "C" fn(*mut usize, *mut u8, *mut std::ffi::c_void) -> i32;
type SquashWrite = unsafe extern "C" fn(*mut usize, *const u8, *mut std::ffi::c_void) -> i32;
struct SquashReader {
    callback: SquashRead,
    user: *mut std::ffi::c_void,
}
struct SquashWriter {
    callback: SquashWrite,
    user: *mut std::ffi::c_void,
}
impl Read for SquashReader {
    fn read(&mut self, buffer: &mut [u8]) -> io::Result<usize> {
        let mut size = buffer.len();
        let status = unsafe { (self.callback)(&mut size, buffer.as_mut_ptr(), self.user) };
        if status == 3 {
            return Ok(0);
        }
        if status != 1 || size > buffer.len() {
            return Err(io::Error::new(
                io::ErrorKind::InvalidData,
                "Squash input callback failed",
            ));
        }
        Ok(size)
    }
}
impl Write for SquashWriter {
    fn write(&mut self, buffer: &[u8]) -> io::Result<usize> {
        let mut size = buffer.len();
        let status = unsafe { (self.callback)(&mut size, buffer.as_ptr(), self.user) };
        if status != 1 || size > buffer.len() {
            return Err(io::Error::new(
                io::ErrorKind::BrokenPipe,
                "Squash output callback failed",
            ));
        }
        if size == 0 && !buffer.is_empty() {
            return Err(io::Error::new(
                io::ErrorKind::WriteZero,
                "Squash output callback wrote no bytes",
            ));
        }
        Ok(size)
    }
    fn flush(&mut self) -> io::Result<()> {
        Ok(())
    }
}
#[no_mangle]
pub unsafe extern "C" fn cix_squash_splice(
    direction: i32,
    level: i32,
    read_cb: Option<SquashRead>,
    write_cb: Option<SquashWrite>,
    user: *mut std::ffi::c_void,
) -> i32 {
    let result =
        std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| -> Result<(), String> {
            let read = read_cb.ok_or("missing Squash read callback")?;
            let write = write_cb.ok_or("missing Squash write callback")?;
            let src = SquashReader {
                callback: read,
                user,
            };
            let dst = SquashWriter {
                callback: write,
                user,
            };
            match direction {
                1 if (1..=9).contains(&level) => {
                    encode(src, dst, 32768, level as u8, None, "hybrid", -1, None)
                }
                1 => Err("invalid Squash CIX compression level".into()),
                2 => decode(src, dst, false, false, -1, 512 * 1024 * 1024),
                _ => Err("invalid Squash stream direction".into()),
            }
        }));
    match result {
        Ok(Ok(())) => 1,
        _ => -1,
    }
}

fn ioerr(e: io::Error) -> String {
    e.to_string()
}
fn cixf1_original_name(input: &str) -> Option<String> {
    if input == "-" {
        return None;
    }
    let mut file = File::open(input).ok()?;
    let end = file.seek(SeekFrom::End(0)).ok()?;
    if end < 9 || file.seek(SeekFrom::End(-9)).ok().is_none() {
        return None;
    }
    let mut footer = [0u8; 9];
    file.read_exact(&mut footer).ok()?;
    if &footer[4..] != b"CIXF1" {
        return None;
    }
    let len = u32::from_le_bytes(footer[..4].try_into().ok()?) as u64;
    if len > 1024 * 1024 || len + 9 > end {
        return None;
    }
    file.seek(SeekFrom::Start(end - len - 9)).ok()?;
    let mut name = vec![0u8; len as usize];
    file.read_exact(&mut name).ok()?;
    let name = std::str::from_utf8(&name).ok()?;
    let base = Path::new(name).file_name()?.to_str()?;
    if base.is_empty() || base == "." || base == ".." {
        return None;
    }
    let parent = Path::new(input).parent().unwrap_or_else(|| Path::new("."));
    Some(parent.join(base).to_string_lossy().into_owned())
}

fn default_output(input: &str, dec: bool) -> String {
    if input == "-" {
        return "-".into();
    }
    let p = Path::new(input);
    if dec {
        if p.extension().map(|x| x == "cix").unwrap_or(false) {
            let mut q = p.to_path_buf();
            q.set_extension("");
            q.to_string_lossy().into_owned()
        } else {
            format!("{input}.out")
        }
    } else {
        format!("{input}.cix")
    }
}
fn atomic_file(
    path: &str,
    force: bool,
    run: impl FnOnce(&mut File) -> Result<(), String>,
) -> Result<(), String> {
    let p = Path::new(path);
    if fs::symlink_metadata(p).is_ok() && !force {
        return Err(format!("refusing to overwrite {path} (use -f)"));
    }
    let parent = p.parent().unwrap_or(Path::new("."));
    let name = p.file_name().unwrap_or_default().to_string_lossy();
    let stamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_nanos();
    let tmp = parent.join(format!(".{name}.cix-tmp-{}-{stamp}", process::id()));
    let mut f = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&tmp)
        .map_err(ioerr)?;
    let result = run(&mut f);
    if result.is_ok() {
        if let Err(e) = f.sync_all() {
            drop(f);
            let _ = fs::remove_file(&tmp);
            return Err(ioerr(e));
        }
    }
    drop(f);
    if let Err(e) = result {
        let _ = fs::remove_file(&tmp);
        return Err(e);
    }
    if force {
        fs::rename(&tmp, p).map_err(|e| {
            let _ = fs::remove_file(&tmp);
            ioerr(e)
        })?;
    } else {
        fs::hard_link(&tmp, p).map_err(|e| {
            let _ = fs::remove_file(&tmp);
            if e.kind() == io::ErrorKind::AlreadyExists {
                format!("refusing to overwrite {path} (use -f)")
            } else {
                ioerr(e)
            }
        })?;
        fs::remove_file(&tmp).map_err(ioerr)?;
    }
    if let Some(dir) = p.parent() {
        if let Ok(d) = File::open(dir) {
            let _ = d.sync_all();
        }
    }
    Ok(())
}
fn block_min(o: &Opt) -> usize {
    o.block
        .unwrap_or(if o.level == 9 { MAX_BLOCK } else { 32768 })
        .min(MAX_BLOCK) as usize
}

fn run() -> Result<(), String> {
    let o = parse()?;
    if o.threads != 1 {
        return Err(
            "this portable build supports --threads 1; parallel coding is not implemented".into(),
        );
    }
    if o.memory < 128 * 1024 {
        return Err("--memory must be at least 128 KiB for a CIXG1 frame".into());
    }
    if o.profile_set && o.external_backend.is_none() {
        return Err("--profile requires --external".into());
    }
    if !matches!(o.format.as_str(), "cixg1" | "cixm6" | "cixf1") {
        return Err("--format accepts cixg1, cixm6 or cixf1".into());
    }
    if matches!(o.format.as_str(), "cixm6" | "cixf1")
        && (o.decode
            || o.test
            || o.list
            || o.external_backend.is_some()
            || o.portfolio.is_some()
            || o.route.is_some())
    {
        return Err(
            "--format cixm6 conflicts with decode, portfolio, external backend and route selection"
                .into(),
        );
    }
    if o.format == "cixf1" && o.input == "-" {
        return Err("--format cixf1 requires a named input to store its basename".into());
    }
    if matches!(o.format.as_str(), "cixm6" | "cixf1") && o.flush_interval.is_some() {
        return Err("--flush-interval is not available for the CIXM6 encoder".into());
    }
    if matches!(o.format.as_str(), "cixm6" | "cixf1") && o.memory < (1 << 20) + block_min(&o) {
        return Err(
            "CIXM6 encoder needs --memory for its 1 MiB history declaration and block".into(),
        );
    }
    if let Some(p) = o.portfolio.as_deref() {
        if o.decode
            || o.test
            || o.list
            || o.external_backend.is_some()
            || o.route.is_some()
            || o.profile_set
        {
            return Err(
                "--portfolio conflicts with decode, --external, --route and --profile".into(),
            );
        }
        if o.stream || o.flush_interval.is_some() {
            return Err(
                "bounded portfolio selection conflicts with --stream/--flush-interval".into(),
            );
        }
        if !matches!(p, "fast" | "current" | "size") {
            return Err("--portfolio accepts fast, current or size".into());
        }
    }
    if o.external_backend.is_some() {
        if o.decode || o.test || o.list {
            return Err("--external is an encoding option".into());
        }
        if o.stream || o.flush_interval.is_some() {
            return Err(
                "bounded CIXB1 external encoding conflicts with --stream/--flush-interval".into(),
            );
        }
        if o.input == "-" {
            return Err("CIXB1 external profiles require a named, bounded input file".into());
        }
        if o.route.is_some() {
            return Err("--external conflicts with --route".into());
        }
        if !matches!(o.profile.as_str(), "fast" | "current" | "size") {
            return Err("--profile accepts fast, current or size".into());
        }
    }
    if o.route.as_deref() == Some("lz") && o.memory < 16 * 1024 * 1024 {
        return Err(
            "--route lz requires --memory of at least 16 MiB for its bounded match index".into(),
        );
    }
    if o.route.as_deref() == Some("ppm") && o.memory < 64 * 1024 * 1024 {
        return Err(
            "--route ppm requires --memory of at least 64 MiB for bounded context tables".into(),
        );
    }
    if o.route.as_deref() == Some("mixture") && o.memory < 16 * 1024 * 1024 {
        return Err("--route mixture requires at least 16 MiB of --memory".into());
    }
    if o.history != 0 {
        if o.independent_blocks {
            return Err("--history conflicts with --independent-blocks".into());
        }
        return Err("persistent history is not supported by the current native routes".into());
    }
    if o.decode && o.flush_interval.is_some() {
        return Err("--flush-interval applies to encoding only".into());
    }
    if o.flush_interval.is_some() && !cfg!(unix) {
        return Err("--flush-interval on non-seekable input requires Unix poll support".into());
    }
    if let Some(r) = &o.route {
        if ![
            "auto",
            "raw",
            "runs",
            "composition",
            "lz",
            "predictor",
            "bwt",
            "stride",
            "phrases",
            "ppm",
            "mixture",
            "deflate",
        ]
        .contains(&r.as_str())
        {
            return Err(format!("unsupported native route: {r}"));
        }
    }
    let requested_block = o
        .block
        .unwrap_or(if o.level == 9 { MAX_BLOCK } else { 32768 });
    if requested_block == 0 {
        return Err("--block-size must be positive".into());
    }
    let block = requested_block.min(MAX_BLOCK);
    if o.route.as_deref() == Some("mixture") {
        let need = (block as usize)
            .saturating_mul(4096)
            .saturating_add(8 * 1024 * 1024);
        if need > o.memory {
            return Err(format!(
                "mixture route needs about {need} bytes; reduce --block-size or raise --memory"
            ));
        }
    }
    if requested_block > MAX_BLOCK {
        eprintln!("cix: CIXG1 limits frames to 65536 bytes; effective block size is 65536 bytes");
    }
    let estimated_working = block as usize * 8 + 65536;
    if estimated_working > o.memory {
        return Err(format!("block needs about {estimated_working} bytes working memory; reduce --block-size or raise --memory"));
    }
    let forced = o.route.as_deref().filter(|r| *r != "auto");
    let out = o.output.clone().unwrap_or_else(|| {
        if o.decode {
            cixf1_original_name(&o.input).unwrap_or_else(|| default_output(&o.input, true))
        } else {
            default_output(&o.input, false)
        }
    });
    if o.test || o.list {
        let f = open_input(&o.input)?;
        let fd = input_fd(&f);
        decode(f, io::sink(), true, o.list, fd, o.memory)?;
        eprintln!("archive OK");
        return Ok(());
    }
    if o.stdout || out == "-" {
        let src = open_input(&o.input)?;
        let fd = input_fd(&src);
        let dst = io::stdout();
        let mut lock = dst.lock();
        if o.decode {
            decode(src, &mut lock, false, false, fd, o.memory)
        } else if o.format == "cixm6" || o.format == "cixf1" {
            let name = if o.format == "cixf1" {
                Path::new(&o.input)
                    .file_name()
                    .and_then(|s| s.to_str())
                    .ok_or("input basename is not valid UTF-8")?
            } else {
                ""
            };
            encode_m6(
                src,
                &mut lock,
                block as usize,
                (o.format == "cixf1").then_some(name),
            )
        } else if let Some(profile) = o.portfolio.as_deref() {
            encode_portfolio(src, &mut lock, profile, o.memory)
        } else if let Some(backend) = o.external_backend.as_deref() {
            encode_external(src, &mut lock, backend, &o.profile, o.memory)
        } else {
            encode(
                src,
                &mut lock,
                block,
                o.level,
                forced,
                &o.backend,
                fd,
                o.flush_interval,
            )
        }?
    } else {
        if o.input == out {
            return Err("input and output paths must differ".into());
        }
        atomic_file(&out, o.force, |dst| {
            let src = open_input(&o.input)?;
            let fd = input_fd(&src);
            if o.decode {
                decode(src, dst, false, false, fd, o.memory)
            } else if o.format == "cixm6" || o.format == "cixf1" {
                let name = if o.format == "cixf1" {
                    Path::new(&o.input)
                        .file_name()
                        .and_then(|s| s.to_str())
                        .ok_or("input basename is not valid UTF-8")?
                } else {
                    ""
                };
                encode_m6(
                    src,
                    dst,
                    block as usize,
                    (o.format == "cixf1").then_some(name),
                )
            } else if let Some(profile) = o.portfolio.as_deref() {
                encode_portfolio(src, dst, profile, o.memory)
            } else if let Some(backend) = o.external_backend.as_deref() {
                encode_external(src, dst, backend, &o.profile, o.memory)
            } else {
                encode(
                    src,
                    dst,
                    block,
                    o.level,
                    forced,
                    &o.backend,
                    fd,
                    o.flush_interval,
                )
            }
        })?;
        eprintln!("{}", out)
    }
    let _ = (o.keep, o.stream);
    Ok(())
}
fn main() {
    if let Err(e) = ctrlc::set_handler(|| INTERRUPTED.store(true, Ordering::Relaxed)) {
        eprintln!("cix: could not install interrupt handler: {e}");
        process::exit(2);
    }
    if let Err(e) = run() {
        eprintln!("cix: {e}");
        process::exit(2)
    }
}
