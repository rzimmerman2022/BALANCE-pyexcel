import pathlib, sys 
file_path = 'src\\balance_pipeline\\ingest.py' 
max_lines = 200 
with open(file_path, encoding='utf-8') as f: 
    for i,line in enumerate(f,1): 
    if i > max_lines: break 
    print(f\"{i:4}: {line.rstrip()}\") 
