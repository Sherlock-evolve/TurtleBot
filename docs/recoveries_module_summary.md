# Recoveries 模块总结

## 1. 什么是 Recoveries

Recoveries 可以理解为导航失败后的“自救动作模块”。

它解决的问题不是常规导航，而是：

1. 机器人卡住了怎么办
2. 局部避障失败了怎么办
3. 路径堵住了怎么办
4. 代价地图脏了怎么办

也就是说，Recoveries 负责在正常规划和控制走不通时，给系统一个恢复机会，而不是直接宣告导航失败。

---

## 2. 本项目里 Recoveries 的作用

在本项目中，恢复行为的目标是：

- 当路径规划失败时尝试清图和重新规划
- 当局部控制失败时尝试退出当前卡住状态
- 当机器人周围环境认知异常时尝试重新观察环境

README 里已经把这类动作概括为：

- `Spin`
- `BackUp`
- `Wait`
- `ClearCostmap`
- `Replan`

其中：

- `Spin`、`BackUp`、`Wait` 是具体恢复动作
- `ClearCostmap` 和 `Replan` 更偏系统级恢复步骤

---

## 3. 本项目的 Recoveries 实现方式

本项目里的恢复行为由两部分组成：

1. 行为树决定什么时候做恢复、按什么顺序做
2. `recoveries_server` 负责执行具体恢复动作

所以 Recoveries 不是单个节点，也不是单个 XML 文件，而是：

```text
行为树恢复逻辑
   +
recoveries_server 动作执行
```

---

## 4. 启动链路

本项目中恢复行为模块的启动链路如下：

```text
ros2 launch nav2_practice navigation.launch.py
    ->
nav2_practice/launch/navigation.launch.py
    ->
nav2_bringup/launch/bringup_launch.py
    ->
nav2_bringup/launch/navigation_launch.py
    ->
recoveries_server + bt_navigator
```

说明：

- `bt_navigator` 决定恢复策略
- `recoveries_server` 提供实际恢复动作能力

---

## 5. 数据流

Recoveries 的逻辑流可以概括为：

```text
规划失败 / 控制失败 / 卡住
            ->
        行为树判断
            ->
      恢复动作或清图重规划
            ->
继续导航 / 最终失败
```

更具体一点：

### 输入

- 来自规划器和控制器的失败状态
- local/global costmap
- 当前机器人位姿和 footprint

### 输出

- 恢复动作命令
- 清图服务调用
- 重试后的再次规划/控制

---

## 6. 本项目里 Recoveries 怎么用上

当前项目中，恢复行为不是你手动调用的，而是导航过程中由 Nav2 自动触发。

使用方式是：

1. 启动导航
2. 发送目标点
3. 如果规划或控制失败，行为树进入恢复分支
4. 调用清图、旋转、等待、后退等动作
5. 然后继续尝试规划和跟踪

这意味着恢复行为是导航闭环的一部分，而不是单独的“附加功能”。

---

## 7. 本项目当前使用的关键配置

恢复行为参数位于：

- `src/nav2_practice/params/nav2_params.yaml`

关键配置是：

```yaml
recoveries_server:
  ros__parameters:
    costmap_topic: local_costmap/costmap_raw
    footprint_topic: local_costmap/published_footprint
    cycle_frequency: 10.0
    recovery_plugins: ["spin", "backup", "wait"]
    spin:
      plugin: "nav2_recoveries/Spin"
    backup:
      plugin: "nav2_recoveries/BackUp"
    wait:
      plugin: "nav2_recoveries/Wait"
```

这说明：

- 当前项目启用了 3 个恢复动作插件
- 没有把 `ClearCostmap` 作为 `recoveries_server` 插件，而是通过行为树服务节点调用

---

## 8. 恢复动作列表

### 8.1 `Spin`

```yaml
spin:
  plugin: "nav2_recoveries/Spin"
```

作用：

- 原地旋转，重新观察周围环境

典型用途：

- 局部障碍信息不完整
- 机器人需要重新扫描周围

### 8.2 `BackUp`

```yaml
backup:
  plugin: "nav2_recoveries/BackUp"
```

作用：

- 后退一小段距离，脱离当前卡住区域

典型用途：

- 机器人离障碍太近
- 当前姿态下局部轨迹难以生成

### 8.3 `Wait`

```yaml
wait:
  plugin: "nav2_recoveries/Wait"
```

作用：

- 暂停等待一段时间

典型用途：

- 假设局部阻塞是暂时性的
- 等环境变化后再继续尝试

---

## 9. 关键参数说明

下面只讲当前项目里 Recoveries 最关键的参数。

### 9.1 `costmap_topic`

```yaml
costmap_topic: local_costmap/costmap_raw
```

作用：

- 恢复行为读取局部代价地图

恢复动作在做安全判断时需要知道机器人周围环境信息。

### 9.2 `footprint_topic`

```yaml
footprint_topic: local_costmap/published_footprint
```

作用：

- 提供机器人轮廓信息

这样恢复动作在后退、旋转时能结合机器人尺寸做碰撞相关判断。

### 9.3 `cycle_frequency`

```yaml
cycle_frequency: 10.0
```

作用：

- 恢复动作执行循环频率

影响：

- 数值越高，恢复动作状态更新越及时
- 对当前项目，`10 Hz` 是比较常见的配置

### 9.4 坐标系与 TF

```yaml
global_frame: odom
robot_base_frame: base_link
transform_timeout: 0.1
```

作用：

- 指定恢复动作执行时依赖的坐标系和 TF 等待时间

`global_frame: odom` 适合恢复行为，因为恢复动作主要关注短时局部运动。

### 9.5 旋转相关参数

```yaml
simulate_ahead_time: 2.0
max_rotational_vel: 1.0
min_rotational_vel: 0.4
rotational_acc_lim: 3.2
```

作用：

- 控制旋转恢复行为的模拟前瞻和角速度约束

这些参数会直接影响 `Spin` 动作执行时的激进程度和动态可行性。

---

## 10. 本项目里 `ClearCostmap` 的位置

这是一个很容易混淆的点。

在你当前项目中：

- `Spin` / `BackUp` / `Wait` 属于 `recoveries_server` 插件
- `ClearCostmap` 不在 `recovery_plugins` 列表里

`ClearCostmap` 是由行为树中的服务动作节点调用的，例如：

- `local_costmap/clear_entirely_local_costmap`
- `global_costmap/clear_entirely_global_costmap`

所以它属于恢复链路的一部分，但不是 `recoveries_server` 中注册的动作插件。

---

## 11. 参数细化原则

Recoveries 参数通常不是第一优先调的，建议顺序是：

1. 先确认定位、costmap、全局规划、局部规划本身正常
2. 只有当导航经常失败或卡住时，再细化恢复行为

优先级较高的参数通常是：

1. `recovery_plugins`
2. `cycle_frequency`
3. `simulate_ahead_time`
4. `max_rotational_vel`
5. `min_rotational_vel`
6. `rotational_acc_lim`

原因很直接：

- 如果基础导航没配好，Recoveries 只是在反复补救根因

---

## 12. 如何判断 Recoveries 是否正常

在本项目中，可以从下面几项判断恢复行为是否工作正常。

### 12.1 失败后是否会自动尝试恢复

- 路径失败后不是立即终止
- 局部控制失败后会尝试恢复动作

### 12.2 能否看到恢复动作现象

- 机器人原地旋转
- 机器人短距离后退
- 机器人短暂停顿后重新尝试

### 12.3 恢复后是否继续导航

- 清图或恢复动作后，系统应重新规划或重新跟踪

### 12.4 是否存在无效恢复循环

- 如果一直反复恢复但始终前进不了，说明根因可能不在恢复模块本身

---

## 13. 常见问题

### 13.1 一失败就直接退出，没有恢复

优先检查：

- 行为树是否加载了带 recovery 的默认 XML
- `recoveries_server` 是否正常启动
- `plugin_lib_names` 是否包含恢复相关 BT 节点

### 13.2 一直在原地转圈

常见原因：

- 局部 costmap 太保守
- DWB 很难找到可执行轨迹
- 恢复动作能执行，但根因没被解决

### 13.3 一直重复清图和重规划

常见原因：

- costmap 持续被错误障碍污染
- 目标本身不可达
- 全局或局部规划参数不合理

### 13.4 后退动作执行不稳定

常见原因：

- footprint / costmap 配置问题
- 动力学约束与机器人模型不匹配

---

## 14. 本项目中的 Recoveries 与行为树区别

这两个模块强相关，但边界不同。

### Recoveries

- 关注“执行什么恢复动作”
- 例如 `Spin`、`BackUp`、`Wait`
- 由 `recoveries_server` 提供具体动作能力

### Behavior Tree

- 关注“什么时候恢复、恢复顺序是什么、失败后如何重试”
- 由 `bt_navigator` 和 XML 行为树定义控制逻辑

简单说：

- 行为树负责决策
- Recoveries 负责执行

---

## 15. 本项目中的实际位置

如果后续要维护 Recoveries，优先关注这些位置：

- `src/nav2_practice/params/nav2_params.yaml`
- `src/nav2_practice/README.md`

如果要继续深挖系统实现，再看：

- `recoveries_server` 对应 Nav2 恢复行为模块
- 行为树 XML 中的恢复分支

---

## 16. 一句话总结

本项目里的 Recoveries 模块本质上是：当规划或控制失败时，由行为树触发恢复流程，并由 `recoveries_server` 执行 `Spin`、`BackUp`、`Wait` 等具体自救动作，配合清图和重规划，尽量让导航从失败状态重新回到可继续执行的轨道上。
