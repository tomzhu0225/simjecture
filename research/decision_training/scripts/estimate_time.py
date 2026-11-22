"""Generate conditional wall-time estimates without running models or solvers."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    average_hours = (1 + 3 + 6 + 12) / 4
    rows = []
    for n, m in [(4, 5), (8, 9), (16, 17)]:
        studies = 376 + 80 * n + 16 * m
        study_hours = studies * average_hours
        low_days = study_hours * 1.15 / (2 * 0.90) / 24 + 4
        high_days = study_hours * 1.25 / (2 * 0.70) / 24 + 16
        rows.append(
            dict(
                n=n,
                m=m,
                studies_before_replication=studies,
                budgeted_study_hours=study_hours,
                conditional_calendar_days=[round(low_days), round(high_days)],
            )
        )
    output = dict(
        budgets_hours_by_level=[1, 3, 6, 12],
        study_formula="376+80*n+16*m+R",
        study_hours_formula="2068+440*n+88*m+H_replication",
        evaluation_baseline_added=16,
        parallel_studies=2,
        scheduling_efficiency=[0.7, 0.9],
        replication_allowance_fraction=[0.15, 0.25],
        serial_NPU_allowance_days=[4, 16],
        assumes_each_study_uses_its_entire_budget=True,
        measured_end_to_end_throughput=False,
        convergence_based_RL_has_no_finite_guaranteed_duration=True,
        rows=rows,
    )
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "time_estimate.json").write_text(json.dumps(output, indent=2), encoding="utf-8")
    lines = [
        "# 总耗时预算",
        "",
        "下表按所有研究用满总预算计算。任务可在证据充分时提前结束，表中 n 与 m 是容量情景。在线 RL 的实际终止由开发结果决定。",
        "",
        "|每题 RL 轨迹 n|开发轮数 m|独立复算前研究次数|研究预算小时|远端 2 并行日历天数|",
        "|---|---|---|---|---|",
    ]
    lines += [
        f"|{r['n']}|{r['m']}|{r['studies_before_replication']}|{r['budgeted_study_hours']:.0f}|{r['conditional_calendar_days'][0]}–{r['conditional_calendar_days'][1]}|"
        for r in rows
    ]
    lines += [
        "",
        "预算分解为 SFT 教师研究 1320 小时、固定开发基线 88 小时、RL 440n 小时、候选开发评测 88m 小时、正式比较 440 小时、建议归因 220 小时，另加独立复算。SFT 的 240 条完整轨迹需要真实科研执行。",
        "",
        "日历估算采用 2 个有效研究并发、70%–90% 排程效率、15%–25% 独立验证开销及 4–16 天串行 NPU 开销。主机只支持一个大规模研究同时运行时，并发项需相应下调。共享 CPU 负载、代码准备、内存与 I/O 会影响效率。",
        "",
        "NPU 初始容量估算使用每轨迹平均 22 个决策、每个决策输入输出合计约 6000 token、SFT 两轮，共约 6336 万训练 token。假设双卡有效训练吞吐 50–200 token/s，SFT 约 88–352 小时。该吞吐属于待实测假设，Gated DeltaNet 算子与长上下文可能显著改变结果。RL 每组四条完整研究，采样与更新不能通过预录数值结果替代。",
        "",
        "如果全部任务实际只消耗一半预算，研究墙钟项约减半，串行 NPU 和准备项保留。尚未运行基准，当前无法给出可信的单一完工日期。",
        "",
        "准备阶段已发生的命题编制、文件校验和环境检查不计为科研实验。首次启动后的模型前后向、概率一致性、两卡同步与恢复、求解器和独立参考资格验证预留 1–3 天，计入最终实际成本。复杂独立参考实现若超出此范围，需按实际新增工期更新。",
        "",
        "GPT-6.1 Sol 使用现有 Codex 登录，token、服务等待与配额单独记录。价格和账户吞吐未获可计费 API 数据，当前成本预算以 token 与设备时记录，人民币或美元成本留待实际账单。",
    ]
    (ROOT / "reports" / "总耗时估算.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(rows))


if __name__ == "__main__":
    main()
