# USAGE.md

本文档说明如何为 G1 和 Tienkung 机器人训练运动跟踪策略。

## 环境准备

```bash
# 安装依赖（需已安装 Isaac Lab v2.1.0）
python -m pip install -e source/whole_body_tracking

# 下载 G1 机器人描述文件
curl -L -o unitree_description.tar.gz https://storage.googleapis.com/qiayuanl_robot_descriptions/unitree_description.tar.gz && \
tar -xzf unitree_description.tar.gz -C source/whole_body_tracking/whole_body_tracking/assets/ && \
rm unitree_description.tar.gz

# Tienkung URDF 需手动放置到以下路径：
# source/whole_body_tracking/whole_body_tracking/assets/tienkung/urdf/tienkung2_lite.urdf
```

登录 WandB 并将 `WANDB_ENTITY` 设置为你的**组织名**（非个人用户名）：

```bash
wandb login
export WANDB_ENTITY=your-org-name
```

---

## 动作数据预处理

将重定向后的 CSV 动作文件转换为 NPZ 格式并上传到 WandB Registry。

```bash
# G1
python scripts/csv_to_npz.py \
  --robot g1 \
  --input_file path/to/motion.csv \
  --input_fps 30 \
  --output_name {motion_name} \
  --headless

# Tienkung
python scripts/csv_to_npz.py \
  --robot tienkung \
  --input_file path/to/motion.csv \
  --input_fps 30 \
  --output_name {motion_name} \
  --headless
```

可选参数：
- `--frame_range START END`：只处理指定帧范围（从 1 开始）
- `--output_fps`：输出帧率，默认 50

验证上传结果：

```bash
python scripts/replay_npz.py \
  --registry_name ${WANDB_ENTITY}-org/wandb-registry-motions/{motion_name}
```

---

## 策略训练

### 基础训练

使用 `--robot` 自动选择默认 task，或用 `--task` 显式指定。

```bash
# G1（两种写法等价）
python scripts/rsl_rl/train.py \
  --robot g1 \
  --registry_name ${WANDB_ENTITY}-org/wandb-registry-motions/{motion_name} \
  --headless --logger wandb --log_project_name {project} --run_name {run}

python scripts/rsl_rl/train.py \
  --task Tracking-Flat-G1-v0 \
  --registry_name ${WANDB_ENTITY}-org/wandb-registry-motions/{motion_name} \
  --headless --logger wandb --log_project_name {project} --run_name {run}

# Tienkung
python scripts/rsl_rl/train.py \
  --robot tienkung \
  --registry_name ${WANDB_ENTITY}-org/wandb-registry-motions/{motion_name} \
  --headless --logger wandb --log_project_name {project} --run_name {run}
```

### 可用 Task ID

| 机器人 | Task ID |
|--------|---------|
| G1 | `Tracking-Flat-G1-v0` |
| G1（无状态估计）| `Tracking-Flat-G1-Wo-State-Estimation-v0` |
| G1（低频控制）| `Tracking-Flat-G1-Low-Freq-v0` |
| Tienkung | `Tracking-Flat-Tienkung-v0` |
| Tienkung（分阶段蒸馏）| `Tracking-Flat-Tienkung-StageDistill-v0` |

### 分阶段训练（Tienkung）

Tienkung 支持两阶段训练（Stage1 AMP 预训练 → Stage2 蒸馏）。在 `agents/rsl_rl_ppo_cfg.py` 中将 `staged_training.enabled` 设为 `True`，或使用专用 task：

```bash
python scripts/rsl_rl/train.py \
  --task Tracking-Flat-Tienkung-StageDistill-v0 \
  --registry_name ${WANDB_ENTITY}-org/wandb-registry-motions/{motion_name} \
  --headless --logger wandb --log_project_name {project} --run_name {run}
```

---

## 策略评估

WandB run path 格式为 `{org}/{project}/{8位ID}`，可在 WandB 的 run 概览页找到。

```bash
# G1
python scripts/rsl_rl/play.py \
  --robot g1 \
  --num_envs 2 \
  --wandb_path {org}/{project}/{run_id}

# Tienkung
python scripts/rsl_rl/play.py \
  --robot tienkung \
  --num_envs 2 \
  --wandb_path {org}/{project}/{run_id}

# 使用本地动作文件覆盖
python scripts/rsl_rl/play.py \
  --robot tienkung \
  --num_envs 2 \
  --wandb_path {org}/{project}/{run_id} \
  --motion_file path/to/motion.npz
```

评估结束后会自动将策略导出为 ONNX 格式，保存在对应日志目录的 `exported/policy.onnx`。

---

## 添加新机器人

1. 在 `source/whole_body_tracking/whole_body_tracking/robots/{robot}.py` 定义 `ArticulationCfg` 和 `ACTION_SCALE`
2. 在 `tasks/tracking/config/{robot}/flat_env_cfg.py` 创建环境配置，继承 `TrackingEnvCfg`
3. 在 `tasks/tracking/config/{robot}/agents/rsl_rl_ppo_cfg.py` 定义 PPO 超参数
4. 在 `tasks/tracking/config/{robot}/__init__.py` 注册 Gym 环境
5. 在 `scripts/csv_to_npz.py` 的 `_ROBOT_CFGS` 和 `_ROBOT_JOINT_NAMES` 中添加新机器人条目
6. 在 `scripts/rsl_rl/train.py` 和 `play.py` 的 `_ROBOT_DEFAULT_TASK` 中添加映射

参考实现：[robots/tienkung.py](source/whole_body_tracking/whole_body_tracking/robots/tienkung.py) 和 [tasks/tracking/config/tienkung/](source/whole_body_tracking/whole_body_tracking/tasks/tracking/config/tienkung/)。
