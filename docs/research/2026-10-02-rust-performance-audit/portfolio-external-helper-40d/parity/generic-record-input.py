from pathlib import Path
out = bytearray()
for record in range(64):
    out += f"record={record:03d}; category=general; token=compress; field=".encode()
    out += b"predictable lossless data path " * (1 + record % 3)
    out += f"; position={record % 11:02d}\n".encode()
Path('/tmp/cix-portfolio-parity-input.bin').write_bytes(out)
