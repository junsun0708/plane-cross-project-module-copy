import os
import json
import argparse
import sys
from plane_client import PlaneAPI, load_env_manual

def check_data():
    load_env_manual()
    
    parser = argparse.ArgumentParser(description="Check Plane API data and structure")
    parser.add_argument("--project", type=str, default=os.environ.get("PLANE_SOURCE_PROJECT"), help="Project name or ID")
    
    args = parser.parse_args()
    
    if not args.project:
        print("Error: Project name or ID is required.")
        sys.exit(1)

    api = PlaneAPI(os.environ["PLANE_BASE_URL"], os.environ["PLANE_API_KEY"], os.environ["PLANE_WORKSPACE_SLUG"])
    
    print("--- Members ---")
    members = api.list_members()
    print(f"Total Members: {len(members)}")
    if members:
        print("Sample Member Keys:", list(members[0].keys()))
        # member 데이터에는 'member' 필드 안에 실제 사용자 정보가 있을 수 있음
        sample = members[0].get('member', members[0])
        print("Sample User Info:", json.dumps(sample, indent=2, ensure_ascii=False))

    # Resolve Project ID
    project = api.find_project_by_name(args.project) or {'id': args.project, 'name': args.project}
    p_id = project['id']
    print(f"\n--- Project: {project['name']} ({p_id}) ---")

    print("\n--- Cycles ---")
    try:
        cycles = api.list_cycles(p_id)
        print(f"Total Cycles: {len(cycles)}")
        if cycles:
            print("Sample Cycle Info:", json.dumps(cycles[0], indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error fetching cycles: {e}")

    print("\n--- Estimate Points ---")
    try:
        eps = api.list_estimate_points(p_id)
        print(f"Total EP: {len(eps)}")
        if eps:
            print("Sample EP:", json.dumps(eps[0], indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error fetching estimate points: {e}")

if __name__ == "__main__":
    check_data()
