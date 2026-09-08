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
cmake = cmake.replace('find_package(libzippp 3.0 REQUIRED)', 'find_package(libzippp REQUIRED CONFIG)')
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
j['dependencies'] = [('rsm-mmio' if x == 'mmio' else x) for x in j['dependencies']]
j['builtin-baseline'] = '4cfabe769eaceb209ea37267e8c50c43b86a4a7b'
manifest.write_text(json.dumps(j, indent=2) + '\n', encoding='utf-8')

pap = bridge_dst / 'Papyrus' / 'Papyrus.cpp'
t = pap.read_text(encoding='utf-8-sig')
if 'PAPYRUS_BIND(GetLoaded3dFlags)' not in t:
    t = t.replace('PAPYRUS_BIND(Update3DPosition);','PAPYRUS_BIND(Update3DPosition);\n\t\tPAPYRUS_BIND(GetLoaded3dFlags);')
pap.write_text(t, encoding='utf-8', newline='\n')


# Apply the small set of AE API corrections already established by the NAF port.
actor_h = common_dst / 'CommonLibF4' / 'include' / 'RE' / 'Bethesda' / 'Actor.h'
t = actor_h.read_text(encoding='utf-8-sig')
t = t.replace(
    "class AIProcess\n\t{\n\tpublic:\n",
    "class AIProcess\n\t{\n\tpublic:\n"
    "\t\tvoid ClearCurrentPackage(RE::Actor* a_actor)\n\t\t{\n"
    "\t\t\tusing func_t = decltype(&AIProcess::ClearCurrentPackage);\n"
    "\t\t\tstatic REL::Relocation<func_t> func{ REL::RelocationID(241540, 2231582) };\n"
    "\t\t\treturn func(this, a_actor);\n\t\t}\n\n"
    "\t\tvoid ClearCurrentDataForProcess(RE::Actor* a_actor)\n\t\t{\n"
    "\t\t\tusing func_t = decltype(&AIProcess::ClearCurrentDataForProcess);\n"
    "\t\t\tstatic REL::Relocation<func_t> func{ REL::RelocationID(577581, 2232435) };\n"
    "\t\t\treturn func(this, a_actor);\n\t\t}\n\n"
)
t = t.replace(
    "static REL::Relocation<func_t> func{ REL::ID(1446774) };",
    "static REL::Relocation<func_t> func{ REL::RelocationID(1446774, 2231704) };"
)
actor_anchor = "\t\tstatic constexpr auto FORM_ID{ ENUM_FORM_ID::kACHR };\n"
if "void EvaluatePackage(bool a_commandMode" not in t:
    t = t.replace(
        actor_anchor,
        actor_anchor +
        "\n\t\tvoid EvaluatePackage(bool a_commandMode, bool a_force)\n\t\t{\n"
        "\t\t\tusing func_t = decltype(&Actor::EvaluatePackage);\n"
        "\t\t\tstatic REL::Relocation<func_t> func{ REL::RelocationID(1395257, 2229805) };\n"
        "\t\t\treturn func(this, a_commandMode, a_force);\n\t\t}\n"
    )
actor_h.write_text(t, encoding='utf-8', newline='\n')

npc_h = common_dst / 'CommonLibF4' / 'include' / 'RE' / 'Bethesda' / 'TESBoundAnimObjects.h'
t = npc_h.read_text(encoding='utf-8-sig')
needle = "\t\t[[nodiscard]] SEX GetSex() noexcept\n"
if "float GetHeight(TESObjectREFR* a_refr" not in t:
    t = t.replace(
        needle,
        "\t\tfloat GetHeight(TESObjectREFR* a_refr, TESRace* a_race)\n\t\t{\n"
        "\t\t\tusing func_t = decltype(&TESNPC::GetHeight);\n"
        "\t\t\tstatic REL::Relocation<func_t> func{ REL::RelocationID(674794, 2207473) };\n"
        "\t\t\treturn func(this, a_refr, a_race);\n\t\t}\n\n" + needle
    )
npc_h.write_text(t, encoding='utf-8', newline='\n')

refr_h = common_dst / 'CommonLibF4' / 'include' / 'RE' / 'Bethesda' / 'TESObjectREFRs.h'
t = refr_h.read_text(encoding='utf-8-sig')
t = t.replace(
    "static REL::Relocation<func_t> func{ REL::ID(281170) };",
    "static REL::Relocation<func_t> func{ REL::RelocationID(281170, 2200861) };"
)
old_link = """\t\tvoid SetLinkedRef(Actor* a_actor, BGSKeyword* a_keyword)
\t\t{
\t\t\tusing func_t = decltype(&TESObjectREFR::SetLinkedRef);
\t\t\tstatic REL::Relocation<func_t> func{ REL::ID(192840) };
\t\t\treturn func(this, a_actor, a_keyword);
\t\t}"""
new_link = """\t\tvoid SetLinkedRef(const TESObjectREFR* a_refr, BGSKeyword* a_keyword)
\t\t{
\t\t\tusing func_t = decltype(&TESObjectREFR::SetLinkedRef);
\t\t\tstatic REL::Relocation<func_t> func{ REL::RelocationID(192840, 2202684) };
\t\t\treturn func(this, a_refr, a_keyword);
\t\t}"""
t = t.replace(old_link, new_link)
refr_h.write_text(t, encoding='utf-8', newline='\n')

hud_h = common_dst / 'CommonLibF4' / 'include' / 'RE' / 'Bethesda' / 'SendHUDMessage.h'
t = hud_h.read_text(encoding='utf-8-sig')
if "inline void ClearMessages()" not in t:
    t = t.replace(
        "\t\tinline void ShowHUDMessage(",
        "\t\tinline void ClearMessages()\n\t\t{\n"
        "\t\t\tusing func_t = decltype(&ClearMessages);\n"
        "\t\t\tstatic REL::Relocation<func_t> func{ REL::RelocationID(973227, 2222460) };\n"
        "\t\t\treturn func();\n\t\t}\n\n"
        "\t\tinline void ShowHUDMessage("
    )
hud_h.write_text(t, encoding='utf-8', newline='\n')

precull_h = common_dst / 'CommonLibF4' / 'include' / 'RE' / 'Bethesda' / 'BSPreCulledObjects.h'
t = precull_h.read_text(encoding='utf-8-sig')
if "Get3DForID" not in t:
    t = t.replace(
        "\tpublic:\n",
        "\tpublic:\n\t\tstatic void* Get3DForID(std::uint32_t a_id)\n\t\t{\n"
        "\t\t\tusing func_t = decltype(&BSPreCulledObjects::Get3DForID);\n"
        "\t\t\tstatic REL::Relocation<func_t> func{ REL::RelocationID(1087700, 2317330) };\n"
        "\t\t\treturn func(a_id);\n\t\t}\n\n",
        1
    )
precull_h.write_text(t, encoding='utf-8', newline='\n')

# Bridge API migrations against the maintained AE CommonLib surface.
utils = bridge_dst / 'Papyrus' / 'NAF_Utils.cpp'
t = utils.read_text(encoding='utf-8-sig')
t = t.replace("actor->ModifyKeyword(keyword, true);", "actor->AddKeyword(keyword);")
t = t.replace("actor->ModifyKeyword(keyword, false);", "actor->RemoveKeyword(keyword);")
t = t.replace("akActors[0]->GetSex() == RE::Actor::Sex::Female", "akActors[0]->GetNPC() && akActors[0]->GetNPC()->GetSex() == RE::SEX::kFemale")
t = t.replace("actor->GetSex() == RE::Actor::Sex::Female", "actor->GetNPC() && actor->GetNPC()->GetSex() == RE::SEX::kFemale")
t = t.replace("akActor->GetSex() == RE::Actor::Sex::Female", "akActor->GetNPC() && akActor->GetNPC()->GetSex() == RE::SEX::kFemale")
t = t.replace("getActorsInRangeImpl(from, distance, 0xFFFFFFFF, includeDead, nullptr)", "getActorsInRangeImpl(from, static_cast<std::uint32_t>(distance), 0x7FFFFFFF, includeDead, nullptr)")
utils.write_text(t, encoding='utf-8', newline='\n')

pap = bridge_dst / 'Papyrus' / 'Papyrus.cpp'
t = pap.read_text(encoding='utf-8-sig')
t = t.replace("return obj->GetFullyLoaded3D()->GetFlags();", "return static_cast<int>(obj->GetFullyLoaded3D()->GetFlags());")
t = t.replace("copy.push_back(flist->arrayOfForms[i]);", "copy.push_back(flist->arrayOfForms[static_cast<decltype(flist->arrayOfForms)::size_type>(i)]);")
pap.write_text(t, encoding='utf-8', newline='\n')

global_h = PLUGIN / 'src' / 'Data' / 'Global.h'
t = global_h.read_text(encoding='utf-8-sig')
t = t.replace('logger::info("Patched {} HeadParts.", count);', 'logger::info("Patched {} HeadParts.", count.load());')
global_h.write_text(t, encoding='utf-8', newline='\n')

# VS 18 promotes this legacy IK narrowing warning to an error under /WX; make the conversion explicit.
ik_h = PLUGIN / 'src' / 'BodyAnimation' / 'IK.h'
t = ik_h.read_text(encoding='utf-8-sig')
t = t.replace('ik.vec3.mul_scalar(dir.f, segmentLength);', 'ik.vec3.mul_scalar(dir.f, static_cast<ikreal_t>(segmentLength));')
ik_h.write_text(t, encoding='utf-8', newline='\n')

os.environ['VCPKG_ROOT'] = os.environ.get('VCPKG_INSTALLATION_ROOT', r'C:\\vcpkg')
build = PLUGIN / 'build-240'
run(['cmake','-S',str(PLUGIN),'-B',str(build),'-G','Visual Studio 18 2026','-A','x64','-DCOPY_BUILD=OFF'])
run(['cmake','--build',str(build),'--config','Release','--target','NAF','--','/m'])

dlls = [p for p in build.rglob('NAF.dll') if 'Release' in p.parts]
if not dlls: raise SystemExit('NAF.dll not found')
out = pathlib.Path.cwd() / 'out'
out.mkdir(exist_ok=True)
shutil.copy2(dlls[0], out / 'NAF.dll')
run(['certutil','-hashfile',str(out / 'NAF.dll'),'SHA256'])
print('BUILT', out / 'NAF.dll')