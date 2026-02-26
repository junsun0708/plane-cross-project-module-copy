#!/usr/bin/env python3
"""
Plane Health Check Tool
=======================
데이터 누락(설명 없음, 담당자 없음, 마감일 누락)이나 지연된 작업을 찾아냅니다.
"""

import argparse
import sys
import os
from datetime import datetime
from plane_client import PlaneAPI, load_env_manual

def check_health(api: PlaneAPI, project_name: str, level: int = 0):
    print(f"\n{'='*60}")
    print(f"  Plane Project Health Check: {project_name} (Level: {level})")
    print(f"{'='*60}\n")

    project = api.find_project_by_name(project_name)
    if not project:
        print(f"  ✗ 프로젝트 '{project_name}'를 찾을 수 없습니다.")
        return
    
    pid = project['id']
    work_items = api.list_work_items(pid)
    states = api.list_states(pid)
    state_group_map = {s['id']: s['group'] for s in states}
    
    today = datetime.now().date()
    
    issues_found = []

    for wi in work_items:
        sid = wi.get('state')
        group = state_group_map.get(sid)
        
        # 완료되거나 취소된 건, 그리고 백로그에 있는 건은 체크 제외
        if group in ['completed', 'cancelled', 'backlog']:
            continue

        reasons = []
        
        # 0. 일정 지연 (기본 레벨)
        if wi.get('target_date'):
            due_date = datetime.strptime(wi['target_date'], '%Y-%m-%d').date()
            if due_date < today:
                reasons.append(f"일정 지연 (Overdue: {wi['target_date']})")

        # 1. 담당자 누락 (Level 1 이상)
        if level >= 1:
            if not wi.get('assignees'):
                reasons.append("담당자 없음 (No Assignee)")
            
        # 2. 설명 부실 (Level 2 이상)
        if level >= 2:
            desc = wi.get('description_html', '')
            if not desc or len(desc) < 20:
                reasons.append("설명 부족 (Short/No Description)")
            
        # 3. 마감일 누락 (Level 3 이상)
        if level >= 3:
            if group == 'started' and not wi.get('target_date'):
                reasons.append("마감일 누락 (No Target Date for Started)")
            
        if reasons:
            issues_found.append({
                'id': wi.get('identifier') or wi.get('sequence_id') or 'N/A',
                'name': wi.get('name', 'Untitled'),
                'reasons': reasons
            })

    if not issues_found:
        print("  ✅ 현재 레벨에서 모든 티켓이 운영 규칙을 잘 준수하고 있습니다!")
    else:
        print(f"  ⚠ {len(issues_found)}개의 티켓에서 개선 권고 사항이 발견되었습니다.\n")
        for item in issues_found:
            print(f"  [{item['id']}] {item['name']}")
            for r in item['reasons']:
                print(f"    - {r}")
            print()

    print(f"{'='*60}")

def main():
    load_env_manual()
    parser = argparse.ArgumentParser(description="Plane Project Health Check Tool")
    parser.add_argument("--project", type=str, default=os.environ.get("PLANE_SOURCE_PROJECT"), help="체크할 프로젝트 이름")
    parser.add_argument("--level", "-l", type=int, default=0, choices=[0, 1, 2, 3], help="검사 레벨 (0: 지연작업만, 1: +담당자, 2: +설명부족, 3: +마감일누락)")
    parser.add_argument("-1", action="store_const", const=1, dest="level", help="레벨 1 설정 (담당자 포함)")
    parser.add_argument("-2", action="store_const", const=2, dest="level", help="레벨 2 설정 (담당자+설명 포함)")
    parser.add_argument("-3", action="store_const", const=3, dest="level", help="레벨 3 설정 (전체 검사)")
    
    parser.add_argument("--base-url", type=str, default=os.environ.get("PLANE_BASE_URL"), help="Plane URL")
    parser.add_argument("--api-key", type=str, default=os.environ.get("PLANE_API_KEY"), help="API Key")
    parser.add_argument("--workspace", type=str, default=os.environ.get("PLANE_WORKSPACE_SLUG"), help="Workspace Slug")
    
    args = parser.parse_args()

    if not args.api_key or not args.project:
        print("Error: API Key와 Project 이름이 필요합니다.")
        sys.exit(1)

    api = PlaneAPI(args.base_url, args.api_key, args.workspace)
    check_health(api, args.project, args.level)

if __name__ == "__main__":
    main()
