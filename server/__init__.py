import os
import shutil

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
# Get the project root directory (parent of server directory)
project_root = os.path.dirname(script_dir)

# Ensure base directory exists
os.makedirs("/tmp/data", exist_ok=True)

# Copy resumes → /tmp/data/resumes
src = os.path.join(project_root, "data", "resumes")
dst = "/tmp/data/resumes"
if os.path.exists(src):
    shutil.copytree(src, dst, dirs_exist_ok=True)
else:
    print(f"Warning: Source directory {src} does not exist. "
          f"Creating empty directory.")
    os.makedirs(dst, exist_ok=True)

# Copy resumes_team → /tmp/data/team_resumes
src_team = os.path.join(project_root, "data", "resumes_team")
dst_team = "/tmp/data/team_resumes"
if os.path.exists(src_team):
    shutil.copytree(src_team, dst_team, dirs_exist_ok=True)
else:
    print(f"Warning: Source directory {src_team} does not exist. "
          f"Creating empty directory.")
    os.makedirs(dst_team, exist_ok=True)

# Copy context.json → /tmp/data/context.json
context_src = os.path.join(project_root, "data", "context.json")
context_dst = "/tmp/data/context.json"
if os.path.exists(context_src):
    shutil.copy(context_src, context_dst)
else:
    print(f"Warning: Source file {context_src} does not exist.")
