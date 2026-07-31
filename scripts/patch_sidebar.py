import glob

files = glob.glob('templates/admin/*.html')
for f in files:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Remove notifications link
    content = content.replace('<a class="nav-link" href="/admin/notifications/">🔔 Notifications</a>\n', '')
    content = content.replace('<a class="nav-link" href="/admin/notifications/">🔔 Notifications</a>', '')
    
    # Add teachers link if not exists
    if 'href="/admin/teachers/"' not in content:
        # We will add it right before <a class="nav-link" href="/admin/students/">🎓 Students</a>
        content = content.replace(
            '<a class="nav-link" href="/admin/students/">🎓 Students</a>',
            '<a class="nav-link" href="/admin/teachers/">👨‍🏫 Teachers</a>\n<a class="nav-link" href="/admin/students/">🎓 Students</a>'
        )

    with open(f, 'w', encoding='utf-8') as file:
        file.write(content)
print(f"Patched {len(files)} files.")
