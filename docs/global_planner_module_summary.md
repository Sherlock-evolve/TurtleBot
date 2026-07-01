# 全局规划模块总结

## 1. 什么是全局规划

全局规划是导航系统中负责“从当前位置到目标点，找到一条可行路径”的模块。

它解决的问题不是如何精确控制机器人运动，也不是如何实时避障，而是：

1. 从全局地图角度判断哪里能走
2. 从起点到终点生成一条整体路径

通常这条路径是给局部规划器或控制器跟随的参考线。

---

## 2. 本项目里全局规划的作用

在本项目中，全局规划处于下面这条链路中：

```text
已有地图
  ->
AMCL 定位
  ->
global costmap
  ->
全局规划
  ->
局部规划 / 跟踪控制
```

它的职责是：

- 在 `map` 坐标系下理解整个环境
- 根据静态地图和全局代价地图规划一条从当前位置到目标点的路径
- 将路径发布给后续模块用于跟踪

如果没有全局规划，Nav2 虽然知道机器人在哪，也知道目标在哪，但无法形成一条从起点到终点的整体路线。

---

## 3. 本项目的全局规划实现方式

本仓库没有自己实现路径搜索算法，实际使用的是 Nav2 自带的规划模块。

当前项目中的全局规划器配置为：

- `planner_server`
- 插件名：`GridBased`
- 插件实现：`nav2_navfn_planner/NavfnPlanner`

也就是说，这个项目当前实际使用的是 **NavFn Planner**。

它是 Nav2 里经典的二维栅格全局规划器，底层可基于 Dijkstra 或 A* 思路工作。

---

## 4. 启动链路

本项目中全局规划模块的启动链路如下：

```text
ros2 launch nav2_practice navigation.launch.py
    ->
nav2_practice/launch/navigation.launch.py
    ->
nav2_bringup/launch/bringup_launch.py
    ->
nav2_bringup/launch/navigation_launch.py
    ->
planner_server
```

说明：

- 你的项目入口是 `navigation.launch.py`
- 真正启动规划模块的是 Nav2 bringup
- 实际运行的节点是 `planner_server`

---

## 5. 数据流

全局规划的数据流可以概括为：

```text
AMCL 位姿 + 目标点 + global costmap
                ->
            planner_server
                ->
              /plan
```

更具体一点：

### 输入

- 机器人当前位姿：来自 AMCL / TF
- 用户设置的目标点：来自 RViz `Nav2 Goal`
- 全局代价地图：来自 `global_costmap`

### 输出

- `/plan`：全局路径

这条全局路径会交给后续局部规划和控制模块去执行。

---

## 6. 本项目里全局规划怎么用上

本项目中的使用方式是标准 Nav2 流程：

1. 启动导航：`ros2 launch nav2_practice navigation.launch.py`
2. 在 RViz 中使用 `2D Pose Estimate` 完成 AMCL 初始定位
3. 使用 `Nav2 Goal` 设置目标点
4. `planner_server` 根据当前位置、目标点和全局代价地图计算路径
5. 生成的路径发布到 `/plan`

README 中对应的验收方式也已经写了：

- 可以在 RViz 中看到全局路径
- 可以通过 `ros2 topic echo --once /plan` 查看规划结果

---

## 7. 本项目当前使用的关键配置

全局规划参数位于：

- `src/nav2_practice/params/nav2_params.yaml`

当前相关配置是：

```yaml
planner_server:
  ros__parameters:
    expected_planner_frequency: 20.0
    use_sim_time: False
    planner_plugins: ["GridBased"]
    GridBased:
      plugin: "nav2_navfn_planner/NavfnPlanner"
      tolerance: 0.5
      use_astar: false
      allow_unknown: true
```

这说明：

- 当前只有一个全局规划插件
- 插件名叫 `GridBased`
- 实现是 `NavfnPlanner`
- 当前 `use_astar: false`，因此更接近 Dijkstra 风格

---

## 8. 核心原理

对于当前项目来说，可以把全局规划理解为“在代价地图上做路径搜索”。

### 8.1 代价地图准备

在全局规划前，系统会先构建 `global_costmap`：

- 静态地图提供墙体和障碍边界
- 障碍层和膨胀层告诉规划器哪些区域不能走，哪些区域尽量不要贴近

### 8.2 路径搜索

规划器在二维栅格地图上，从起点开始搜索，找到一条到目标点的可行路径。

### 8.3 路径输出

生成的路径通常是离散的路径点序列，发布到 `/plan`，再由局部规划器或控制器跟踪。

---

## 9. 当前项目里的规划器：NavFn Planner

你这个项目当前使用的是：

```yaml
plugin: "nav2_navfn_planner/NavfnPlanner"
```

NavFn Planner 的特点：

- 经典、稳定
- 基于二维栅格地图
- 适合入门导航项目和室内场景
- 可以在 Dijkstra / A* 风格之间切换

对你当前 TurtleBot3 + 室内仿真项目，这个选择是合理的，因为：

- 路径规划逻辑简单直接
- 行为容易理解
- 参数量不大
- 与 Nav2 默认生态兼容性好

---

## 10. 关键参数说明

下面只讲当前项目里最关键的全局规划参数。

### 10.1 `expected_planner_frequency`

```yaml
expected_planner_frequency: 20.0
```

作用：

- 表示期望的规划频率

影响：

- 系统希望规划器能够较快响应目标变化或重规划需求
- 数值不是路径质量参数，更多是运行期性能预期

对当前项目，这个值主要影响系统对规划响应速度的预期。

### 10.2 `planner_plugins`

```yaml
planner_plugins: ["GridBased"]
```

作用：

- 声明 `planner_server` 下启用哪些规划插件

当前项目只有一个规划器，所以这里只有一个插件名 `GridBased`。

### 10.3 `plugin`

```yaml
plugin: "nav2_navfn_planner/NavfnPlanner"
```

作用：

- 指定 `GridBased` 这个插件到底使用哪种规划器实现

当前项目中，它绑定到 NavFn Planner。

### 10.4 `tolerance`

```yaml
tolerance: 0.5
```

作用：

- 如果目标点本身正好不可达，允许规划器在目标附近一定范围内寻找可接受终点

影响：

- 数值太小：有时目标点稍微卡在障碍边上就会规划失败
- 数值太大：可能规划到距离目标略远但可接受的位置

对当前项目，`0.5 m` 是较常见的保守值。

### 10.5 `use_astar`

```yaml
use_astar: false
```

作用：

- 控制 NavFn Planner 采用更接近 A* 还是更接近 Dijkstra 的搜索方式

当前项目：

- `false` 表示当前不是 A* 模式
- 更接近经典 Dijkstra 搜索

影响：

- Dijkstra：更经典、更稳，搜索范围可能更大
- A*：加入启发信息，通常效率更高

### 10.6 `allow_unknown`

```yaml
allow_unknown: true
```

作用：

- 决定规划时是否允许路径穿过未知区域

影响：

- `true`：在某些未知区域存在时仍可能规划出路径
- `false`：更保守，只走已知可通行区域

对当前项目，由于仿真地图和静态地图通常较明确，这个参数的影响取决于全局代价地图中是否保留未知空间。

---

## 11. 参数细化原则

全局规划参数通常不需要像控制器那样高频调节。对这个项目来说，调参顺序建议是：

1. 先确认地图和定位正常
2. 再确认 `global_costmap` 是否合理
3. 最后才细化规划器参数

优先级较高的参数通常是：

1. `plugin`
2. `tolerance`
3. `use_astar`
4. `allow_unknown`
5. `expected_planner_frequency`

原因很简单：

- 如果地图或定位错了，改规划器没意义
- 如果全局代价地图错了，规划器看到的“世界”本身就不对

---

## 12. 如何判断全局规划是否正常

在本项目中，可以从下面几项判断全局规划状态。

### 12.1 能否正常生成路径

- 在 RViz 中发送 `Nav2 Goal`
- 系统应生成一条从当前位置到目标点的路径

### 12.2 路径起点是否正确

- 路径起点应紧贴机器人当前位置
- 如果起点明显偏离，通常是定位问题，不一定是规划器问题

### 12.3 路径是否绕开障碍物

- 全局路径应避开墙体和障碍区域
- 不应穿墙

### 12.4 路径是否具有整体合理性

- 路径应从全局上连通起点和终点
- 不应频繁断裂或明显绕远

---

## 13. 常见问题

### 13.1 发目标后没有路径

优先检查：

- AMCL 是否已经收敛
- 地图是否正确加载
- `global_costmap` 是否正常
- 目标点是否落在不可达区域

### 13.2 路径起点偏了

常见原因：

- AMCL 定位不准
- 初始位姿估计不准
- `map -> odom` 不稳定

### 13.3 路径看起来穿墙

常见原因：

- 地图数据异常
- global costmap 没正确叠加障碍信息
- RViz 显示理解有偏差

### 13.4 路径能生成但机器人走不过去

常见原因：

- 这通常不是全局规划本身的问题
- 更可能出在局部规划、控制器、局部代价地图或机器人尺寸配置上

---

## 14. 本项目中的全局规划与局部规划区别

这两个模块职责不同。

### 全局规划

- 关注整体路线
- 使用全局地图和全局代价地图
- 输出从起点到终点的参考路径

### 局部规划

- 关注短时运动与实时避障
- 使用局部代价地图和实时障碍信息
- 输出速度指令或短时轨迹

在本项目中：

- `planner_server` 负责全局规划
- `controller_server` 负责局部规划和跟踪控制

---

## 15. 本项目中的实际位置

如果后续要维护这个模块，优先关注这些文件：

- `src/nav2_practice/launch/navigation.launch.py`
- `src/nav2_practice/params/nav2_params.yaml`
- `src/nav2_practice/README.md`

如果要继续深挖系统实现，再看：

- `/opt/ros/humble/share/nav2_bringup/launch/bringup_launch.py`
- `/opt/ros/humble/share/nav2_bringup/launch/navigation_launch.py`

---

## 16. 一句话总结

本项目里的全局规划模块本质上是：在 AMCL 提供当前位置、global costmap 提供可通行信息之后，由 `planner_server` 中的 `NavfnPlanner` 生成从起点到目标点的全局路径 `/plan`，供后续局部规划和控制执行。
