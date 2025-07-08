import os
import yaml
import subprocess
import re
from typing import List, Dict, Any, Tuple
import sys

# 所有任务列表
TASKS = [
    #"beat_block_hammer",
    #"adjust_bottle",
    # "blocks_ranking_rgb",
    # "blocks_ranking_size",
    #"click_alarmclock",
    #"click_bell",
    "dump_bin_bigbin",
    "grab_roller",
    #"handover_block",
    #"handover_mic",
    #"hanging_mug",
    "lift_pot",
    #"move_can_pot",
    #"move_pillbottle_pad",
    #"move_playingcard_away",
    #"move_stapler_pad",
    #"open_laptop",
    #"open_microwave",
    "pick_diverse_bottles",
    "pick_dual_bottles",
    #"place_a2b_left",
    #"place_a2b_right",
    "place_bread_basket",
    "place_bread_skillet",
    "place_burger_fries",
    "place_can_basket",
    "place_cans_plasticbox",
    #"place_container_plate",
    "place_dual_shoes",
    #"place_empty_cup",
    #"place_fan",
    #"place_mouse_pad",
    #"place_object_basket",
    #"place_object_scale",
    #"place_object_stand",
    #"place_phone_stand",
    #"place_shoe",
    #"press_stapler",
    #"put_bottles_dustbin",
    #"put_object_cabinet",
    #"rotate_qrcode",
    "scan_object",
    #"shake_bottle",
    #"shake_bottle_horizontally",
    "stack_blocks_three",
    #"stack_blocks_two",
    "stack_bowls_three",
    "stack_bowls_two",
    #"stamp_seal",
    #"turn_switch"
]

def check_missing_configs(config_dir: str = "eat_check_config") -> List[str]:
    """Check for missing configuration files and return list of missing tasks"""
    if not os.path.exists(config_dir):
        print(f"Config directory {config_dir} does not exist, need to create all configuration files")
        return TASKS
    
    existing_configs = set()
    for filename in os.listdir(config_dir):
        if filename.endswith('.yml'):
            task_name = filename[:-4]  # Remove .yml suffix
            existing_configs.add(task_name)
    
    missing_tasks = []
    for task in TASKS:
        if task not in existing_configs:
            missing_tasks.append(task)
    
    print(f"Total tasks: {len(TASKS)}")
    print(f"Existing config files: {len(existing_configs)}")
    print(f"Missing config files: {len(missing_tasks)}")
    
    if missing_tasks:
        print("\nMissing configuration files:")
        for task in missing_tasks:
            print(f"  - {task}.yml")
    else:
        print("\nAll configuration files already exist!")
    
    return missing_tasks



def parse_pose_line(line: str) -> Tuple[List[float], List[float]]:
    """Parse a line containing pose information and return position and quaternion."""
    # Extract all numbers from the line
    numbers = re.findall(r'-?\d+\.\d+e?-?\d*', line)
    numbers = [float(n) for n in numbers]
    
    # First 3 numbers are position, last 4 are quaternion
    position = numbers[:3]
    quaternion = numbers[3:]
    return position, quaternion

def process_full_episode_data(lines: List[str], start_idx: int) -> Tuple[Dict[str, Dict], int]:
    """Process one complete episode's data and return data for both arms separately."""
    left_arm_data = {"target_poses": [], "constraint_poses": []}
    right_arm_data = {"target_poses": [], "constraint_poses": []}
    
    current_left_target = None
    current_right_target = None
    
    i = start_idx
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Check if we've reached the end of this episode
        if "simulate data episode" in line:
            if "success" not in line:
                print(f"    Skipping failed episode at line {i}")
                return None, i + 1  # Skip failed episodes
            break
            
        # Parse left arm target pose
        if "left arm target_pose" in line:
            pos, quat = parse_pose_line(line)
            current_left_target = pos + quat
            print(f"    Found left arm target pose: pos={pos}, quat={quat}")
            
        # Parse right arm target pose
        elif "right arm target_pose" in line:
            pos, quat = parse_pose_line(line)
            current_right_target = pos + quat
            print(f"    Found right arm target pose: pos={pos}, quat={quat}")
            
        # Parse left arm constraint pose
        elif "left arm constraint_pose" in line:
            constraint = [0, 0, 0, 0, 0, 0]  # Default values
            if "None" not in line:
                # Extract the constraint values if they exist
                numbers = re.findall(r'-?\d+\.?\d*', line)
                constraint = [float(n) for n in numbers]
            print(f"    Found left arm constraint pose: {constraint}")
            
            if current_left_target is not None:
                left_arm_data["target_poses"].append(current_left_target)
                left_arm_data["constraint_poses"].append(constraint)
                current_left_target = None
                
        # Parse right arm constraint pose
        elif "right arm constraint_pose" in line:
            constraint = [0, 0, 0, 0, 0, 0]  # Default values
            if "None" not in line:
                # Extract the constraint values if they exist
                numbers = re.findall(r'-?\d+\.?\d*', line)
                constraint = [float(n) for n in numbers]
            print(f"    Found right arm constraint pose: {constraint}")
            
            if current_right_target is not None:
                right_arm_data["target_poses"].append(current_right_target)
                right_arm_data["constraint_poses"].append(constraint)
                current_right_target = None
                
        i += 1
        
    result = {}
    if left_arm_data["target_poses"]:
        result["left"] = left_arm_data
    if right_arm_data["target_poses"]:
        result["right"] = right_arm_data
        
    return result, i + 1

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
        # Look for any arm target_pose to start processing an episode
        if "arm target_pose" in line:
            print(f"\nProcessing episode starting at line {i}:")
            episode_data, i = process_full_episode_data(output_lines, i)
            
            if episode_data is not None:
                # Process left arm data if exists
                if "left" in episode_data:
                    episode_name = f"left_arm_{episode_count['left']}"
                    print(f"  Successfully processed {episode_name} with {len(episode_data['left']['target_poses'])} poses")
                    all_episodes[episode_name] = episode_data["left"]
                    episode_count["left"] += 1
                
                # Process right arm data if exists
                if "right" in episode_data:
                    episode_name = f"right_arm_{episode_count['right']}"
                    print(f"  Successfully processed {episode_name} with {len(episode_data['right']['target_poses'])} poses")
                    all_episodes[episode_name] = episode_data["right"]
                    episode_count["right"] += 1
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
    """Generate configuration files for missing tasks only."""
    print(f"Checking configuration file status...")
    missing_tasks = check_missing_configs(output_dir)
    
    if not missing_tasks:
        print("All configuration files already exist, no need to generate!")
        return
    
    print(f"\nStarting to generate {len(missing_tasks)} missing configuration files...")
    
    success_count = 0
    for i, task in enumerate(missing_tasks, 1):
        print(f"\n[{i}/{len(missing_tasks)}] Generating configuration file: {task}")
        try:
            generate_config(task, output_dir)
            success_count += 1
            print(f"✓ Successfully generated {task}.yml")
        except Exception as e:
            print(f"✗ Failed to generate {task}.yml: {e}")
            continue
    
    print(f"\nConfiguration file generation completed! Successfully generated {success_count}/{len(missing_tasks)} configuration files")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Generate EAT check configuration files')
    parser.add_argument('--task', type=str, help='Specific task to process. If not provided, will check and generate missing configurations.')
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
