import re,sys,json
src=open('/home/claude/itgmania/src/PlayerOptions.cpp').read().split('\n')
body='\n'.join(src[767:1521])   # FromOneModString, lines 768-1521
lit=sorted(set(re.findall(r'sBit == "([a-z0-9\-]+)"',body)))
fam=sorted(set(re.findall(r'ssprintf\("([a-z]+)%d"',body)))
fam2=sorted(set(re.findall(r'ssprintf\("([a-z]+)%d"',body)))
gates=sorted(set(re.findall(r'sBit\.find\("([a-z]+)"\)',body)))
regex=re.findall(r'Regex \w+\("([^"]+)"\)',body)
json.dump({'literals':lit,'numbered_families':fam,'find_gates':gates,'regexes':regex},open(sys.argv[1],'w'),indent=1)
print(len(lit),'literals;',len(fam),'numbered families;',len(gates),'find() gates')
print('NUMBERED',fam); print('GATES',gates); print('REGEX',regex)
