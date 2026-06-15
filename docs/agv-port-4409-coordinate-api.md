# AGV 车载端口与坐标获取

本文档仅描述 AGV **车载端**的端口及坐标获取方式。

---

## 一、车载端口总览

车载端运行 `mtArmService`（基于 Bottle 框架的 Web 服务）作为统一入口，底层通过 NSP 协议与 `motion_template` 等进程通信。

| 端口 | 协议 | 进程/服务 | 用途 |
|:----:|------|------|------|
| **4405** | HTTP | mtArmService (Bottle) | **Web API** — 查询/控制接口 |
| **4406** | WebSocket | mtArmService (Rocket) | **实时推送** — 位置/状态事件 |
| 4407 | TCP | Jess | 配置管理端口 |
| 4409 | TCP/UDP | motion_template | **MT 控制** — NSP 二进制协议 |
| 4410 | TCP/UDP | agv_shell | Shell 管理 |
| 7000 | UDP | locViewUdpServer | **定位数据流** — 实时位置广播 |

> 来源：`mtArmService/utils/settings.py`、`agvloc/loc_udp_ser.py`

---

## 二、坐标数据结构

所有位置坐标使用统一的 `position_t` 结构体：

```c
position_t {
  x_     double   // 世界坐标系 X 轴坐标
  y_     double   // 世界坐标系 Y 轴坐标
  theta_ double   // 朝向角度（弧度）
}
```

`navigation_t` 中的位置字段（来源：`agvmt/mtproto/view_data.py:161-167`）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `pos_` | `position_t` | **当前实时位置** |
| `dest_pos_` | `position_t` | 目标点位置 |
| `pos_confidence_` | `double` | 定位置信度（0~1） |
| `pos_status_` | `uint32` | 定位状态码 |
| `base_point_` | `position_t` | 基准点 |
| `aim_point_` | `position_t` | 瞄准点 |
| `predict_point_` | `position_t` | 预测点 |
| `upl_` | `upl_t` | 当前所在边信息 |

---

## 三、获取坐标的三种方式

### 方式 1：Web API（端口 4405）

**适用场景：** HTTP 请求获取当前位置，适合轮询/按需查询。

#### 1.1 查询 MT 变量数据

```
POST http://<agv_ip>:4405/mt/info/query
Content-Type: application/json
```

**请求体：**
```json
{
  "detail": "query_var_data",
  "var_list": [<var_id_of_navigation>]
}
```

**响应（部分字段）：**
```json
{
  "code": 0,
  "data": {
    "pos_": {
      "x_": 21.65,
      "y_": 16.29,
      "theta_": -3.14
    },
    "pos_confidence_": 0.95,
    "pos_status_": 0
  }
}
```

#### 1.2 其他可用查询（`/mt/info/query` 的 `detail` 参数）

| detail 值 | 说明 |
|------|------|
| `version` | MT 版本信息 |
| `chassis_type` | 底盘类型 |
| `var_list` | 获取可用变量列表 |
| `ctrl_status` | 遥控状态 |
| `safety_info` | 安全防护信息 |
| `battery` | 电量信息 |
| `speed_config` | 速度配置 |
| `agv_type` | 车辆类型 |

#### 1.3 控制接口

```
POST http://<agv_ip>:4405/mt/action
Content-Type: application/json

// 遥控
{"action": "remote_ctrl", "enable_ctrl": 1}

// 发速度 (x/y/w)
{"action": "nav_task", ...}
```

> 来源：`app/mt/mtview.py`

---

### 方式 2：Loc View UDP 数据流（端口 7000）

**适用场景：** 需要高频、低延迟的实时位置数据，UDP 广播方式持续推送。

#### 数据格式

| 参数 | 值 |
|------|------|
| 端口 | `7000` (UDP) |
| 数据包大小 | `6904` 字节 |
| 推送频率 | 约 1 Hz |
| 数据协议 | `proto_loc_view_report` |

#### 位置字段

```python
# 来源: agvloc/loc_udp_ser.py:50
agv_point = [x_, y_, w_]
# x_:    double   X 坐标
# y_:    double   Y 坐标
# w_:    double   朝向角度（弧度）
```

**辅助数据：**

```python
ref_map_points  = [[var_id, var_x, var_y, var_status], ...]   # 参考地图点
cloud_map_points = [[var_x, var_y], ...]                       # 点云地图
```

**超时判定：** 超过 30 秒未收到数据视为超时（来源：`loc_udp_ser.py:71`）。

> 来源：`agvloc/loc_udp_ser.py`、`agvloc/locproto/proto_view.py`

---

### 方式 3：WebSocket 实时推送（端口 4406）

**适用场景：** 需要双向通信、事件驱动的实时位置更新。

通过 WebSocket 连接后，可订阅位置相关事件：
- `event_mt_send_speed` — 发送速度指令（含 x/y/w 坐标参数）

```json
{
  "event": "event_mt_send_speed",
  "direction": "1,2,3",
  "x": 1.5,
  "y": 2.0,
  "w": 0.1
}
```

> 来源：`app/mt/mtview.py:96-101`

---

## 四、方式对比

| 维度 | Web API (4405) | Loc View UDP (7000) | WebSocket (4406) |
|------|:--:|:--:|:--:|
| 协议 | HTTP POST | UDP 广播 | WebSocket |
| 数据粒度 | 完整 navigation_t | 精简 agv_point | 事件驱动 |
| 延迟 | 请求-响应 | 持续推送 (~1Hz) | 实时推送 |
| 方向 | 单向查询 | 仅接收 | 双向 |
| 适用 | 按需查询 | 监控面板/日志记录 | 遥控/实时交互 |

---

## 五、位置数据依赖链

```
定位传感器 (激光/二维码/IMU)
  │
  ▼
motion_template (NSP: 4409)
  │
  ├──▶ navigation_t.pos_    ← 底层实时位置
  │
  ▼
mtArmService (Web: 4405 / WS: 4406)
  │
  ├──▶ HTTP API 查询
  └──▶ WebSocket 推送
  │
  ▼
locViewUdpServer (UDP: 7000)
  │
  └──▶ proto_loc_view_report  ← 精简位置 + 地图数据
```

---

## 六、车载端 profile 配置

```ini
# MT 通信端口
foundation.global.mt_tcp_port=4409
foundation.global.mt_udp_port=4409

# 定位模块 NSP 端点（均指向本地 4409）
localization.LaserMarkLocV2.nsp.nsp_ip=127.0.0.1
localization.LaserMarkLocV2.nsp.nsp_ep=4409
localization.Deviation.Deviation.nsp_ep=4409
localization.sensor.motion_templateNet.nsp_ep=4409
```

> 来源：`2车.profile`

---

## 七、备注

- Web API 端口默认 `4405`，可通过车载配置 `webvehicle_port` 覆盖
- WebSocket 端口默认 `4406`，可通过 `websocket_port` 覆盖
- Loc View UDP 端口默认 `7000`，可通过 `loc_view_udp_port` 覆盖
- 所有端口配置定义在 `mtArmService/utils/settings.py`
