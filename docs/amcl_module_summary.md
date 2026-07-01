# AMCL 模块总结

## 1. 什么是 AMCL

AMCL 是 `Adaptive Monte Carlo Localization`，中文通常叫“自适应蒙特卡洛定位”。

AMCL 的任务不是建图，而是：

1. 在一张已有地图上估计机器人当前所在位置
2. 持续修正机器人在全局坐标系中的位姿

它适用于“地图已经存在”的场景，因此通常出现在 SLAM 建图之后的导航阶段。

---

## 2. 本项目里 AMCL 的作用

本项目的流程分成两个阶段：

1. 建图阶段：`slam_toolbox`
2. 导航阶段：已有地图 + `AMCL` + `Nav2`

AMCL 在本项目中的职责是：

- 加载已有地图后进行定位
- 结合激光雷达和里程计，估计机器人在 `map` 坐标系中的位置
- 发布 `/amcl_pose`
- 发布 `map -> odom` 变换
- 为 Nav2 的全局规划和局部规划提供当前位姿

如果没有 AMCL，导航模块不知道“机器人在地图里具体在哪”，即使地图加载成功，也无法正常规划路径。

---

## 3. 本项目的 AMCL 实现方式

本仓库没有自己实现 AMCL 算法，实际使用的是 ROS 2 Nav2 生态中的 `nav2_amcl`。

本项目做的事情主要是：

- 在导航启动时关闭 SLAM
- 加载地图文件
- 通过 Nav2 bringup 启动 `map_server` 和 `amcl`
- 在参数文件中配置 AMCL

因此仍然要区分两层：

### 3.1 项目内的接入代码

- `src/nav2_practice/launch/navigation.launch.py`
- `src/nav2_practice/params/nav2_params.yaml`
- `src/nav2_practice/README.md`

### 3.2 系统里真正执行定位的模块

- `/opt/ros/humble/share/nav2_bringup/launch/bringup_launch.py`
- `/opt/ros/humble/share/nav2_bringup/launch/localization_launch.py`
- `nav2_amcl` 包中的 `amcl` 节点

---

## 4. 启动链路

本项目中 AMCL 的启动链路如下：

```text
ros2 launch nav2_practice navigation.launch.py
    ->
nav2_practice/launch/navigation.launch.py
    ->
nav2_bringup/launch/bringup_launch.py
    ->
nav2_bringup/launch/localization_launch.py
    ->
map_server + amcl
```

这里最关键的是：

- `navigation.launch.py` 里传入了 `slam=False`
- 所以 Nav2 bringup 不会走建图链路
- 而是进入定位链路，启动 `map_server` 和 `amcl`

---

## 5. 数据流

AMCL 的数据流可以概括为：

```text
已有地图 + /scan + /odom + /tf
              ->
粒子滤波定位
              ->
/amcl_pose + map->odom
```

更具体一点：

### 输入

- 地图文件：`my_map.yaml` / `my_map.pgm`
- `/scan`：激光雷达
- `/odom`：里程计
- `/tf`：坐标变换

### 输出

- `/amcl_pose`：机器人在地图中的位姿估计
- `map -> odom`：定位修正后的全局变换
- 粒子云：用于 RViz 中观察定位收敛情况

---

## 6. 核心原理

AMCL 的本质是粒子滤波定位。

它维护很多个“机器人可能在这里”的假设，每个假设叫一个粒子。算法每次循环大致分三步：

### 6.1 运动预测

根据里程计信息预测机器人可能移动到了哪些位置，所有粒子按运动模型一起扩散。

### 6.2 传感器校正

把当前激光雷达观测与已有地图做比较。哪个粒子所在位置更符合激光观测，哪个粒子的权重就更高。

### 6.3 重采样

淘汰低权重粒子，保留高权重粒子。随着不断迭代，粒子会逐渐集中到机器人真实位置附近。

这就是为什么在 RViz 中使用 `2D Pose Estimate` 后，粒子云会先比较散，再逐渐收敛。

---

## 7. 本项目里 AMCL 怎么用上

本项目里 AMCL 的使用方式是标准的“先建图，再定位导航”流程：

1. 先用 `slam_toolbox` 建图
2. 保存地图到 `src/nav2_practice/maps/my_map.yaml`
3. 启动导航：`ros2 launch nav2_practice navigation.launch.py`
4. 在 RViz 中使用 `2D Pose Estimate` 指定机器人初始位姿
5. 等 AMCL 粒子云收敛
6. 再发送 `Nav2 Goal`

这说明 AMCL 不是单独运行的工具，而是导航前置定位模块。

---

## 8. 本项目当前使用的关键配置

本项目中的 AMCL 参数位于：

- `src/nav2_practice/params/nav2_params.yaml`

当前重点参数包括：

- `base_frame_id`
- `global_frame_id`
- `odom_frame_id`
- `scan_topic`
- `min_particles`
- `max_particles`
- `robot_model_type`
- `laser_model_type`
- `update_min_a`
- `update_min_d`
- `tf_broadcast`

这些参数决定了：

- AMCL 读哪路数据
- 坐标系怎么串起来
- 粒子滤波规模多大
- 激光匹配使用什么模型
- 什么时候触发更新

---

## 9. 关键参数说明

下面只总结当前项目里最关键的一批参数。

### 9.1 坐标系与话题

```yaml
base_frame_id: "base_footprint"
global_frame_id: "map"
odom_frame_id: "odom"
scan_topic: scan
tf_broadcast: true
transform_tolerance: 1.0
```

作用：

- `base_frame_id`：机器人底座坐标系
- `global_frame_id`：地图坐标系
- `odom_frame_id`：里程计坐标系
- `scan_topic`：订阅的激光话题
- `tf_broadcast`：是否发布 `map -> odom`

在本项目中，最核心的坐标关系是：

```text
map -> odom -> base_footprint
```

如果这组配置错误，常见现象是：

- 机器人和地图对不上
- `2D Pose Estimate` 后粒子不收敛
- `/amcl_pose` 波动很大

### 9.2 粒子数量

```yaml
min_particles: 500
max_particles: 2000
pf_err: 0.05
pf_z: 0.99
```

作用：

- 控制粒子滤波的规模
- 允许系统根据定位不确定性自适应调整粒子数量

影响：

- 粒子越多，定位通常更稳，但更耗计算资源
- 粒子越少，计算更轻，但收敛和鲁棒性可能变差

### 9.3 运动模型

```yaml
robot_model_type: "nav2_amcl::DifferentialMotionModel"
alpha1: 0.2
alpha2: 0.2
alpha3: 0.2
alpha4: 0.2
alpha5: 0.2
```

作用：

- 指定机器人是差速运动模型
- `alpha` 参数描述里程计运动噪声

影响：

- `alpha` 越大，越不信任里程计，粒子分布会更发散
- `alpha` 越小，越信任里程计，粒子会更集中

对当前 TurtleBot3 仿真来说，这组配置是比较常见的保守设置。

### 9.4 激光传感器模型

```yaml
laser_model_type: "likelihood_field"
laser_likelihood_max_dist: 2.0
laser_max_range: 100.0
laser_min_range: -1.0
max_beams: 60
sigma_hit: 0.2
z_hit: 0.5
z_rand: 0.5
z_short: 0.05
z_max: 0.05
lambda_short: 0.1
```

作用：

- 定义 AMCL 如何把当前激光数据与地图进行比较

重点理解：

- `laser_model_type: likelihood_field`：常见且稳定的激光定位模型
- `max_beams: 60`：每次定位时参与计算的激光束数量
- `sigma_hit`：命中模型的误差尺度
- `z_hit` / `z_rand` / `z_short` / `z_max`：不同观测类型的权重

这些参数决定了 AMCL 如何评价“某个粒子位置是否像真实位置”。

### 9.5 更新触发阈值

```yaml
update_min_a: 0.2
update_min_d: 0.25
resample_interval: 1
```

作用：

- `update_min_a`：机器人转过一定角度后再更积极更新
- `update_min_d`：机器人移动一定距离后再更积极更新
- `resample_interval`：多少次更新做一次重采样

影响：

- 阈值太小：定位更新更频繁，更灵敏，但更吃资源
- 阈值太大：定位更省资源，但会显得慢

### 9.6 束跳过参数

```yaml
do_beamskip: false
beam_skip_distance: 0.5
beam_skip_threshold: 0.3
beam_skip_error_threshold: 0.9
```

作用：

- 用于在部分激光束明显异常时，跳过部分不一致观测

当前项目中：

- `do_beamskip: false`

因此后面几个参数当前不生效。对静态仿真场景来说，这种设置是合理的，因为流程更简单、行为更稳定。

---

## 10. 参数细化原则

调 AMCL 参数时，不建议一上来动很多项。更合理的顺序是：

1. 先确认坐标系和话题正确
2. 再看粒子数是否够用
3. 再调整更新频率
4. 最后才动激光模型细节参数

在当前项目里，优先级最高的通常是：

1. `base_frame_id`
2. `global_frame_id`
3. `odom_frame_id`
4. `scan_topic`
5. `min_particles`
6. `max_particles`
7. `update_min_a`
8. `update_min_d`
9. `max_beams`
10. `sigma_hit`

---

## 11. 如何判断 AMCL 是否正常

在本项目里，判断 AMCL 是否正常可以看下面几项。

### 11.1 初始位姿后能否收敛

- 使用 `2D Pose Estimate` 后，粒子云应逐渐集中
- 机器人位姿应与地图中的真实位置基本对齐

### 11.2 位姿是否稳定

- `/amcl_pose` 不应频繁跳变
- 机器人静止时，位姿应基本稳定

### 11.3 运动时是否连续

- 机器人移动时，地图中的位置变化应平滑
- 不应出现明显瞬移

### 11.4 导航是否能从正确起点开始

- 发送 `Nav2 Goal` 后，全局路径起点应贴近机器人当前位置
- 如果起点明显错位，通常是 AMCL 或初始位姿有问题

---

## 12. 常见问题

### 12.1 `2D Pose Estimate` 后不收敛

优先检查：

- 地图是否正确加载
- 激光话题是否有数据
- 坐标系是否一致
- 初始位姿是否给得太离谱

### 12.2 粒子云一直很散

常见原因：

- 里程计误差较大
- 激光和地图匹配效果差
- 粒子数不足
- 初始位姿估计太远

### 12.3 机器人在地图里跳动

常见原因：

- TF 不稳定
- 激光模型参数不合适
- 地图与当前环境不一致

### 12.4 路径规划起点不对

常见原因：

- `/amcl_pose` 不准确
- `map -> odom` 变换不稳定
- AMCL 尚未收敛就开始发导航目标

---

## 13. 本项目中的 AMCL 与 SLAM 区别

这两个模块职责完全不同。

### SLAM

- 用于未知环境
- 不需要已有地图
- 一边建图，一边定位

### AMCL

- 用于已有地图场景
- 需要先加载地图
- 只做定位，不做建图

在本项目中：

- `slam_toolbox` 负责第一次建图
- `AMCL` 负责后续导航时的定位

---

## 14. 本项目中的实际位置

如果后续要维护 AMCL 相关内容，优先关注这些文件：

- `src/nav2_practice/launch/navigation.launch.py`
- `src/nav2_practice/params/nav2_params.yaml`
- `src/nav2_practice/README.md`

如果要继续深挖系统实现，再看：

- `/opt/ros/humble/share/nav2_bringup/launch/bringup_launch.py`
- `/opt/ros/humble/share/nav2_bringup/launch/localization_launch.py`

---

## 15. 一句话总结

本项目里的 AMCL 模块本质上是：在加载已有地图后，使用激光雷达、里程计和 TF 做粒子滤波定位，输出 `/amcl_pose` 和 `map -> odom`，为 Nav2 的路径规划和导航执行提供可靠的机器人当前位置。
