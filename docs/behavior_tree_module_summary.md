# Behavior Tree 模块总结

## 1. 什么是 Behavior Tree

Behavior Tree，简称 BT，中文通常叫“行为树”。

在 Nav2 里，行为树不是做 SLAM、不是做定位、也不是直接做路径搜索或控制，而是负责：

1. 决定导航任务的整体执行流程
2. 决定模块之间的调用顺序
3. 决定失败时如何恢复、何时重试、何时终止

可以把行为树理解为导航系统的“任务编排层”。

---

## 2. 本项目里 Behavior Tree 的作用

在本项目中，行为树控制的是完整的导航闭环：

```text
接收导航目标
   ->
规划路径
   ->
跟踪路径
   ->
失败时恢复
   ->
必要时重新规划
```

它的职责不是做单点算法，而是把这些模块组织起来：

- 全局规划
- 局部规划
- 清图
- 恢复动作
- 目标更新检查
- 重试次数控制

如果没有行为树，导航栈里的各个节点虽然都能工作，但不会形成一条完整、可恢复的任务执行逻辑。

---

## 3. 本项目的 Behavior Tree 实现方式

本项目使用的是 Nav2 默认的 `bt_navigator` 机制。

关键配置位于：

- `src/nav2_practice/params/nav2_params.yaml`

其中最关键的一项是：

```yaml
default_bt_xml_filename: "navigate_w_replanning_and_recovery.xml"
```

这说明：

- 本项目使用带“重规划 + 恢复”的默认导航行为树

实际对应到系统文件时，导航到单目标位姿常用的是：

- `/opt/ros/humble/share/nav2_bt_navigator/behavior_trees/navigate_to_pose_w_replanning_and_recovery.xml`

---

## 4. 启动链路

本项目中行为树模块的启动链路如下：

```text
ros2 launch nav2_practice navigation.launch.py
    ->
nav2_practice/launch/navigation.launch.py
    ->
nav2_bringup/launch/bringup_launch.py
    ->
nav2_bringup/launch/navigation_launch.py
    ->
bt_navigator
```

说明：

- 你的项目入口是 `navigation.launch.py`
- 真正加载和执行行为树的是 `bt_navigator`

---

## 5. 数据流

行为树的数据流更像“决策控制流”，而不是单纯传感器数据流：

```text
导航目标
   ->
行为树调度 ComputePath / FollowPath
   ->
失败时调度 ClearCostmap / Spin / Wait / BackUp
   ->
继续执行或最终失败
```

更具体一点：

### 输入

- 导航目标
- 规划成功/失败状态
- 控制成功/失败状态
- 是否更新目标
- 各动作节点的运行结果

### 输出

- 触发规划动作
- 触发控制动作
- 触发恢复动作
- 调用清图服务
- 决定是否继续重试

---

## 6. 本项目里 Behavior Tree 怎么用上

本项目里你不会直接手工运行某个 XML，而是：

1. 启动 `navigation.launch.py`
2. Nav2 启动 `bt_navigator`
3. 你在 RViz 发送 `Nav2 Goal`
4. 行为树开始接管整个导航任务

这说明行为树是“导航动作背后的执行逻辑”，不是一个孤立模块。

---

## 7. 本项目当前使用的关键配置

行为树相关参数位于：

- `src/nav2_practice/params/nav2_params.yaml`

关键配置包括：

```yaml
bt_navigator:
  ros__parameters:
    global_frame: map
    robot_base_frame: base_link
    odom_topic: /odom
    default_bt_xml_filename: "navigate_w_replanning_and_recovery.xml"
    bt_loop_duration: 10
    default_server_timeout: 20
    enable_groot_monitoring: True
    plugin_lib_names:
      ...
```

这说明：

- 行为树运行在 `bt_navigator` 节点中
- 使用 `map`、`base_link`、`/odom` 等导航基础信息
- 通过 `plugin_lib_names` 注册了一批可在 XML 中使用的 BT 节点

---

## 8. `plugin_lib_names` 的意义

`plugin_lib_names` 是本项目行为树配置里非常关键的一部分。

它决定了 XML 行为树里可以调用哪些动作节点、条件节点和控制节点。

当前项目中你已经启用了这些重要节点：

### 8.1 规划与控制相关

- `nav2_compute_path_to_pose_action_bt_node`
- `nav2_follow_path_action_bt_node`

### 8.2 恢复相关

- `nav2_back_up_action_bt_node`
- `nav2_spin_action_bt_node`
- `nav2_wait_action_bt_node`
- `nav2_clear_costmap_service_bt_node`
- `nav2_recovery_node_bt_node`

### 8.3 条件判断相关

- `nav2_is_stuck_condition_bt_node`
- `nav2_goal_reached_condition_bt_node`
- `nav2_goal_updated_condition_bt_node`
- `nav2_transform_available_condition_bt_node`
- `nav2_time_expired_condition_bt_node`
- `nav2_distance_traveled_condition_bt_node`
- `nav2_initial_pose_received_condition_bt_node`

### 8.4 控制结构相关

- `nav2_pipeline_sequence_bt_node`
- `nav2_round_robin_node_bt_node`
- `nav2_rate_controller_bt_node`
- `nav2_single_trigger_bt_node`

这些插件共同构成了“可被行为树调用的指令集”。

---

## 9. 本项目默认行为树结构

你当前系统默认使用的行为树核心结构，可以从系统 XML 里概括为：

```text
RecoveryNode (总重试)
  ->
PipelineSequence
  -> ComputePathToPose
  -> FollowPath

失败后：
ReactiveFallback
  -> GoalUpdated
  -> RoundRobin RecoveryActions
       -> Clear local/global costmap
       -> Spin
       -> Wait
       -> BackUp
```

这说明当前项目的导航逻辑是：

1. 先规划
2. 再跟踪
3. 失败后先尝试恢复
4. 恢复后再继续导航

---

## 10. 核心 XML 节点说明

下面只讲当前项目默认树里最关键的节点。

### 10.1 `RecoveryNode`

作用：

- 包裹一个主任务和一个恢复分支
- 当主任务失败时，进入恢复逻辑
- 在达到重试上限前继续尝试

在默认树里：

- 顶层 `NavigateRecovery` 是总恢复框架
- `ComputePathToPose` 和 `FollowPath` 自己也被单独包在恢复节点里

### 10.2 `PipelineSequence`

作用：

- 用流水线方式组织导航主流程

在默认树里：

- 一边周期性重规划
- 一边持续执行跟踪

这就是“重规划 + 跟随路径”能并行构成闭环的关键。

### 10.3 `RateController`

作用：

- 控制某个子树执行频率

在默认树里：

- 全局规划按 `1 Hz` 周期性重规划

### 10.4 `ComputePathToPose`

作用：

- 调用全局规划器生成路径

在默认树里：

- 使用 `planner_id="GridBased"`
- 对应你项目的 `NavfnPlanner`

### 10.5 `FollowPath`

作用：

- 调用局部规划 / 控制器跟随路径

在默认树里：

- 使用 `controller_id="FollowPath"`
- 对应你项目的 `DWBLocalPlanner`

### 10.6 `ClearEntireCostmap`

作用：

- 调用清图服务

默认树中有两种位置：

1. 规划或跟踪局部失败时的上下文清图
2. 总恢复分支里的恢复动作之一

### 10.7 `ReactiveFallback`

作用：

- 先检查是否有更高优先级条件成立
- 否则执行后面的恢复动作

在默认树中：

- 如果目标被更新，优先切回新的任务目标
- 否则继续恢复流程

### 10.8 `RoundRobin`

作用：

- 按轮转方式尝试恢复动作

当前默认顺序是：

1. 清 local/global costmap
2. `Spin`
3. `Wait`
4. `BackUp`

这意味着系统不会永远卡在同一种恢复动作上，而是逐步尝试不同策略。

---

## 11. 关键参数说明

下面只讲当前项目行为树层面最关键的参数。

### 11.1 `default_bt_xml_filename`

```yaml
default_bt_xml_filename: "navigate_w_replanning_and_recovery.xml"
```

作用：

- 指定默认导航任务使用哪棵行为树

这是行为树模块最核心的入口参数。

### 11.2 `bt_loop_duration`

```yaml
bt_loop_duration: 10
```

作用：

- 控制行为树主循环节拍相关配置

它影响行为树决策刷新节奏，但通常不是第一优先调参项。

### 11.3 `default_server_timeout`

```yaml
default_server_timeout: 20
```

作用：

- 行为树等待某些动作服务器响应的默认超时时间

如果动作长时间无响应，行为树可能据此进入失败处理逻辑。

### 11.4 Groot 监控参数

```yaml
enable_groot_monitoring: True
groot_zmq_publisher_port: 1666
groot_zmq_server_port: 1667
```

作用：

- 允许用 Groot 监控行为树执行状态

这对调试行为树非常有帮助，但不是导航功能本身的必要条件。

---

## 12. 本项目里行为树与其他模块的关系

行为树并不替代规划器、控制器或恢复模块，而是调度它们。

### 对全局规划

- 调用 `ComputePathToPose`

### 对局部规划

- 调用 `FollowPath`

### 对 Costmap

- 调用清图服务

### 对 Recoveries

- 决定何时执行 `Spin`、`Wait`、`BackUp`

所以行为树是这几个模块的上层控制逻辑。

---

## 13. 参数细化原则

行为树通常不是第一批需要改的配置。建议顺序是：

1. 先把 SLAM / AMCL / Costmap / 规划 / 控制都跑通
2. 再看恢复逻辑是否符合预期
3. 最后才考虑改行为树 XML

优先级较高的行为树相关配置通常是：

1. `default_bt_xml_filename`
2. `plugin_lib_names`
3. XML 中的恢复顺序
4. XML 中的重试次数
5. `default_server_timeout`

原因很直接：

- 如果底层模块本身不稳定，改行为树只是调度问题，解决不了根因

---

## 14. 如何判断 Behavior Tree 是否正常

在本项目中，可以从下面几项判断行为树状态。

### 14.1 能否正常触发完整导航流程

- 发送目标后能够先规划、再跟踪

### 14.2 失败后是否自动进入恢复

- 出现失败时，不应立即退出
- 应进入清图、旋转、等待或后退等恢复流程

### 14.3 恢复后是否继续重试

- 恢复后应能再次尝试规划或继续跟踪

### 14.4 目标更新时是否及时响应

- 如果目标变化，行为树应优先切换到新目标

---

## 15. 常见问题

### 15.1 导航没有恢复逻辑

优先检查：

- 是否真的加载了带 recovery 的 XML
- `plugin_lib_names` 是否包含恢复相关 BT 节点

### 15.2 清图或恢复动作不执行

常见原因：

- 行为树节点有，但对应服务或动作服务器没准备好
- `recoveries_server` 未正常启动

### 15.3 一直在恢复循环中出不来

常见原因：

- 根因在 costmap、局部规划、目标不可达等底层模块
- 行为树只是不断重复恢复流程

### 15.4 行为树配置改了但效果不对

常见原因：

- 修改了错误的 XML 文件
- 仍然加载的是默认系统树而不是自定义树

---

## 16. 本项目中的 Behavior Tree 与 Recoveries 区别

这两个模块强相关，但职责不同。

### Behavior Tree

- 决定导航流程怎么跑
- 决定何时规划、何时跟踪、何时恢复、何时重试

### Recoveries

- 提供恢复动作本身
- 例如 `Spin`、`BackUp`、`Wait`

简单说：

- 行为树是“调度大脑”
- Recoveries 是“失败后可调用的动作集合”

---

## 17. 本项目中的实际位置

如果后续要维护行为树模块，优先关注这些位置：

- `src/nav2_practice/params/nav2_params.yaml`
- `src/nav2_practice/launch/navigation.launch.py`

如果要继续深挖系统实现，再看：

- `/opt/ros/humble/share/nav2_bt_navigator/behavior_trees/navigate_to_pose_w_replanning_and_recovery.xml`
- `/opt/ros/humble/share/nav2_bringup/launch/navigation_launch.py`

---

## 18. 一句话总结

本项目里的 Behavior Tree 模块本质上是：由 `bt_navigator` 加载默认的“重规划 + 恢复”导航行为树，把全局规划、局部跟踪、清图、恢复动作和重试逻辑组织成一套可执行的任务流程，从而让整个导航系统不仅能走，还能在失败时自动尝试恢复。
