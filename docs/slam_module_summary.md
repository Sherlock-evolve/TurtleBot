# SLAM 模块总结

## 1. 什么是 SLAM

SLAM 是 `Simultaneous Localization and Mapping`，中文通常叫“同时定位与建图”。

对移动机器人来说，SLAM 解决两个问题：

1. 机器人当前在什么位置
2. 周围环境的地图长什么样

在未知环境中，机器人没有现成地图，单靠里程计也会逐渐漂移，所以需要把激光、里程计、坐标变换组合起来，一边估计自身位姿，一边构建地图。

---

## 2. 本项目里 SLAM 的作用

本项目的导航流程分成两个阶段：

1. 建图阶段：使用 `slam_toolbox`
2. 导航阶段：使用已有地图 + `AMCL` 定位 + `Nav2` 导航

也就是说，SLAM 只负责“第一次探索环境并生成地图”，不负责后续目标导航。

在本项目中，SLAM 的职责是：

- 订阅激光雷达数据 `/scan`
- 结合里程计 `/odom` 和 TF
- 生成二维栅格地图 `/map`
- 发布 `map -> odom` 变换
- 为后续保存地图、加载地图、AMCL 定位提供基础

---

## 3. 本项目的 SLAM 实现方式

本仓库没有自己实现一套 SLAM 算法，实际使用的是 ROS 2 官方生态中的 `slam_toolbox`。

本项目做的事情主要是：

- 写 launch 文件组织启动流程
- 提供参数文件
- 串起 Gazebo、TurtleBot3、RViz、SLAM 和 Nav2

因此要区分两层：

### 3.1 项目内的接入代码

- `src/nav2_practice/launch/slam.launch.py`
- `src/nav2_practice/params/nav2_params.yaml`
- `src/nav2_practice/README.md`

### 3.2 系统里真正执行 SLAM 的模块

- `/opt/ros/humble/share/nav2_bringup/launch/slam_launch.py`
- `/opt/ros/humble/share/slam_toolbox/launch/online_sync_launch.py`
- `/opt/ros/humble/lib/slam_toolbox/sync_slam_toolbox_node`

本项目的 `slam.launch.py` 会包含 `nav2_bringup` 的 `slam_launch.py`，后者再启动 `slam_toolbox` 的同步在线建图节点。

---

## 4. 启动链路

本项目的 SLAM 启动链路如下：

```text
ros2 launch nav2_practice slam.launch.py
    ->
nav2_practice/launch/slam.launch.py
    ->
nav2_bringup/launch/slam_launch.py
    ->
slam_toolbox/launch/online_sync_launch.py
    ->
sync_slam_toolbox_node
```

这条链路说明：

- 你仓库里的入口是 `slam.launch.py`
- 真正运行的建图节点是 `sync_slam_toolbox_node`

---

## 5. 数据流

本项目中的 SLAM 数据流可以概括为：

```text
/scan + /odom + /tf
        ->
扫描匹配 / 位姿估计 / 图优化
        ->
/map + map->odom
```

更具体一点：

### 输入

- `/scan`：激光雷达数据
- `/odom`：轮式里程计
- `/tf`：坐标变换，尤其是 `odom -> base_footprint` 或相关机器人底座坐标

### 输出

- `/map`：二维栅格地图
- `map -> odom`：全局坐标到里程计坐标的修正
- 机器人在地图中的估计位姿

---

## 6. 核心原理

`slam_toolbox` 在这个项目里的核心思路可以简化为以下几步：

### 6.1 扫描匹配

机器人获得当前一帧激光数据后，会尝试与历史扫描或当前地图进行对齐，估计当前位置相对上一时刻的变化。

### 6.2 里程计辅助

轮式里程计提供一个位姿变化初值。它通常短时间内平滑，但长时间会累积误差。

### 6.3 地图更新

根据估计出的机器人位姿，把激光观测投影到二维栅格地图中，更新占据和空闲区域。

### 6.4 回环检测

当机器人绕一圈重新回到之前走过的位置时，系统会尝试识别“回到了旧地点”。

### 6.5 图优化

在发现回环后，会对整段历史轨迹和地图一致性进行优化，减小累计误差。

---

## 7. 本项目当前使用的关键配置

本项目已经在 `src/nav2_practice/params/nav2_params.yaml` 中加入了 `slam_toolbox` 参数段。

当前关注的核心参数包括：

- `odom_frame`
- `map_frame`
- `base_frame`
- `scan_topic`
- `mode`
- `resolution`
- `minimum_travel_distance`
- `minimum_travel_heading`
- `map_update_interval`
- `do_loop_closing`

这些参数已经足够支撑当前 TurtleBot3 室内仿真建图。

---

## 8. 关键参数说明

下面只总结对当前项目最关键的一批参数。

### 8.1 坐标系和输入源

```yaml
odom_frame: odom
map_frame: map
base_frame: base_footprint
scan_topic: /scan
```

作用：

- 指定 SLAM 从哪个激光话题读数据
- 指定机器人底座坐标系
- 指定地图坐标系和里程计坐标系

如果这组配置错误，常见现象是：

- 地图出不来
- TF 报错
- 地图漂移严重

### 8.2 工作模式

```yaml
mode: mapping
```

作用：

- `mapping` 表示建图模式

在本项目建图阶段必须使用 `mapping`。后续导航阶段不是用它，而是切换到已有地图 + AMCL。

### 8.3 地图分辨率

```yaml
resolution: 0.05
```

作用：

- 地图每个栅格代表 `0.05 m`

影响：

- 分辨率越小，地图越细
- 计算和内存消耗也越大

### 8.4 更新触发阈值

```yaml
minimum_travel_distance: 0.3
minimum_travel_heading: 0.3
```

作用：

- 机器人至少移动一段距离或转过一定角度后，才更积极地处理新扫描并更新建图状态

影响：

- 阈值太小：更新更频繁，但更吃资源，也更容易受噪声影响
- 阈值太大：地图更稳，但更新会变慢

### 8.5 地图刷新频率

```yaml
map_update_interval: 2.0
```

作用：

- 控制地图发布和可视化更新的时间间隔

影响：

- 数值越小，RViz 中地图刷新越勤
- 数值越大，系统负担更低，但看起来更新更慢

### 8.6 回环闭合

```yaml
do_loop_closing: true
```

作用：

- 允许系统在机器人重新经过旧区域时进行回环检测和轨迹优化

影响：

- 开启后，地图整体一致性通常更好
- 关闭后，累计误差更难被修正

---

## 9. 参数细化原则

调 `slam_toolbox` 时，不建议一次改很多项。更合理的做法是：

1. 先明确目标：要更稳，还是要更灵敏
2. 每次只改少数几个高影响参数
3. 走同一条测试路线对比结果

当前项目里，最值得优先细化的是：

1. `minimum_travel_distance`
2. `minimum_travel_heading`
3. `map_update_interval`
4. `do_loop_closing`

更底层的匹配搜索空间、惩罚项、闭环响应阈值，通常放到后面再动。

---

## 10. 如何判断 SLAM 是否正常

建图时主要看下面几项：

### 10.1 地图是否持续生成

- RViz 中能看到 `/map`
- 机器人移动时地图逐步扩展

### 10.2 墙体和障碍物轮廓是否清晰

- 墙线是否基本平直
- 障碍物轮廓是否稳定

### 10.3 轨迹和地图是否一致

- 机器人走过一圈后，地图不应明显撕裂
- 回到起点附近时，不应出现大幅错位

### 10.4 系统是否实时

- RViz 中更新不过分卡顿
- 机器人移动时地图不会长时间滞后

---

## 11. 常见问题

### 11.1 看不到地图

优先检查：

- `slam.launch.py` 是否正常启动
- `/scan` 是否有数据
- TF 是否完整
- 坐标系参数是否正确

### 11.2 地图漂移或扭曲

常见原因：

- 机器人转向过快
- 里程计误差较大
- 更新阈值不合适
- 回环效果不好

### 11.3 地图更新太慢

常见原因：

- 更新阈值过大
- 地图更新时间间隔过长
- 机器性能不足

### 11.4 CPU 负载高

常见原因：

- 地图更新过于频繁
- 输入扫描过密
- 参数设置过于激进

---

## 12. 本项目中的 SLAM 与 AMCL 区别

这两个模块在流程里容易混淆，但职责不同：

### SLAM

- 用于未知环境
- 不需要已有地图
- 负责建图和定位

### AMCL

- 用于已有地图场景
- 需要先有地图文件
- 只负责定位，不负责建图

在本项目里：

- `slam_toolbox` 用于第一次建图
- `AMCL` 用于保存地图之后的导航定位

---

## 13. 本项目中的实际位置

如果后续要继续维护这个模块，优先关注这些文件：

- `src/nav2_practice/launch/slam.launch.py`
- `src/nav2_practice/params/nav2_params.yaml`
- `src/nav2_practice/README.md`

如果要继续深挖系统实现，再看这些系统文件：

- `/opt/ros/humble/share/nav2_bringup/launch/slam_launch.py`
- `/opt/ros/humble/share/slam_toolbox/launch/online_sync_launch.py`

---

## 14. 一句话总结

本项目里的 SLAM 模块本质上是：在 Gazebo 仿真中，使用 `slam_toolbox` 基于 `/scan`、`/odom` 和 TF 做 2D 激光建图，输出 `/map` 和 `map -> odom`，为后续保存地图、AMCL 定位和 Nav2 导航提供基础。
