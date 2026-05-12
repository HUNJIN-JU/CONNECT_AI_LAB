#!/usr/bin/env python3
# version: pack_apply_v4
"""두뇌의 템플릿 팩을 사용자 프로젝트에 한 번에 적용.

흐름:
  1. KIT_NAME — 두뇌의 40_템플릿/developer/<KIT_NAME>/ 폴더
  2. PROJECT_PATH — 적용할 사용자 프로젝트 (비우면 web_init 결과 자동)
  3. manifest.json 의 apply.{copy_to, post_install, app_imports, app_body} 사용:
     - files/* → PROJECT_PATH/copy_to/ (예: src/components/)
     - post_install: npm install / npx expo install 자동 실행
     - app_imports: App.tsx 또는 App.tsx 에 import 추가 + JSX 본문 자동
  4. 결과 출력 — 다음 단계 안내 (npm run dev 등)

이 도구가 코다리에게 주는 슈퍼파워:
  - 매뉴얼 cp + npm install 호출 안 해도 됨
  - 한 명령으로 "키트 적용 완료"
  - 의존성 누락 없음 (manifest 가 진실 소스)
"""
import os, sys, json, subprocess, shutil


HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HERE, "pack_apply.json")
WEB_INIT_CFG = os.path.join(HERE, "web_init.json")


def _log(msg, kind="info"):
    prefix = {"info": "📋", "ok": "✅", "warn": "⚠️ ", "err": "❌", "step": "▸"}.get(kind, "•")
    print(f"{prefix} {msg}", file=sys.stderr, flush=True)


def _load(p):
    if not os.path.exists(p):
        return {}
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _run(cmd, cwd):
    _log(f"$ {cmd}", "step")
    r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        for line in (r.stderr or "").splitlines()[-8:]:
            _log(line, "warn")
        return False
    return True


def _copy_tree(src_dir, dst_dir):
    """v2: 기존 파일이 있으면 .backup 자동 생성 (사용자 코드 보호).
    백업이 이미 있으면 덮어쓰지 않음 (멱등성)."""
    os.makedirs(dst_dir, exist_ok=True)
    copied = 0
    backed_up = []
    for root, _dirs, files in os.walk(src_dir):
        rel = os.path.relpath(root, src_dir)
        target = os.path.join(dst_dir, rel) if rel != "." else dst_dir
        os.makedirs(target, exist_ok=True)
        for f in files:
            dst_path = os.path.join(target, f)
            if os.path.exists(dst_path):
                bk = dst_path + ".backup"
                if not os.path.exists(bk):
                    try:
                        shutil.copy2(dst_path, bk)
                        backed_up.append(os.path.relpath(dst_path, dst_dir))
                    except Exception:
                        pass
            shutil.copy2(os.path.join(root, f), dst_path)
            copied += 1
    if backed_up:
        _log(f"기존 파일 {len(backed_up)}개 .backup 보존: {', '.join(backed_up[:3])}{' …' if len(backed_up) > 3 else ''}", "info")
    return copied


def _find_app_file(project_path):
    """vite/next 모두 커버. src/App.tsx 우선, 없으면 App.tsx (expo)."""
    for cand in ["src/App.tsx", "App.tsx", "src/app/page.tsx", "app/page.tsx"]:
        p = os.path.join(project_path, cand)
        if os.path.exists(p):
            return p
    return None


def _update_app_tsx(app_path, imports, body):
    """App.tsx 를 깨끗하게 새로 작성. 원본은 .backup 으로 보존.
    v2: regex 부분 매칭으로 옛 JSX 가 남던 사고 → 전체 덮어쓰기 + 백업 방식으로 변경."""
    try:
        with open(app_path, "r", encoding="utf-8") as f:
            original = f.read()
    except Exception:
        return False

    # 이미 키트 적용됐으면 skip
    if all(f"from './components/{n}'" in original for n in imports):
        return False

    # 백업 — 사용자가 손댄 거 잃지 않게
    try:
        backup_path = app_path + ".backup"
        if not os.path.exists(backup_path):
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(original)
    except Exception:
        pass

    # 새 App.tsx — 깨끗한 최소 버전
    import_lines = "\n".join([f"import {n} from './components/{n}'" for n in imports])
    new_content = f"""{import_lines}

export default function App() {{
  return (
    <main className="min-h-screen bg-white text-gray-900">
      {body}
    </main>
  );
}}
"""
    try:
        with open(app_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        return True
    except Exception:
        return False


def _find_brain_root():
    """두뇌 폴더 자동 탐색 (한국어 폴더명 포함)."""
    cands = [
        os.path.expanduser("~/.connect-ai-brain"),
        os.path.expanduser("~/Downloads/지식메모리"),
        os.path.expanduser("~/.connect-ai-brain-imported"),
    ]
    for c in cands:
        if os.path.exists(c):
            return c
    return cands[0]  # 첫 번째 fallback


def _list_kits(brain_root):
    """developer 카테고리의 모든 키트와 manifest 반환."""
    tdir = os.path.join(brain_root, "40_템플릿", "developer")
    if not os.path.exists(tdir):
        return []
    kits = []
    for name in os.listdir(tdir):
        d = os.path.join(tdir, name)
        if not os.path.isdir(d):
            continue
        mp = os.path.join(d, "manifest.json")
        if not os.path.exists(mp):
            continue
        try:
            with open(mp, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            kits.append({"name": name, "manifest": manifest})
        except Exception:
            pass
    return kits


def _score_kit(manifest, intent_text):
    """매니페스트 vs 사용자 의도(intent_text) 매칭 점수.
    keywords + name + description 단어 매칭. 한국어·영어 모두."""
    if not intent_text:
        return 0
    haystack = " ".join([
        manifest.get("name", ""),
        manifest.get("description", ""),
        " ".join(manifest.get("keywords") or []),
        manifest.get("category", ""),
    ]).lower()
    intent_lc = intent_text.lower()
    score = 0
    # keywords 직접 매칭 (높은 가중치)
    for kw in (manifest.get("keywords") or []):
        if kw.lower() in intent_lc:
            score += 10
    # name 자체가 의도에 있으면 (예: "landing-kit" → "landing")
    for token in manifest.get("name", "").split():
        if len(token) >= 3 and token.lower() in intent_lc:
            score += 5
    # 카테고리
    if (manifest.get("category", "").lower() or "") in intent_lc:
        score += 3
    return score


def _autodetect_kit(brain_root, intent_text):
    """사용자 의도에서 가장 적합한 키트 자동 추론. (kit_name, score, alternatives) 반환."""
    kits = _list_kits(brain_root)
    if not kits:
        return None, 0, []
    scored = [(k["name"], _score_kit(k["manifest"], intent_text), k["manifest"].get("description", "")) for k in kits]
    scored.sort(key=lambda x: -x[1])
    if scored[0][1] == 0:
        # 매치 0 — fallback: 가장 일반적인 landing-kit
        for k in kits:
            if k["name"] == "landing-kit":
                return "landing-kit", 0, scored[:3]
        return kits[0]["name"], 0, scored[:3]
    return scored[0][0], scored[0][1], scored[:3]


def _parse_cli_args():
    """v4: 로컬 LLM 이 CLI 인자로 호출하는 패턴도 지원.
       `--kit landing-kit --user-intent "..." --project /path` 또는
       환경변수 KIT_NAME / USER_INTENT / PROJECT_PATH."""
    out = {}
    args = sys.argv[1:]
    i = 0
    aliases = {
        "--kit": "KIT_NAME", "--kit-name": "KIT_NAME",
        "--user-intent": "USER_INTENT", "--intent": "USER_INTENT",
        "--project": "PROJECT_PATH", "--project-path": "PROJECT_PATH",
    }
    while i < len(args):
        a = args[i]
        if a in aliases and i + 1 < len(args):
            out[aliases[a]] = args[i + 1]
            i += 2
        elif "=" in a and a.startswith("--"):
            k, v = a[2:].split("=", 1)
            key = aliases.get("--" + k)
            if key:
                out[key] = v
            i += 1
        else:
            i += 1
    for k in ("KIT_NAME", "USER_INTENT", "PROJECT_PATH"):
        if k in os.environ and os.environ[k].strip():
            out.setdefault(k, os.environ[k])
    return out


def main():
    cfg = _load(CONFIG)
    init_cfg = _load(WEB_INIT_CFG)

    cli = _parse_cli_args()
    for k, v in cli.items():
        if v and str(v).strip():
            cfg[k] = v

    kit_name = (cfg.get("KIT_NAME") or "").strip()
    user_intent = (cfg.get("USER_INTENT") or "").strip()

    # 두뇌 폴더 찾기 (자동 추론에도 필요)
    brain_root = _find_brain_root()

    # v3: KIT_NAME 비어있고 USER_INTENT 있으면 자동 매칭
    selection_card = ""
    if not kit_name and user_intent:
        detected, score, alts = _autodetect_kit(brain_root, user_intent)
        if detected:
            kit_name = detected
            _log(f"자동 추론 → '{kit_name}' (매칭 점수 {score})", "info")
            if score == 0:
                _log("  ⚠️ 사용자 의도와 명확한 매칭 없음. 가장 일반적인 키트로 fallback.", "warn")
            # 시각 카드 (stdout에 마크다운 — 채팅창에 렌더링됨)
            card_lines = [
                "",
                "## 🎯 키트 자동 선택",
                "",
                f"> 사용자 의도: _\"{user_intent}\"_",
                "",
                "| 순위 | 키트 | 매칭 점수 | 비고 |",
                "|---|---|---|---|",
            ]
            for i, (n, s, desc) in enumerate(alts):
                marker = "**⭐ 선택**" if n == kit_name else ""
                d_short = (desc[:50] + "…") if len(desc) > 50 else desc
                card_lines.append(f"| {i+1} | `{n}` | **{s}** | {marker} {d_short} |")
            if score == 0:
                card_lines.append("")
                card_lines.append("⚠️ _명확한 매칭 없음 — fallback으로 가장 일반적인 키트 선택._")
            card_lines.append("")
            card_lines.append("> 💡 다른 키트로 바꾸려면 `pack_apply` 를 `KIT_NAME=<원하는 키트>` 로 다시 실행.")
            card_lines.append("")
            selection_card = "\n".join(card_lines)

    if not kit_name:
        kits = _list_kits(brain_root)
        avail = ", ".join([f"'{k['name']}'" for k in kits]) or "(두뇌에 키트 없음 — EZER 에서 먼저 주입)"
        _log(f"KIT_NAME 비어있고 USER_INTENT 도 없음.", "err")
        _log(f"  방법 1: KIT_NAME 명시 → {avail}", "info")
        _log(f"  방법 2: USER_INTENT 에 '다이어트 SaaS 랜딩' 같은 자연어 입력 → 자동 추론", "info")
        sys.exit(1)

    project = (cfg.get("PROJECT_PATH") or "").strip()
    if not project:
        project = (init_cfg.get("LAST_PROJECT") or "").strip()
    if not project:
        _log("PROJECT_PATH 비어있고 web_init 기록도 없음", "err")
        sys.exit(1)
    project = os.path.expanduser(project)
    if not os.path.isdir(project):
        _log(f"프로젝트 폴더 없음: {project}", "err")
        sys.exit(1)

    kit_dir = os.path.join(brain_root, "40_템플릿", "developer", kit_name)
    if not os.path.exists(kit_dir):
        _log(f"키트 없음: {kit_dir}", "err")
        _log(f"먼저 EZER Pack Vault 에서 '{kit_name}' 주입하세요.", "info")
        sys.exit(1)

    manifest_path = os.path.join(kit_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        _log(f"manifest 없음: {manifest_path}", "err")
        sys.exit(1)
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    apply = manifest.get("apply", {})
    copy_to = apply.get("copy_to", "src/components/")
    post_install = apply.get("post_install", [])
    app_imports = apply.get("app_imports", [])
    app_body = apply.get("app_body", "")

    _log(f"키트: {manifest.get('name', kit_name)} → {project}", "info")
    _log(f"기반: {manifest.get('base', '?')}", "info")

    # 1) 파일 복사
    src_files = os.path.join(kit_dir, "files")
    dst_files = os.path.join(project, copy_to.lstrip("./"))
    if not os.path.exists(src_files):
        _log("키트의 files/ 폴더 없음 — 파일 복사 스킵", "warn")
    else:
        n = _copy_tree(src_files, dst_files)
        _log(f"{n}개 파일 복사 → {dst_files}", "ok")

    # 2) 의존성 자동 설치
    if post_install:
        _log(f"의존성 {len(post_install)}개 설치 중...", "info")
        for cmd in post_install:
            ok = _run(cmd, cwd=project)
            if not ok:
                _log(f"부가 명령 실패: {cmd} — 계속 진행", "warn")

    # 3) App.tsx 자동 업데이트 (best-effort)
    if app_imports:
        app_file = _find_app_file(project)
        if app_file:
            changed = _update_app_tsx(app_file, app_imports,
                                      app_body or "\n".join([f"<{n} />" for n in app_imports]))
            if changed:
                _log(f"App.tsx 자동 업데이트: {app_file}", "ok")
            else:
                _log(f"App.tsx 이미 정정됨 또는 패턴 매칭 실패 — 수동 확인: {app_file}", "warn")
        else:
            _log("App.tsx 못 찾음 — 수동으로 import + JSX 추가 필요", "warn")

    # 결과 — stdout 으로 마크다운 (채팅창 렌더링)
    if selection_card:
        print(selection_card)
    print()
    print(f"## ✅ 적용 완료: `{manifest.get('name', kit_name)}`")
    print()
    print(f"- **위치**: `{project}`")
    print(f"- **기반**: {manifest.get('base', '?')}")
    if "expo" in (manifest.get("base", "").lower()):
        print(f"- **실행**: `cd {project} && npm start` → 폰에 Expo Go 깔고 QR 스캔")
    else:
        print(f"- **실행**: `cd {project} && npm run dev` → http://localhost:5173")
    print()
    _log(f"적용 완료: {kit_name}", "ok")


if __name__ == "__main__":
    main()
