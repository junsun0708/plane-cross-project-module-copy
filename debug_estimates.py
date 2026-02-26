import os
import json
import argparse
import sys
import time
from plane_client import PlaneAPI, load_env_manual

def debug_data():
    load_env_manual()
    
    parser = argparse.ArgumentParser(description="Debug Plane Data for Estimates and Attachments")
    parser.add_argument("--project", type=str, default=os.environ.get("PLANE_SOURCE_PROJECT"), help="Project name or ID")
    
    args = parser.parse_args()
    
    if not args.project:
        print("Error: Project name or ID is required.")
        sys.exit(1)

    api = PlaneAPI(os.environ["PLANE_BASE_URL"], os.environ["PLANE_API_KEY"], os.environ["PLANE_WORKSPACE_SLUG"])
    
    # Resolve Project ID
    project = api.find_project_by_name(args.project) or {'id': args.project, 'name': args.project}
    p_id = project['id']
    print(f"--- Project: {project['name']} ({p_id}) ---")

    # 1. Project Details
    print("\n--- Project Details ---")
    est_id = None
    try:
        proj_detail = api._get(f"projects/{p_id}/")
        print(f"Project Name: {proj_detail.get('name')}")
        est_id = proj_detail.get('estimate')
        print(f"Estimate ID from Project: {est_id}")
    except Exception as e:
        print(f"Error fetching project details: {e}")

    # 2. Fetch Estimate Points using the ID
    if est_id:
        print("\n--- Fetching Estimate Points ---")
        try:
            url = f"projects/{p_id}/estimates/{est_id}/estimate-points/"
            print(f"Trying: {api._url(url)}")
            points = api._get(url)
            print(f"SUCCESS! Found {len(points)} points.")
            for p in points:
                print(f"  - Point: {p['value']} (ID: {p['id']})")
        except Exception as e:
            print(f"FAILED to fetch points: {e}")

    # 3. Search for Images in Comments
    print("\n--- Searching for Images in Comments ---")
    try:
        work_items = api.list_work_items(p_id)
        found_img = False
        for wi in work_items[:200]:
            try:
                comments = api.list_comments(p_id, wi['id'])
                for cmt in comments:
                    html = cmt.get('comment_html', '')
                    if '<img' in html or 'attachment' in html.lower():
                        print(f"Found potential image in comment! Issue: {wi['name']}")
                        print(f"  Comment HTML: {html[:500]}...")
                        found_img = True
                        break
            except: pass
            if found_img: break
            time.sleep(0.1)
        if not found_img:
            print("No images found in comments within the first 200 issues.")
    except Exception as e:
        print(f"Error searching comments: {e}")

if __name__ == "__main__":
    debug_data()
