#!/usr/bin/env python3
"""
Plane Reporting Tool
====================
프로젝트별 진행 현황, 모듈 상태, 작업자별 통계를 요약하여 리포트를 생성합니다.
"""

import argparse
import sys
import os
from plane_client import PlaneAPI, load_env_manual

def generate_report(api: PlaneAPI, project_name: str):
    print(f"\n{'='*60}")
    print(f"  Plane Project Report: {project_name}")
    print(f"{'='*60}\n")

    # 1. 프로젝트 정보 조회
    project = api.find_project_by_name(project_name)
    if not project:
        print(f"  ✗ 프로젝트 '{project_name}'를 찾을 수 없습니다.")
        return
    
    pid = project['id']
    print(f"  [Project] {project['name']} ({project.get('identifier', 'N/A')})")
    
    # 2. 통계 데이터 수집
    print("  데이터 수집 중...")
    states = api.list_states(pid)
    state_map = {s['id']: s['name'] for s in states}
    state_group_map = {s['id']: s['group'] for s in states} # backlog, unstarted, started, completed, cancelled
    
    modules = api.list_modules(pid)
    work_items = api.list_work_items(pid)
    members = api.list_members()
    member_map = {}
    for m in members:
        # 멤버 정보가 'member' 키 안에 중첩되어 있거나 바로 상위에 있을 수 있음
        user = m.get('member', m)
        uid = user.get('id')
        if uid:
            full_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            member_map[uid] = full_name or user.get('email', 'Unknown')

    # 3. 진행 현황 (Overall Stats)
    total_count = len(work_items)
    group_stats = {"backlog": 0, "unstarted": 0, "started": 0, "completed": 0, "cancelled": 0}
    
    for wi in work_items:
        sid = wi.get('state')
        group = state_group_map.get(sid, "unstarted")
        group_stats[group] = group_stats.get(group, 0) + 1

    completed = group_stats.get('completed', 0)
    progress = (completed / total_count * 100) if total_count > 0 else 0

    # 이슈 ID -> 상태 그룹 매핑 생성 (정확한 통계를 위해)
    wi_group_map = {}
    for wi in work_items:
        sid = wi.get('state')
        wi_group_map[wi['id']] = state_group_map.get(sid, "unstarted")

    print("\n  📊 진행 현황 (Overall)")
    print(f"    - Total Issues: {total_count}")
    print(f"    - Completed: {completed}")
    print(f"    - Progress: {progress:.1f}%")
    
    print("\n  📂 모듈별 현황")
    if not modules:
        print("    (모듈 없음)")
    for m in modules:
        m_issues = api.list_module_work_items(pid, m['id'])
        m_total = len(m_issues)
        m_done = 0
        for mi in m_issues:
            # mi에서 이슈 ID 추출 (v1 API 호환성)
            mi_id = mi.get('issue') or mi.get('work_item') or mi.get('id')
            if mi_id and wi_group_map.get(mi_id) == 'completed':
                m_done += 1
        
        m_progress = (m_done / m_total * 100) if m_total > 0 else 0
        print(f"    • {m['name']:<20} | {m_done}/{m_total} | {m_progress:>5.1f}% | Status: {m.get('status', 'N/A')}")

    print("\n  👤 담당자별 남은 작업 (Uncompleted)")
    assignee_stats = {}
    for wi in work_items:
        sid = wi.get('state')
        if state_group_map.get(sid) in ['completed', 'cancelled']:
            continue
        
        assignees = wi.get('assignees', [])
        if not assignees:
            assignee_stats['Unassigned'] = assignee_stats.get('Unassigned', 0) + 1
        else:
            for aid in assignees:
                name = member_map.get(aid, "Unknown")
                assignee_stats[name] = assignee_stats.get(name, 0) + 1

    for name, count in sorted(assignee_stats.items(), key=lambda x: x[1], reverse=True):
        print(f"    • {name:<20}: {count} issues")

    print(f"\n{'='*60}")

def main():
    load_env_manual()
    parser = argparse.ArgumentParser(description="Plane Project Reporting Tool")
    parser.add_argument("--project", type=str, default=os.environ.get("PLANE_SOURCE_PROJECT"), help="리포트를 생성할 프로젝트 이름")
    parser.add_argument("--base-url", type=str, default=os.environ.get("PLANE_BASE_URL"), help="Plane URL")
    parser.add_argument("--api-key", type=str, default=os.environ.get("PLANE_API_KEY"), help="API Key")
    parser.add_argument("--workspace", type=str, default=os.environ.get("PLANE_WORKSPACE_SLUG"), help="Workspace Slug")
    
    args = parser.parse_args()

    if not args.api_key or not args.project:
        print("Error: API Key와 Project 이름이 필요합니다.")
        sys.exit(1)

    api = PlaneAPI(args.base_url, args.api_key, args.workspace)
    generate_report(api, args.project)

if __name__ == "__main__":
    main()
