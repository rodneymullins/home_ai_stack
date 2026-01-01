import textwrap

files = ['app/templates/machine_detail.html', 'app/templates/bank_detail.html']

for f_path in files:
    with open(f_path, 'r') as f:
        lines = f.readlines()
    
    # Remove first line if it contains TEMPLATE =
    if 'TEMPLATE =' in lines[0]:
        lines = lines[1:]
    
    # Remove last line if it contains """
    if '"""' in lines[-1]:
        lines = lines[:-1]
    
    content = "".join(lines)
    # Dedent
    content = textwrap.dedent(content)
    
    with open(f_path, 'w') as f:
        f.write(content)
print("Cleaned templates")
