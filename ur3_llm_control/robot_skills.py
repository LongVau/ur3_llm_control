import time
import yaml
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from geometry_msgs.msg import PoseStamped, Pose
from shape_msgs.msg import SolidPrimitive
from visualization_msgs.msg import Marker, MarkerArray
from moveit_msgs.action import MoveGroup
from moveit_msgs.srv import ApplyPlanningScene
from moveit_msgs.msg import (
    Constraints, PositionConstraint, OrientationConstraint, 
    JointConstraint, CollisionObject, AttachedCollisionObject,
    PlanningScene
)

class RobotSkills:
    def __init__(self, node: Node, scene_cfg_path: str):
        self.node = node
        with open(scene_cfg_path, 'r', encoding='utf-8') as f:
            self.scene = yaml.safe_load(f)['scene']

        # 1. Publisher vẽ Marker 3D liên tục lên RViz
        self._marker_pub = self.node.create_publisher(MarkerArray, '/rviz_scene_markers', 10)

        # 2. Service MoveIt Planning Scene
        self._apply_scene_client = self.node.create_client(ApplyPlanningScene, '/apply_planning_scene')
        self._planning_scene_pub = self.node.create_publisher(
            AttachedCollisionObject, '/attached_collision_object', 10
        )

        # 3. Action Client MoveGroup
        self._action_client = ActionClient(self.node, MoveGroup, 'move_action')
        self.node.get_logger().info("Đang kết nối tới MoveIt 2 Action Server...")
        self._action_client.wait_for_server()
        self.node.get_logger().info("MoveIt 2 đã sẵn sàng!")

        self.object_poses = dict(self.scene['objects'])
        self.held_object = None

        # Nạp bàn cản cứng ở độ cao an toàn (z=0.035) để ép khuỷu tay vểnh lên trời
        time.sleep(1.0)
        self._init_planning_scene()

        # Timer phát liên tục 3D Marker lên RViz
        self._marker_timer = self.node.create_timer(0.5, self._publish_rviz_markers)
        self.home()

    def _wait_for_future(self, future, timeout=30.0):
        start_t = time.time()
        while not future.done():
            if time.time() - start_t > timeout:
                return None
            time.sleep(0.02)
        return future.result()

    def _publish_rviz_markers(self):
        ma = MarkerArray()
        m_id = 0
        now = self.node.get_clock().now().to_msg()

        def make_marker(shape, x, y, z, sx, sy, sz, r, g, b, text=None):
            nonlocal m_id
            m = Marker()
            m.header.frame_id = "world"
            m.header.stamp = now
            m.ns = "scene"
            m.id = m_id
            m_id += 1
            m.type = shape
            m.action = Marker.ADD
            m.pose.position.x = float(x)
            m.pose.position.y = float(y)
            m.pose.position.z = float(z)
            m.pose.orientation.w = 1.0
            m.scale.x = float(sx)
            m.scale.y = float(sy)
            m.scale.z = float(sz)
            m.color.r = float(r)
            m.color.g = float(g)
            m.color.b = float(b)
            m.color.a = 1.0
            if text:
                m.text = text
            return m

        # 2 Mặt Bàn
        ma.markers.append(make_marker(Marker.CUBE, 0.30, 0.0, 0.025, 0.35, 0.80, 0.05, 0.75, 0.75, 0.75))
        ma.markers.append(make_marker(Marker.CUBE, -0.25, 0.0, 0.025, 0.30, 0.80, 0.05, 0.65, 0.65, 0.65))

        # 3 Vùng Zone A, B, C và chữ nổi
        for z_name, pos in self.scene['zones'].items():
            ma.markers.append(make_marker(Marker.CUBE, pos['x'], pos['y'], 0.051, 0.12, 0.12, 0.002, 0.4, 0.4, 0.4))
            label = z_name.replace("zone_", "Zone ").upper()
            ma.markers.append(make_marker(Marker.TEXT_VIEW_FACING, pos['x'], pos['y'], 0.12, 0.06, 0.06, 0.06, 1.0, 1.0, 1.0, label))

        # 3 Khối hộp (Đỏ, Vàng, Xanh)
        colors = {"red_cube": (1.0, 0.0, 0.0), "yellow_cube": (1.0, 1.0, 0.0), "blue_cube": (0.0, 0.3, 1.0)}
        for name, pos in self.object_poses.items():
            c = colors.get(name, (1.0, 1.0, 1.0))
            ma.markers.append(make_marker(Marker.CUBE, pos['x'], pos['y'], pos['z'], 0.04, 0.04, 0.04, c[0], c[1], c[2]))

        self._marker_pub.publish(ma)

    def _init_planning_scene(self):
        """Khai báo bàn ảo MoveIt ở z=0.035 để bảo vệ khuỷu tay mà không làm dính đáy hộp"""
        scene_msg = PlanningScene()
        scene_msg.is_diff = True

        def make_co(obj_id, sx, sy, sz, x, y, z):
            co = CollisionObject()
            co.header.frame_id = "world"
            co.id = obj_id
            box = SolidPrimitive()
            box.type = SolidPrimitive.BOX
            box.dimensions = [float(sx), float(sy), float(sz)]
            p = Pose()
            p.position.x = float(x)
            p.position.y = float(y)
            p.position.z = float(z)
            p.orientation.w = 1.0
            co.primitives.append(box)
            co.primitive_poses.append(p)
            co.operation = CollisionObject.ADD
            return co

        floor = make_co("floor_plane", 2.0, 2.0, 0.05, 0.0, 0.0, -0.025)
        # Mặt bàn ảo cao 3.5cm (đỉnh ở z = 0.035, thấp hơn đáy hộp 1.5cm -> TUYỆT ĐỐI KHÔNG DÍNH HỘP)
        table_front = make_co("table_front", 0.35, 0.80, 0.035, 0.30, 0.0, 0.0175)
        table_back = make_co("table_back", 0.30, 0.80, 0.035, -0.25, 0.0, 0.0175)
        scene_msg.world.collision_objects.extend([floor, table_front, table_back])

        req = ApplyPlanningScene.Request()
        req.scene = scene_msg
        future = self._apply_scene_client.call_async(req)
        self._wait_for_future(future, timeout=5.0)

    def _attach_object_in_moveit(self, obj_name: str):
        """Khóa vật thể chuẩn xác vào mặt bích tool0 (Cách đầu bích đúng 2cm)"""
        aco = AttachedCollisionObject()
        aco.link_name = "tool0"
        aco.object.header.frame_id = "tool0"
        aco.object.id = obj_name

        box = SolidPrimitive()
        box.type = SolidPrimitive.BOX
        box.dimensions = [0.04, 0.04, 0.04]

        box_pose = Pose()
        box_pose.position.z = 0.02
        box_pose.orientation.w = 1.0

        aco.object.primitives.append(box)
        aco.object.primitive_poses.append(box_pose)
        aco.object.operation = CollisionObject.ADD
        aco.touch_links = ["tool0", "wrist_3_link", "flange"]
        self._planning_scene_pub.publish(aco)

    def _detach_object_in_moveit(self, obj_name: str, zone_pos: dict):
        """Tháo vật thể khỏi tool0"""
        aco = AttachedCollisionObject()
        aco.link_name = "tool0"
        aco.object.id = obj_name
        aco.object.operation = CollisionObject.REMOVE
        self._planning_scene_pub.publish(aco)

    def _send_pose_goal(self, x: float, y: float, z: float) -> str:
        goal_msg = MoveGroup.Goal()
        goal_msg.request.group_name = "ur_manipulator"
        goal_msg.request.num_planning_attempts = 15
        goal_msg.request.allowed_planning_time = 7.0
        goal_msg.request.max_velocity_scaling_factor = 0.25
        goal_msg.request.max_acceleration_scaling_factor = 0.25
        goal_msg.request.start_state.is_diff = True

        c = Constraints()

        pc = PositionConstraint()
        pc.header.frame_id = "world"
        pc.link_name = "tool0"
        pc.weight = 1.0

        primitive = SolidPrimitive()
        primitive.type = SolidPrimitive.SPHERE
        primitive.dimensions = [0.03]

        target_pose = PoseStamped()
        target_pose.header.frame_id = "world"
        target_pose.pose.position.x = float(x)
        target_pose.pose.position.y = float(y)
        target_pose.pose.position.z = float(z)

        pc.constraint_region.primitives.append(primitive)
        pc.constraint_region.primitive_poses.append(target_pose.pose)
        c.position_constraints.append(pc)

        oc = OrientationConstraint()
        oc.header.frame_id = "world"
        oc.link_name = "tool0"
        oc.orientation.x = 1.0
        oc.orientation.y = 0.0
        oc.orientation.z = 0.0
        oc.orientation.w = 0.0
        # Giữ đầu gắp chúc vuông góc xuống mặt bàn (chống cắm xiên)
        oc.absolute_x_axis_tolerance = 0.4
        oc.absolute_y_axis_tolerance = 0.4
        # MỞ LẠI TRỤC Z: Cho phép tự do xoay quanh trục thẳng đứng để luôn tìm thấy đường đi 100%
        oc.absolute_z_axis_tolerance = 3.14
        oc.weight = 0.5
        c.orientation_constraints.append(oc)

        goal_msg.request.goal_constraints.append(c)

        send_goal_future = self._action_client.send_goal_async(goal_msg)
        goal_handle = self._wait_for_future(send_goal_future, timeout=10.0)

        if not goal_handle or not goal_handle.accepted:
            return "PLANNING_FAILED"

        res_future = goal_handle.get_result_async()
        res = self._wait_for_future(res_future, timeout=25.0)

        if not res or res.result.error_code.val != 1:
            return "FAILED"
        return "SUCCESS"

    def home(self) -> str:
        goal_msg = MoveGroup.Goal()
        goal_msg.request.group_name = "ur_manipulator"
        goal_msg.request.start_state.is_diff = True
        goal_msg.request.num_planning_attempts = 15
        goal_msg.request.allowed_planning_time = 7.0
        goal_msg.request.max_velocity_scaling_factor = 0.25
        goal_msg.request.max_acceleration_scaling_factor = 0.25

        c = Constraints()
        joint_names = [
            "shoulder_pan_joint", "shoulder_lift_joint", "elbow_joint",
            "wrist_1_joint", "wrist_2_joint", "wrist_3_joint"
        ]
        for name, val in zip(joint_names, self.scene['home_joints']):
            jc = JointConstraint()
            jc.joint_name = name
            jc.position = float(val)
            jc.tolerance_above = 0.15
            jc.tolerance_below = 0.15
            jc.weight = 1.0
            c.joint_constraints.append(jc)

        goal_msg.request.goal_constraints.append(c)

        send_goal_future = self._action_client.send_goal_async(goal_msg)
        goal_handle = self._wait_for_future(send_goal_future, timeout=10.0)

        if not goal_handle or not goal_handle.accepted:
            return "PLANNING_FAILED"

        res_future = goal_handle.get_result_async()
        res = self._wait_for_future(res_future, timeout=25.0)

        if not res or res.result.error_code.val != 1:
            return "FAILED"
        return "SUCCESS"

    def open_gripper(self):
        time.sleep(0.5)

    def close_gripper(self):
        time.sleep(0.5)

    def pick(self, obj_name: str) -> str:
        if obj_name not in self.object_poses: return "INVALID_OBJECT"
        pos = self.object_poses[obj_name]

        # 1. Tiếp cận từ trên cao
        if self._send_pose_goal(pos['x'], pos['y'], pos['z'] + self.scene['z_offset_approach']) != "SUCCESS": return "FAILED"
        self.open_gripper()
        
        # 2. Hạ sát mặt bích xuống đỉnh khối hộp
        if self._send_pose_goal(pos['x'], pos['y'], pos['z'] + self.scene['z_offset_grasp']) != "SUCCESS": return "FAILED"
        self.close_gripper()
        self._attach_object_in_moveit(obj_name)
        self.held_object = obj_name

        # 3. Nhấc vật lên cao an toàn trên không
        return self._send_pose_goal(pos['x'], pos['y'], pos['z'] + self.scene['z_offset_approach'])

    def place(self, obj_name: str, zone_name: str) -> str:
        if zone_name not in self.scene['zones']: return "FAILED"
        zone_pos = self.scene['zones'][zone_name]

        # 1. Bay đến trên đỉnh Zone đích
        if self._send_pose_goal(zone_pos['x'], zone_pos['y'], zone_pos['z'] + self.scene['z_offset_approach']) != "SUCCESS": return "FAILED"
        
        # 2. Hạ sát xuống đặt vật
        if self._send_pose_goal(zone_pos['x'], zone_pos['y'], zone_pos['z'] + self.scene['z_offset_grasp']) != "SUCCESS": return "FAILED"

        self.object_poses[obj_name] = zone_pos
        self._detach_object_in_moveit(obj_name, zone_pos)
        self.open_gripper()
        self.held_object = None

        # 3. Rút thẳng lên cao an toàn trước khi về Home
        return self._send_pose_goal(zone_pos['x'], zone_pos['y'], zone_pos['z'] + self.scene['z_offset_approach'])