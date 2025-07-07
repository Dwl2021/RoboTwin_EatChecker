import os
import yaml
import subprocess
import re
from typing import List, Dict, Any, Tuple
import sys

# 所有任务列表
TASKS = [
    "beat_block_hammer",
    "adjust_bottle",
    # "blocks_ranking_rgb",
    # "blocks_ranking_size",
    # "click_alarmclock",
    # "click_bell",
    # "dump_bin_bigbin",
    # "grab_roller",
    # "handover_block",
    # "handover_mic",
    # "hanging_mug",
    # "lift_pot",
    # "move_can_pot",
    # "move_pillbottle_pad",
    # "move_playingcard_away",
    # "move_stapler_pad",
    # "open_laptop",
    # "open_microwave",
    # "pick_diverse_bottles",
    # "pick_dual_bottles",
    # "place_a2b_left",
    # "place_a2b_right",
    # "place_bread_basket",
    # "place_bread_skillet",
    # "place_burger_fries",
    # "place_can_basket",
    # "place_cans_plasticbox",
    # "place_container_plate",
    # "place_dual_shoes",
    # "place_empty_cup",
    # "place_fan",
    # "place_mouse_pad",
    # "place_object_basket",
    # "place_object_scale",
    # "place_object_stand",
    # "place_phone_stand",
    # "place_shoe",
    # "press_stapler",
    # "put_bottles_dustbin",
    # "put_object_cabinet",
    # "rotate_qrcode",
    # "scan_object",
    # "shake_bottle",
    # "shake_bottle_horizontally",
    # "stack_blocks_three",
    # "stack_blocks_two",
    # "stack_bowls_three",
    # "stack_bowls_two",
    # "stamp_seal",
    # "turn_switch"
]

def parse_pose_line(line: str) -> Tuple[List[float], List[float]]:
    """Parse a line containing pose information and return position and quaternion."""
    # Extract all numbers from the line
    numbers = re.findall(r'-?\d+\.\d+e?-?\d*', line)
    numbers = [float(n) for n in numbers]
    
    # First 3 numbers are position, last 4 are quaternion
    position = numbers[:3]
    quaternion = numbers[3:]
    return position, quaternion

def process_episode_data(lines: List[str], start_idx: int) -> Tuple[Dict[str, List[Dict]], int]:
    """Process one episode's data and return the processed data and the next line index."""
    episode_data = {"target_poses": [], "constraint_poses": []}
    current_target = None
    i = start_idx
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Check if we've reached the end of this episode
        if "simulate data episode" in line:
            if "success" not in line:
                print(f"    Skipping failed episode at line {i}")
                return None, i + 1  # Skip failed episodes
            break
            
        # Parse target pose
        if "target_pose" in line:
            pos, quat = parse_pose_line(line)
            current_target = pos + quat
            print(f"    Found target pose: pos={pos}, quat={quat}")
            
        # Parse constraint pose
        elif "constraint_pose" in line:
            constraint = [0, 0, 0, 0, 0, 0]  # Default values
            if "None" not in line:
                # Extract the constraint values if they exist
                numbers = re.findall(r'-?\d+\.?\d*', line)
                constraint = [float(n) for n in numbers]
            print(f"    Found constraint pose: {constraint}")
            
            if current_target is not None:
                episode_data["target_poses"].append(current_target)
                episode_data["constraint_poses"].append(constraint)
                current_target = None
                
        i += 1
        
    return episode_data, i + 1

def generate_config(task_name: str, output_dir: str = "eat_check_config"):
    """Generate configuration file for a given task."""
    if task_name not in TASKS:
        print(f"Error: Unknown task '{task_name}'")
        print("Available tasks:")
        for task in TASKS:
            print(f"  - {task}")
        return
        
    print(f"\nStarting data collection for task: {task_name}")
    
    # Run the data collection command and capture output in real-time
    cmd = f"bash collect_data.sh {task_name} demo_randomized 0"
    process = subprocess.Popen(
        cmd, 
        shell=True, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE, 
        bufsize=1,
        universal_newlines=True
    )
    
    # Store all output lines
    output_lines = []
    
    # Read output in real-time
    print("\nCollecting data (this may take a while)...")
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            print(output.strip())  # Print in real-time
            output_lines.append(output.strip())
    
    # Check for errors
    rc = process.poll()
    if rc != 0:
        print(f"Error running command (return code: {rc})")
        stderr = process.stderr.read()
        if stderr:
            print(f"Error output: {stderr}")
        return
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    print("\nProcessing collected data...")
    i = 0
    episode_count = {"left": 0, "right": 0}
    all_episodes = {}
    
    while i < len(output_lines):
        line = output_lines[i].strip()
        if "arm target_pose" in line:
            arm_type = "left" if "left arm" in line else "right"
            print(f"\nProcessing {arm_type} arm episode:")
            episode_data, i = process_episode_data(output_lines, i)
            
            if episode_data is not None:
                episode_name = f"{arm_type}_arm_{episode_count[arm_type]}"
                print(f"  Successfully processed {episode_name}")
                all_episodes[episode_name] = {
                    "target_poses": episode_data["target_poses"],
                    "constraint_poses": episode_data["constraint_poses"]
                }
                episode_count[arm_type] += 1
        else:
            i += 1
    
    print(f"\nWriting configuration to {output_dir}/{task_name}.yml")
    output_file = os.path.join(output_dir, f"{task_name}.yml")
    with open(output_file, 'w') as f:
        yaml.dump(all_episodes, f, default_flow_style=None)
    
    print(f"\nDone! Successfully processed:")
    print(f"  - Left arm episodes: {episode_count['left']}")
    print(f"  - Right arm episodes: {episode_count['right']}")
    print(f"Configuration saved to: {output_file}")

def generate_all_configs(output_dir: str = "eat_check_config"):
    """Generate configuration files for all tasks."""
    print(f"Starting to generate configs for all {len(TASKS)} tasks")
    
    for i, task in enumerate(TASKS, 1):
        print(f"\n[{i}/{len(TASKS)}] Processing task: {task}")
        generate_config(task, output_dir)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Generate EAT check configuration files')
    parser.add_argument('--task', type=str, help='Specific task to process. If not provided, will process all tasks.')
    args = parser.parse_args()
    # Clean up data directory before generating configs
    data_dir = "./data"
    if os.path.exists(data_dir):
        print(f"\nCleaning up {data_dir}...")
        for file in os.listdir(data_dir):
            file_path = os.path.join(data_dir, file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    import shutil
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"Error: {e}")
        print("Data directory cleaned")
    
    if args.task:
        generate_config(args.task)
    else:
        generate_all_configs()
