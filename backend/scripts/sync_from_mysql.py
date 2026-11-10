"""
MySQL 数据接入脚本 —— 模拟企业从 CRM 表同步维修记录到 Chroma
运行方式：
    cd e:\baishan2607c\projects\project1-enterprise-rag\backend
    uv run --project e:\baishan2607c\05_RAG python scripts/sync_from_mysql.py

模拟数据：工厂 CRM 系统的维修记录表 repair_records
字段：fault_desc（故障描述）、solution（解决方案）、device_type（设备型号）、report_time（报修时间）
"""
import sys
sys.path.insert(0, ".")

from langchain_core.documents import Document
from core.vectorstore import get_vectorstore, add_documents
from core.parser import split_text

# ========== 模拟的 MySQL CRM 维修数据（实际生产用 pymysql 连数据库查） ==========
# 面试时可以说"生产环境用 pymysql 连 MySQL 的 CRM 表同步"
MOCK_CRM_DATA = [
    {"fault_desc": "CK6132 普通车床主轴异响，开机 15 分钟后出现，转速越高越明显",
     "solution": "1. 检查主轴轴承型号 6207，发现外圈有疲劳剥落 → 更换新轴承\n2. 检查齿轮啮合间隙，调整到 0.12mm\n3. 加注主轴润滑油至正常液位",
     "device_type": "CK6132", "report_time": "2026-10-15"},
    {"fault_desc": "CK6140 数控车床伺服过载报警 E0201，刀塔快速移动时触发",
     "solution": "1. 检查 X 轴伺服电机负载，发现负载率 115%（正常值 <80%）\n2. 检查丝杠润滑，发现润滑脂干涸 → 清洗丝杠加新润滑脂\n3. 降低快速移动速度参数 FANUC P1420 从 3000 降到 2500",
     "device_type": "CK6140", "report_time": "2026-10-20"},
    {"fault_desc": "VMC850 立式加工中心 Z 轴抖动，加工表面出现振纹",
     "solution": "1. 检查气缸压力，发现只有 0.25MPa（正常值 0.4MPa）→ 调整减压阀\n2. 检查 FANUC P1825 Z 轴伺服增益，从 150 调整到 120\n3. 检查立柱导轨润滑，补充导轨油",
     "device_type": "VMC850", "report_time": "2026-10-22"},
    {"fault_desc": "CK6132 液压系统压力不稳定，加工尺寸波动大",
     "solution": "1. 检查液压泵出口压力，发现在 3.2~5.1MPa 之间波动（要求 4.5±0.2MPa）\n2. 检查溢流阀，发现阀芯磨损 → 更换溢流阀\n3. 检查油管接头，发现有轻微泄漏 → 更换密封圈",
     "device_type": "CK6132", "report_time": "2026-10-25"},
    {"fault_desc": "VMC850 冷却液液位报警，但液位实际在正常范围",
     "solution": "1. 检查液位传感器，发现探头表面有冷却液结晶 → 用砂纸打磨清洁\n2. 检查冷却液浓度，发现浓度过高（15%→调整到 8%）\n3. 复位报警后正常",
     "device_type": "VMC850", "report_time": "2026-10-28"},
]


def sync_from_mysql():
    """模拟从 MySQL CRM 表同步数据到 Chroma"""
    print("=" * 60)
    print("📥 MySQL CRM → Chroma 数据接入")
    print("=" * 60)
    print(f"📋 准备同步 {len(MOCK_CRM_DATA)} 条维修记录...\n")

    chunks = []
    for row in MOCK_CRM_DATA:
        # 拼接成完整的故障记录文档
        text = (
            f"【设备型号】{row['device_type']}\n"
            f"【故障描述】{row['fault_desc']}\n"
            f"【解决方案】{row['solution']}\n"
            f"【报修时间】{row['report_time']}\n"
        )
        # 分块 + metadata
        c = split_text(
            text,
            source=f"CRM_{row['report_time']}_{row['device_type']}",
            device=row["device_type"],
            security_level="V1",
        )
        chunks.extend(c)

    # 入库
    print(f"⏳ 向量化 {len(chunks)} 个 chunk...")
    add_documents(chunks)
    print(f"✅ 入库完成！新增 {len(chunks)} 个向量碎片")

    vs = get_vectorstore()
    print(f"📊 Chroma 总碎片数：{vs._collection.count()}")
    print("\n💡 面试话术：")
    print("  我做了一个数据接入层，能从 MySQL 企业 CRM 表同步维修记录到 Chroma——")
    print("  生产环境用 pymysql 连数据库，查 repair_records 表，")
    print("  每条记录拼成文本文档后分块、打 metadata（device_type + security_level），")
    print("  然后批量 add_documents 进 Chroma。这是企业真实的做法，")
    print("  不是把故障手册手动转成 Markdown。")
    print("=" * 60)


if __name__ == "__main__":
    sync_from_mysql()
