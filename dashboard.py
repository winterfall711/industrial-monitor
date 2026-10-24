
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_autorefresh import st_autorefresh


# =====================================
# 1. 页面配置与数据路径
# =====================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

CSV_FILE = DATA_DIR / "equipment_data.csv"
ALARM_FILE = DATA_DIR / "alarm_events.csv"
TORQUE_LIMIT = 34.5
st.set_page_config(
    page_title="Industrial Monitor",
    page_icon="🏭",
    layout="wide",
)

# 每隔 2 秒刷新一次网页
st_autorefresh(
    interval=2000,
    key="dashboard_refresh",
)


# =====================================
# 2. 页面标题
# =====================================

st.title("🏭 Industrial Equipment Monitor")
st.caption("工业设备实时监控系统")

st.markdown("---")


# =====================================
# 3. 读取 CSV 文件
# =====================================

def load_csv(file_path):
    """读取 CSV 文件，不存在或为空时返回空表格。"""

    if not file_path.exists():
        return pd.DataFrame()

    try:
        df = pd.read_csv(
            file_path,
            encoding="utf-8-sig",
        )

        df.columns = [
            str(column).strip()
            for column in df.columns
        ]

        return df

    except pd.errors.EmptyDataError:
        return pd.DataFrame()

    except (OSError, UnicodeError, ValueError) as e:
        st.warning(
            f"读取文件失败：{file_path.name}，原因：{e}"
        )
        return pd.DataFrame()


# =====================================
# 4. 实时设备数据
# =====================================

st.header("实时设备状态")

equipment_df = load_csv(CSV_FILE)

if equipment_df.empty:
    st.info(
        "暂无设备数据。请先启动 modbus_server.py "
        "和 modbus_client.py。"
    )

else:
    required_columns = [
        "timestamp",
        "temperature",
        "speed",
        "torque",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in equipment_df.columns
    ]

    if missing_columns:
        st.error(
            f"设备 CSV 缺少字段：{missing_columns}"
        )

    else:
        df = equipment_df[required_columns].copy()

        df["timestamp"] = pd.to_datetime(
            df["timestamp"],
            errors="coerce",
        )

        for column in [
            "temperature",
            "speed",
            "torque",
        ]:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )

        df = (
            df.dropna(subset=required_columns)
            .sort_values("timestamp")
            .reset_index(drop=True)
        )

        if df.empty:
            st.warning("暂时没有有效的设备数据。")

        else:
            latest = df.iloc[-1]

            # =====================================
            # 最新设备数据与采集状态
            # =====================================

            now = pd.Timestamp.now()

            age_seconds = max(
                0,
                (now - latest["timestamp"]).total_seconds(),
            )

            if age_seconds <= 5:
                status_text = "正常"
                status_message = "设备数据正在持续更新。"
            elif age_seconds <= 15:
                status_text = "数据延迟"
                status_message = (
                    f"已经 {age_seconds:.0f} 秒没有新数据，请检查采集程序。"
                )
            else:
                status_text = "无新数据"
                status_message = (
                    f"已经 {age_seconds:.0f} 秒没有新数据，请检查客户端和服务端。"
                )

            # 四张监控指标卡片
            col1, col2, col3, col4 = st.columns(4)

            col1.metric(
                "设备温度",
                f"{latest['temperature']:.2f} °C",
            )

            col2.metric(
                "设备转速",
                f"{latest['speed']:.0f} rpm",
            )

            col3.metric(
                "设备扭矩",
                f"{latest['torque']:.2f} N·m",
            )

            col4.metric(
                "采集状态",
                status_text,
            )

            # 根据最新数据的时间显示状态提示
            if age_seconds <= 5:
                st.success(status_message)
            elif age_seconds <= 15:
                st.warning(status_message)
            else:
                st.error(status_message)

            st.caption(
                f"最新采集时间："
                f"{latest['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}"
            )

            # =====================================
            # 实时扭矩报警与恢复提示
            # =====================================

            st.subheader("实时扭矩报警状态")

            is_alarm = df["torque"] > TORQUE_LIMIT

            # 采集数据过期时，不误报当前设备状态
            if age_seconds > 15:
                st.warning(
                    "⚠️ 数据已超过 15 秒未更新，"
                    "无法确认当前实时报警状态。"
                )

            elif latest["torque"] > TORQUE_LIMIT:

                # 找到当前连续超限的这一段数据
                group_id = is_alarm.ne(
                    is_alarm.shift()
                ).cumsum()

                current_episode = df[
                    group_id == group_id.iloc[-1]
                    ]

                alarm_start = current_episode.iloc[0]["timestamp"]

                duration = (
                        latest["timestamp"] - alarm_start
                ).total_seconds()

                max_torque = current_episode["torque"].max()

                st.error(
                    f"🚨 扭矩超限报警！"
                    f"当前扭矩：{latest['torque']:.2f} N·m；"
                    f"报警阈值：{TORQUE_LIMIT:.2f} N·m"
                )

                st.write(
                    f"本次连续超限开始时间："
                    f"{alarm_start.strftime('%Y-%m-%d %H:%M:%S')}"
                )

                st.write(
                    f"连续超限采样点数：{len(current_episode)}"
                )

                st.write(
                    f"本段最大扭矩：{max_torque:.2f} N·m"
                )

                st.write(
                    f"本段已持续：{duration:.0f} 秒"
                )

            else:
                st.success(
                    f"✅ 当前扭矩正常："
                    f"{latest['torque']:.2f} N·m，"
                    f"报警阈值：{TORQUE_LIMIT:.2f} N·m"
                )

                # 查找最近一次超限及其后的恢复采样
                over_rows = df[is_alarm]

                if not over_rows.empty:
                    last_over_index = over_rows.index[-1]

                    recovery_rows = df.loc[
                        last_over_index + 1:
                    ]

                    if not recovery_rows.empty:
                        recovery_time = (
                            recovery_rows.iloc[0]["timestamp"]
                        )

                        st.info(
                            f"最近一次超限后的正常采样时间："
                            f"{recovery_time.strftime('%Y-%m-%d %H:%M:%S')}"
                        )
                    else:
                        st.caption("暂时没有超限后的恢复采样记录。")

            # 只显示最近 5 分钟的有效记录
            cutoff = (
                df["timestamp"].max()
                - pd.Timedelta(minutes=5)
            )

            plot_df = df[
                df["timestamp"] >= cutoff
            ].copy()

            st.markdown("---")
            st.subheader("最近 5 分钟设备趋势")

            # 温度趋势
            fig_temp = px.line(
                plot_df,
                x="timestamp",
                y="temperature",
                title="温度趋势（°C）",
                markers=True,
            )

            fig_temp.update_layout(height=320)

            st.plotly_chart(
                fig_temp,
                use_container_width=True,
            )

            # 转速趋势
            fig_speed = px.line(
                plot_df,
                x="timestamp",
                y="speed",
                title="转速趋势（rpm）",
                markers=True,
            )

            fig_speed.update_layout(height=320)

            st.plotly_chart(
                fig_speed,
                use_container_width=True,
            )

            # 扭矩趋势
            fig_torque = px.line(
                plot_df,
                x="timestamp",
                y="torque",
                title="扭矩趋势（N·m）",
                markers=True,
            )

            fig_torque.update_layout(height=320)

            st.plotly_chart(
                fig_torque,
                use_container_width=True,
            )


# =====================================
# 5. 报警管理与历史记录
# =====================================

st.markdown("---")
st.header("🚨 设备报警管理")

alarm_df = load_csv(ALARM_FILE)

if alarm_df.empty:
    st.info("暂无报警记录，或者报警文件尚未生成。")

else:
    # 检查 CSV 必需字段
    required_columns = [
        "start_time",
        "trigger_time",
        "end_time",
        "sample_count",
        "max_torque",
        "duration_seconds",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in alarm_df.columns
    ]

    if missing_columns:
        st.error(
            f"报警文件缺少字段：{missing_columns}"
        )

    else:
        alarm_df = alarm_df.copy()

        # 转换时间字段
        time_columns = [
            "start_time",
            "trigger_time",
            "end_time",
        ]

        for column in time_columns:
            alarm_df[column] = pd.to_datetime(
                alarm_df[column],
                errors="coerce",
            )

        # 转换数值字段
        numeric_columns = [
            "sample_count",
            "max_torque",
            "duration_seconds",
        ]

        for column in numeric_columns:
            alarm_df[column] = pd.to_numeric(
                alarm_df[column],
                errors="coerce",
            )

        # 判断是否有记录结束时间
        end_time_text = (
            alarm_df["end_time"]
            .astype("string")
            .str.strip()
        )

        no_end_time = (
            alarm_df["end_time"].isna()
            | end_time_text.eq("").fillna(True)
        )

        # 计算统计指标
        total_alarms = len(alarm_df)

        incomplete_alarms = int(
            no_end_time.sum()
        )

        max_torque = alarm_df[
            "max_torque"
        ].max()

        average_duration = alarm_df[
            "duration_seconds"
        ].mean()

        # 最新报警触发时间
        valid_trigger_times = alarm_df[
            "trigger_time"
        ].dropna()

        if not valid_trigger_times.empty:
            latest_trigger_time = (
                valid_trigger_times.max().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            )
        else:
            latest_trigger_time = "暂无"

        # 四项统计卡片
        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "累计报警事件",
            f"{total_alarms}",
        )

        col2.metric(
            "未记录结束时间",
            f"{incomplete_alarms}",
        )

        col3.metric(
            "历史最大扭矩",
            (
                f"{max_torque:.2f} N·m"
                if pd.notna(max_torque)
                else "暂无"
            ),
        )

        col4.metric(
            "平均报警持续时间",
            (
                f"{average_duration:.1f} 秒"
                if pd.notna(average_duration)
                else "暂无"
            ),
        )

        st.caption(
            f"最近一次报警触发时间："
            f"{latest_trigger_time}"
        )

        # 生成报警状态
        alarm_df["记录状态"] = no_end_time.map(
            {
                True: "未记录结束时间",
                False: "已结束",
            }
        )

        # =====================================
        # 报警历史筛选与 CSV 导出
        # =====================================

        # 为旧版报警记录提供兼容显示
        if "event_id" not in alarm_df.columns:
            alarm_df["event_id"] = "历史记录（无ID）"
        else:
            alarm_df["event_id"] = (
                alarm_df["event_id"]
                .fillna("历史记录（无ID）")
            )

        # 默认日期范围覆盖全部已有报警记录
        valid_times = alarm_df["trigger_time"].dropna()

        if not valid_times.empty:
            default_start = valid_times.min().date()
            default_end = valid_times.max().date()
        else:
            default_start = pd.Timestamp.now().date()
            default_end = default_start

        st.subheader("报警历史查询")

        date_range = st.date_input(
            "选择报警触发日期范围",
            value=(default_start, default_end),
            key="alarm_date_range",
        )

        # 处理用户选择的日期范围
        if isinstance(date_range, (tuple, list)):
            if len(date_range) == 2:
                start_date, end_date = date_range
            elif len(date_range) == 1:
                start_date = end_date = date_range[0]
            else:
                start_date, end_date = default_start, default_end
        else:
            start_date = end_date = date_range

        if start_date > end_date:
            st.warning("开始日期不能晚于结束日期。")
            filtered_alarms = alarm_df.iloc[0:0].copy()
        else:
            trigger_dates = alarm_df["trigger_time"].dt.date

            mask = (
                    (trigger_dates >= start_date)
                    & (trigger_dates <= end_date)
            )

            filtered_alarms = alarm_df.loc[mask].copy()

        # 最近的报警排在前面
        filtered_alarms = filtered_alarms.sort_values(
            "trigger_time",
            ascending=False,
            na_position="last",
        )

        st.caption(
            f"当前筛选范围：{start_date} 至 {end_date}，"
            f"共找到 {len(filtered_alarms)} 条报警记录。"
        )

        # 表格显示
        display_columns = [
            "event_id",
            "记录状态",
            "start_time",
            "trigger_time",
            "end_time",
            "sample_count",
            "max_torque",
            "duration_seconds",
        ]

        display_names = {
            "event_id": "报警事件 ID",
            "记录状态": "记录状态",
            "start_time": "报警开始时间",
            "trigger_time": "报警触发时间",
            "end_time": "报警结束时间",
            "sample_count": "超限采样点数",
            "max_torque": "最大扭矩 (N·m)",
            "duration_seconds": "持续时间 (秒)",
        }

        st.dataframe(
            filtered_alarms[display_columns].rename(
                columns=display_names
            ),
            use_container_width=True,
            hide_index=True,
        )

        # 导出筛选后的完整记录
        csv_data = filtered_alarms.to_csv(
            index=False,
        ).encode("utf-8-sig")

        st.download_button(
            label="下载筛选后的报警记录 CSV",
            data=csv_data,
            file_name="alarm_events_filtered.csv",
            mime="text/csv",
            disabled=filtered_alarms.empty,
        )

        st.caption(
            "说明：日期筛选依据报警触发时间。"
            "未记录结束时间不一定代表设备当前仍处于报警状态。"
        )

# =====================================
# 6. 原始数据查询
# =====================================

with st.expander("查看最近 20 条设备采集记录"):

    if not equipment_df.empty:
        st.dataframe(
            equipment_df.tail(20).iloc[::-1],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("当前没有设备采集记录。")
