#!/bin/bash
# crs_mods_parser_test.sh - synthetic test of the REAL v1.3.0 #MODS parsing text.
# Usage: bash crs_mods_parser_test.sh /path/to/itgmania   (checked out at tag v1.3.0, 8a3bf8884a)
# Cuts MsdFile::ReadBuf & co, RageUtil split/Trim, CompareNoCase and CourseLoaderCRS::ParseCourseMods
# out of the source by LINE RANGE (valid for v1.3.0 only), builds them with stubs and runs scenarios.
set -e
S="${1:?path to itgmania checkout}/src"; W=$(mktemp -d); cd "$W"
cp "$S/MsdFile.h" MsdFile.h
printf '#pragma once\n#include <string>\n#include <vector>\n#include <algorithm>\n#include <cstring>\n#include <cstdio>\n#include <cstdarg>\n#include <cmath>\n#define ASSERT(x) ((void)0)\n' > global.h
sed -n 21,150p "$S/MsdFile.cpp" > ex_msd.inc; sed -n 178,189p "$S/MsdFile.cpp" >> ex_msd.inc
sed -n 504,546p "$S/RageUtil.cpp" > ex_split.inc; sed -n 548,556p "$S/RageUtil.cpp" >> ex_split.inc
sed -n 340,385p "$S/CourseLoaderCRS.cpp" > ex_mods.inc
sed -n 1006,1016p "$S/RageUtil.cpp" > ex_trim.inc
sed -n 55,67p "$S/StdString.h" > ex_cmp.inc
cat > driver.cpp <<'DRV'
// Synthetic test: REAL MsdFile::ReadBuf, RageUtil do_split/split and
// CourseLoaderCRS::ParseCourseMods text (extracted with sed, see *.inc),
// with stubs for logging, Attack, WarnOnInvalidMods, StringToFloat, Trim.
#include "global.h"
#include "MsdFile.h"
#include <cstdlib>
#include <iostream>
#include <sstream>

#define ATTACK_STARTS_NOW (-10000.f)
struct Attack {
  float fStartSecond = ATTACK_STARTS_NOW;
  float fSecsRemaining = 0;
  std::string sModifiers;
};
struct AttackArray : std::vector<Attack> {};

static std::vector<std::string> g_log;
struct LogStub {
  void UserLog(const char* a, const std::string& p, const char* fmt, ...) {
    char buf[512]; va_list ap; va_start(ap, fmt); vsnprintf(buf, sizeof buf, fmt, ap); va_end(ap);
    g_log.push_back(std::string(a) + " " + p + " " + buf);
  }
} logstub, *LOG = &logstub;
namespace CourseUtil { void WarnOnInvalidMods(std::string s) { g_log.push_back("WarnOnInvalidMods(" + s + ")"); } }
struct CourseLoaderCRS {
  static bool ParseCourseMods(const MsdFile::value_t&, AttackArray&, const std::string&);
};
static float StringToFloat(const std::string& s) { float f = std::strtof(s.c_str(), nullptr); return std::isfinite(f) ? f : 0.0f; }
void Trim(std::string& sStr, const char* s = "\r\n\t ");
#include "ex_cmp.inc"
#include "ex_trim.inc"
#include "ex_split.inc"
#include "ex_msd.inc"
#include "ex_mods.inc"

static void run(const std::string& label, const std::string& crs) {
  MsdFile msd;
  msd.ReadFromString(crs, false);  // same call as CourseLoaderCRS::LoadFromBuffer / file load (unescape off)
  AttackArray attacks;
  std::cout << "=== " << label << "\n";
  for (unsigned i = 0; i < msd.GetNumValues(); i++) {
    std::string name = msd.GetParam(i, 0);
    const MsdFile::value_t& p = msd.GetValue(i);
    if (!CompareNoCase(name, "MODS")) {  // mirrors LoadFromMsd lines 129-130
      CourseLoaderCRS::ParseCourseMods(p, attacks, "test.crs");
    } else if (!CompareNoCase(name, "SONG")) {  // mirrors 131-141 (attacks attach to the next entry)
      std::cout << "  #SONG " << p[1] << " -> " << attacks.size() << " attack(s)";
      for (auto& a : attacks) std::cout << " [start=" << a.fStartSecond << " len=" << a.fSecsRemaining << " mods='" << a.sModifiers << "']";
      std::cout << "\n";
      attacks.clear();
    } else {
      std::cout << "  (tag " << name << ")\n";
    }
  }
  for (auto& l : g_log) std::cout << "  log: " << l << "\n";
  g_log.clear();
}

int main() {
  run("shipped example (Forced Modifiers (Advanced).crs style, '=' format)",
      "#MODS:TIME=0.00:LEN=60:MODS=Sudden;\n#MODS:TIME=60.00:LEN=60:MODS=Hidden;\n#SONG:StepMania 5\\Springtime:Medium:nodifficult;\n");
  run("CourseFormat.txt format 1 (repeated block, ':' separators)",
      "#MODS:TIME:0.500:LEN:0.500:MODS:2x;\n#MODS:TIME:1.500:LEN:0.500:MODS:0.5x;\n#SONG:A/B:Medium:;\n");
  run("CourseFormat.txt format 2 (nested block with length, ':' separators)",
      "#MODS:\n\tTIME:0.500:LEN:0.500:MODS:2x;\n\tTIME:1.500:LEN:0.500:MODS:0.5x;\n#SONG:A/B:Medium:;\n");
  run("CourseFormat.txt format 3 (nested block with ends, ':' separators)",
      "#MODS:\n\tTIME:0.500:END:1.000:MODS:2x;\n\tTIME:1.500:END:1.500:MODS:0.5x;\n#SONG:A/B:Medium:;\n");
  run("'=' format, LEN",  "#MODS:TIME=0.500:LEN=0.500:MODS=2x;\n#SONG:A/B:Medium:;\n");
  run("'=' format, END",  "#MODS:TIME=0.500:END=1.000:MODS=2x;\n#SONG:A/B:Medium:;\n");
  run("'=' format, several groups in ONE #MODS (RhythmLunatic wiki style)",
      "#MODS:TIME=0.000:END=300.000:MODS=*2 2x,Metal,Overhead,-1000% Cover,*4 90% Mini;\n#SONG:A/B:Medium:;\n");
  run("two groups in one #MODS; second omits LEN (inherits the first LEN?)",
      "#MODS:TIME=5:LEN=10:MODS=mirror:TIME=20:MODS=flip;\n#SONG:A/B:Medium:;\n");
  run("END given, then second group without END",
      "#MODS:TIME=5:END=15:MODS=mirror:TIME=20:LEN=3:MODS=flip;\n#SONG:A/B:Medium:;\n");
  run("MODS with no length at all",
      "#MODS:TIME=5:MODS=mirror;\n#SONG:A/B:Medium:;\n");
  run("TIME only after MODS (key order matters)",
      "#MODS:MODS=mirror:TIME=5:LEN=10;\n#SONG:A/B:Medium:;\n");
  run("mod string containing '=' (truncated?)",
      "#MODS:TIME=1:LEN=5:MODS=no mirror,foo=bar;\n#SONG:A/B:Medium:;\n");
  run("#MODS after the #SONG (attaches to the NEXT entry, not this one)",
      "#SONG:A/B:Medium:;\n#MODS:TIME=1:LEN=5:MODS=mirror;\n#SONG:C/D:Medium:;\n");
  run("#MODS before #SONGSELECT-like non-SONG tag then #SONG",
      "#MODS:TIME=1:LEN=5:MODS=mirror;\n#COURSE:x;\n#SONG:A/B:Medium:;\n");
  run("lowercase keys, spaces around key",
      "#MODS: time=1 : len=5 : mods=mirror ;\n#SONG:A/B:Medium:;\n");
  run("negative TIME",
      "#MODS:TIME=-5:LEN=10:MODS=mirror;\n#SONG:A/B:Medium:;\n");
  run("// comment inside value, and a line comment",
      "// hi\n#MODS:TIME=1:LEN=5:MODS=mirror;//trailing\n#SONG:A/B:Medium:;\n");
  run("CourseWriterCRS cache format (nested lines, ':' between groups)",
      "#MODS:\n  TIME=0.50:LEN=0.50:MODS=2x:\n  TIME=1.50:LEN=0.50:MODS=0.5x;\n#SONG:A/B:Medium:;\n");
  run("whitespace-only entry in MODS list (what WarnOnInvalidMods would receive)",
      "#MODS:TIME=1:LEN=5:MODS=flip, ,mirror;\n#SONG:A/B:Medium:;\n");
  return 0;
}
DRV
g++ -std=c++17 -I. -o drv driver.cpp && ./drv
