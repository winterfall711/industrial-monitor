
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

            # 最新设备数据卡片
            col1, col2, col3 = st.columns(3)

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

            st.caption(
                f"最新采集时间："
                f"{latest['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}"
            )

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
# 5. 报警事件记录
# =====================================

st.markdown("---")
st.header("设备报警事件")

alarm_df = load_csv(ALARM_FILE)

if alarm_df.empty:
    st.info(
        "暂无报警记录，或者报警文件尚未生成。"
    )

else:
    st.caption(
        f"累计报警事件：{len(alarm_df)} 条"
    )

    # 先显示最近写入的 10 条记录
    recent_alarms = (
        alarm_df.tail(10)
        .iloc[::-1]
        .reset_index(drop=True)
    )

    st.dataframe(
        recent_alarms,
        use_container_width=True,
        hide_index=True,
    )

    st.caption(
        f"报警数据来源：{ALARM_FILE.name}"
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
