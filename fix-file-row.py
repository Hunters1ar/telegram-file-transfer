import os

file_path = 'website/components/hunterstar/file-row.tsx'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('<Download size={15} />', '⬇️')
content = content.replace('<Link2 size={15} />', '🔗')
content = content.replace('<Trash2 size={15} />', '🗑️')
content = content.replace('<Globe size={13} />', '🌍')
content = content.replace('<Lock size={13} />', '🔒')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("file-row updated")
