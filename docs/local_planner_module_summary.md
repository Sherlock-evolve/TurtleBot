# 局部规划模块总结

## 1. 什么是局部规划

局部规划是导航系统中负责“短时间内怎么走、怎么避障、怎么输出速度指令”的模块。

它解决的问题不是全局路线选择，而是：

1. 如何跟随全局路径
2. 如何根据当前局部环境实时调整运动
3. 如何输出机器人此刻应执行的速度指令

全局规划负责“从哪里到哪里走”，局部规划负责“这一小段怎么走”。

---

## 2. 本项目里局部规划的作用

在本项目中，局部规划位于下面这条链路中：

```text
AMCL 定位
  ->
全局路径 /plan
  ->
local costmap
  ->
局部规划
  ->
/cmd_vel
```

它的职责是：

- 接收全局路径
- 结合 local costmap 和当前机器人状态进行短时决策
- 避开近距离障碍物
- 输出连续的速度指令让机器人运动

如果没有局部规划，全局规划虽然可以给出一条整体路线，但机器人无法根据局部障碍和当前姿态稳定地跟踪这条路线。

---

## 3. 本项目的局部规划实现方式

本仓库没有自己实现局部规划算法，实际使用的是 Nav2 自带的 `controller_server` 和 DWB 控制器。

当前项目中的局部规划配置为：

- 节点：`controller_server`
- 控制器插件名：`FollowPath`
- 插件实现：`dwb_core::DWBLocalPlanner`

也就是说，这个项目当前实际使用的是 **DWB Local Planner**。

---

## 4. 启动链路

本项目中局部规划模块的启动链路如下：

```text
ros2 launch nav2_practice navigation.launch.py
    ->
nav2_practice/launch/navigation.launch.py
    ->
nav2_bringup/launch/bringup_launch.py
    ->
nav2_bringup/launch/navigation_launch.py
    ->
controller_server
```

说明：

- 你的项目入口仍然是 `navigation.launch.py`
- 真正启动局部规划模块的是 Nav2 bringup
- 实际运行的节点是 `controller_server`

---

## 5. 数据流

局部规划的数据流可以概括为：

```text
当前位姿 + 全局路径 + local costmap
                ->
          controller_server / DWB
                ->
              /cmd_vel
```

更具体一点：

### 输入

- 当前机器人位姿：来自 TF / AMCL / odom
- 全局路径：来自 `/plan`
- 局部代价地图：来自 `local_costmap`
- 机器人速度和运动状态

### 输出

- `/cmd_vel`：机器人速度指令

局部规划器会持续产生线速度和角速度，驱动机器人沿路径前进并规避局部障碍。

---

## 6. 本项目里局部规划怎么用上

本项目中的使用方式是标准 Nav2 流程：

1. 启动导航：`ros2 launch nav2_practice navigation.launch.py`
2. 使用 `2D Pose Estimate` 完成 AMCL 初始定位
3. 用 `Nav2 Goal` 设置目标点
4. 全局规划器生成 `/plan`
5. `controller_server` 中的 DWB 控制器根据 `/plan` 和 `local_costmap` 持续输出 `/cmd_vel`

README 中对应的现象是：

- 机器人能沿路径前进
- 遇到障碍物时会调整运动
- `/cmd_vel` 能持续输出速度指令

---

## 7. 本项目当前使用的关键配置

局部规划参数位于：

- `src/nav2_practice/params/nav2_params.yaml`

当前相关配置的核心部分是：

```yaml
controller_server:
  ros__parameters:
    controller_frequency: 10.0
    progress_checker_plugin: "progress_checker"
    goal_checker_plugins: ["general_goal_checker"]
    controller_plugins: ["FollowPath"]

    progress_checker:
      plugin: "nav2_controller::SimpleProgressChecker"

    general_goal_checker:
      plugin: "nav2_controller::SimpleGoalChecker"

    FollowPath:
      plugin: "dwb_core::DWBLocalPlanner"
```

这说明：

- 当前只有一个控制器插件
- 插件名叫 `FollowPath`
- 真正执行局部规划的是 `DWBLocalPlanner`

---

## 8. 核心原理

对当前项目来说，可以把局部规划理解为“围绕全局路径，在机器人当前可行动力学约束下，采样一批候选速度轨迹，再挑一个最合适的”。

### 8.1 速度采样

DWB 会在允许的线速度、角速度范围内采样一批候选控制量。

### 8.2 轨迹前向模拟

对每组候选速度，向前模拟一小段时间，形成一条短时轨迹。

### 8.3 轨迹打分

每条轨迹都会根据多个评价器打分，例如：

- 是否接近障碍物
- 是否贴合全局路径
- 是否朝向目标
- 是否会产生振荡

### 8.4 选最优轨迹

得分最优的轨迹会被选中，并转成当前时刻的 `/cmd_vel` 输出。

---

## 9. 当前项目里的局部规划器：DWB

你这个项目当前使用的是：

```yaml
plugin: "dwb_core::DWBLocalPlanner"
```

DWB 可以理解为 DWA 思想在 Nav2 中的一套常见实现。

它的特点是：

- 适合差速机器人
- 通过采样速度空间来选运动轨迹
- 能兼顾路径跟踪和局部避障
- 参数相对较多，但行为容易从配置上理解

对你当前的 TurtleBot3 室内仿真项目，这个选择是合理的，因为：

- 机器人运动模型简单
- 场景是典型二维室内导航
- DWB 是 Nav2 中较成熟的默认路线之一

---

## 10. 关键参数说明

下面只讲当前项目里最关键的局部规划参数。

### 10.1 控制频率

```yaml
controller_frequency: 10.0
```

作用：

- 控制器期望以每秒 10 次的频率输出控制决策

影响：

- 频率越高，响应越及时，但计算更密
- 频率越低，控制更省资源，但可能显得迟钝

### 10.2 速度阈值

```yaml
min_x_velocity_threshold: 0.001
min_y_velocity_threshold: 0.5
min_theta_velocity_threshold: 0.001
```

作用：

- 控制对极小速度值的处理阈值

对差速机器人来说：

- `min_y_velocity_threshold` 实际意义不大，因为机器人不走横移
- `x` 和 `theta` 阈值用于避免非常小的噪声速度

### 10.3 失败容忍

```yaml
failure_tolerance: 0.3
```

作用：

- 允许控制器在短时间内对某些失败情况保持一定容忍

这个值影响控制器在边界状态下的鲁棒性，但通常不是第一优先调参项。

### 10.4 进度检查器

```yaml
progress_checker_plugin: "progress_checker"

progress_checker:
  plugin: "nav2_controller::SimpleProgressChecker"
  required_movement_radius: 0.5
  movement_time_allowance: 10.0
```

作用：

- 判断机器人是否真的在往前推进

含义：

- 如果机器人在 `10` 秒内移动不到 `0.5 m`，系统可能认为它卡住了

这组参数直接影响“机器人是否被判定为没进展”。

### 10.5 目标检查器

```yaml
goal_checker_plugins: ["general_goal_checker"]

general_goal_checker:
  stateful: True
  plugin: "nav2_controller::SimpleGoalChecker"
  xy_goal_tolerance: 0.25
  yaw_goal_tolerance: 0.25
```

作用：

- 判断机器人是否已经到达目标

含义：

- 位置误差小于 `0.25 m`
- 朝向误差小于 `0.25 rad`

这组参数决定导航什么时候算完成。

### 10.6 控制器插件选择

```yaml
controller_plugins: ["FollowPath"]

FollowPath:
  plugin: "dwb_core::DWBLocalPlanner"
```

作用：

- 声明当前使用的局部控制器

当前项目只有一个控制器插件，就是 DWB。

---

## 11. DWB 参数说明

这部分是本项目局部规划最核心的参数组。

### 11.1 速度范围

```yaml
min_vel_x: 0.0
min_vel_y: 0.0
max_vel_x: 0.22
max_vel_y: 0.0
max_vel_theta: 1.0
min_speed_xy: 0.0
max_speed_xy: 0.22
min_speed_theta: 0.0
```

作用：

- 定义局部规划可采样的速度边界

对 TurtleBot3 来说：

- 只允许前进和旋转
- 不允许横移

这些参数决定 DWB 搜索空间有多大。

### 11.2 加减速度限制

```yaml
acc_lim_x: 2.5
acc_lim_y: 0.0
acc_lim_theta: 3.2
decel_lim_x: -2.5
decel_lim_y: 0.0
decel_lim_theta: -3.2
```

作用：

- 约束速度变化不能超过机器人可实现的动态能力

影响：

- 限制过紧：动作保守
- 限制过松：可能产生不现实或不稳定的控制指令

### 11.3 采样密度

```yaml
vx_samples: 20
vy_samples: 0
vtheta_samples: 40
sim_time: 2.0
linear_granularity: 0.05
angular_granularity: 0.025
```

作用：

- `vx_samples` / `vtheta_samples`：控制线速度和角速度采样数量
- `sim_time`：每条候选轨迹向前模拟多久
- `linear_granularity` / `angular_granularity`：模拟时的离散步长

影响：

- 采样越密，轨迹评估更充分，但更吃 CPU
- `sim_time` 越大，看得更远，但也更容易变慢

### 11.4 容差与停止判断

```yaml
transform_tolerance: 0.2
xy_goal_tolerance: 0.05
trans_stopped_velocity: 0.25
short_circuit_trajectory_evaluation: True
stateful: True
```

作用：

- `transform_tolerance`：TF 容差
- `xy_goal_tolerance`：DWB 内部跟踪过程中的位置容差
- `trans_stopped_velocity`：判断机器人是否基本停止
- `short_circuit_trajectory_evaluation`：允许提前终止低质量轨迹评估以提升效率

---

## 12. Critics 评分器说明

本项目中 DWB 使用了下面这些 critics：

```yaml
critics:
  ["RotateToGoal", "Oscillation", "BaseObstacle", "GoalAlign", "PathAlign", "PathDist", "GoalDist"]
```

可以把 critics 理解为“每条候选轨迹的打分规则”。

### 12.1 `BaseObstacle`

```yaml
BaseObstacle.scale: 0.02
```

作用：

- 惩罚靠近障碍物的轨迹

### 12.2 `PathAlign`

```yaml
PathAlign.scale: 32.0
PathAlign.forward_point_distance: 0.1
```

作用：

- 鼓励轨迹朝全局路径方向对齐

### 12.3 `GoalAlign`

```yaml
GoalAlign.scale: 24.0
GoalAlign.forward_point_distance: 0.1
```

作用：

- 鼓励轨迹朝目标方向对齐

### 12.4 `PathDist`

```yaml
PathDist.scale: 32.0
```

作用：

- 惩罚偏离全局路径过远的轨迹

### 12.5 `GoalDist`

```yaml
GoalDist.scale: 24.0
```

作用：

- 鼓励轨迹更接近目标

### 12.6 `RotateToGoal`

```yaml
RotateToGoal.scale: 32.0
RotateToGoal.slowing_factor: 5.0
RotateToGoal.lookahead_time: -1.0
```

作用：

- 在接近目标时帮助机器人调整朝向

### 12.7 `Oscillation`

作用：

- 抑制左右来回、小范围振荡等不稳定行为

---

## 13. 参数细化原则

局部规划是导航里最容易“看起来有反应，但又不好调”的部分。对这个项目，建议按下面顺序调：

1. 先确认全局路径正常
2. 再确认 `local_costmap` 合理
3. 再看速度限制是否匹配机器人
4. 最后再调 DWB critics 权重

优先级较高的参数通常是：

1. `max_vel_x`
2. `max_vel_theta`
3. `acc_lim_x`
4. `acc_lim_theta`
5. `vx_samples`
6. `vtheta_samples`
7. `sim_time`
8. `PathAlign.scale`
9. `PathDist.scale`
10. `BaseObstacle.scale`

原因很直接：

- 如果速度边界不合理，后面的轨迹评分再好也没用
- 如果 local costmap 错了，控制器看到的局部环境就是错的

---

## 14. 如何判断局部规划是否正常

在本项目中，可以从下面几项判断局部规划状态。

### 14.1 能否持续输出 `/cmd_vel`

- 发送导航目标后，应看到持续的速度指令输出

### 14.2 是否能跟住全局路径

- 机器人应大体沿着全局路径前进
- 不应严重偏离

### 14.3 是否能避开近距离障碍物

- 机器人遇到墙体或障碍时应减速、转向或绕行

### 14.4 是否存在抖动和振荡

- 不应频繁左右摇摆
- 不应原地反复小转动却不前进

### 14.5 到目标附近能否平稳收敛

- 接近目标时应减速
- 最终应停在容差范围内

---

## 15. 常见问题

### 15.1 有全局路径，但机器人不动

优先检查：

- `/cmd_vel` 是否有输出
- progress checker 是否判定机器人无进展
- local costmap 是否把机器人周围全判成不可走

### 15.2 机器人来回抖动

常见原因：

- critics 权重不平衡
- 速度限制与采样设置不合适
- local costmap 过于紧张

### 15.3 机器人总贴墙走

常见原因：

- `BaseObstacle.scale` 太低
- inflation 配置不足
- 路径跟踪权重大于避障权重太多

### 15.4 机器人走得太慢或太保守

常见原因：

- `max_vel_x` 偏小
- 加速度限制偏紧
- 避障惩罚过重

### 15.5 能规划但总到不了目标

常见原因：

- goal checker 容差太严
- 接近目标时姿态调整不稳定
- DWB 在目标附近选不出稳定轨迹

---

## 16. 本项目中的局部规划与全局规划区别

这两个模块职责不同。

### 全局规划

- 关注整体路线
- 输出 `/plan`
- 使用全局地图和 global costmap

### 局部规划

- 关注短时运动和实时避障
- 输出 `/cmd_vel`
- 使用 local costmap 和当前运动状态

在本项目中：

- `planner_server` 负责全局路径
- `controller_server` 负责局部轨迹和速度输出

---

## 17. 本项目中的实际位置

如果后续要维护这个模块，优先关注这些文件：

- `src/nav2_practice/launch/navigation.launch.py`
- `src/nav2_practice/params/nav2_params.yaml`
- `src/nav2_practice/README.md`

如果要继续深挖系统实现，再看：

- `/opt/ros/humble/share/nav2_bringup/launch/navigation_launch.py`
- `controller_server` 对应的 Nav2 控制模块

---

## 18. 一句话总结

本项目里的局部规划模块本质上是：在全局路径 `/plan` 和 `local_costmap` 的基础上，由 `controller_server` 中的 `DWBLocalPlanner` 采样候选速度轨迹、打分并选出当前最优控制量，持续输出 `/cmd_vel`，让 TurtleBot3 既能跟踪路径，又能进行近距离避障。
