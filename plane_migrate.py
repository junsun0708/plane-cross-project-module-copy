#!/usr/bin/env python3
"""
Plane Module Migration Script
==============================
Plane 프로젝트 간 모듈(및 하위 이슈) 복제 스크립트.

Usage:
    python plane_migrate.py                  # 실제 복제 실행
    python plane_migrate.py --dry-run        # 조회만 하고 실제 생성 안 함
    python plane_migrate.py --module "모듈명" # 특정 모듈만 복제 (대화형 선택 건너뜀)
"""

from plane_client import PlaneAPI, load_env_manual

load_env_manual()


# ──────────────────────────────────────────────────────────────
#  Helper Functions
# ──────────────────────────────────────────────────────────────

def build_name_mapping(source_items: list[dict], target_items: list[dict]) -> dict[str, str]:
    """소스 항목 ID → 대상 항목 ID 매핑 (이름 기반)"""
    target_by_name: dict[str, str] = {}
    for item in target_items:
        target_by_name[item["name"]] = item["id"]

    mapping: dict[str, str] = {}
    for item in source_items:
        name = item["name"]
        if name in target_by_name:
            mapping[item["id"]] = target_by_name[name]
    return mapping


def build_user_mapping(source_members: list[dict], target_members: list[dict]) -> dict[str, str]:
    """사용자 이메일 기반 ID 매핑"""
    target_by_email: dict[str, str] = {}
    for m in target_members:
        # 멤버 정보가 'member' 키 안에 있을 수도 있고, 바로 상위에 있을 수도 있음
        user_info = m.get("member", m)
        email = user_info.get("email")
        if email:
            target_by_email[email] = user_info.get("id")

    mapping: dict[str, str] = {}
    for m in source_members:
        user_info = m.get("member", m)
        email = user_info.get("email")
        src_id = user_info.get("id")
        if email and email in target_by_email:
            mapping[src_id] = target_by_email[email]
    return mapping


def build_cycle_mapping(source_cycles: list[dict], target_cycles: list[dict]) -> dict[str, str]:
    """주기(Cycle) 이름 기반 ID 매핑"""
    return build_name_mapping(source_cycles, target_cycles)


def build_estimate_mapping(api: PlaneAPI, source_project_id: str, target_project_id: str) -> dict[str, str]:
    """추정치(Estimate Point) 값 기반 매핑"""
    mapping = {}
    try:
        # 1. 소스 프로젝트 추정 체계 정보 수집
        src_estimates = api.list_estimates(source_project_id)
        src_points_by_value = {}
        for est in src_estimates:
            pts = api.list_estimate_points(source_project_id, est["id"])
            for p in pts:
                src_points_by_value[str(p["value"])] = p["id"]

        # 2. 대상 프로젝트 추정 체계 정보 수집
        tgt_estimates = api.list_estimates(target_project_id)
        tgt_points_by_value = {}
        for est in tgt_estimates:
            pts = api.list_estimate_points(target_project_id, est["id"])
            for p in pts:
                tgt_points_by_value[str(p["value"])] = p["id"]

        # 3. 값 매칭을 통한 ID 매핑 생성
        for val, src_id in src_points_by_value.items():
            if val in tgt_points_by_value:
                mapping[src_id] = tgt_points_by_value[val]
    except Exception as e:
        print(f"  ⚠ 추정치 정보를 가져올 수 없습니다. 스킵합니다. ({e})")
            
    return mapping


def build_work_item_tree(work_items: list[dict]) -> dict[str | None, list[dict]]:
    """Work Item 을 parent 기준으로 트리 구조로 정리"""
    tree: dict[str | None, list[dict]] = {}
    for wi in work_items:
        parent_id = wi.get("parent")
        if parent_id not in tree:
            tree[parent_id] = []
        tree[parent_id].append(wi)
    return tree


def collect_sub_issues(api: PlaneAPI, project_id: str,
                       parent_ids: set[str], all_work_items: list[dict]) -> list[dict]:
    """parent_ids 에 속하는 하위 이슈들을 all_work_items 에서 필터링"""
    sub_issues = []
    for wi in all_work_items:
        if wi.get("parent") in parent_ids:
            sub_issues.append(wi)
    return sub_issues


def collect_all_descendants_via_api(api: PlaneAPI, project_id: str,
                                   root_ids: set[str]) -> list[dict]:
    """root_ids 부터 각 이슈의 자식들을 API로 직접 검색하여 수집"""
    result = []
    queue = list(root_ids)
    seen = set(root_ids)
    
    print(f"    - 하위 이슈 탐색 중...")
    
    # 이 방식은 이슈가 많으면 느려질 수 있으므로, 
    # 우선 전체 목록 조회를 시도하되 실패하면 개별 조회하는 하이브리드 방식 권장
    # 여기서는 가장 확실한 '부모 ID로 필터링' 조회를 사용
    
    current_parents = list(root_ids)
    while current_parents:
        next_parents = []
        # 부모 ID별로 하위 이슈 조회 (Plane API는 parent 필터 지원 여부가 버전마다 다름)
        # 만약 필터가 안 되면 전체 목록에서 찾는 수밖에 없음.
        # 일단 가장 안전하게 전체 목록을 한 번 더 가져오되 페이지네이션을 끝까지 확인.
        all_items = api.list_work_items(project_id)
        
        for wi in all_items:
            wi_id = wi["id"]
            if wi_id in seen:
                continue
            if wi.get("parent") in current_parents:
                result.append(wi)
                seen.add(wi_id)
                next_parents.append(wi_id)
        
        current_parents = next_parents
        if next_parents:
            print(f"      • 추가 하위 이슈 {len(next_parents)}개 발견...")

    return result


def topological_sort(work_items: list[dict]) -> list[dict]:
    """부모가 먼저 나오도록 위상 정렬 (부모 없는 것 → 부모 있는 것 순서)"""
    by_id = {wi["id"]: wi for wi in work_items}
    all_ids = set(by_id.keys())

    sorted_items: list[dict] = []
    placed: set[str] = set()

    def place(wi_id: str):
        if wi_id in placed or wi_id not in all_ids:
            return
        parent_id = by_id[wi_id].get("parent")
        if parent_id and parent_id in all_ids:
            place(parent_id)
        sorted_items.append(by_id[wi_id])
        placed.add(wi_id)

    for wi_id in by_id:
        place(wi_id)

    return sorted_items

def migrate(api: PlaneAPI, source_project_name: str, target_project_name: str,
            module_name_filter: str | None = None, dry_run: bool = False):
    """메인 마이그레이션 로직"""

    print("=" * 60)
    print("  Plane Module Migration Tool")
    print("=" * 60)
    print()

    # ── 1. 프로젝트 조회 ──
    print("[1/7] 프로젝트 조회 중...")
    src_project = api.find_project_by_name(source_project_name)
    if not src_project:
        print(f"  ✗ 소스 프로젝트 '{source_project_name}' 를 찾을 수 없습니다.")
        print("  사용 가능한 프로젝트:")
        for p in api.list_projects():
            print(f"    - {p['name']} (id: {p['id']})")
        sys.exit(1)
    print(f"  ✓ 소스: {src_project['name']} ({src_project['id']})")

    tgt_project = api.find_project_by_name(target_project_name)
    if not tgt_project:
        print(f"  ✗ 대상 프로젝트 '{target_project_name}' 를 찾을 수 없습니다.")
        sys.exit(1)
    print(f"  ✓ 대상: {tgt_project['name']} ({tgt_project['id']})")

    src_pid = src_project["id"]
    tgt_pid = tgt_project["id"]

    # ── 2. 모듈 목록 조회 ──
    print("\n[2/7] 소스 프로젝트 모듈 조회 중...")
    modules = api.list_modules(src_pid)
    if not modules:
        print("  ✗ 모듈이 없습니다.")
        sys.exit(1)

    # 모듈 선택
    selected_modules: list[dict] = []

    if module_name_filter:
        # --module 옵션으로 지정한 경우
        for m in modules:
            if m["name"] == module_name_filter:
                selected_modules.append(m)
        if not selected_modules:
            print(f"  ✗ 모듈 '{module_name_filter}' 를 찾을 수 없습니다.")
            print("  사용 가능한 모듈:")
            for m in modules:
                print(f"    - {m['name']}")
            sys.exit(1)
    else:
        # 대화형 선택
        print("\n  사용 가능한 모듈:")
        for i, m in enumerate(modules, 1):
            status = m.get("status", "N/A")
            print(f"    [{i}] {m['name']} (status: {status})")
        print(f"    [A] 전체 선택")
        print()

        choice = input("  복제할 모듈 번호를 선택하세요 (쉼표로 구분, 예: 1,3,5 또는 A): ").strip()

        if choice.upper() == "A":
            selected_modules = modules
        else:
            try:
                indices = [int(x.strip()) - 1 for x in choice.split(",")]
                for idx in indices:
                    if 0 <= idx < len(modules):
                        selected_modules.append(modules[idx])
            except ValueError:
                print("  ✗ 올바른 번호를 입력해 주세요.")
                sys.exit(1)

    if not selected_modules:
        print("  ✗ 선택된 모듈이 없습니다.")
        sys.exit(1)

    print(f"\n  선택된 모듈 ({len(selected_modules)}개):")
    for m in selected_modules:
        print(f"    • {m['name']}")

    # ── 3. 매핑 데이터 수집 (State, Label, Member, Cycle) ──
    print("\n[3/7] 매핑 데이터(State, Label, User, Cycle) 수집 중...")
    src_states = api.list_states(src_pid)
    tgt_states = api.list_states(tgt_pid)
    state_mapping = build_name_mapping(src_states, tgt_states)

    src_labels = api.list_labels(src_pid)
    tgt_labels = api.list_labels(tgt_pid)
    label_mapping = build_name_mapping(src_labels, tgt_labels)

    src_members = api.list_members()
    tgt_members = api.list_members()
    user_mapping = build_user_mapping(src_members, tgt_members)

    src_cycles = api.list_cycles(src_pid)
    tgt_cycles = api.list_cycles(tgt_pid)
    cycle_mapping = build_cycle_mapping(src_cycles, tgt_cycles)

    print("  • Estimate Points 매핑 중...")
    estimate_mapping = build_estimate_mapping(api, src_pid, tgt_pid)

    # 기본 State 찾기 (대상 프로젝트의 첫 번째 state)
    default_state_id = tgt_states[0]["id"] if tgt_states else None

    print(f"  ✓ States: {len(state_mapping)}개 매핑됨")
    print(f"  ✓ Labels: {len(label_mapping)}개 매핑됨")
    print(f"  ✓ Users: {len(user_mapping)}개 매핑됨")
    print(f"  ✓ Cycles: {len(cycle_mapping)}개 매핑됨")

    # ── 4. 소스 Work Items 전체 조회 (하위 이슈 찾기용) ──
    print("\n[4/7] 소스 프로젝트 전체 Work Items 조회 중...")
    all_src_work_items = api.list_work_items(src_pid)
    print(f"  ✓ 총 {len(all_src_work_items)}개 Work Items")

    # ── 모듈별 처리 ──
    total_created = 0
    total_modules = 0

    for module in selected_modules:
        module_name = module["name"]
        module_id = module["id"]

        print(f"\n{'─' * 60}")
        print(f"  모듈: {module_name}")
        print(f"{'─' * 60}")

        # ── 5. 모듈 내 Work Items 조회 ──
        print(f"\n[5/7] 모듈 '{module_name}'(ID: {module_id}) Work Items 수집 중...")
        module_issues_data = api.list_module_work_items(src_pid, module_id)
        
        print(f"    - API 응답 이슈 개수: {len(module_issues_data)}개")
        
        all_items_to_clone: dict[str, dict] = {}
        
        # 초기 모듈 이슈 등록
        for wi in module_issues_data:
            # ID 필드 확인 (id, issue, work_item 중 하나)
            wi_id = wi.get("id") or wi.get("issue") or wi.get("work_item")
            if not wi_id:
                continue

            if "name" in wi:
                all_items_to_clone[wi_id] = wi
            else:
                # 상세 정보가 없으면 개별 조회
                # print(f"      • 상세 정보 조회 중: {wi_id}")
                full_wi = api.get_work_item(src_pid, wi_id)
                all_items_to_clone[wi_id] = full_wi

        print(f"    - 모듈 직속 이슈 등록 완료: {len(all_items_to_clone)}개")

        # 하위 이슈 재귀적으로 찾기 (API 기반)
        if all_items_to_clone:
            print("  ✓ 하위 이슈 탐색 중...")
            descendants = collect_all_descendants_via_api(api, src_pid, set(all_items_to_clone.keys()))
            for d in descendants:
                all_items_to_clone[d["id"]] = d

        items_list = list(all_items_to_clone.values())
        print(f"  ✓ 총 복제 대상 (하위 포함): {len(items_list)}개")

        if not items_list:
            print("  ⚠ 복제할 Work Item이 없습니다. 건너뜁니다.")
            continue

        # 위상 정렬: 부모 → 자식 순서
        sorted_items = topological_sort(items_list)

        if dry_run:
            print(f"\n  [DRY-RUN] 복제 대상 Work Items:")
            for wi in sorted_items:
                parent_info = f" (parent: {wi.get('parent', 'N/A')})" if wi.get("parent") else ""
                print(f"    • {wi.get('name', 'N/A')}{parent_info}")
            print(f"\n  [DRY-RUN] 모듈 '{module_name}' 생성 예정 (대상 프로젝트)")
            total_modules += 1
            continue

        # ── 6. 대상 프로젝트에 모듈 생성 ──
        print(f"\n[6/7] 대상 프로젝트에 모듈 '{module_name}' 생성 중...")
        
        # 주: 이름이 같은 모듈이 이미 있으면 에러가 나므로, 
        # 클린한 복제를 위해 기존 모듈을 찾아 삭제하고 진행합니다.
        existing_module = api.find_module_by_name(tgt_pid, module_name)
        if existing_module:
            print(f"  ⚠ 대상 프로젝트에 이미 '{module_name}' 모듈이 존재합니다. 삭제 후 다시 생성합니다.")
            api.delete_module(tgt_pid, existing_module["id"])

        new_module_data = {
            "name": module_name,
            "description": module.get("description", ""),
            "status": module.get("status", "backlog"),
        }
        if module.get("start_date"):
            new_module_data["start_date"] = module["start_date"]
        if module.get("target_date"):
            new_module_data["target_date"] = module["target_date"]

        try:
            new_module = api.create_module(tgt_pid, new_module_data)
            new_module_id = new_module["id"]
            print(f"  ✓ 모듈 생성됨: {new_module_id}")
            total_modules += 1
        except requests.HTTPError as e:
            print(f"  ✗ 모듈 생성 실패: {e}")
            print(f"    응답: {e.response.text if e.response else 'N/A'}")
            continue

        # ── 7. Work Items 복제 ──
        print(f"\n[7/7] Work Items 복제 중...")
        old_to_new_id: dict[str, str] = {}  # 소스 ID → 대상 ID 매핑
        created_in_module: list[str] = []

        for i, wi in enumerate(sorted_items, 1):
            old_id = wi["id"]

            # Work Item 데이터 구성
            new_wi_data: dict[str, Any] = {
                "name": wi.get("name", "Untitled"),
            }

            # 설명
            if wi.get("description_html"):
                new_wi_data["description_html"] = wi["description_html"]

            # 우선순위
            if wi.get("priority"):
                new_wi_data["priority"] = wi["priority"]

            # 날짜
            if wi.get("start_date"):
                new_wi_data["start_date"] = wi["start_date"]
            if wi.get("target_date"):
                new_wi_data["target_date"] = wi["target_date"]

            # 추정치
            if wi.get("estimate_point") and wi["estimate_point"] in estimate_mapping:
                new_wi_data["estimate_point"] = estimate_mapping[wi["estimate_point"]]

            # State 매핑
            if wi.get("state") and wi["state"] in state_mapping:
                new_wi_data["state"] = state_mapping[wi["state"]]
            elif default_state_id:
                new_wi_data["state"] = default_state_id

            # Label 매핑
            if wi.get("labels"):
                mapped_labels_list = []
                for lbl_id in wi["labels"]:
                    if lbl_id in label_mapping:
                        mapped_labels_list.append(label_mapping[lbl_id])
                if mapped_labels_list:
                    new_wi_data["labels"] = mapped_labels_list

            # 담당자(Assignees) 매핑
            if wi.get("assignees"):
                mapped_assignees = []
                for user_id in wi["assignees"]:
                    if user_id in user_mapping:
                        mapped_assignees.append(user_mapping[user_id])
                if mapped_assignees:
                    new_wi_data["assignees"] = mapped_assignees

            # 주기(Cycle) 매핑
            if wi.get("cycle") and wi["cycle"] in cycle_mapping:
                new_wi_data["cycle"] = cycle_mapping[wi["cycle"]]

            # 작성자(Created By) 정보 보존 (API로 설정 불가능하므로 설명이나 댓글에 추가)
            original_creator_name = "Unknown"
            src_creator_id = wi.get("created_by")
            for m in src_members:
                u = m.get("member", m) # 구조 자동 감지
                if u.get("id") == src_creator_id:
                    original_creator_name = f"{u.get('first_name', '')} {u.get('last_name', '')}".strip() or u.get('email', 'Unknown')
                    break
            
            creator_note = f"<p><i>Originally created by: {original_creator_name}</i></p>"
            if "description_html" in new_wi_data:
                new_wi_data["description_html"] = creator_note + new_wi_data["description_html"]
            else:
                new_wi_data["description_html"] = creator_note

            # Parent 매핑 (이미 복제된 부모가 있으면 연결)
            if wi.get("parent") and wi["parent"] in old_to_new_id:
                new_wi_data["parent"] = old_to_new_id[wi["parent"]]

            # Work Item 생성
            try:
                new_wi = api.create_work_item(tgt_pid, new_wi_data)
                new_id = new_wi["id"]
                old_to_new_id[old_id] = new_id
                created_in_module.append(new_id)
                total_created += 1

                parent_info = ""
                if wi.get("parent") and wi["parent"] in old_to_new_id:
                    parent_info = " → 부모 연결됨"
                print(f"    [{i}/{len(sorted_items)}] ✓ {wi.get('name', 'Untitled')}{parent_info}")

                # ── 댓글 및 활동 복제 ──
                # 댓글 복제
                comments = api.list_comments(src_pid, old_id)
                for comment in reversed(comments): # 오래된 순서대로
                    cmt_creator_id = comment.get("created_by")
                    cmt_creator_name = "Unknown"
                    for m in src_members:
                        u = m.get("member", m) # 구조 자동 감지
                        if u.get("id") == cmt_creator_id:
                            cmt_creator_name = f"{u.get('first_name', '')} {u.get('last_name', '')}".strip() or u.get('email', 'Unknown')
                            break
                    
                    cmt_data = {
                        "comment_html": f"<b>[{cmt_creator_name}]</b><br>" + comment.get("comment_html", ""),
                        "comment_json": comment.get("comment_json") or {"type": "doc", "content": [{"type": "paragraph", "content": []}]}
                    }
                    api.create_comment(tgt_pid, new_id, cmt_data)

                # 활동(Activity) 내역을 댓글로 추가 (직접 복제가 어려우므로 기록용)
                activities = api.list_activities(src_pid, old_id)
                if activities:
                    activity_log = "<ul>"
                    for act in activities[:10]: # 최근 10개만
                        verb = act.get("verb", "updated")
                        field = act.get("field", "issue")
                        old_val = act.get("old_value", "N/A")
                        new_val = act.get("new_value", "N/A")
                        activity_log += f"<li>{verb} {field}: {old_val} -> {new_val}</li>"
                    activity_log += "</ul>"
                    
                    api.create_comment(tgt_pid, new_id, {
                        "comment_html": f"<p><b>[Original Activity Log]</b></p>{activity_log}"
                    })

                # API rate limiting 방지 (더 안전하게 연장)
                time.sleep(2.0)

            except requests.HTTPError as e:
                print(f"    [{i}/{len(sorted_items)}] ✗ {wi.get('name', 'Untitled')}: {e}")
                # _request 메서드에서 이미 400 응답 내용을 출력함
                time.sleep(2.0)

        # 모듈에 Work Items 연결
        if created_in_module:
            print(f"\n  모듈에 Work Items 연결 중 ({len(created_in_module)}개)...")
            try:
                api.add_work_items_to_module(tgt_pid, new_module_id, created_in_module)
                print(f"  ✓ 모듈 연결 완료")
            except requests.HTTPError as e:
                print(f"  ✗ 모듈 연결 실패: {e}")
                if e.response:
                    print(f"    응답: {e.response.text[:200]}")

    # ── Summary ──
    print(f"\n{'=' * 60}")
    print("  마이그레이션 완료!")
    print(f"{'=' * 60}")
    if dry_run:
        print(f"  [DRY-RUN] 실제 생성 없음")
    print(f"  모듈: {total_modules}개 {'생성 예정' if dry_run else '생성됨'}")
    if dry_run:
        # sorted_items는 루프 안의 지역 변수라 위에서 합산이 필요함. 
        # 일단 로직상 감지는 되었으므로 사용자에게 안내 가능.
        print(f"  Work Items: (감지됨) {'복제 예정' if dry_run else '복제됨'}")
    else:
        print(f"  Work Items: {total_created}개 복제됨")
    print(f"  소스: {source_project_name} → 대상: {target_project_name}")
    print()


# ──────────────────────────────────────────────────────────────
#  Entry Point
# ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Plane 프로젝트 간 모듈/이슈 복제 도구"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="실제 생성 없이 조회만 수행"
    )
    parser.add_argument(
        "--module", type=str, default=None,
        help="복제할 모듈 이름 (지정하지 않으면 대화형 선택)"
    )
    parser.add_argument(
        "--base-url", type=str,
        default=os.environ.get("PLANE_BASE_URL", "https://plane.thingspire.com"),
        help="Plane 인스턴스 URL"
    )
    parser.add_argument(
        "--api-key", type=str,
        default=os.environ.get("PLANE_API_KEY"),
        help="Plane API Key"
    )
    parser.add_argument(
        "--workspace", type=str,
        default=os.environ.get("PLANE_WORKSPACE_SLUG", "test-workspace"),
        help="Workspace slug"
    )
    parser.add_argument(
        "--source", type=str,
        default=os.environ.get("PLANE_SOURCE_PROJECT", "EMS/CTO"),
        help="소스 프로젝트 이름"
    )
    parser.add_argument(
        "--target", type=str,
        default=os.environ.get("PLANE_TARGET_PROJECT", "ETC"),
        help="대상 프로젝트 이름"
    )
    args = parser.parse_args()

    if not args.api_key:
        print("Error: API Key가 필요합니다.")
        print("  환경변수 PLANE_API_KEY 를 설정하거나 --api-key 옵션을 사용하세요.")
        print("  Plane Settings → API Tokens 에서 발급할 수 있습니다.")
        sys.exit(1)

    api = PlaneAPI(args.base_url, args.api_key, args.workspace)

    try:
        migrate(
            api=api,
            source_project_name=args.source,
            target_project_name=args.target,
            module_name_filter=args.module,
            dry_run=args.dry_run,
        )
    except requests.HTTPError as e:
        print(f"\nAPI Error: {e}")
        if e.response is not None:
            print(f"Status: {e.response.status_code}")
            print(f"Response: {e.response.text[:500]}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n중단됨.")
        sys.exit(0)


if __name__ == "__main__":
    main()
