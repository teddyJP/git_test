import pathlib
import subprocess

src = pathlib.Path('naf-bridge-build/port.py')
text = src.read_text(encoding='utf-8')

patch = r'''
# Compatibility shim for current alandtse/CommonLibF4 under VS 18/2026.
# The maintained tree declares two virtual destructors that are not emitted by
# the library target used here, causing NAF to link-fail. These are interface /
# value-shell destructors, so defaulting them inline preserves the expected ABI
# while avoiding a dependency on the missing out-of-line definitions.
for hp in (common_dst / 'CommonLibF4' / 'include').rglob('*.h'):
    try:
        ht = hp.read_text(encoding='utf-8-sig')
    except UnicodeDecodeError:
        continue
    hn = ht
    hn = hn.replace('virtual ~ActionInput();', 'virtual ~ActionInput() = default;')
    hn = hn.replace('~ActionInput() override;', '~ActionInput() override = default;')
    hn = hn.replace('~ActionInput();', '~ActionInput() = default;')
    hn = hn.replace('virtual ~IStackCallbackFunctor();', 'virtual ~IStackCallbackFunctor() = default;')
    hn = hn.replace('~IStackCallbackFunctor() override;', '~IStackCallbackFunctor() override = default;')
    hn = hn.replace('~IStackCallbackFunctor();', '~IStackCallbackFunctor() = default;')
    if hn != ht:
        print('Patched missing destructor definition in', hp, flush=True)
        hp.write_text(hn, encoding='utf-8', newline='\n')
'''

needle = "os.environ['VCPKG_ROOT']"
if needle not in text:
    raise SystemExit('Could not locate build section in port.py')
text = text.replace(needle, patch + '\n' + needle, 1)

runtime = pathlib.Path('naf-bridge-build/port_runtime.py')
runtime.write_text(text, encoding='utf-8', newline='\n')
subprocess.run(['python', str(runtime)], check=True)
