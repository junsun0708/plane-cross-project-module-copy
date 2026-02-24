import os
import json
from plane_migrate import PlaneAPI

def debug_ids():
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
    
    # 에너지플랫폼 ID
    p_id = "26b20311-c3ef-40ed-8879-c0d98dc2df5f"
    # ETC 모듈 ID
    m_id = "d2ba6578-831d-4f62-9f7d-0971fce888c3"
    
    print("Fetching Module Issues...")
    module_issues = api.list_module_work_items(p_id, m_id)
    mod_ids = [mi.get('id') for mi in module_issues]
    
    print("Fetching All Project Issues...")
    all_issues = api.list_work_items(p_id)
    all_ids = [ai.get('id') for ai in all_issues]
    
    print(f"Module Issues Count: {len(mod_ids)}")
    print(f"Total Project Issues Count: {len(all_ids)}")
    
    matches = [mid for mid in mod_ids if mid in all_ids]
    print(f"Matches count: {len(matches)}")
    
    if len(matches) == 0 and mod_ids and all_ids:
        print(f"Sample Mod ID: '{mod_ids[0]}'")
        print(f"Sample All ID: '{all_ids[0]}'")
        # 혹시 name으로라도 찾을 수 있는지
        mod_name = module_issues[0].get('name')
        matching_by_name = [ai.get('id') for ai in all_issues if ai.get('name') == mod_name]
        print(f"Search Module Issue by Name ('{mod_name}'): Found matching IDs: {matching_by_name}")

if __name__ == "__main__":
    debug_ids()
