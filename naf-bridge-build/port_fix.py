import pathlib
import subprocess

src = pathlib.Path('naf-bridge-build/port.py')
text = src.read_text(encoding='utf-8')

# Keep the audited AE runtime/hooks, but layer the current Bridge-facing API,
# Papyrus bindings, and the minimal Bridge-only overlay data model on top.
merge_patch = r'''
bridge_api = BRIDGE / 'f4se-plugin' / 'src' / 'API' / 'API.h'
ae_api = PLUGIN / 'src' / 'API' / 'API.h'
shutil.copy2(bridge_api, ae_api)

bridge_pap = BRIDGE / 'f4se-plugin' / 'src' / 'Scripts' / 'Papyrus' / 'NAF.h'
ae_pap = PLUGIN / 'src' / 'Scripts' / 'Papyrus' / 'NAF.h'
shutil.copy2(bridge_pap, ae_pap)

bridge_reg = BRIDGE / 'f4se-plugin' / 'src' / 'Scripts' / 'Papyrus.h'
ae_reg = PLUGIN / 'src' / 'Scripts' / 'Papyrus.h'
shutil.copy2(bridge_reg, ae_reg)

# Migrate Bridge Papyrus calls to the AE compatibility helpers.
pt = ae_pap.read_text(encoding='utf-8-sig')
pt = pt.replace('a_actor->ModifyKeyword(Data::Forms::NAFDoNotUseKW, !a_usable);',
                'EngineCompat::ModifyKeyword(a_actor, Data::Forms::NAFDoNotUseKW, !a_usable);')
pt = pt.replace('player->ReenableInputForPlayer();',
                'EngineCompat::ReenableInputForPlayer(player);')
pt = pt.replace('object3d->world.WorldToLocal(parent3d->world)',
                'MathUtil::WorldToLocal(object3d->world, parent3d->world)')
# Current CommonLib structure_wrapper prefers values/rvalues here.
pt = pt.replace('res.insert("template", tmplt.Template);', 'res.insert("template", std::string(tmplt.Template));')
pt = pt.replace('res.insert("duration", ovrl->duration);', 'res.insert("duration", float(ovrl->duration));')
pt = pt.replace('res.insert("isFemale", tmplt.isFemale);', 'res.insert("isFemale", bool(tmplt.isFemale));')
pt = pt.replace('res.insert("alpha", tmplt.alpha);', 'res.insert("alpha", int(tmplt.alpha));')
pt = pt.replace('logger::info("GetOverlay request {}, result {}, dur:{}, isFemale:{}, alpha:{}", id, tmplt.Template, ovrl->duration, tmplt.isFemale, tmplt.alpha);',
                'logger::info("Bridge GetOverlay request {}", id);')
ae_pap.write_text(pt, encoding='utf-8', newline='\n')

# Hard-code the Bridge script name instead of depending on the old Forms.h macro.
rt = ae_reg.read_text(encoding='utf-8-sig').replace('MODNAME, #funcName, NAFBridge::funcName', '"NAFBridge"sv, #funcName, NAFBridge::funcName')
ae_reg.write_text(rt, encoding='utf-8', newline='\n')

# Minimal Overlay data support required by NAFBridge.GetOverlay.
gh = PLUGIN / 'src' / 'Data' / 'Global.h'
gt = gh.read_text(encoding='utf-8-sig')
gt = gt.replace('class GraphInfo;\n', 'class GraphInfo;\n\tclass Overlay;\n', 1)
gt = gt.replace('std::shared_ptr<const GraphInfo> GetGraphInfo(const std::string&, RE::Actor* actorBase = nullptr);',
                'std::shared_ptr<const GraphInfo> GetGraphInfo(const std::string&, RE::Actor* actorBase = nullptr);\n\tstd::shared_ptr<const Overlay> GetOverlaySet(const std::string&);', 1)
gt = gt.replace('#include "BodyAnimation/NANIM.h"',
                '#include "BodyAnimation/NANIM.h"\n#include "Bridge/NewData/Overlay.h"', 1)
gt = gt.replace('inline static IDMap<GraphInfo> GraphInfos;',
                'inline static IDMap<GraphInfo> GraphInfos;\n\t\tinline static IDMap<Overlay> Overlays;', 1)
gt = gt.replace('GraphInfos.clear();', 'GraphInfos.clear();\n\t\t\tOverlays.clear();')
gt = gt.replace('static inline constexpr std::array<std::string_view, 10> topNodeNames{',
                'static inline constexpr std::array<std::string_view, 11> topNodeNames{', 1)
gt = gt.replace('"tagData"\n\t\t};', '"tagData",\n\t\t\t"overlayData"\n\t\t};', 1)
gt = gt.replace('{ "graph", [](auto& m) { ParseXMLType<GraphInfo>(GraphInfos, m); } }',
                '{ "graph", [](auto& m) { ParseXMLType<GraphInfo>(GraphInfos, m); } },\n\t\t\t{ "overlaySet", [](auto& m) { ParseXMLType<Overlay>(Overlays, m); } }', 1)
gt = gt.replace('std::shared_ptr<const Race> GetRace(const std::string& id) { return GetObjectFromIDMap(Global::Races, id); }',
                'std::shared_ptr<const Race> GetRace(const std::string& id) { return GetObjectFromIDMap(Global::Races, id); }\n\tstd::shared_ptr<const Overlay> GetOverlaySet(const std::string& id) { return GetObjectFromIDMap(Global::Overlays, id); }', 1)
gh.write_text(gt, encoding='utf-8', newline='\n')

# Bridge NAF.h declares this logging toggle.
mainp = PLUGIN / 'src' / 'main.cpp'
mt = mainp.read_text(encoding='utf-8-sig')
if 'int PRINT_LOG = 1;' not in mt:
    mt = mt.replace('bool g_gameDataReady = false;', 'bool g_gameDataReady = false;\nint PRINT_LOG = 1;', 1)
mainp.write_text(mt, encoding='utf-8', newline='\n')

print('Merged Bridge API/Papyrus surfaces plus AE-compatible overlay support', flush=True)
'''

merge_needle = "cmake_path = PLUGIN / 'CMakeLists.txt'"
if merge_needle not in text:
    raise SystemExit('Could not locate compatibility merge point in port.py')
text = text.replace(merge_needle, merge_patch + '\n' + merge_needle, 1)

patch = r'''
# Compatibility shim for current alandtse/CommonLibF4 under VS 18/2026.
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
