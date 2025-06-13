import os
import shutil

# Ensure base directory exists
os.makedirs("/tmp/data", exist_ok=True)

# Copy resumes → /tmp/data/resumes
src = "data/resumes"
dst = "/tmp/data/resumes"
shutil.copytree(src, dst, dirs_exist_ok=True)

# Copy resumes again → /tmp/data/team_resumes
dst_team = "/tmp/data/team_resumes"
shutil.copytree(src, dst_team, dirs_exist_ok=True)

# Copy context.json → /tmp/data/context.json
context_src = "data/context.json"
context_dst = "/tmp/data/context.json"
shutil.copy(context_src, context_dst)
