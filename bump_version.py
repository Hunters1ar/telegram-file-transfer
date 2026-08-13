import re
import sys

file_path = 'website/public/sw.js'
try:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
except FileNotFoundError:
    print(f"ERROR: {file_path} not found!")
    sys.exit(1)

pattern = r"(const CACHE_NAME\s*=\s*['\"])hunterstar-v(\d+)(?:\.(\d+))?(['\"])"
match = re.search(pattern, content)

if not match:
    print('ERROR: CACHE_NAME not found!')
    sys.exit(1)

prefix = match.group(1)
major = int(match.group(2))
minor = match.group(3)
suffix = match.group(4)

if not minor:
    new_version = f'{major}.1'
elif int(minor) >= 9:
    new_version = f'{major + 1}'
else:
    new_version = f'{major}.{int(minor) + 1}'

new_string = f'{prefix}hunterstar-v{new_version}{suffix}'
new_content = content[:match.start()] + new_string + content[match.end():]

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f"SUCCESS: updated to hunterstar-v{new_version}")
