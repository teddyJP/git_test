import pathlib
import subprocess

src = pathlib.Path('naf-bridge-build/port.py')
text = src.read_text(encoding='utf-8')

# Keep the 1.11.221 AE runtime/core, but replace the two compatibility-facing
# headers with the Bridge variants.  They contain the extra NAFAPI exports and
# NAFBridge Papyrus natives while leaving hooks/scene/runtime implementation on
# the audited AE base.
merge_patch = r'''
bridge_api = BRIDGE / 'f4se-plugin' / 'src' / 'API' / 'API.h'
ae_api = PLUGIN / 'src' / 'API' / 'API.h'
shutil.copy2(bridge_api, ae_api)

bridge_pap = BRIDGE / 'f4se-plugin' / 'src' / 'Scripts' / 'Papyrus' / 'NAF.h'
ae_pap = PLUGIN / 'src' / 'Scripts' / 'Papyrus' / 'NAF.h'
shutil.copy2(bridge_pap, ae_pap)
print('Merged Bridge API.h and Scripts/Papyrus/NAF.h over AE core', flush=True)
'''

merge_needle = "cmake_path = PLUGIN / 'CMakeLists.txt'"
if merge_needle not in text:
    raise SystemExit('Could not locate compatibility merge point in port.py')
text = text.replace(merge_needle, merge_patch + '\n' + merge_needle, 1)

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
