import os
import sys
import threading
import rclpy
from rclpy.node import Node
from ament_index_python.packages import get_package_share_directory

from ur3_llm_control.llm_planner import LLMPlanner
from ur3_llm_control.task_validator import PlanValidator
from ur3_llm_control.robot_skills import RobotSkills

try:
    if hasattr(sys.stdin, 'reconfigure'):
        sys.stdin.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

class SkillExecutorNode(Node):
    def __init__(self):
        super().__init__('skill_executor_node')
        
        pkg_share = get_package_share_directory('ur3_llm_control')
        student_cfg = os.path.join(pkg_share, 'config', 'student_config.yaml')
        scene_cfg = os.path.join(pkg_share, 'config', 'scene.yaml')

        self.planner = LLMPlanner(student_cfg)
        self.skills = RobotSkills(self, scene_cfg)

    def run_command(self, user_command: str):
        print("\n" + "="*50)
        print("USER COMMAND:")
        print(f"{user_command}\n")

        try:
            plan_json = self.planner.plan(user_command)
        except Exception as e:
            print(f"Lỗi khi gọi LLM: {e}")
            return

        is_valid, reason = PlanValidator.validate(plan_json)
        if not is_valid:
            print(f"TASK REJECTED: Kế hoạch không hợp lệ ({reason})")
            return

        print("LLM PLAN:")
        for step in plan_json.get('plan', []):
            skill = step.get('skill')
            if skill == 'home':
                print("home()")
            elif skill == 'pick':
                print(f"pick({step.get('object')})")
            elif skill == 'place':
                print(f"place({step.get('object')}, {step.get('zone')})")
        print("\nEXECUTION:")

        all_success = True
        for step in plan_json.get('plan', []):
            skill = step.get('skill')
            status = "FAILED"

            if skill == 'home':
                step_str = "home()"
                status = self.skills.home()
            elif skill == 'pick':
                obj = step.get('object')
                step_str = f"pick({obj})"
                status = self.skills.pick(obj)
            elif skill == 'place':
                obj = step.get('object')
                zone = step.get('zone')
                step_str = f"place({obj}, {zone})"
                status = self.skills.place(obj, zone)

            dots = "." * max(2, 35 - len(step_str))
            print(f"{step_str} {dots} {status}")

            if status != "SUCCESS":
                all_success = False
                break

        print()
        if all_success:
            print("TASK SUCCESS")
        else:
            print("TASK FAILED")
        print("="*50 + "\n")

def safe_input(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except UnicodeDecodeError:
        raw = sys.stdin.buffer.readline()
        return raw.decode('utf-8', errors='ignore').strip()

def main(args=None):
    rclpy.init(args=args)
    executor = SkillExecutorNode()

    # CHẠY LUỒNG SPIN NGẦM: Giúp Timer phát 3D sang RViz liên tục mà không bị nghẽn
    spin_thread = threading.Thread(target=rclpy.spin, args=(executor,), daemon=True)
    spin_thread.start()

    try:
        while rclpy.ok():
            cmd = safe_input("Nhập lệnh ngôn ngữ tự nhiên (hoặc 'exit' để thoát): ")
            if not cmd:
                continue
            if cmd.lower() in ['exit', 'quit']:
                break
            executor.run_command(cmd)
    except KeyboardInterrupt:
        pass
    finally:
        executor.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()