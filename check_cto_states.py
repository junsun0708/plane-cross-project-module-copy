import os
from plane_client import PlaneAPI, load_env_manual

def debug_states():
    load_env_manual()
    api = PlaneAPI(os.environ["PLANE_BASE_URL"], os.environ["PLANE_API_KEY"], os.environ["PLANE_WORKSPACE_SLUG"])
    
    project_name = "CTO"
    project = api.find_project_by_name(project_name)
    if not project:
        print(f"Project {project_name} not found")
        return
    
    pid = project['id']
    states = api.list_states(pid)
    print(f"--- States for {project_name} ---")
    state_map = {}
    for s in states:
        print(f"ID: {s['id']}, Name: {s['name']}, Group: {s['group']}")
        state_map[s['id']] = s
    
    work_items = api.list_work_items(pid)
    print(f"\n--- Checking reported issues ---")
    target_ids = ["89", "78", "12"]
    for wi in work_items:
        seq_id = str(wi.get('sequence_id'))
        if seq_id in target_ids:
            sid = wi.get('state')
            state = state_map.get(sid)
            print(f"Issue: [{seq_id}] {wi['name']}")
            print(f"  State ID: {sid}")
            if state:
                print(f"  State Name: {state['name']}, Group: {state['group']}")
            else:
                print(f"  State info not found for ID: {sid}")
            print(f"  Target Date: {wi.get('target_date')}")

if __name__ == "__main__":
    debug_states()
