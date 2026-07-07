import re
file_path = 'app/employee/routes.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace f\" with f"
content = re.sub(r'f\\"', 'f"', content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed syntax errors in employee routes')
