import os
import sys
import json
import argparse
from plane_client import PlaneAPI, load_env_manual

def check_names():
    load_env_manual()
    
    parser = argparse.ArgumentParser(description="Check Plane projects and modules sample data")
    parser.add_argument("--project", type=str, default=os.environ.get("PLANE_SOURCE_PROJECT"), help="Project name or ID")
    parser.add_argument("--module", type=str, help="Module name to sample (e.g., ETC)")
    
    args = parser.parse_args()
    
    if not args.project:
        print("Error: Project name or ID is required.")
        sys.exit(1)

    api = PlaneAPI(os.environ["PLANE_BASE_URL"], os.environ["PLANE_API_KEY"], os.environ["PLANE_WORKSPACE_SLUG"])
    
    projects = api.list_projects()
    target_project = None
    for p in projects:
        if p.get('name') == args.project or p.get('identifier') == args.project or p.get('id') == args.project:
            target_project = p
            break
            
    if not target_project:
        print(f"Error: Project '{args.project}' not found.")
        return

    p_name = target_project.get('name')
    p_id = target_project.get('id')
    print(f"\nProject: {p_name} ({p_id})")
    
    modules = api.list_modules(p_id)
    if not args.module:
        print("Modules found:")
        for m in modules:
            print(f" - {m.get('name')} ({m.get('id')})")
        return

    for m in modules:
        m_name = m.get('name', '')
        if m_name == args.module or m.get('id') == args.module:
            m_id = m.get('id')
            print(f"Sampling Module: {m_name} ({m_id})")
            module_issues = api.list_module_work_items(p_id, m_id)
            output_file = f"sample_{m_name.lower() or 'module'}_issues.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(module_issues[:3], f, ensure_ascii=False, indent=2)
            print(f"Saved {len(module_issues[:3])} module issues sample to {output_file}")
            break
    else:
        print(f"Module '{args.module}' not found in project '{p_name}'.")

if __name__ == "__main__":
    check_names()
