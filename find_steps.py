with open(r'C:/Users/user/Documents/Proyecto predeterminado/README.md',encoding='utf-8') as f:
    s=f.read()
idx = s.find('Próximos pasos')
if idx >= 0:
    print(repr(s[idx:idx+300]))
else:
    print('not found')
