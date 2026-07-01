# 🤖 TurtleBot3 室内自主导航

> 基于 **ROS 2 Humble · Nav2 · SLAM Toolbox · Gazebo Classic** 的室内自主导航闭环。
>
> 从 **建图 → 保存地图 → 定位 → 路径规划 → 避障**，完整跑通移动机器人导航全链路。

**技术栈：** `ROS 2 Humble` · `Nav2` · `SLAM Toolbox` · `Gazebo Classic` · `TurtleBot3 Waffle` · `RViz2`

---

> 📖 本文档同时作为项目的**需求文档**与**运行说明**。
>
> 项目目标：在 Gazebo Classic 仿真环境中，使用 TurtleBot3、SLAM Toolbox 和 Nav2 完成一个室内自主导航闭环。

```text
启动仿真环境 ──► 加载 TurtleBot3 ──► 键盘遥控建图 ──► 保存地图
                                                              │
   到达目标点 ◄── Nav2 规划路径并避障 ◄── AMCL 定位 ◄── 加载已有地图
```

## 📑 目录

- [1. 项目目标](#1-项目目标)
- [2. 环境要求](#2-环境要求)
- [3. 项目结构](#3-项目结构)
- [4. 构建](#4-构建)
- [5. 启动仿真](#5-启动仿真)
- [6. 键盘控制](#6-键盘控制)
- [7. SLAM 建图](#7-slam-建图)
- [8. 保存地图](#8-保存地图)
- [9. 启动导航](#9-启动导航)
- [10. 功能需求与验收标准](#10-功能需求与验收标准)
- [11. 非功能需求](#11-非功能需求)
- [12. 项目验收清单](#12-项目验收清单)
- [13. 算法对应关系](#13-算法对应关系)
- [14. 常用检查命令](#14-常用检查命令)
- [15. 已处理的本机问题](#15-已处理的本机问题)
- [16. 最小可行版本与扩展方向](#16-最小可行版本与扩展方向)

## 1. 项目目标

> 🎯 **最终目标**：在 Gazebo 仿真环境中，让 TurtleBot3 从起点自主导航到指定目标点，并能够避开障碍物。

移动机器人导航链路：

```text
传感器采集
   ↓
数据预处理
   ↓
建图 SLAM / 加载已有地图
   ↓
定位 Localization
   ↓
代价地图 Costmap
   ↓
全局路径规划 Global Planning
   ↓
局部路径规划 / 避障 Local Planning
   ↓
运动控制 Control
   ↓
底盘执行
```

## 2. 环境要求

| 项目 | 要求 |
|---|---|
| 操作系统 | Ubuntu 22.04 |
| ROS 版本 | ROS 2 Humble |
| 仿真器 | Gazebo Classic |
| 机器人模型 | TurtleBot3 Waffle（默认） |
| 导航框架 | Nav2 |
| 建图工具 | SLAM Toolbox |
| 可视化工具 | RViz2 |

## 3. 项目结构

```text
TurtleBot/
├── launch/
│   ├── bringup_sim.launch.py   # 启动 Gazebo + TurtleBot3
│   ├── slam.launch.py          # 启动 SLAM Toolbox 建图
│   └── navigation.launch.py    # 启动 Nav2 导航
├── maps/
│   ├── my_map.pgm              # 栅格地图
│   └── my_map.yaml             # 地图元数据
├── params/
│   └── nav2_params.yaml        # Nav2 参数配置
├── rviz/
│   └── nav2_view.rviz          # RViz2 预设配置
├── docs/                       # 各模块原理小结
├── CMakeLists.txt
├── package.xml
└── README.md
```

## 4. 构建

```bash
cd ~/Desktop/TurtleBot
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
```

> 💡 如果在受限沙箱或只读 home 目录里运行 ROS 2，先指定可写日志目录：

```bash
export ROS_LOG_DIR=/tmp/ros_logs
```

## 5. 启动仿真

**终端 1：**

```bash
cd ~/Desktop/TurtleBot
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch nav2_practice bringup_sim.launch.py
```

**验收：**

```bash
ros2 topic list | grep -E '(/scan|/odom|/tf)'
ros2 topic echo --once /scan
ros2 topic echo --once /odom
```

**期望结果：**

- Gazebo 中能看到 TurtleBot3。
- `/scan`、`/odom`、`/tf` 正常发布。
- `robot_state_publisher` 正常发布机器人 TF。

## 6. 键盘控制

**终端 2：**

```bash
source /opt/ros/humble/setup.bash
source ~/Desktop/TurtleBot/install/setup.bash
ros2 run turtlebot3_teleop teleop_keyboard
```

**验收：**

- 机器人能前进、后退、左转、右转。
- `ros2 topic echo /cmd_vel` 能看到速度指令。
- `ros2 topic echo /odom` 能看到里程计变化。
- `ros2 topic echo /scan` 能看到激光雷达数据。

## 7. SLAM 建图

**终端 3：**

```bash
source /opt/ros/humble/setup.bash
source ~/Desktop/TurtleBot/install/setup.bash
ros2 launch nav2_practice slam.launch.py
```

使用终端 2 慢速遥控机器人沿墙边和障碍物周围移动。RViz 中应看到 `/map` 逐渐生成。

**SLAM 输入输出：**

```text
输入：                输出：
  /scan                 /map
  /odom                 map -> odom 坐标变换
  /tf                   机器人位姿
```

**验收：**

- RViz2 中能够显示 `/map`。
- 地图能随着机器人运动逐渐生成。
- 墙壁和障碍物轮廓清晰。
- 机器人轨迹与地图基本一致。

## 8. 保存地图

建图完成后执行：

```bash
source /opt/ros/humble/setup.bash
source ~/Desktop/TurtleBot/install/setup.bash
ros2 run nav2_map_server map_saver_cli -f ~/Desktop/TurtleBot/maps/my_map
```

**验收：**

```bash
ls -lh ~/Desktop/TurtleBot/maps/my_map.*
```

期望文件：

```text
my_map.pgm
my_map.yaml
```

## 9. 启动导航

> ⚠️ 先停止 SLAM，保持 Gazebo 仿真运行。键盘控制终端也先停止，避免继续手动发布 `/cmd_vel`。

**新终端：**

```bash
source /opt/ros/humble/setup.bash
source ~/Desktop/TurtleBot/install/setup.bash
ros2 launch nav2_practice navigation.launch.py
```

> ⚠️ 如果要显式指定地图，**命令必须是一整行**：

```bash
ros2 launch nav2_practice navigation.launch.py map:=$HOME/Desktop/TurtleBot/maps/my_map.yaml
```

**RViz 操作顺序：**

1. 固定坐标系使用 `map`。
2. 用 `2D Pose Estimate` 设置机器人初始位姿。
3. 等 AMCL 粒子云收敛到机器人附近。
4. 用 `Nav2 Goal` 设置目标点。
5. 观察全局路径、local costmap、global costmap 和 `/cmd_vel` 输出。

**验收：**

```bash
ros2 topic echo --once /amcl_pose
ros2 topic echo --once /plan
ros2 topic echo --once /cmd_vel
```

## 10. 功能需求与验收标准

### 10.1 仿真环境启动

**目标：** 启动 Gazebo Classic 并加载 TurtleBot3。

**涉及模块：**

| 模块 | 作用 |
|---|---|
| Gazebo | 仿真环境 |
| TurtleBot3 Gazebo | 机器人模型和仿真世界 |
| robot_state_publisher | 发布机器人 TF |
| joint_state_publisher | 发布关节状态 |

**验收标准：**

- Gazebo 中能够看到 TurtleBot3。
- RViz2 中能够显示机器人模型。
- `/scan`、`/odom`、`/tf` 正常发布。

### 10.2 手动控制机器人

**目标：** 通过键盘控制 TurtleBot3 移动，为建图做准备。

**关键话题：**

| 话题 | 含义 |
|---|---|
| `/cmd_vel` | 控制机器人速度 |
| `/odom` | 机器人里程计 |
| `/scan` | 激光雷达数据 |
| `/tf` | 坐标变换 |

**验收标准：**

- 机器人能够前进、后退、左转、右转。
- `/cmd_vel`、`/odom`、`/scan` 有有效数据。

### 10.3 SLAM 建图

**目标：** 机器人在未知环境中边运动边建立二维栅格地图。

**主要算法：**

| 算法 / 模块 | 作用 |
|---|---|
| SLAM Toolbox | ROS 2 中常用 2D 激光 SLAM |
| 激光扫描匹配 | 根据相邻激光帧估计机器人运动 |
| 里程计融合 | 利用轮速里程计辅助估计位姿 |
| 图优化 | 优化机器人轨迹和地图一致性 |

**验收标准：**

- RViz2 能显示 `/map`。
- 墙壁和障碍物轮廓清晰。
- 地图保存后能重新加载。

### 10.4 AMCL 定位

**目标：** 在已有地图上估计机器人在 `map` 坐标系中的位置。

**SLAM 与 AMCL 区别：**

| 对比项 | SLAM | AMCL |
|---|---|---|
| 是否建图 | 建图 | 不建图 |
| 是否需要已有地图 | 不需要 | 需要 |
| 主要作用 | 建图 + 定位 | 定位 |
| 常用场景 | 第一次探索环境 | 已有地图后导航 |

**验收标准：**

- AMCL 节点正常运行。
- RViz2 中能看到粒子云。
- 使用 `2D Pose Estimate` 后，机器人位姿能与地图对齐。
- 机器人移动时定位结果基本稳定。

### 10.5 全局路径规划

**目标：** 在 RViz2 中设置目标点后，Nav2 能规划从当前位置到目标点的全局路径。

**常见算法：**

| 算法 | 特点 |
|---|---|
| Dijkstra | 能找到最短路径，但搜索范围较大 |
| A\* | 加入启发函数，搜索效率更高 |
| Theta\* | 路径更平滑，不完全受栅格方向限制 |
| Hybrid A\* | 适合有转弯半径约束的车辆 |
| Smac Planner | Nav2 中常用规划器，支持多种规划模式 |
| NavFn Planner | 经典全局规划器，基于 Dijkstra / A\* |

**验收标准：**

- RViz2 中能够设置 `Nav2 Goal`。
- 系统能够生成全局路径。
- 全局路径能够绕开墙壁和障碍物。

### 10.6 局部规划与避障

**目标：** 机器人沿全局路径运动，并根据局部障碍物实时调整。

**常见算法：**

| 算法 | 作用 |
|---|---|
| DWA | 动态窗口法，通过速度采样选择最优轨迹 |
| DWB | Nav2 中常用局部控制器，思想类似 DWA |
| TEB | 时间弹性带算法，路径平滑但调参复杂 |
| Regulated Pure Pursuit | 增强版路径跟踪控制器，简单稳定 |
| MPPI | 基于采样优化的模型预测控制器 |
| MPC | 模型预测控制，适合复杂约束控制 |

**验收标准：**

- 机器人能沿路径前进。
- 遇到障碍物时能够调整运动。
- 不会明显撞墙。
- `/cmd_vel` 能持续输出速度指令。

### 10.7 代价地图 Costmap

**目标：** 根据静态地图和实时传感器数据生成可用于规划的代价地图。

**主要层：**

| 层 | 作用 |
|---|---|
| Static Layer | 使用已有静态地图 |
| Obstacle Layer | 根据实时雷达或深度相机添加障碍物 |
| Inflation Layer | 对障碍物进行安全膨胀 |
| Voxel Layer | 处理 3D 点云障碍物 |

**关键参数：**

| 参数 | 作用 |
|---|---|
| `robot_radius` | 机器人半径 |
| `footprint` | 机器人轮廓 |
| `inflation_radius` | 障碍物膨胀半径 |
| `cost_scaling_factor` | 膨胀代价衰减速度 |
| `obstacle_range` | 障碍物检测范围 |
| `raytrace_range` | 清除障碍物的射线范围 |

**验收标准：**

- RViz2 中能够显示 global costmap。
- RViz2 中能够显示 local costmap。
- 障碍物附近存在膨胀区域。
- 机器人规划路径不会紧贴障碍物。

### 10.8 恢复行为

**目标：** 导航失败、机器人卡住或路径被堵住时，系统能够执行恢复行为。

**常见恢复行为：**

| 行为 | 作用 |
|---|---|
| Spin | 原地旋转，重新观察环境 |
| BackUp | 后退，退出卡住区域 |
| Wait | 等待动态障碍物离开 |
| ClearCostmap | 清除错误代价地图 |
| Replan | 重新规划路径 |

**验收标准：**

- 路径失败后能重新规划。
- 局部规划失败后能执行恢复行为。
- 清除代价地图后能继续导航。

## 11. 非功能需求

| 指标 | 要求 |
|---|---|
| 地图分辨率 | 0.05 m |
| 简单地图导航成功率 | 大于 80% |
| 路径规划时间 | 一般小于数秒 |
| 定位效果 | 仿真中基本与地图对齐 |
| 避障能力 | 能避开静态障碍物 |

**RViz2 应能显示：**

```text
/map               global costmap
/scan              local costmap
/odom              global path
/tf                robot footprint
                   particle cloud
```

**可维护性要求：**

- 清晰的 launch 文件。
- 独立的地图目录。
- 独立的参数文件。
- README 使用说明。
- 可复现实验步骤。

## 12. 项目验收清单

- [ ] 能启动 Gazebo 仿真环境
- [ ] 能加载 TurtleBot3
- [ ] 能用键盘控制机器人
- [ ] 能查看 `/scan`、`/odom`、`/tf`
- [ ] 能启动 SLAM Toolbox 建图
- [ ] 能保存地图
- [ ] 能重新加载地图
- [ ] 能启动 AMCL 定位
- [ ] 能在 RViz2 中设置初始位姿
- [ ] 能在 RViz2 中设置导航目标点
- [ ] 能看到全局路径
- [ ] 能看到 local costmap 和 global costmap
- [ ] 机器人能自动到达目标点
- [ ] 机器人能避开墙壁或障碍物
- [ ] 能解释 SLAM、AMCL、A\*、DWB 分别在哪一步使用

## 13. 算法对应关系

| 阶段 | 主要解决问题 | 常见算法 / 模块 |
|---|---|---|
| 传感器采集 | 获取环境信息 | LiDAR、Camera、IMU、Odometry |
| 数据预处理 | 降噪、降采样、坐标统一 | 滤波、Voxel Grid、TF、时间同步 |
| 建图 | 建立环境地图 | SLAM Toolbox、Cartographer、GMapping |
| 定位 | 确定机器人在哪里 | AMCL、EKF、UKF、ICP、NDT |
| 代价地图 | 判断哪里能走 | Static Layer、Obstacle Layer、Inflation Layer |
| 全局规划 | 从起点到目标点找路 | Dijkstra、A\*、Theta\*、Hybrid A\* |
| 局部规划 | 近距离避障并生成速度 | DWA、DWB、TEB、RPP、MPPI |
| 路径跟踪 | 沿着路径运动 | Pure Pursuit、Stanley、LQR、MPC |
| 底盘控制 | 控制电机执行 | PID、速度闭环、位置闭环 |
| 恢复行为 | 卡住后自救 | Spin、BackUp、ClearCostmap、Replan |

**本项目当前实际使用：**

- 🗺️ **SLAM Toolbox**：建图。
- 📍 **AMCL**：已有地图后的定位。
- 🧭 **NavFn Planner**：全局规划，配置在 `params/nav2_params.yaml` 的 `planner_server`。
- 🚗 **DWB**：局部规划和避障控制，配置在 `controller_server.FollowPath`。
- 🧱 **Costmap**：`global_costmap` 使用静态地图和实时障碍物，`local_costmap` 用于近距离避障。

## 14. 常用检查命令

```bash
ros2 topic list
ros2 topic hz /scan
ros2 topic echo --once /tf
ros2 lifecycle nodes
ros2 lifecycle get /map_server
ros2 lifecycle get /amcl
ros2 action list | grep navigate
```

## 15. 已处理的本机问题

### 15.1 Gazebo spawn 超时

**现象：**

```text
Service /spawn_entity unavailable
```

**处理：**

- `bringup_sim.launch.py` 禁用 Gazebo 在线模型库。
- 延迟 5 秒后再 spawn TurtleBot3。
- 将 spawn 等待时间设置为 120 秒。

### 15.2 Gazebo GUI 刷 `Missing model.config`

**原因：** 某些系统包导出了过宽的 Gazebo 模型路径，Gazebo GUI 会把大量 ROS 包当成模型扫描。

**处理：**

- `bringup_sim.launch.py` 直接启动 `gzserver` 和 `gzclient`。
- 显式设置干净的 `GAZEBO_MODEL_PATH`、`GAZEBO_PLUGIN_PATH`、`GAZEBO_RESOURCE_PATH`。

### 15.3 RViz 插件加载失败

**现象：**

```text
nav2_rviz_plugins/Selector failed to load
nav2_rviz_plugins/Docking failed to load
```

**原因：** 官方 RViz 配置引用了当前 Humble 安装中不存在的 Nav2 面板。

**处理：**

- `rviz/nav2_view.rviz` 删除 `Selector` 和 `Docking` 面板。
- 将 `/scan` 的过滤队列调大到 `100`。

### 15.4 导航时看不到地图

**原因：** 常见是 `map:=...` 参数被换行拆断。推荐直接使用默认地图：

```bash
ros2 launch nav2_practice navigation.launch.py
```

如果显式传地图，**必须保持一整行**：

```bash
ros2 launch nav2_practice navigation.launch.py map:=$HOME/Desktop/TurtleBot/maps/my_map.yaml
```

## 16. 最小可行版本与扩展方向

**最小可行版本：**

```text
TurtleBot3 + Gazebo + SLAM Toolbox + Nav2
```

**最小闭环：**

```text
建图 ──► 保存地图 ──► 加载地图 ──► 定位 ──► 导航
```

**完成后应能理解：**

| 问题 | 对应模块 |
|---|---|
| 地图怎么来的 | SLAM |
| 机器人怎么知道自己在哪 | AMCL |
| 路径怎么规划出来 | A\* / Dijkstra |
| 怎么避障 | DWB / DWA / RPP |
| 怎么控制运动 | `/cmd_vel` + 底盘控制 |

**后续可扩展：**

- 🌍 更换不同地图环境。
- 🎛️ 调整 Nav2 参数。
- ⚖️ 比较 DWB、RPP、MPPI 控制器效果。
- 🚧 添加动态障碍物。
- 🦾 尝试真实机器人部署。
- 📷 使用深度相机或 3D 雷达进行导航。

---

Built with ROS 2 Humble · Nav2 · SLAM Toolbox · Gazebo Classic.
