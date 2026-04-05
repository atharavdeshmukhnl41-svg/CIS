with open('azure-collector/api/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Count quotes before line 700
triple_count = 0
for i in range(0, 699):
    triple_count += lines[i].count('"""')

print(f"Triple quote count before line 700: {triple_count}")
print(f"State before line 700: {'UNCLOSED' if triple_count % 2 == 1 else 'CLOSED'}")
print()

# Show line 489-510
for i in range(484, 535):
    line = lines[i]
    triple_in_line = line.count('"""')
    marker = f" ({'"""' in line})" if '"""' in line else ""
    print(f"L{i+1}: {line[:90]}{marker}")
