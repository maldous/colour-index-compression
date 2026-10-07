//! Canonical bounded ROBDD member-set representation for constraint-space work.
//!
//! The wire form is `node_count: u16 LE`, `root: u16 LE`, followed by
//! `node_count` records of `var: u8, low: u16 LE, high: u16 LE`.  IDs zero and
//! one are the false and true terminals; record `i` has ID `i + 2`.

use std::collections::BTreeMap;

const MIN_BITS: usize = 2;
const MAX_BITS: usize = 12;
const MAX_NODES: usize = 4095;
const HEADER_LEN: usize = 4;
const NODE_LEN: usize = 5;

#[derive(Clone, Copy, Eq, Ord, PartialEq, PartialOrd)]
struct Node {
    var: u8,
    low: u16,
    high: u16,
}

fn check_bits(b: usize) -> Result<(), String> {
    if !(MIN_BITS..=MAX_BITS).contains(&b) {
        return Err("BDD bit width must be in 2..=12".into());
    }
    Ok(())
}

fn universe(b: usize) -> usize {
    1usize << b
}

fn checked_members(b: usize, members: &[u16]) -> Result<(), String> {
    check_bits(b)?;
    let limit = universe(b);
    let mut previous = None;
    for &member in members {
        if usize::from(member) >= limit {
            return Err("BDD member outside bit-width universe".into());
        }
        if previous.is_some_and(|last| member <= last) {
            return Err("BDD members must be sorted and unique".into());
        }
        previous = Some(member);
    }
    Ok(())
}

fn build(
    b: usize,
    var: usize,
    start: usize,
    width: usize,
    members: &[u16],
    nodes: &mut Vec<Node>,
    interned: &mut BTreeMap<Node, u16>,
) -> Result<u16, String> {
    let first = members.partition_point(|&value| usize::from(value) < start);
    let end = start + width;
    let after = members.partition_point(|&value| usize::from(value) < end);
    if first == after {
        return Ok(0);
    }
    if after - first == width {
        return Ok(1);
    }
    if var == b {
        return Err("BDD construction reached a mixed leaf".into());
    }

    let half = width / 2;
    let low = build(b, var + 1, start, half, members, nodes, interned)?;
    let high = build(b, var + 1, start + half, half, members, nodes, interned)?;
    if low == high {
        return Ok(low);
    }
    let node = Node {
        var: var as u8,
        low,
        high,
    };
    if let Some(&id) = interned.get(&node) {
        return Ok(id);
    }
    if nodes.len() == MAX_NODES {
        return Err("BDD nonterminal-node limit exceeded".into());
    }
    let id = u16::try_from(nodes.len() + 2).map_err(|_| "BDD node ID overflow")?;
    nodes.push(node);
    interned.insert(node, id);
    Ok(id)
}

/// Encodes an ordered, duplicate-free member list as the canonical ROBDD wire form.
pub fn encode(b: usize, members: &[u16]) -> Result<Vec<u8>, String> {
    checked_members(b, members)?;
    let mut nodes = Vec::new();
    let mut interned = BTreeMap::new();
    let root = build(b, 0, 0, universe(b), members, &mut nodes, &mut interned)?;

    let mut out = Vec::with_capacity(HEADER_LEN + NODE_LEN * nodes.len());
    out.extend_from_slice(&(nodes.len() as u16).to_le_bytes());
    out.extend_from_slice(&root.to_le_bytes());
    for node in nodes {
        out.push(node.var);
        out.extend_from_slice(&node.low.to_le_bytes());
        out.extend_from_slice(&node.high.to_le_bytes());
    }
    Ok(out)
}

fn node_at(nodes: &[Node], id: u16) -> Option<Node> {
    id.checked_sub(2)
        .and_then(|index| nodes.get(usize::from(index)))
        .copied()
}

fn validate_wire(b: usize, data: &[u8]) -> Result<(u16, Vec<Node>), String> {
    check_bits(b)?;
    if data.len() < HEADER_LEN {
        return Err("truncated BDD header".into());
    }
    let count = usize::from(u16::from_le_bytes([data[0], data[1]]));
    let root = u16::from_le_bytes([data[2], data[3]]);
    if count > MAX_NODES || data.len() != HEADER_LEN + NODE_LEN * count {
        return Err("invalid BDD node count or wire length".into());
    }
    let greatest_id = count + 1;
    if usize::from(root) > greatest_id {
        return Err("BDD root ID outside node table".into());
    }

    let mut nodes = Vec::with_capacity(count);
    let mut triples = BTreeMap::new();
    for index in 0..count {
        let offset = HEADER_LEN + NODE_LEN * index;
        let node = Node {
            var: data[offset],
            low: u16::from_le_bytes([data[offset + 1], data[offset + 2]]),
            high: u16::from_le_bytes([data[offset + 3], data[offset + 4]]),
        };
        let id = index + 2;
        if usize::from(node.var) >= b || node.low == node.high {
            return Err("invalid BDD node fields".into());
        }
        if usize::from(node.low) >= id || usize::from(node.high) >= id {
            return Err("BDD child must precede its parent".into());
        }
        for child in [node.low, node.high] {
            if child >= 2 {
                let child_node = node_at(&nodes, child).ok_or("BDD child ID outside node table")?;
                if child_node.var <= node.var {
                    return Err("BDD variable order is not increasing along an edge".into());
                }
            }
        }
        if triples.insert(node, ()).is_some() {
            return Err("duplicate BDD node triple".into());
        }
        nodes.push(node);
    }

    let mut reachable = vec![false; count];
    let mut stack = Vec::new();
    if root >= 2 {
        stack.push(root);
    }
    while let Some(id) = stack.pop() {
        let index = usize::from(id - 2);
        if reachable[index] {
            continue;
        }
        reachable[index] = true;
        let node = nodes[index];
        for child in [node.low, node.high] {
            if child >= 2 {
                stack.push(child);
            }
        }
    }
    if reachable.iter().any(|&seen| !seen) {
        return Err("BDD contains unreachable node records".into());
    }
    Ok((root, nodes))
}

fn accepts(b: usize, root: u16, nodes: &[Node], value: usize) -> bool {
    let mut id = root;
    while id >= 2 {
        let node = nodes[usize::from(id - 2)];
        let bit = (value >> (b - 1 - usize::from(node.var))) & 1;
        id = if bit == 0 { node.low } else { node.high };
    }
    id == 1
}

/// Decodes only canonical, reduced, fully reachable ROBDD wire forms.
pub fn decode(b: usize, data: &[u8]) -> Result<Vec<u16>, String> {
    let (root, nodes) = validate_wire(b, data)?;
    let mut members = Vec::new();
    for value in 0..universe(b) {
        if accepts(b, root, &nodes, value) {
            members.push(value as u16);
        }
    }
    // Structural checks above make the graph an ROBDD.  Re-encoding also binds
    // the exact postorder ID allocation and rejects semantically equivalent but
    // noncanonical wire layouts.
    if encode(b, &members)? != data {
        return Err("noncanonical BDD wire form".into());
    }
    Ok(members)
}
