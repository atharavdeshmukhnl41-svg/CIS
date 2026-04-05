with open('azure-collector/api/main.py', 'r', encoding='utf-8') as f:
    content = f.read()
    lines = content.split('\n')
    
    in_triple = False
    triple_start = 0
    
    for i, line in enumerate(lines, 1):
        triple_count = line.count('"""')
        
        if triple_count % 2 == 1:  # Odd number = toggle state
            if not in_triple:
                in_triple = True
                triple_start = i
                print(f"Triple quote opened at line {i}: {line[:60]}")
            else:
                in_triple = False
                print(f"Triple quote closed at line {i}: {line[:60]}")
        
        if i > 700 and i < 746:
            print(f"L{i}: in_triple={in_triple} | {line[:70]}")
    
    if in_triple:
        print(f"\nERROR: Unclosed triple quote started at line {triple_start}")
