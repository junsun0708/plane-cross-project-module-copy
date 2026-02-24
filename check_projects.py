import os
import sys
import json
from plane_migrate import PlaneAPI

def check_names():
    # 환경변수 로드 (plane_migrate의 로직 활용)
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
    
    base_url = os.environ.get("PLANE_BASE_URL")
    api_key = os.environ.get("PLANE_API_KEY")
    ws_slug = os.environ.get("PLANE_WORKSPACE_SLUG")
    
    api = PlaneAPI(base_url, api_key, ws_slug)
    projects = api.list_projects()
    for p in projects:
        p_name = p.get('name')
        p_id = p.get('id')
        if p_name == "에너지플랫폼" or p.get('identifier') == "EMS":
            print(f"\nProject: {p_name}")
            modules = api.list_modules(p_id)
            for m in modules:
                m_name = m.get('name', '')
                if m_name == "ETC":
                    m_id = m.get('id')
                    module_issues = api.list_module_work_items(p_id, m_id)
                    with open("module_issues_sample.json", "w", encoding="utf-8") as f:
                        json.dump(module_issues[:3], f, ensure_ascii=False, indent=2)
                    print(f"Saved module issues sample to module_issues_sample.json")
                    break
            break

if __name__ == "__main__":
    check_names()
