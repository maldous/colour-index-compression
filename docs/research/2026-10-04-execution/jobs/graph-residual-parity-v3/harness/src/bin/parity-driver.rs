use cix_native::full_engine::graph_residuals as graph;
fn main() {
    let args: Vec<String> = std::env::args().collect();
    assert_eq!(args.len(), 5, "kind archive output exact-output-cap");
    let frame = std::fs::read(&args[2]).unwrap();
    let limit: usize = args[4].parse().unwrap();
    let decoded = match args[1].as_str() {
        "hydrogen" => graph::decode_hydrogen_with_limit(&frame, limit),
        "graph" => graph::decode_with_limit(&frame, limit),
        _ => panic!("unknown frame kind"),
    }.unwrap();
    std::fs::write(&args[3], decoded).unwrap();
}
