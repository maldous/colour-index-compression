//! Lease-only exhaustive 8-bit constraint theory search; outside Cargo/src.
use std::env;
const U: usize = 256;
const WORDS: usize = 4;
const COMMON: u32 = 7; // stored gamma(8)
#[derive(Clone)]
struct P {
    kind: u8,
    a: u8,
    b: u8,
    set: [u64; WORDS],
    bits: u32,
    name: String,
}
fn setbit(s: &mut [u64; WORDS], x: usize) {
    s[x / 64] |= 1 << (x % 64)
}
fn has(s: &[u64; WORDS], x: usize) -> bool {
    s[x / 64] >> (x % 64) & 1 != 0
}
fn cnt(s: &[u64; WORDS]) -> u32 {
    s.iter().map(|x| x.count_ones()).sum()
}
fn inter(a: &[u64; WORDS], b: &[u64; WORDS]) -> [u64; WORDS] {
    [a[0] & b[0], a[1] & b[1], a[2] & b[2], a[3] & b[3]]
}
fn gamma(n: u32) -> u32 {
    if n == 0 {
        0
    } else {
        2 * (31 - n.leading_zeros()) + 1
    }
}
fn rank_width(n: u32) -> u32 {
    if n <= 1 {
        0
    } else {
        32 - (n - 1).leading_zeros()
    }
}
fn rank(s: &[u64; WORDS], x: usize) -> u32 {
    (0..x).filter(|&y| has(s, y)).count() as u32
}
fn unrank(s: &[u64; WORDS], r: u32) -> Option<usize> {
    let mut q = r;
    for x in 0..U {
        if has(s, x) {
            if q == 0 {
                return Some(x);
            }
            q -= 1
        }
    }
    None
}
fn add(v: &mut Vec<P>, kind: u8, a: u8, b: u8, bits: u32, name: String, f: impl Fn(u8) -> bool) {
    let mut s = [0; WORDS];
    for x in 0..U {
        if f(x as u8) {
            setbit(&mut s, x)
        }
    }
    v.push(P {
        kind,
        a,
        b,
        set: s,
        bits,
        name,
    })
}
fn main() {
    let _ = env::args();
    let mut p = Vec::new();
    for pos in 0..8 {
        for val in 0..2 {
            add(
                &mut p,
                0,
                pos,
                val,
                6,
                format!("bit{pos}={val}"),
                move |x| ((x >> pos) & 1) == val,
            )
        }
    }
    for i in 0..8 {
        for j in i + 1..8 {
            for v in 0..2 {
                add(&mut p, 1, i, j, 9, format!("xor{i},{j}={v}"), move |x| {
                    (((x >> i) ^ (x >> j)) & 1) == v
                })
            }
        }
    }
    for k in 0..=8 {
        add(&mut p, 2, k, 0, 6, format!("popcount={k}"), move |x| {
            x.count_ones() == k as u32
        })
    }
    for t in 0..=255 {
        add(&mut p, 3, t, 0, 10, format!("x<={t}"), move |x| x <= t)
    }
    assert_eq!(p.len(), 337);
    let mut rows = Vec::new();
    let mut redundant = 0;
    let mut contradiction = 0;
    let mut independent = 0;
    let mut overlap = 0;
    let mut win = 0;
    let mut losewin = 0;
    let mut checks = 0u64;
    let mut positive = 0u64;
    for i in 0..p.len() {
        for j in i + 1..p.len() {
            let a = &p[i];
            let b = &p[j];
            let na = cnt(&a.set);
            let nb = cnt(&b.set);
            let s = inter(&a.set, &b.set);
            let ni = cnt(&s);
            if ni == 0 {
                contradiction += 1;
                continue;
            }
            if ni == na || ni == nb {
                redundant += 1
            } else if na * nb == 256 * ni {
                independent += 1
            } else {
                overlap += 1
            }
            for x in 0..U {
                if has(&s, x) {
                    let r = rank(&s, x);
                    assert_eq!(unrank(&s, r), Some(x));
                    checks += 1
                }
            }
            let raw = 16;
            let joint = 7 + 1 + gamma(2) + a.bits + b.bits + rank_width(ni);
            let ia = 7 + 1 + gamma(1) + a.bits + rank_width(na);
            let ib = 7 + 1 + gamma(1) + b.bits + rank_width(nb);
            let interaction = ((na as f64 * nb as f64) / (256.0 * ni as f64)).log2();
            if na * nb > 256 * ni {
                positive += 1;
            }
            rows.push((
                raw as i32 - joint as i32,
                format!("{} + {} interaction={interaction:.4}", a.name, b.name),
                na,
                nb,
                ni,
                interaction,
            ));
            if joint < raw {
                win += 1;
                if ia >= raw && ib >= raw {
                    losewin += 1
                }
            }
        }
    }
    rows.sort_by(|a, b| b.5.total_cmp(&a.5).then_with(|| b.0.cmp(&a.0)));
    println!("catalog=337 pairs=56496 contradictions={contradiction} redundant={redundant} independent={independent} overlap={overlap} joint_winning={win} individually_losing_joint_winning={losewin} positive_volume_interactions={positive} rank_unrank_checks={checks}");
    for r in rows.into_iter().take(10) {
        println!("gain={} {} NA={} NB={} NI={}", r.0, r.1, r.2, r.3, r.4)
    }
}
