
# Hướng Dẫn Cài Đặt & Chạy Gói `ur3_llm_control`

Package ROS 2 điều khiển robot UR3 trong mô phỏng Gazebo bằng ngôn ngữ tự nhiên thông qua **9Router (LLM)** và **MoveIt 2**.

---

## 1. Cài đặt các gói phụ thuộc hệ thống (Prerequisites)

Chạy các lệnh sau trong terminal Ubuntu 22.04 / WSL2 để cài MoveIt 2 và các driver điều khiển robot:

```bash
sudo apt update
sudo apt install -y ros-humble-ur-description ros-humble-ur-moveit-config \
  ros-humble-gazebo-ros-pkgs ros-humble-gazebo-ros2-control ros-humble-moveit
```

---

## 2. Tải và Cài đặt gói mô phỏng `ur_simulation_gazebo`

Trên máy mới chưa có gói mô phỏng của hãng Universal Robots, tải mã nguồn và cài các thư viện phụ thuộc:

```bash
# 1. Tải repo mô phỏng vào thư mục src
cd ~/ros2_ws/src
git clone -b humble https://github.com/UniversalRobots/Universal_Robots_ROS2_Gazebo_Simulation.git

# 2. Cập nhật và cài đặt các dependency còn thiếu
cd ~/ros2_ws
rosdep update
rosdep install --ignore-src --from-paths src -y
```

---

## 3. Khởi động 9Router (Trên máy Windows)

1. Mở cửa sổ **PowerShell trên Windows** (không mở trong WSL), chạy lệnh:
   ```powershell
   npx 9router
   ```
2. Mở trình duyệt web truy cập vào: [http://localhost:20128](http://localhost:20128)
3. Vào mục **Providers** $\rightarrow$ Thêm API Key của bạn (Groq / Gemini / OpenAI) và chọn model khả dụng (ví dụ: `openai/gpt-oss-20b` hoặc `gemini-1.5-flash`).

---

## 4. Biên dịch Workspace

Biên dịch cả gói mô phỏng robot `ur_simulation_gazebo` và gói điều khiển `ur3_llm_control`:

```bash
cd ~/ros2_ws
colcon build --packages-select ur_simulation_gazebo ur3_llm_control
source install/setup.bash
```

---

## 5. Hướng dẫn Chạy (Mở 3 Terminal theo thứ tự)

### Terminal 1: Khởi chạy Gazebo + UR3 + MoveIt 2
```bash
source ~/ros2_ws/install/setup.bash
ros2 launch ur_simulation_gazebo ur_sim_moveit.launch.py ur_type:=ur3 launch_rviz:=true
```
*(Chờ khoảng 10-15 giây để giao diện Gazebo và RViz tải hoàn tất).*

---

### Terminal 2: Nạp Bàn thao tác & 3 Khối hộp vào Gazebo
```bash
source ~/ros2_ws/install/setup.bash
ros2 run ur3_llm_control spawn_scene
```

---

### Terminal 3: Chạy Node điều khiển bằng LLM
```bash
source ~/ros2_ws/install/setup.bash

# Trỏ kết nối sang 9Router đang chạy trên Windows
export ROUTER9_BASE_URL="http://$(ip route show | grep -i default | awk '{print $3}'):20128/v1"

# Khởi chạy node điều khiển
ros2 run ur3_llm_control skill_executor
```

---

## 6. Các câu lệnh Test mẫu

Sau khi chạy Terminal 3, gõ lệnh vào dấu nhắc:

* **Mức cơ bản (Thao tác 1 vật):**
  ```text
  Please put the red cube in zone B
  ```
  *(hoặc: `Put the blue cube in zone A`)*

* **Mức nâng cao (Sắp xếp theo MSSV):**
  ```text
  according to mssv
  ```
  *(hoặc: `Arrange all objects according to my student ID`)*

* **Thoát chương trình:** Gõ `exit` hoặc `quit`.
```
