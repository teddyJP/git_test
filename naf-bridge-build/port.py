import json
import os
import pathlib
import shutil
import subprocess

ROOT = pathlib.Path.cwd() / 'work'
NAF = ROOT / 'naf'
BRIDGE = ROOT / 'bridge'
COMMON = ROOT / 'commonlib'
PLUGIN = NAF / 'f4se-plugin'

def run(args, cwd=None):
    print('+', ' '.join(map(str, args)), flush=True)
    subprocess.run(list(map(str, args)), cwd=cwd, check=True)

ROOT.mkdir(exist_ok=True)
run(['git','clone','--branch','ae-1.11.221','--single-branch','https://github.com/LZB7/Native-Animation-Framework.git',str(NAF)])
run(['git','clone','--branch','master','--single-branch','https://github.com/NoAbleEngles/Native-Animation-Framework.git',str(BRIDGE)])
run(['git','clone','--branch','master','--single-branch','https://github.com/alandtse/CommonLibF4.git',str(COMMON)])
run(['git','submodule','update','--init','f4se-plugin/extern/ik','f4se-plugin/extern/pugixml'], cwd=NAF)

common_dst = PLUGIN / 'extern' / 'CommonLibF4'
if common_dst.exists(): shutil.rmtree(common_dst)
shutil.copytree(COMMON, common_dst, ignore=shutil.ignore_patterns('.git'))

bridge_dst = PLUGIN / 'extern' / 'Bridge'
if bridge_dst.exists(): shutil.rmtree(bridge_dst)
shutil.copytree(BRIDGE / 'f4se-plugin' / 'extern' / 'Bridge', bridge_dst)

cmake_path = PLUGIN / 'CMakeLists.txt'
cmake = cmake_path.read_text(encoding='utf-8')
cmake = cmake.replace('${CMAKE_CURRENT_SOURCE_DIR}/src\n)', '${CMAKE_CURRENT_SOURCE_DIR}/src\n\t\t${CMAKE_CURRENT_SOURCE_DIR}/extern\n)')
if 'extern/Bridge/Papyrus/Papyrus.cpp' not in cmake:
    cmake = cmake.replace('\t${SOURCES}\n\t${CMAKE_CURRENT_BINARY_DIR}/version.rc',
        '\t${SOURCES}\n'
        '\t${CMAKE_CURRENT_SOURCE_DIR}/extern/Bridge/Bridge.cpp\n'
        '\t${CMAKE_CURRENT_SOURCE_DIR}/extern/Bridge/IniParser/Ini.cpp\n'
        '\t${CMAKE_CURRENT_SOURCE_DIR}/extern/Bridge/IniParser/utility.cpp\n'
        '\t${CMAKE_CURRENT_SOURCE_DIR}/extern/Bridge/Papyrus/Papyrus.cpp\n'
        '\t${CMAKE_CURRENT_SOURCE_DIR}/extern/Bridge/Papyrus/NAF_Utils.cpp\n'
        '\t${CMAKE_CURRENT_BINARY_DIR}/version.rc')
cmake_path.write_text(cmake, encoding='utf-8', newline='\n')

for p in PLUGIN.rglob('*'):
    if not p.is_file() or p.suffix.lower() not in {'.h','.hpp','.cpp'}: continue
    try: t = p.read_text(encoding='utf-8-sig')
    except UnicodeDecodeError: continue
    n = t.replace('F4SE::RUNTIME_1_11_221', 'REL::Version{ 1, 11, 240, 0 }')
    n = n.replace('1.11.221.0','1.11.240.0').replace('1.11.221','1.11.240')
    if n != t: p.write_text(n, encoding='utf-8', newline='\n')

main_path = PLUGIN / 'src' / 'main.cpp'
main = main_path.read_text(encoding='utf-8-sig')
main = main.replace('v.MinimumRequiredXSEVersion({ 0, 7, 8, 0 });','v.MinimumRequiredXSEVersion({ 0, 7, 9, 0 });')
main = main.replace('#include "API/API.h"', '#include "API/API.h"\n#include "Bridge/Papyrus/Papyrus.h"\n#include "Bridge/Papyrus/NAF_Utils.h"')
main = main.replace('if (!papyrus || !papyrus->Register(Papyrus::RegisterFunctions)) {',
    'if (!papyrus || !papyrus->Register(Papyrus::RegisterFunctions) || !papyrus->Register(Papyrus::RegisterBridgeFunctions) || !papyrus->Register(Papyrus::RegisterNAFUtilsFunctions)) {')
main_path.write_text(main, encoding='utf-8', newline='\n')

engine = PLUGIN / 'src' / 'Compat' / 'Engine.h'
if engine.exists():
    t = engine.read_text(encoding='utf-8-sig').replace('0x55F490','0x55F7B0')
    engine.write_text(t, encoding='utf-8', newline='\n')

manifest = PLUGIN / 'vcpkg.json'
j = json.loads(manifest.read_text(encoding='utf-8-sig'))
if 'rapidcsv' not in j['dependencies']: j['dependencies'].append('rapidcsv')
manifest.write_text(json.dumps(j, indent=2) + '\n', encoding='utf-8')

pap = bridge_dst / 'Papyrus' / 'Papyrus.cpp'
t = pap.read_text(encoding='utf-8-sig')
if 'PAPYRUS_BIND(GetLoaded3dFlags)' not in t:
    t = t.replace('PAPYRUS_BIND(Update3DPosition);','PAPYRUS_BIND(Update3DPosition);\n\t\tPAPYRUS_BIND(GetLoaded3dFlags);')
pap.write_text(t, encoding='utf-8', newline='\n')

os.environ['VCPKG_ROOT'] = os.environ.get('VCPKG_INSTALLATION_ROOT', r'C:\\vcpkg')
build = PLUGIN / 'build-240'
run(['cmake','-S',str(PLUGIN),'-B',str(build),'-G','Visual Studio 17 2022','-A','x64','-DCOPY_BUILD=OFF'])
run(['cmake','--build',str(build),'--config','Release','--target','NAF','--','/m'])

dlls = [p for p in build.rglob('NAF.dll') if 'Release' in p.parts]
if not dlls: raise SystemExit('NAF.dll not found')
out = pathlib.Path.cwd() / 'out'
out.mkdir(exist_ok=True)
shutil.copy2(dlls[0], out / 'NAF.dll')
run(['certutil','-hashfile',str(out / 'NAF.dll'),'SHA256'])
print('BUILT', out / 'NAF.dll')