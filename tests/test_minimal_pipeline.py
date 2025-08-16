from src.minimal_pipeline import minimal_pipeline


def test_file_reading_and_transformation(tmp_path):
    # Create a known input file
    input_file = tmp_path / "input.txt"
    input_content = "Hello, BALANCE!"
    input_file.write_text(input_content, encoding="utf-8")
    output_file = tmp_path / "output.txt"
    # Run minimal pipeline
    proof = minimal_pipeline(str(input_file), str(output_file))
    # Verify output file exists and is correct
    assert output_file.exists(), "Output file not created"
    output_content = output_file.read_text(encoding="utf-8")
    assert output_content == input_content[::-1], "Transformation failed"
    # Verify execution trace
    trace_file = tmp_path / "output.trace.json"
    assert trace_file.exists(), "Execution trace not created"
    import json

    trace = json.loads(trace_file.read_text(encoding="utf-8"))
    assert trace["input_size"] == len(input_content)
    assert trace["output_size"] == len(output_content)
    assert trace["input_hash"] != trace["output_hash"], "No transformation occurred"
    assert trace["duration"] > 0, "Execution time suspiciously short"
