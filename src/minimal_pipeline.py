import time
import hashlib
from pathlib import Path

# Minimal pipeline: read, transform, write, log proof

def minimal_pipeline(input_path, output_path):
    proof = {
        'start_time': time.time(),
        'input_file': str(input_path),
        'output_file': str(output_path)
    }
    # Read
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()
    proof['input_size'] = len(content)
    proof['input_hash'] = hashlib.sha256(content.encode()).hexdigest()
    # Transform (reverse content as a trivial real transformation)
    result = content[::-1]
    proof['output_size'] = len(result)
    proof['output_hash'] = hashlib.sha256(result.encode()).hexdigest()
    # Write
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(result)
    proof['end_time'] = time.time()
    proof['duration'] = proof['end_time'] - proof['start_time']
    # Save execution trace
    trace_path = Path(output_path).with_suffix('.trace.json')
    import json
    with open(trace_path, 'w', encoding='utf-8') as f:
        json.dump(proof, f, indent=2)
    print(f"Execution trace saved to {trace_path}")
    return proof

if __name__ == "__main__":
    # Example usage: minimal_pipeline('input.txt', 'output.txt')
    import sys
    if len(sys.argv) == 3:
        minimal_pipeline(sys.argv[1], sys.argv[2])
    else:
        print("Usage: python minimal_pipeline.py <input_path> <output_path>")
