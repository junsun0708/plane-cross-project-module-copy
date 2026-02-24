import os
import json
from plane_migrate import PlaneAPI

def check_data():
    def load_env_manual(file_path=".env"):
        if not os.path.exists(file_path): return
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"): continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip().strip('"').strip("'")

    load_env_manual()
    api = PlaneAPI(os.environ["PLANE_BASE_URL"], os.environ["PLANE_API_KEY"], os.environ["PLANE_WORKSPACE_SLUG"])
    
    print("--- Members ---")
    members = api.list_members()
    print(f"Total Members: {len(members)}")
    if members:
        print("Sample Member Keys:", list(members[0].keys()))
        # member 데이터에는 'member' 필드 안에 실제 사용자 정보가 있을 수 있음
        sample = members[0].get('member', members[0])
        print("Sample User Info:", json.dumps(sample, indent=2, ensure_ascii=False))

    p_id = "26b20311-c3ef-40ed-8879-c0d98dc2df5f" # 에너지플랫폼

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
