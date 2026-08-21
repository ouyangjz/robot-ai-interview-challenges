# 完成报告

## 完成情况

本次任务范围内的功能均已完成：

- 保留指定的 `Event`、`Effect` 和 `RobotApplication` 导入路径；
- 首次进入产生 `ROBOT_ACTION / wave_hand` 和 `SPEECH / 欢迎光临`；
- 同一接待周期内不重复迎宾；
- 对话和会议分别抑制迎宾、送客和机器人动作，结束后不补发；
- 最后一人离开满配置时间后由 `TICK` 产生一次送客效果；
- 短暂离开后返回时取消离场计时，不送客也不重复迎宾；
- 完整离场后再次进入会开始新的接待周期；
- `handle_event()` 只返回当前事件新增的效果；
- `snapshot()` 不暴露内部可变状态；
- 业务模块不依赖 ROS 2、相机或硬件 SDK。

送客的具体效果在题目中没有固定值，本实现选择：

```text
effect_type=SPEECH
value=欢迎下次光临
reason=absence timeout reached
```

## 测试

环境：Python 3.11.15。

命令：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

最近一次完整执行结果：

```text
Ran 13 tests in 0.001s
OK
```

测试覆盖：

- 首次迎宾和重复进入；
- 题目给出的完整事件序列；
- 对话和会议对迎宾、送客的抑制以及结束后不补发；
- 对话与会议状态同时存在时的独立性；
- 离场不足 10 秒、恰好 10 秒和重复 `TICK`；
- 短暂离场返回及完整离场后的新接待；
- 多人场景下最后一人离场才开始计时；
- 重复离开事件不重置计时；
- `snapshot()` 隔离；
- 自定义超时、零超时和非法输入。

## ROS 2 判断题

### 1. 已经能证明什么

#### 事实

- 应用日志记录了 `effect_created type=ROBOT_ACTION value=wave_hand`，说明应用层创建了挥手意图。
- bridge 记录了 `request_submitted task_id=task-17 action=wave_hand` 和 `accepted_async`，说明 bridge 接收并登记了该异步请求。
- `/basic_action_play_v2` 当前可发现 1 个 Action Client、0 个 Action Server。
- `/get_robot_mode` 返回 `STAND`。
- `robot-action.service` 当前为 `inactive`。

#### 推断

- 请求已经到达 bridge 边界，但动作执行链路没有可用的 Action Server。
- `robot-action.service` 未运行与 Action Server 为 0 高度一致，最可能是动作执行服务没有启动或已经退出。

#### 仍不能证明

- 请求是否成功发送到机器人控制器；
- 机器人是否开始、完成或失败了挥手；
- `STAND` 是否等同于所有安全条件和动作前置条件均满足。

### 2. `accepted_async` 是否代表机器人已经完成挥手

不代表。它只证明 bridge 接受了异步处理请求。完成动作至少需要可用的 Action Server，并获得执行成功的 result 或其他可信的完成反馈；当前证据中没有这些信息。

### 3. 问题最可能在哪一层

最可能在 ROS 2 动作执行/机器人动作服务层，而不是迎宾业务规则层。直接证据是 Action Server 数量为 0，且对应的 systemd 服务处于 `inactive`。

仍需排除另一种可能：服务其实运行在不同的 ROS Domain、命名空间、容器或 RMW 配置中，导致当前终端无法发现。因此“服务未启动或退出”是最强推断，不是已经完全证明的根因。

### 4. 下一步检查顺序

1. 保留 `task-17` 的完整 bridge 日志，检查接受之后是否有投递失败、超时或结果记录。
2. 查看 `systemctl status robot-action.service` 以及该服务的 journal，确认未启动、主动停止还是启动失败。
3. 检查服务单元的启动命令、依赖、环境文件和机器人连接配置。
4. 对比服务与诊断终端的 `ROS_DOMAIN_ID`、RMW、命名空间、Action 名称和 Action 类型，排除“运行但不可发现”。
5. 在获得操作授权并满足现场安全条件后恢复服务，再确认 `/basic_action_play_v2` 的 Action Server 数量至少为 1，并检查接口类型匹配。
6. 检查急停、使能、控制权、机器人模式和动作资源占用等安全前置条件。
7. 先使用模拟器、mock server 或低风险受控动作验证完整的 feedback/result 链路，再考虑真实挥手。

### 5. 当前能否直接执行真实动作

不能。当前没有可发现的 Action Server，动作服务为 `inactive`，也没有动作完成反馈；同时仅有 `STAND` 模式不足以证明急停、使能、控制权和现场安全条件均满足。直接尝试真实动作既缺少可用执行链路，也缺少必要的安全证据。
