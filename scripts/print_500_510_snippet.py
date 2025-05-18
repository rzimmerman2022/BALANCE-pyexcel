import inspect
import pathlib
import textwrap
import balance_pipeline.csv_consolidator as mod

print('>>> imported from:', pathlib.Path(mod.__file__).resolve())
lines = inspect.getsource(mod).splitlines()
print('>>> snippet 500-510:')
print(textwrap.dedent("\n".join(lines[499:510])))
