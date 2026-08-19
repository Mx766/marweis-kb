"""Device registration department API — knowledge graph and specialized search."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.auth import get_current_user_optional
from app.models.user import User
from app.models.document import Document
from app.models.category import Category
from app.permissions import PermissionService

router = APIRouter(prefix="/api/device-reg", tags=["器械注册"])

# The 8 modules of device registration department
DEVICE_MODULES = [
    "公共文件",
    "参考文件",
    "共性问题",
    "分类目录",
    "技术要求",
    "临床评价",
    "审评意见",
    "OA注册资料",
]


@router.get("/knowledge-graph")
async def knowledge_graph(
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    """
    Generate knowledge graph data for the device registration department.
    Returns nodes (categories) and links (parent-child relationships).
    Shows the 7-module workflow structure with all sub-categories.
    """
    # Find the 7 top-level modules
    modules_result = await db.execute(
        select(Category).where(Category.name.in_(DEVICE_MODULES))
    )
    modules = modules_result.scalars().all()
    if not modules:
        return {"nodes": [], "links": []}

    module_ids = {str(m.id) for m in modules}

    # Collect all descendants recursively
    all_cats = await db.execute(
        select(Category.id, Category.name, Category.parent_id)
    )
    children_map: dict[str, list] = {}
    name_map: dict[str, str] = {}
    for cid, cname, cpid in all_cats:
        name_map[str(cid)] = cname
        pid_str = str(cpid) if cpid else None
        if pid_str:
            children_map.setdefault(pid_str, []).append((str(cid), cname))

    def get_descendants(pid_str: str) -> list[str]:
        """Get all descendant category IDs."""
        result = [pid_str]
        for cid, _ in children_map.get(pid_str, []):
            result.extend(get_descendants(cid))
        return result

    # Collect all IDs in the device reg subtree
    all_ids: set[str] = set()
    for m in modules:
        all_ids.update(get_descendants(str(m.id)))

    # 权限过滤：只返回当前用户可见分类（与分类列表接口一致）
    if not (current_user and current_user.role == "super_admin"):
        perm = PermissionService(db, current_user)
        visible = await perm.get_visible_category_ids()
        visible_str = {str(v) for v in visible}
        all_ids = {cid for cid in all_ids if cid in visible_str}

    # Doc counts per category
    doc_counts_result = await db.execute(
        select(Document.category_id, func.count(Document.id))
        .where(
            Document.category_id.in_([cid for cid in all_ids]),
            Document.is_deleted == False,
        )
        .group_by(Document.category_id)
    )
    doc_counts = {str(r[0]): r[1] for r in doc_counts_result.all()}

    # Colors for the 8 modules
    module_colors = [
        "#1e50ae", "#2e86c1", "#27ae60", "#8e44ad", "#e74c3c",
        "#f39c12", "#16a085", "#e67e22",
    ]
    module_color_map: dict[str, str] = {}
    for i, m in enumerate(modules):
        for cid in get_descendants(str(m.id)):
            module_color_map[cid] = module_colors[i % len(module_colors)]

    nodes = []
    links = []

    # Create a virtual root node
    virtual_root_id = "root_device_reg"
    nodes.append({
        "id": virtual_root_id,
        "name": "器械注册知识体系",
        "label": "器械注册",
        "symbolSize": 40,
        "category": 0,
        "value": sum(doc_counts.get(cid, 0) for cid in all_ids),
    })

    # Build category nodes
    for cid in all_ids:
        cname = name_map.get(cid, "")
        cnt = doc_counts.get(cid, 0)

        # Determine depth and symbol size
        depth = cname.count("  ") if cname.startswith("  ") else 0
        symbol_size = max(12, min(50, 10 + cnt * 0.3)) if cnt > 0 else 12

        # Short label for display
        label = cname
        # Strip numbering prefixes for readability
        short = label
        for prefix in [
            "01_", "02_", "03_", "04_", "05_", "06_", "07_", "08_",
            "09_", "10_", "11_", "12_", "13_", "14_", "15_", "16_",
            "17_", "18_", "19_", "20_", "21_", "22_", "23_",
        ]:
            if short.startswith(prefix):
                short = short[3:]
                break
        if len(short) > 10:
            short = short[:10] + ".."

        nodes.append({
            "id": cid,
            "name": cname,
            "label": short,
            "symbolSize": symbol_size,
            "category": 1 if cid in module_ids else 2,
            "value": cnt,
            "itemStyle": {"color": module_color_map.get(cid, "#999")},
        })

        # Link to parent
        parent_id = None
        for pid_str, children in children_map.items():
            if any(child_id == cid for child_id, _ in children):
                parent_id = pid_str
                break

        if parent_id and parent_id in all_ids:
            links.append({
                "source": parent_id,
                "target": cid,
                "value": cnt,
            })
        elif cid in module_ids:
            # Link module directly to virtual root
            links.append({
                "source": virtual_root_id,
                "target": cid,
                "value": cnt,
            })

    # Add 临床研究部ss-links between modules (reference lines)
    module_id_list = [str(m.id) for m in modules]
    for i in range(len(module_id_list)):
        for j in range(i + 1, len(module_id_list)):
            links.append({
                "source": module_id_list[i],
                "target": module_id_list[j],
                "value": 1,
                "lineStyle": {"type": "dashed", "opacity": 0.3, "color": "#ccc"},
            })

    # Document type nodes per category
    type_labels = {
        "pdf": ("PDF", "#e74c3c"),
        "doc": ("Word", "#2980b9"),
        "docx": ("Word", "#2980b9"),
        "xls": ("Excel", "#27ae60"),
        "xlsx": ("Excel", "#27ae60"),
        "link": ("链接", "#8e44ad"),
    }

    cat_types = await db.execute(
        select(Document.category_id, Document.file_type, func.count(Document.id))
        .where(
            Document.category_id.in_([cid for cid in all_ids if cid not in module_ids]),
            Document.is_deleted == False,
        )
        .group_by(Document.category_id, Document.file_type)
    )

    for cid, ft, cnt in cat_types.all():
        if cnt < 5:
            continue
        if ft not in type_labels:
            continue
        tlabel, tcolor = type_labels[ft]
        node_id = f"type_{cid}_{ft}"
        nodes.append({
            "id": node_id,
            "name": tlabel,
            "label": f"{tlabel}({cnt})",
            "symbolSize": max(8, min(30, 8 + cnt)),
            "category": 3,
            "value": cnt,
            "itemStyle": {"color": tcolor},
        })
        links.append({
            "source": str(cid),
            "target": node_id,
            "value": cnt,
        })

    return {
        "nodes": nodes,
        "links": links,
        "categories": [
            {"name": "根节点"},
            {"name": "工作流模块"},
            {"name": "子分类"},
            {"name": "文档类型"},
        ],
        "title": "器械注册知识体系",
        "totalDocs": sum(doc_counts.values()),
        "catCount": len(all_ids),
    }
