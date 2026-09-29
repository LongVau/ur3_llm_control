import rclpy
from rclpy.node import Node
from gazebo_msgs.srv import SpawnEntity
from geometry_msgs.msg import Pose

class SceneSpawner(Node):
    def __init__(self):
        super().__init__('scene_spawner')
        self.client = self.create_client(SpawnEntity, '/spawn_entity')
        self.client.wait_for_service()
        self.spawn_all()

    def make_table_sdf(self, name, size_x, size_y, size_z):
        """Mặt bàn có COLLISION cứng để đỡ hộp dynamic"""
        return f"""<?xml version="1.0"?>
<sdf version="1.6">
  <model name="{name}">
    <static>true</static>
    <link name="link">
      <collision name="collision">
        <geometry><box><size>{size_x} {size_y} {size_z}</size></box></geometry>
      </collision>
      <visual name="visual">
        <geometry><box><size>{size_x} {size_y} {size_z}</size></box></geometry>
        <material>
          <ambient>0.75 0.75 0.75 1</ambient>
          <diffuse>0.75 0.75 0.75 1</diffuse>
        </material>
      </visual>
    </link>
  </model>
</sdf>"""

    def make_dynamic_cube_sdf(self, name, r, g, b):
        """Khối cube DYNAMIC có trọng lượng 50g và va chạm thật"""
        return f"""<?xml version="1.0"?>
<sdf version="1.6">
  <model name="{name}">
    <static>false</static>
    <link name="link">
      <inertial>
        <mass>0.05</mass>
        <inertia>
          <ixx>0.00001</ixx><ixy>0</ixy><ixz>0</ixz>
          <iyy>0.00001</iyy><iyz>0</iyz><izz>0.00001</izz>
        </inertia>
      </inertial>
      <collision name="collision">
        <geometry><box><size>0.04 0.04 0.04</size></box></geometry>
        <surface>
          <friction>
            <ode><mu>1.0</mu><mu2>1.0</mu2></ode>
          </friction>
        </surface>
      </collision>
      <visual name="visual">
        <geometry><box><size>0.04 0.04 0.04</size></box></geometry>
        <material>
          <ambient>{r} {g} {b} 1</ambient>
          <diffuse>{r} {g} {b} 1</diffuse>
        </material>
      </visual>
    </link>
  </model>
</sdf>"""

    def make_zone_sdf(self, name, r, g, b):
        return f"""<?xml version="1.0"?>
<sdf version="1.6">
  <model name="{name}">
    <static>true</static>
    <link name="link">
      <visual name="visual">
        <geometry><box><size>0.12 0.12 0.002</size></box></geometry>
        <material>
          <ambient>{r} {g} {b} 1</ambient>
          <diffuse>{r} {g} {b} 1</diffuse>
        </material>
      </visual>
    </link>
  </model>
</sdf>"""

    def send_spawn_request(self, name, sdf_xml, x, y, z):
        req = SpawnEntity.Request()
        req.name = name
        req.xml = sdf_xml
        req.initial_pose = Pose()
        req.initial_pose.position.x = float(x)
        req.initial_pose.position.y = float(y)
        req.initial_pose.position.z = float(z)

        future = self.client.call_async(req)
        rclpy.spin_until_future_complete(self, future)

    def spawn_all(self):
        self.get_logger().info("Đang nạp hệ thống Bàn Đôi và 3 Hộp ở cự ly thoáng đãng...")

        # 1. Bàn trước mở rộng ra một chút: tâm x=0.33, dài 40cm
        front_table = self.make_table_sdf("table_front", 0.40, 0.85, 0.05)
        self.send_spawn_request("table_front", front_table, 0.33, 0.0, 0.025)

        # 2. Bàn sau giữ nguyên
        back_table = self.make_table_sdf("table_back", 0.30, 0.80, 0.05)
        self.send_spawn_request("table_back", back_table, -0.25, 0.0, 0.025)

        # 3. 03 Vùng Zone A, B, C
        self.send_spawn_request("zone_a", self.make_zone_sdf("zone_a", 0.35, 0.35, 0.35), -0.20, 0.25, 0.052)
        self.send_spawn_request("zone_b", self.make_zone_sdf("zone_b", 0.45, 0.45, 0.45), -0.25, 0.00, 0.052)
        self.send_spawn_request("zone_c", self.make_zone_sdf("zone_c", 0.55, 0.55, 0.55), -0.20, -0.25, 0.052)

        # 4. 03 Khối Cube ở tọa độ mới (ĐẨY RA XA HƠN 8CM):
        red_cube = self.make_dynamic_cube_sdf("red_cube", 1.0, 0.0, 0.0)
        yellow_cube = self.make_dynamic_cube_sdf("yellow_cube", 1.0, 1.0, 0.0)
        blue_cube = self.make_dynamic_cube_sdf("blue_cube", 0.0, 0.2, 1.0)

        self.send_spawn_request("red_cube", red_cube, 0.33, -0.22, 0.075)
        self.send_spawn_request("yellow_cube", yellow_cube, 0.36, 0.00, 0.075)
        self.send_spawn_request("blue_cube", blue_cube, 0.33, 0.22, 0.075)

        self.get_logger().info("=== NẠP SCENE MỚI THÀNH CÔNG ===")

def main():
    rclpy.init()
    node = SceneSpawner()
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()