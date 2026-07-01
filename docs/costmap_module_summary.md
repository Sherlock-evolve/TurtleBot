# Costmap 模块总结

## 1. 什么是 Costmap

Costmap 是导航系统中用来描述“哪里能走、哪里不能走、哪里尽量别贴近走”的地图表示。

它不是原始地图本身，而是：

1. 把静态地图、实时传感器和机器人尺寸综合起来
2. 转成规划器和控制器可直接使用的代价值地图

可以把 Costmap 理解为“导航用的工作地图”。

---

## 2. 本项目里 Costmap 的作用

在本项目中，Costmap 连接着定位、全局规划和局部规划：

```text
地图 / 传感器 / 机器人尺寸
          ->
       Costmap
          ->
全局规划 / 局部规划
```

它的职责是：

- 告诉全局规划器哪些区域可以走
- 告诉局部规划器机器人附近哪些区域危险
- 根据机器人半径和安全边界对障碍物做膨胀
- 结合实时激光数据更新可通行区域

如果没有 Costmap：

- 全局规划器无法知道障碍边界
- 局部规划器无法根据近距离环境避障

---

## 3. 本项目中的 Costmap 结构

本项目使用了两套 Costmap：

1. `global_costmap`
2. `local_costmap`

它们职责不同。

### 3.1 `global_costmap`

作用：

- 面向全局规划
- 站在地图尺度看整个导航环境
- 帮助 `planner_server` 生成从起点到终点的整体路径

### 3.2 `local_costmap`

作用：

- 面向局部规划
- 只关注机器人附近一小块区域
- 帮助 `controller_server` 和 DWB 做近距离避障与路径跟踪

---

## 4. 启动链路

本项目中的 Costmap 由 Nav2 导航链路启动：

```text
ros2 launch nav2_practice navigation.launch.py
    ->
nav2_practice/launch/navigation.launch.py
    ->
nav2_bringup/launch/bringup_launch.py
    ->
nav2_bringup/launch/navigation_launch.py
    ->
global_costmap + local_costmap
```

说明：

- Costmap 不是单独手动启动的
- 它作为 Nav2 导航栈的一部分和 `planner_server`、`controller_server` 一起运行

---

## 5. 数据流

Costmap 的数据流可以概括为：

```text
静态地图 + /scan + TF + 机器人尺寸
                ->
      global_costmap / local_costmap
                ->
     planner_server / controller_server
```

更具体一点：

### 输入

- 静态地图：来自 `map_server`
- 激光雷达：`/scan`
- 坐标变换：TF
- 机器人尺寸：例如 `robot_radius`

### 输出

- `/global_costmap/costmap`
- `/local_costmap/costmap`
- footprint 相关话题
- voxel 可视化相关话题

这些输出可以在 RViz 中直接显示。

---

## 6. 本项目里 Costmap 怎么用上

本项目中的使用方式如下：

1. 加载已有地图
2. AMCL 提供机器人当前位姿
3. `global_costmap` 结合静态地图和激光障碍信息服务于全局规划
4. `local_costmap` 以机器人为中心滚动更新，服务于局部规划
5. `planner_server` 用 `global_costmap`
6. `controller_server` / DWB 用 `local_costmap`

README 里的观察项也已经对应到了这两套地图：

- RViz 中能看到 `global costmap`
- RViz 中能看到 `local costmap`
- 路径不会紧贴障碍物

---

## 7. 本项目当前使用的关键配置

Costmap 参数位于：

- `src/nav2_practice/params/nav2_params.yaml`

### 7.1 `local_costmap`

当前核心配置包括：

- `global_frame: odom`
- `robot_base_frame: base_link`
- `rolling_window: true`
- `width: 3`
- `height: 3`
- `resolution: 0.05`
- `robot_radius: 0.22`
- `plugins: ["obstacle_layer", "voxel_layer", "inflation_layer"]`

### 7.2 `global_costmap`

当前核心配置包括：

- `global_frame: map`
- `robot_base_frame: base_link`
- `resolution: 0.05`
- `track_unknown_space: true`
- `plugins: ["static_layer", "obstacle_layer", "voxel_layer", "inflation_layer"]`
- `robot_radius: 0.22`

---

## 8. `global_costmap` 与 `local_costmap` 的区别

这是 Costmap 部分最重要的区分。

### 8.1 坐标系不同

`local_costmap`：

```yaml
global_frame: odom
```

`global_costmap`：

```yaml
global_frame: map
```

含义：

- `local_costmap` 更关注机器人附近的短时稳定运动，用 `odom` 更自然
- `global_costmap` 要服务全局路线规划，必须站在 `map` 坐标系看环境

### 8.2 范围不同

`local_costmap`：

```yaml
rolling_window: true
width: 3
height: 3
```

含义：

- 这是一个以机器人为中心滚动的小窗口
- 只关注附近约 `3m x 3m` 区域

`global_costmap`：

- 不使用滚动小窗
- 更关注整个导航环境

### 8.3 插件不同

`local_costmap` 当前没有显式启用 `static_layer` 插件，仅使用：

- `obstacle_layer`
- `voxel_layer`
- `inflation_layer`

`global_costmap` 使用：

- `static_layer`
- `obstacle_layer`
- `voxel_layer`
- `inflation_layer`

这意味着：

- 全局规划更依赖已有静态地图
- 局部规划更依赖机器人周围实时感知

---

## 9. 核心原理

Costmap 的核心思路是把不同来源的信息叠加成一张“代价地图”。

### 9.1 静态层

从已知地图中读取墙体、障碍和不可通行区域。

### 9.2 障碍层

根据实时传感器数据在地图上标记障碍物。

### 9.3 体素层

用于处理更立体的障碍表示。即便当前传感器是 2D LaserScan，VoxelLayer 也会以体素形式维护障碍信息。

### 9.4 膨胀层

对障碍物周围做安全扩张，避免规划出的路径紧贴墙体或障碍边缘。

---

## 10. 层插件说明

### 10.1 `StaticLayer`

```yaml
plugin: "nav2_costmap_2d::StaticLayer"
```

作用：

- 从静态地图中读取已知环境

本项目中：

- 只在 `global_costmap` 中显式启用

### 10.2 `ObstacleLayer`

```yaml
plugin: "nav2_costmap_2d::ObstacleLayer"
```

作用：

- 根据 `/scan` 把观测到的障碍物标记到 Costmap 中

关键配置：

- `observation_sources: scan`
- `topic: /scan`
- `marking: True`
- `clearing: True`

含义：

- `marking`：能把障碍加入地图
- `clearing`：能通过射线清除旧障碍

### 10.3 `VoxelLayer`

```yaml
plugin: "nav2_costmap_2d::VoxelLayer"
```

作用：

- 使用体素结构维护障碍信息

关键配置：

- `z_resolution: 0.05`
- `z_voxels: 16`
- `origin_z: 0.0`
- `publish_voxel_map: True`

当前项目虽然是二维导航，但仍然启用了 VoxelLayer，这会让障碍表达更完整，也能在 RViz 中看到 voxel 相关可视化。

### 10.4 `InflationLayer`

```yaml
plugin: "nav2_costmap_2d::InflationLayer"
```

作用：

- 在障碍物周围形成一圈逐渐衰减的高代价区域

这层非常关键，因为它让规划器倾向于“离障碍远一点”，而不是刚好擦边通过。

---

## 11. 关键参数说明

下面只讲当前项目里最关键的 Costmap 参数。

### 11.1 `robot_radius`

```yaml
robot_radius: 0.22
```

作用：

- 定义机器人在规划和避障中占据的安全半径

影响：

- 太小：路径可能贴障碍太近
- 太大：可通行区域会被压缩

### 11.2 `resolution`

```yaml
resolution: 0.05
```

作用：

- Costmap 每个栅格代表 `0.05 m`

影响：

- 越小越精细
- 越小也越吃内存和计算

### 11.3 `update_frequency`

`local_costmap`：

```yaml
update_frequency: 5.0
```

`global_costmap`：

```yaml
update_frequency: 1.0
```

含义：

- 局部代价地图更新更频繁，因为它直接服务实时避障
- 全局代价地图更新更慢，因为它更关注整体结构

### 11.4 `publish_frequency`

`local_costmap`：

```yaml
publish_frequency: 2.0
```

`global_costmap`：

```yaml
publish_frequency: 1.0
```

作用：

- 控制代价地图发布到话题上的频率

### 11.5 `rolling_window`

```yaml
rolling_window: true
```

作用：

- 仅对 `local_costmap` 生效
- 让局部地图始终围绕机器人移动

这正是局部地图适合短时避障的原因。

### 11.6 `width` / `height`

```yaml
width: 3
height: 3
```

作用：

- 定义局部代价地图窗口大小

当前项目是约 `3m x 3m`，这对 TurtleBot3 室内仿真属于较常见配置。

### 11.7 `track_unknown_space`

```yaml
track_unknown_space: true
```

作用：

- 让 `global_costmap` 追踪未知区域

影响：

- 对全局规划是否允许穿过未知区有直接关联
- 会和全局规划器的 `allow_unknown` 一起决定规划行为

### 11.8 `always_send_full_costmap`

```yaml
always_send_full_costmap: True
```

作用：

- 每次发布都发送完整 Costmap，而不是只发增量

优点：

- 可视化和调试更直接

代价：

- 消息量会更大一些

---

## 12. 膨胀参数说明

膨胀层是最影响“路径是否贴墙”的参数组。

### 12.1 `inflation_radius`

`local_costmap`：

```yaml
inflation_radius: 1.0
```

`global_costmap`：

```yaml
inflation_radius: 0.55
```

这是你当前配置里一个很值得注意的点：

- 局部地图的膨胀半径比全局地图更大

含义：

- 全局规划允许整体路径相对接近通道边缘
- 局部避障阶段会更保守，不愿太贴近障碍走

这对室内 TurtleBot3 导航是有实际意义的，因为：

- 全局路线可以先保证“能过去”
- 局部控制再负责“走得别太冒险”

### 12.2 `cost_scaling_factor`

```yaml
cost_scaling_factor: 3.0
```

作用：

- 控制代价随离障碍距离增加而衰减的速度

影响：

- 数值大：代价下降更快
- 数值小：高代价区域更宽、更平缓

---

## 13. 传感器范围参数说明

在 `ObstacleLayer` 和 `VoxelLayer` 中，你当前使用了这些典型参数：

```yaml
raytrace_max_range: 3.0
raytrace_min_range: 0.0
obstacle_max_range: 2.5
obstacle_min_range: 0.0
max_obstacle_height: 2.0
```

作用：

- `obstacle_max_range`：多远以内的障碍会被加入地图
- `raytrace_max_range`：多远以内可用来清理旧障碍
- `max_obstacle_height`：超过这个高度的不参与障碍建模

对当前二维仿真项目：

- 这些值属于比较标准的室内范围设置

---

## 14. 参数细化原则

调 Costmap 参数时，建议顺序如下：

1. 先确认坐标系和传感器话题正确
2. 再确认 `robot_radius` 是否合理
3. 再调 `inflation_radius`
4. 最后再调障碍层和体素层的范围参数

优先级较高的参数通常是：

1. `robot_radius`
2. `resolution`
3. `inflation_radius`
4. `cost_scaling_factor`
5. `obstacle_max_range`
6. `raytrace_max_range`
7. `width`
8. `height`

原因很直接：

- 机器人尺寸错了，整张 Costmap 的安全语义就错了
- 膨胀配置错了，路径会要么太保守，要么太贴墙

---

## 15. 如何判断 Costmap 是否正常

在本项目中，可以从下面几项判断 Costmap 状态。

### 15.1 RViz 中是否能看到地图层

- 能看到 `global_costmap`
- 能看到 `local_costmap`

### 15.2 障碍物附近是否有膨胀区域

- 墙边和障碍边缘应有明显高代价带

### 15.3 路径是否贴墙

- 如果路径总贴墙，通常膨胀不足或机器人半径偏小

### 15.4 局部地图是否跟着机器人移动

- `local_costmap` 应围绕机器人滚动

### 15.5 动态清除是否正常

- 障碍物移开后，局部地图应能逐步清除旧占据

---

## 16. 常见问题

### 16.1 路径总贴墙

常见原因：

- `inflation_radius` 太小
- `robot_radius` 太小
- `cost_scaling_factor` 不合适

### 16.2 机器人明明能过，但系统判定过不去

常见原因：

- `robot_radius` 设得过大
- 膨胀半径过大
- 局部地图窗口太小或障碍过于密集

### 16.3 局部规划总被障碍卡死

常见原因：

- `local_costmap` 过于保守
- 传感器障碍层持续标记但没正确清除
- DWB 与 Costmap 参数不匹配

### 16.4 全局规划能出路径，但局部走不过去

常见原因：

- `global_costmap` 比较宽松
- `local_costmap` 更保守

这在你当前配置里是有可能出现的，因为：

- `global_costmap.inflation_radius = 0.55`
- `local_costmap.inflation_radius = 1.0`

### 16.5 可视化看起来不对

常见原因：

- RViz 固定坐标系错误
- `map` / `odom` / `base_link` 关系有问题
- 使用者把全局和局部 Costmap 混看了

---

## 17. 本项目中的 Costmap 与规划模块关系

Costmap 不是终端控制器，也不是路径搜索器，它是规划模块共享的环境表达。

### 对全局规划

- `global_costmap` 提供整张地图上的可通行信息
- `planner_server` 依赖它生成 `/plan`

### 对局部规划

- `local_costmap` 提供机器人附近的局部障碍信息
- `controller_server` / DWB 依赖它输出 `/cmd_vel`

---

## 18. 本项目中的实际位置

如果后续要维护 Costmap，优先关注这些文件：

- `src/nav2_practice/params/nav2_params.yaml`
- `src/nav2_practice/launch/navigation.launch.py`
- `src/nav2_practice/rviz/nav2_view.rviz`
- `src/nav2_practice/README.md`

如果要继续深挖系统实现，再看：

- `/opt/ros/humble/share/nav2_bringup/launch/navigation_launch.py`
- Nav2 的 `nav2_costmap_2d` 相关模块

---

## 19. 一句话总结

本项目里的 Costmap 模块本质上是：把静态地图、激光雷达、机器人尺寸和 TF 叠加成 `global_costmap` 与 `local_costmap` 两套导航工作地图，分别服务于全局路径规划和局部实时避障，使 Nav2 知道哪里能走、哪里危险、应该与障碍保持多大安全距离。
