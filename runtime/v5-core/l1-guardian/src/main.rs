//! VALO V5.0 — L1 Guardian: Simulation Entry Point

use std::process;

fn print_usage() {
    println!("VALO V5.0 — L1 Guardian Security Monitor Interface");
    println!("Usage: l1_guardian [OPTIONS]");
    println!("Options:");
    println!("  --uds [PATH]    Run Unix Domain Socket server (Default: /tmp/valo_v5_l1.sock)");
    println!("  --tcp [ADDR]    Run TCP server (Default: 127.0.0.1:7743)");
    println!("  --help, -h      Show system interface documentation");
}

fn main() {
    let args: Vec<String> = std::env::args().collect();

    match args.get(1).map(|s| s.as_str()) {
        Some("--uds") => {
            let path = args.get(2).map(|s| s.as_str()).unwrap_or("/tmp/valo_v5_l1.sock");
            if path.len() > 107 {
                eprintln!("Error: Unix socket path exceeds 107 characters.");
                process::exit(1);
            }
            l1_guardian::server::run_uds(path);
        }
        Some("--tcp") => {
            let addr = args.get(2).map(|s| s.as_str()).unwrap_or("127.0.0.1:7743");
            l1_guardian::server::run_tcp(addr);
        }
        Some("--help") | Some("-h") => {
            print_usage();
        }
        _ => {
            print_usage();
            println!("\nNo configuration specified. Falling back to safe local TCP proxy...");
            l1_guardian::server::run_tcp("127.0.0.1:7743");
        }
    }
}
