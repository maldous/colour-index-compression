//! Exact V2000 coordinate skeleton and graph-residual primitives.
//!
//! This module does not choose a payload representation.  It only owns the
//! byte-preserving record operation shared by the historical SDF specialists.

const COORDINATE_STARTS: [usize; 3] = [0, 10, 20];

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ExtractedRecord {
    pub skeleton: Vec<u8>,
    pub residuals: Vec<[i64; 3]>,
    pub groups: Vec<u8>,
    pub parents: Vec<usize>,
}

pub fn fixed(value: i64) -> Result<[u8; 10], String> {
    let sign = if value < 0 { "-" } else { "" };
    let absolute = value.checked_abs().ok_or("coordinate overflow")?;
    let text = format!("{}{}.{:04}", sign, absolute / 10_000, absolute % 10_000);
    if text.len() > 10 {
        return Err("coordinate outside fixed field".into());
    }
    let mut out = [b' '; 10];
    out[10 - text.len()..].copy_from_slice(text.as_bytes());
    Ok(out)
}

fn lines_keepends(record: &[u8]) -> Vec<&[u8]> {
    let mut lines = Vec::new();
    let mut start = 0;
    let mut i = 0;
    while i < record.len() {
        let n = match record[i] {
            b'\n' => 1,
            b'\r' => {
                if record.get(i + 1) == Some(&b'\n') {
                    2
                } else {
                    1
                }
            }
            _ => {
                i += 1;
                continue;
            }
        };
        lines.push(&record[start..i + n]);
        start = i + n;
        i += n;
    }
    if start < record.len() {
        lines.push(&record[start..]);
    }
    lines
}
fn trim_ascii(mut field: &[u8]) -> &[u8] {
    fn space(b: &u8) -> bool {
        matches!(*b, b' ' | b'\t' | b'\n' | b'\r' | 0x0b | 0x0c)
    }
    while field.first().is_some_and(space) {
        field = &field[1..];
    }
    while field.last().is_some_and(space) {
        field = &field[..field.len() - 1];
    }
    field
}
fn parse_field(field: &[u8]) -> Result<i64, String> {
    let text = std::str::from_utf8(trim_ascii(field)).map_err(|_| "non-ASCII coordinate")?;
    let digits = text.replace('.', "");
    let value = digits.parse::<i64>().map_err(|_| "invalid coordinate")?;
    if fixed(value)? != field {
        return Err("noncanonical coordinate retained literally".into());
    }
    Ok(value)
}
pub fn atom_group(suffix: &[u8]) -> u8 {
    match std::str::from_utf8(trim_ascii(suffix.get(..4).unwrap_or(suffix))).unwrap_or("") {
        "C" => 0,
        "H" => 1,
        "N" => 2,
        "O" => 3,
        _ => 4,
    }
}
pub fn counts(lines: &[&[u8]]) -> Result<(usize, usize), String> {
    if lines.len() < 4 || !trim_ascii(lines[3]).ends_with(b"V2000") {
        return Err("unsupported record".into());
    }
    let atoms: usize = std::str::from_utf8(lines[3].get(..3).ok_or("short counts")?)
        .map_err(|_| "invalid counts")?
        .trim()
        .parse()
        .map_err(|_| "invalid counts")?;
    let bonds: usize = std::str::from_utf8(lines[3].get(3..6).ok_or("short counts")?)
        .map_err(|_| "invalid counts")?
        .trim()
        .parse()
        .map_err(|_| "invalid counts")?;
    if atoms == 0
        || atoms > 999
        || bonds > 999
        || lines.len() < 5 + atoms + bonds
        || !lines[4 + atoms + bonds].starts_with(b"M  ")
    {
        return Err("incomplete record".into());
    }
    Ok((atoms, bonds))
}
pub fn bond_parent(line: &[u8], atoms: usize) -> Result<(usize, usize), String> {
    let a = std::str::from_utf8(line.get(..3).ok_or("short bond")?)
        .map_err(|_| "invalid bond")?
        .trim()
        .parse::<usize>()
        .map_err(|_| "invalid bond")?
        .checked_sub(1)
        .ok_or("invalid bond")?;
    let b = std::str::from_utf8(line.get(3..6).ok_or("short bond")?)
        .map_err(|_| "invalid bond")?
        .trim()
        .parse::<usize>()
        .map_err(|_| "invalid bond")?
        .checked_sub(1)
        .ok_or("invalid bond")?;
    if a >= atoms || b >= atoms || a == b {
        return Err("unsupported bond indices".into());
    }
    Ok(if a < b { (a, b) } else { (b, a) })
}
pub fn layout(lines: &[&[u8]]) -> Result<(usize, Vec<usize>), String> {
    let (a, b) = counts(lines)?;
    let mut parents = (0..a).map(|i| i.saturating_sub(1)).collect::<Vec<_>>();
    for line in &lines[4 + a..4 + a + b] {
        let (x, y) = bond_parent(line, a)?;
        parents[y] = x;
    }
    Ok((a, parents))
}
pub fn extract(record: &[u8], mode: u8) -> Result<ExtractedRecord, String> {
    if mode > 2 {
        return Err("unknown geometry mode".into());
    }
    let lines = lines_keepends(record);
    let (atoms, parents) = layout(&lines)?;
    let mut coords = Vec::new();
    let mut groups = Vec::new();
    for line in &lines[4..4 + atoms] {
        if line.len() < 34 {
            return Err("short atom".into());
        }
        let mut v = [0; 3];
        for (i, s) in COORDINATE_STARTS.iter().enumerate() {
            v[i] = parse_field(&line[*s..*s + 10])?;
        }
        coords.push(v);
        groups.push(atom_group(&line[30..]));
    }
    let mut residuals = Vec::new();
    for (i, v) in coords.iter().enumerate() {
        let p = if mode == 0 {
            None
        } else if mode == 1 {
            i.checked_sub(1)
        } else {
            let p = parents[i];
            if p < i {
                Some(p)
            } else {
                None
            }
        };
        let base = p.map(|p| coords[p]).unwrap_or([0; 3]);
        residuals.push([v[0] - base[0], v[1] - base[1], v[2] - base[2]]);
    }
    let mut out = Vec::new();
    for (i, line) in lines.iter().enumerate() {
        if (4..4 + atoms).contains(&i) {
            out.extend_from_slice(&line[30..]);
        } else {
            out.extend_from_slice(line)
        }
    }
    Ok(ExtractedRecord {
        skeleton: out,
        residuals,
        groups,
        parents,
    })
}
pub fn restore(skeleton: &[u8], mode: u8, residuals: &[[i64; 3]]) -> Result<Vec<u8>, String> {
    if mode > 2 {
        return Err("unknown geometry mode".into());
    }
    let lines = lines_keepends(skeleton);
    let (atoms, parents) = layout(&lines)?;
    if atoms != residuals.len() {
        return Err("coordinate count mismatch".into());
    }
    let mut rebuilt = lines.iter().map(|x| x.to_vec()).collect::<Vec<_>>();
    let mut coords: Vec<[i64; 3]> = Vec::with_capacity(atoms);
    for i in 0..atoms {
        let p = if mode == 0 {
            None
        } else if mode == 1 {
            i.checked_sub(1)
        } else {
            let p = parents[i];
            if p < i {
                Some(p)
            } else {
                None
            }
        };
        let base = p.map(|p| coords[p]).unwrap_or([0; 3]);
        let v = [
            base[0]
                .checked_add(residuals[i][0])
                .ok_or("coordinate overflow")?,
            base[1]
                .checked_add(residuals[i][1])
                .ok_or("coordinate overflow")?,
            base[2]
                .checked_add(residuals[i][2])
                .ok_or("coordinate overflow")?,
        ];
        coords.push(v);
        let mut prefix = Vec::with_capacity(30);
        for x in v {
            prefix.extend_from_slice(&fixed(x)?)
        }
        prefix.extend_from_slice(&rebuilt[4 + i]);
        rebuilt[4 + i] = prefix;
    }
    Ok(rebuilt.concat())
}

#[cfg(test)]
mod tests {
    use super::*;

    // Generated fields: the edge 1 -> 3 differs from sequential prediction.
    // No evaluation-corpus bytes or assumed record identity are used here.
    fn fixture(endings: &[&[u8]]) -> Vec<u8> {
        let lines: [&[u8]; 11] = [
            b"coordinate fixture",
            b"native test",
            b"fixed-point coordinates",
            b"  3  2  0  0  0  0            999 V2000 \t",
            b"    1.0000   -2.0000    0.0000 C   0  0  0",
            b"    3.0000    2.0000    0.0000 H   0  0  0",
            b"    4.0000   -1.0000    0.5000 O   0  0  0",
            b"  1  2  1  0",
            b"  1  3  1  0",
            b"M  END",
            b"> extra\x0bdata",
        ];
        let mut out = Vec::new();
        for (i, line) in lines.iter().enumerate() {
            out.extend_from_slice(line);
            if i + 1 != lines.len() {
                out.extend_from_slice(endings[i % endings.len()]);
            }
        }
        out
    }

    #[test]
    fn known_graph_and_sequential_residuals() {
        let input = fixture(&[b"\n"]);
        let absolute = extract(&input, 0).unwrap();
        assert_eq!(
            absolute.residuals,
            [[10000, -20000, 0], [30000, 20000, 0], [40000, -10000, 5000]]
        );
        assert_eq!(absolute.parents, [0, 0, 0]); // First vertex uses zero base, not itself.
        assert_eq!(absolute.groups, [0, 1, 3]);
        assert_eq!(
            extract(&input, 1).unwrap().residuals,
            [[10000, -20000, 0], [20000, 40000, 0], [10000, -30000, 5000]]
        );
        assert_eq!(
            extract(&input, 2).unwrap().residuals,
            [[10000, -20000, 0], [20000, 40000, 0], [30000, 10000, 5000]]
        );
    }

    #[test]
    fn all_modes_preserve_line_endings_and_literal_bytes() {
        let styles: &[&[&[u8]]] = &[&[b"\n"], &[b"\r"], &[b"\r\n"], &[b"\r\n", b"\r", b"\n"]];
        for endings in styles {
            let input = fixture(endings);
            for mode in 0..=2 {
                let record = extract(&input, mode).unwrap();
                assert_eq!(record.skeleton.len() + 90, input.len());
                assert_eq!(
                    restore(&record.skeleton, mode, &record.residuals).unwrap(),
                    input
                );
            }
        }
    }

    #[test]
    fn rejects_noncanonical_fields_modes_and_counts() {
        assert!(parse_field(b"   -0.0000").is_err());
        assert!(parse_field(b"   +1.0000").is_err());
        assert!(parse_field(b"    1.00.0").is_err());
        let mut input = fixture(&[b"\n"]);
        assert!(extract(&input, 3).is_err());
        assert!(restore(&input, 3, &[]).is_err());
        let at = input.windows(6).position(|s| s == b"  3  2").unwrap();
        input[at..at + 3].copy_from_slice(b" -1");
        assert!(extract(&input, 2).is_err());
        assert!(extract(b"short", 0).is_err());
        assert!(bond_parent(b"  1  1", 3).is_err());
        assert!(bond_parent(b"  1  4", 3).is_err());
    }

    #[test]
    fn rejects_reconstruction_overflow_and_missing_vectors() {
        let record = extract(&fixture(&[b"\n"]), 2).unwrap();
        assert!(restore(&record.skeleton, 2, &record.residuals[..2]).is_err());
        let mut residuals = record.residuals;
        residuals[1][0] = i64::MAX;
        assert!(restore(&record.skeleton, 2, &residuals).is_err());
        assert!(fixed(i64::MIN).is_err());
        assert!(fixed(10_000_000_000).is_err());
        assert_eq!(fixed(-1).unwrap(), *b"   -0.0001");
    }
}
