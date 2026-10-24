
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from pathlib import Path


# =====================================
# 1. 定位 CSV 文件
# =====================================

BASE_DIR = Path(__file__).resolve().parent
CSV_FILE = BASE_DIR / "data" / "equipment_data.csv"


# =====================================
# 2. 读取和检查数据
# =====================================

def main():

    if not CSV_FILE.exists():
        print("错误：找不到 CSV 文件。")
        print("请检查 data/equipment_data.csv 是否存在。")
        return

    try:
        df = pd.read_csv(CSV_FILE)
    except (pd.errors.EmptyDataError, pd.errors.ParserError) as e:
        print("CSV 文件读取失败：", e)
        return

    # 清理列名两侧的空格
    df.columns = df.columns.str.strip()

    required_columns = ["timestamp", "torque"]

    for column in required_columns:
        if column not in df.columns:
            print(f"错误：CSV 缺少必要的列：{column}")
            print("当前列名：", df.columns.tolist())
            return

    if df.empty:
        print("CSV 文件中没有数据。")
        return

    # 转换数据类型
    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce",
    )

    df["torque"] = pd.to_numeric(
        df["torque"],
        errors="coerce",
    )

    # 删除无效数据
    df = df.dropna(
        subset=["timestamp", "torque"]
    ).copy()

    if df.empty:
        print("没有有效的时间和扭矩数据。")
        return


    # =====================================
    # 3. 统计全部有效数据
    # =====================================

    print("\n========== 工业设备扭矩分析 ==========")

    print(f"有效记录数：{len(df)}")

    print(
        f"平均扭矩：{df['torque'].mean():.2f} N·m"
    )

    print(
        f"最大扭矩：{df['torque'].max():.2f} N·m"
    )

    print(
        f"最小扭矩：{df['torque'].min():.2f} N·m"
    )

    print(
        f"扭矩标准差：{df['torque'].std(ddof=0):.2f} N·m"
    )


    # =====================================
    # 4. 筛选最新五分钟的数据
    # =====================================

    df = df.sort_values("timestamp")

    latest_time = df["timestamp"].max()

    start_time = latest_time - pd.Timedelta(
        minutes=5
    )

    plot_df = df[
        (df["timestamp"] >= start_time)
        & (df["timestamp"] <= latest_time)
    ].copy()

    # =====================================
    # 扭矩异常检测
    # =====================================

    TORQUE_LIMIT = 34.5

    # 筛选超过模拟实验阈值的记录
    alarm_df = plot_df[
        plot_df["torque"] > TORQUE_LIMIT
        ]

    print("\n========== 扭矩异常检测 ==========")
    print(f"模拟报警阈值：{TORQUE_LIMIT:.2f} N·m")

    if alarm_df.empty:
        print("最近五分钟没有发现超过阈值的记录。")
    else:
        print(f"发现 {len(alarm_df)} 条超限记录：")

        for _, row in alarm_df.iterrows():
            print(
                f"时间：{row['timestamp']} | "
                f"扭矩：{row['torque']:.2f} N·m | "
                f"超过阈值："
                f"{row['torque'] - TORQUE_LIMIT:.2f} N·m"
            )

    plot_df = plot_df.sort_values("timestamp")
    # 计算相邻采样记录之间的时间间隔
    time_gap = plot_df["timestamp"].diff().dt.total_seconds()

    # 如果采样间隔超过3秒，就断开曲线
    plot_df.loc[time_gap > 3, "torque"] = float("nan")

    # =====================================
    # 连续3次扭矩超限检测
    # =====================================

    # =====================================
    # 连续超限检测与报警事件统计
    # =====================================

    # 整理用于检测的数据
    detection_df = (
        plot_df[["timestamp", "torque"]]
        .sort_values("timestamp")
        .reset_index(drop=True)
        .copy()
    )

    # 判断每条记录是否超过实验阈值
    over_limit = detection_df["torque"] > TORQUE_LIMIT

    # 计算相邻记录的时间间隔
    time_gap = (
        detection_df["timestamp"]
        .diff()
        .dt.total_seconds()
    )

    # 新事件的开始条件：
    # 1. 当前超限，但上一条没有超限
    # 2. 当前超限，且与上一条记录间隔超过3秒
    run_start = over_limit & (
            ~over_limit.shift(1, fill_value=False)
            | time_gap.gt(3)
    )

    # 为每段连续超限记录分配事件编号
    detection_df["run_id"] = run_start.cumsum()

    # 只保留超限记录
    over_df = detection_df.loc[over_limit].copy()

    continuous_alarms = []
    alarm_events = []

    for _, group in over_df.groupby("run_id"):

        group = (
            group.sort_values("timestamp")
            .reset_index(drop=True)
        )

        # 至少连续3次超限，才算一个报警事件
        if len(group) < 3:
            continue

        # 第3个采样点是报警触发点
        trigger_row = group.iloc[2]

        continuous_alarms.append(trigger_row)

        # 记录该次报警事件的信息
        event = {
            "start_time": group.iloc[0]["timestamp"],
            "trigger_time": trigger_row["timestamp"],
            "end_time": group.iloc[-1]["timestamp"],
            "sample_count": len(group),
            "max_torque": group["torque"].max(),
            "duration_seconds": (
                    group.iloc[-1]["timestamp"]
                    - group.iloc[0]["timestamp"]
            ).total_seconds(),
        }

        alarm_events.append(event)

    # =====================================
    # 输出报警事件统计报告
    # =====================================

    print("\n========== 报警事件统计 ==========")
    print(f"模拟报警阈值：{TORQUE_LIMIT:.2f} N·m")
    print(f"独立连续超限事件数：{len(alarm_events)}")

    if not alarm_events:
        print("最近五分钟没有发现连续3次超限事件。")

    for index, event in enumerate(alarm_events, start=1):
        print(f"\n--- 报警事件 {index} ---")
        print(f"开始时间：{event['start_time']}")
        print(f"触发时间：{event['trigger_time']}")
        print(f"结束时间：{event['end_time']}")
        print(f"超限采样点数：{event['sample_count']}")
        print(f"最大扭矩：{event['max_torque']:.2f} N·m")
        print(
            f"持续时间："
            f"{event['duration_seconds']:.1f} 秒"
        )

    # =====================================
    # 保存报警事件报告
    # =====================================

    ALARM_FILE = BASE_DIR / "data" / "alarm_events.csv"

    if alarm_events:
        event_report_df = pd.DataFrame(alarm_events)

        event_report_df.to_csv(
            ALARM_FILE,
            index=False,
            encoding="utf-8-sig",
        )

        print(f"\n报警事件报告已保存：{ALARM_FILE}")
        print(f"本次报告包含 {len(event_report_df)} 个事件。")

    else:
        print("\n本次没有连续超限事件。")

    # =====================================
    # 5. 绘制扭矩趋势图
    # =====================================

    fig, ax = plt.subplots(figsize=(12, 5))

    ax.plot(
        plot_df["timestamp"],
        plot_df["torque"],
        marker=".",
        markersize=5,
        linewidth=1.2,
        label="Torque",
    )

    # 在趋势图上标记超过阈值的扭矩点
    if not alarm_df.empty:
        ax.scatter(
            alarm_df["timestamp"],
            alarm_df["torque"],
            color="red",
            marker="x",
            s=70,
            label="Torque Alarm",
            zorder=5,
        )

    # 标记连续3次超限的报警触发点
    if continuous_alarms:
        continuous_alarm_df = pd.DataFrame(
            continuous_alarms
        )

        ax.scatter(
            continuous_alarm_df["timestamp"],
            continuous_alarm_df["torque"],
            marker="*",
            s=180,
            label="3 Consecutive Alarm",
            zorder=6,
        )

    # 最近五分钟数据的平均扭矩
    recent_average = plot_df["torque"].mean()

    ax.axhline(
        y=recent_average,
        linestyle="--",
        label=f"5-minute average: {recent_average:.2f}",
    )

    ax.set_title(
        "Industrial Equipment Torque Trend - Latest 5 Minutes"
    )

    ax.set_xlabel("Time")
    ax.set_ylabel("Torque (N.m)")

    ax.xaxis.set_major_formatter(
        mdates.DateFormatter("%H:%M:%S")
    )

    ax.legend()
    ax.grid(True, alpha=0.3)

    fig.autofmt_xdate()
    fig.tight_layout()

    plt.show()


# =====================================
# 6. 程序入口
# =====================================

if __name__ == "__main__":
    main()

