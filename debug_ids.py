import os
import json
import argparse
import sys
from plane_client import PlaneAPI, load_env_manual

def debug_ids():
    load_env_manual()
    
    parser = argparse.ArgumentParser(description="Debug Plane IDs and Module issue mapping")
    parser.add_argument("--project", type=str, default=os.environ.get("PLANE_SOURCE_PROJECT"), help="Project name or ID")
    parser.add_argument("--module", type=str, help="Module name or ID")
    
    args = parser.parse_args()
    
    if not args.project:
        print("Error: Project name or ID is required.")
        sys.exit(1)

    api = PlaneAPI(os.environ["PLANE_BASE_URL"], os.environ["PLANE_API_KEY"], os.environ["PLANE_WORKSPACE_SLUG"])
    
    # Resolve Project ID
    project = api.find_project_by_name(args.project) or {'id': args.project, 'name': args.project}
    p_id = project['id']
    print(f"Project: {project['name']} ({p_id})")
    
    # Resolve Module ID if provided
    m_id = args.module
    if args.module and len(args.module) < 30: # Assume it's a name if short
        modules = api.list_modules(p_id)
        for m in modules:
            if m['name'] == args.module:
                m_id = m['id']
                print(f"Module: {m['name']} ({m_id})")
                break
    
    if not m_id:
        print("Warning: No module ID/name provided or found. Skipping module-specific checks.")
        module_issues = []
    else:
        print(f"Fetching Module Issues for {m_id}...")
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
