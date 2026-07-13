"""Seed script — creates initial admin user, departments, categories, and sample documents."""
import asyncio
import uuid
import os
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.config import settings, DEPARTMENTS
from app.auth import hash_password
from app.models.user import User
from app.models.category import Category
from app.models.document import Document
from scripts.demo_files.generate_demo_files import generate_demo_files
from io import BytesIO

CATEGORIES_DATA = [
    {"name": "公共知识区", "icon": "folder", "visible": None,
     "children": [
         {"name": "行业新闻 & 法规动态", "icon": "news", "visible": None},
         {"name": "NMPA 法规库", "icon": "law", "visible": None},
         {"name": "FDA 法规库", "icon": "law", "visible": None},
         {"name": "CE MDR 法规库", "icon": "law", "visible": None},
         {"name": "公司制度 & 通用 SOP", "icon": "doc", "visible": None},
         {"name": "培训资料（通用）", "icon": "book", "visible": None},
     ]},
    {"name": "器械注册部", "icon": "registered", "visible": ["器械注册部"],
     "children": [
         {"name": "I类医疗器械注册", "icon": "doc", "visible": ["器械注册部"]},
         {"name": "II类医疗器械注册", "icon": "doc", "visible": ["器械注册部"]},
         {"name": "III类医疗器械注册", "icon": "doc", "visible": ["器械注册部"]},
         {"name": "检测代理", "icon": "flask", "visible": ["器械注册部"]},
         {"name": "分类界定", "icon": "tag", "visible": ["器械注册部"]},
         {"name": "创新申报", "icon": "star", "visible": ["器械注册部"]},
         {"name": "应急补发", "icon": "clock", "visible": ["器械注册部"]},
         {"name": "注册申报模板 & 案例库", "icon": "archive", "visible": ["器械注册部"]},
     ]},
    {"name": "临床评价部（CER）", "icon": "chart", "visible": ["临床评价部"],
     "children": [
         {"name": "临床评价报告模板", "icon": "doc", "visible": ["临床评价部"]},
         {"name": "等同性论证文献库", "icon": "book", "visible": ["临床评价部"]},
         {"name": "CER 案例库", "icon": "archive", "visible": ["临床评价部"]},
         {"name": "评价方法学指南", "icon": "guide", "visible": ["临床评价部"]},
     ]},
    {"name": "临床试验部（CRO + 善芃 SMO）", "icon": "monitor", "visible": ["临床试验部"],
     "children": [
         {"name": "临床试验方案库", "icon": "doc", "visible": ["临床试验部"]},
         {"name": "GCP 规范 & 稽查指南", "icon": "law", "visible": ["临床试验部"]},
         {"name": "中心筛选 & 患者招募 SOP", "icon": "guide", "visible": ["临床试验部"]},
         {"name": "数据统计分析模板", "icon": "excel", "visible": ["临床试验部"]},
         {"name": "临床试验报告模板", "icon": "doc", "visible": ["临床试验部"]},
         {"name": "SMO 操作手册", "icon": "book", "visible": ["临床试验部"]},
     ]},
    {"name": "生产体系部", "icon": "gear", "visible": ["生产体系部"],
     "children": [
         {"name": "ISO13485 体系文件", "icon": "doc", "visible": ["生产体系部"]},
         {"name": "质量手册 & 程序文件", "icon": "book", "visible": ["生产体系部"]},
         {"name": "模拟体考检查清单", "icon": "checklist", "visible": ["生产体系部"]},
         {"name": "供应商审核指南", "icon": "guide", "visible": ["生产体系部"]},
         {"name": "体系培训资料", "icon": "book", "visible": ["生产体系部"]},
     ]},
    {"name": "化妆品·医美部（迈美丝）", "icon": "cosmetic", "visible": ["化妆品·医美部"],
     "children": [
         {"name": "进口化妆品备案", "icon": "doc", "visible": ["化妆品·医美部"]},
         {"name": "国产特殊化妆品注册", "icon": "doc", "visible": ["化妆品·医美部"]},
         {"name": "新原料注册备案", "icon": "flask", "visible": ["化妆品·医美部"]},
         {"name": "化妆品法规库", "icon": "law", "visible": ["化妆品·医美部"]},
     ]},
    {"name": "特医食品部（大道力维）", "icon": "food", "visible": ["特医食品部"],
     "children": [
         {"name": "特医食品注册指南", "icon": "doc", "visible": ["特医食品部"]},
         {"name": "临床试验方案", "icon": "doc", "visible": ["特医食品部"]},
         {"name": "产品标准 & 检测方法", "icon": "standard", "visible": ["特医食品部"]},
         {"name": "特医食品法规库", "icon": "law", "visible": ["特医食品部"]},
     ]},
    {"name": "管理层专区", "icon": "shield", "visible": ["管理层"],
     "children": [
         {"name": "战略规划 & 经营数据", "icon": "chart", "visible": ["管理层"]},
         {"name": "客户合同 & 报价模板", "icon": "doc", "visible": ["管理层"]},
         {"name": "各部门月度报告", "icon": "report", "visible": ["管理层"]},
     ]},
]

SAMPLE_DOCUMENTS = [
    # 公共知识区 - NMPA法规库
    {"title": "医疗器械监督管理条例（2025修订）", "category": "NMPA 法规库",
     "tags": ["法规", "监督管理", "2025"], "source": "国务院", "file_type": "link",
     "summary": "《医疗器械监督管理条例》于2025年修订施行，明确了医疗器械全生命周期监管要求，涵盖注册备案、生产、经营、使用等环节。",
     "source_url": "https://www.nmpa.gov.cn/xxgk/fgwj/flxzhg/20241101151126150.html"},
    {"title": "医疗器械注册管理办法（2025版）", "category": "NMPA 法规库",
     "tags": ["注册管理", "2025"], "source": "NMPA", "file_type": "link",
     "summary": "规范医疗器械注册管理，明确注册申请、技术审评、行政审批等流程和要求。",
     "source_url": "https://www.nmpa.gov.cn/ylqx/ylqxfgwj/ylqxbmgzh/20250101181001561.html"},
    {"title": "体外诊断试剂注册管理办法", "category": "NMPA 法规库",
     "tags": ["IVD", "注册管理"], "source": "NMPA", "file_type": "link",
     "summary": "规范体外诊断试剂产品注册管理，包括注册检验、临床试验、技术审评等。",
     "source_url": "https://www.nmpa.gov.cn/ylqx/ylqxfgwj/ylqxbmgzh/20231215171014152.html"},
    {"title": "医疗器械分类目录（2024修订版）", "category": "NMPA 法规库",
     "tags": ["分类目录", "2024"], "source": "NMPA", "file_type": "link",
     "summary": "明确医疗器械产品分类框架和具体类别，新增AI医疗软件等分类条目。",
     "source_url": "https://www.nmpa.gov.cn/ylqx/ylqxggtg/ylqxzhgg/20240411091014152.html"},

    # 器械注册部 - III类
    {"title": "三类医疗器械注册申报指南 v3.2", "category": "III类医疗器械注册",
     "tags": ["注册申报", "三类器械", "2025版"], "source": "CMDE", "file_type": "link",
     "summary": "三类医疗器械注册申报全流程指南，包括产品技术要求编写、检测要点、临床评价策略。",
     "source_url": "https://www.cmde.org.cn/xwdt/zxyw/20250301151014152.html"},
    {"title": "创新医疗器械特别审查程序", "category": "创新申报",
     "tags": ["创新", "绿色通道"], "source": "NMPA", "file_type": "link",
     "summary": "创新医疗器械特别审查程序申请指南，适用于具有核心技术发明专利、国际领先水平的产品。",
     "source_url": "https://www.nmpa.gov.cn/ylqx/ylqxggtg/ylqxzhgg/20250120171014152.html"},
    {"title": "射频消融仪NMPA注册案例", "category": "注册申报模板 & 案例库",
     "tags": ["案例", "有源器械", "射频消融"], "source": "迈瑞生项目组", "file_type": "link",
     "summary": "高频手术系统/射频消融仪的注册申报成功案例，包含技术资料清单和审评沟通记录。",
     "source_url": "https://www.maris-reg.com/nd.jsp?id=870"},

    # 临床评价部
    {"title": "医疗器械临床评价技术指导原则（2025版）", "category": "评价方法学指南",
     "tags": ["临床评价", "技术指导", "2025"], "source": "CMDE", "file_type": "link",
     "summary": "更新版临床评价技术指导原则，明确了临床评价报告的撰写要求、等同性论证路径和评价流程。",
     "source_url": "https://www.cmde.org.cn/CL0112/25300.html"},
    {"title": "角膜交联仪临床评价报告", "category": "CER 案例库",
     "tags": ["案例", "眼科器械", "CER"], "source": "迈瑞生项目组", "file_type": "link",
     "summary": "迈瑞生助力Iromed公司角膜交联仪免临床评价通过NMPA审批的成功案例。",
     "source_url": "https://www.maris-reg.com/nd.jsp?id=831"},

    # 临床试验部
    {"title": "GCP规范与临床试验质量管理指南", "category": "GCP 规范 & 稽查指南",
     "tags": ["GCP", "质量管理", "稽查"], "source": "NMPA", "file_type": "link",
     "summary": "药物/医疗器械临床试验质量管理规范（GCP）最新版本，含稽查要点和常见问题解答。",
     "source_url": "https://www.nmpa.gov.cn/xxgk/fgwj/gzwj/gzwjyp/20231215171014152.html"},
    {"title": "中日友好医院临床试验SMO优选经验总结", "category": "SMO 操作手册",
     "tags": ["SMO", "临床研究", "中日友好医院"], "source": "善芃", "file_type": "link",
     "summary": "北京善芃入选中日友好医院优选SMO名单的经验分享，含中心筛选和患者招募策略。",
     "source_url": "https://www.maris-reg.com/nd.jsp?id=960"},

    # 生产体系部
    {"title": "ISO 13485:2016 医疗器械质量管理体系", "category": "ISO13485 体系文件",
     "tags": ["ISO13485", "质量管理", "体系"], "source": "ISO", "file_type": "link",
     "summary": "ISO 13485:2016医疗器械质量管理体系标准全文，适用于医疗器械全生命周期的质量管理。",
     "source_url": "https://www.iso.org/standard/59752.html"},
    {"title": "模拟体考全流程检查清单", "category": "模拟体考检查清单",
     "tags": ["体考", "检查", "清单"], "source": "迈瑞生项目组", "file_type": "link",
     "summary": "医疗器械注册体考（医疗器械生产质量管理规范现场检查）全流程准备清单和注意事项。",
     "source_url": "https://www.nmpa.gov.cn/ylqx/ylqxggtg/ylqxzhgg/20250301181014152.html"},

    # 化妆品·医美部
    {"title": "进口化妆品注册备案全流程指南", "category": "进口化妆品备案",
     "tags": ["进口", "化妆品", "备案"], "source": "NMPA", "file_type": "link",
     "summary": "进口非特殊用途化妆品备案管理要求及全流程操作指南，含备案资料清单。",
     "source_url": "https://www.nmpa.gov.cn/hzhp/hzhpfgwj/hzhpbmgzh/20240101151014152.html"},
    {"title": "医美广告合规指引解读（北京朝阳 2026）", "category": "化妆品法规库",
     "tags": ["医美", "广告", "合规", "2026"], "source": "北京朝阳市场监管局", "file_type": "link",
     "summary": "北京市朝阳区发布的首个医美广告合规指引，禁止效果对比，禁止推荐官、体验官宣传。",
     "source_url": "https://www.maris-reg.com/nd.jsp?id=971"},

    # 特医食品部
    {"title": "特殊医学用途配方食品注册管理办法", "category": "特医食品注册指南",
     "tags": ["特医食品", "注册管理"], "source": "市场监管总局", "file_type": "link",
     "summary": "规范特殊医学用途配方食品注册管理，包括申请、研制现场核查、抽样检验、技术审评等。",
     "source_url": "https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/tssps/art/2023/art_202312.html"},
    {"title": "特医食品临床试验质量管理规范", "category": "临床试验方案",
     "tags": ["特医食品", "临床试验", "GCP"], "source": "市场监管总局", "file_type": "link",
     "summary": "特殊医学用途配方食品临床试验质量管理规范，涵盖方案设计、知情同意、数据管理等内容。",
     "source_url": "https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/tssps/art/2024/art_202403.html"},

    # FDA法规库
    {"title": "FDA 21 CFR Part 820 质量体系法规", "category": "FDA 法规库",
     "tags": ["FDA", "QSR", "质量体系"], "source": "FDA", "file_type": "link",
     "summary": "FDA 21 CFR Part 820 质量体系法规（QSR），规定了医疗器械CGMP要求。FDA正在推进QSR与ISO 13485的协调工作。",
     "source_url": "https://www.ecfr.gov/current/title-21/chapter-I/subchapter-H/part-820"},
    {"title": "EU MDR 2017/745 医疗器械法规", "category": "CE MDR 法规库",
     "tags": ["EU MDR", "CE认证", "欧洲"], "source": "欧盟委员会", "file_type": "link",
     "summary": "EU Medical Device Regulation (MDR) 2017/745 是欧盟医疗器械监管的核心法规，对技术文档、临床评价等提出更高要求。",
     "source_url": "https://eur-lex.europa.eu/eli/reg/2017/745/oj"},
]

# ---------------------------------------------------------------------------
# File-type sample documents — MinIO keys are assigned at upload time
# ---------------------------------------------------------------------------
FILE_SAMPLE_DOCUMENTS = [
    {
        "title": "医疗器械注册流程指南（示例PDF）",
        "category": "II类医疗器械注册",
        "tags": ["注册流程", "示例", "PDF"],
        "summary": "自动生成的PDF示例文档，介绍医疗器械注册流程和NMPA法规要点，用于测试文件上传和预览功能。",
        "source": "迈瑞生知识库",
        "demo_file": "sample_guide.pdf",
    },
    {
        "title": "注册文档管理快速参考（示例TXT）",
        "category": "注册申报模板 & 案例库",
        "tags": ["快速参考", "注册分类", "示例"],
        "summary": "纯文本格式的医疗器械注册文档管理快速参考，涵盖注册分类、关键法规和技术文档清单。",
        "source": "迈瑞生知识库",
        "demo_file": "sample_notes.txt",
    },
    {
        "title": "临床评价报告（CER）撰写模板（示例Markdown）",
        "category": "临床评价报告模板",
        "tags": ["模板", "CER", "临床评价", "示例"],
        "summary": "Markdown格式的临床评价报告撰写模板，包含基本信息、评价范围、等同性论证要点和参考文献。",
        "source": "迈瑞生知识库",
        "demo_file": "sample_readme.md",
    },
]


def _upload_file_bytes_to_minio(file_name: str, file_bytes: bytes, mime_type: str) -> dict:
    """Upload bytes to MinIO and return the Document field values (no preview conversion)."""
    import boto3

    s3 = boto3.client(
        "s3",
        endpoint_url=f"{'https' if settings.MINIO_SECURE else 'http'}://{settings.MINIO_ENDPOINT}",
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
    )

    # Ensure bucket exists
    try:
        s3.head_bucket(Bucket=settings.MINIO_BUCKET)
    except Exception:
        s3.create_bucket(Bucket=settings.MINIO_BUCKET)

    object_key = f"originals/{uuid.uuid4()}/{file_name}"
    ext = file_name.rsplit(".", 1)[-1] if "." in file_name else ""
    s3.upload_fileobj(BytesIO(file_bytes), settings.MINIO_BUCKET, object_key)

    return {
        "original_path": f"s3://{settings.MINIO_BUCKET}/{object_key}",
        "file_size": len(file_bytes),
        "file_ext": ext,
        "mime_type": mime_type,
        "original_filename": file_name,
    }


async def seed():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # Check if already seeded
        existing = (await db.execute(select(User).limit(1))).scalar_one_or_none()
        if existing:
            print("Database already seeded. Skipping.")
            return

        # Create admin user
        admin = User(
            username="admin",
            password_hash=hash_password("marweis2026"),
            display_name="系统管理员",
            department="管理层",
            role="super_admin",
            email="admin@maris-reg.com",
        )
        db.add(admin)

        # Create demo users for each department
        demo_users = [
            ("zhangsan", "器械部张三", "器械注册部", "dept_admin"),
            ("lisi", "临床评价部李四", "临床评价部", "dept_admin"),
            ("wangwu", "临床试验部王五", "临床试验部", "dept_admin"),
            ("zhaoliu", "生产体系部赵六", "生产体系部", "dept_admin"),
            ("sunqi", "医美部孙七", "化妆品·医美部", "dept_admin"),
            ("zhouba", "食品部周八", "特医食品部", "dept_admin"),
            ("wuqian", "器械工程师小吴", "器械注册部", "editor"),
            ("zhengshi", "临床专员小郑", "临床试验部", "editor"),
            ("test_user", "普通员工测试", "器械注册部", "employee"),
        ]
        demo_user_objects = {}
        for uname, dname, dept, role in demo_users:
            user = User(
                username=uname,
                password_hash=hash_password("123456"),
                display_name=dname,
                department=dept,
                role=role,
                is_active=True,
            )
            db.add(user)
            demo_user_objects[uname] = user

        await db.flush()

        # Create categories
        category_map: dict[str, str] = {}

        async def create_categories(items, parent_id=None):
            for item_data in items:
                children = item_data.pop("children", [])
                visible = item_data.pop("visible", None)
                cat = Category(
                    name=item_data["name"],
                    parent_id=parent_id,
                    icon=item_data.get("icon"),
                    visible_departments=visible,
                )
                db.add(cat)
                await db.flush()
                category_map[cat.name] = str(cat.id)
                if children:
                    await create_categories(children, cat.id)

        await create_categories(CATEGORIES_DATA)

        # ---- Generate and upload demo files to MinIO ----
        print("Generating demo files and uploading to MinIO ...")
        demo_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo_files")
        demo_file_bytes = generate_demo_files(demo_dir)

        MIME_MAP = {
            ".pdf": "application/pdf",
            ".txt": "text/plain",
            ".md": "text/markdown",
        }
        uploaded: dict[str, dict] = {}
        for file_name, file_data in demo_file_bytes.items():
            ext = "." + file_name.rsplit(".", 1)[-1] if "." in file_name else ""
            mime = MIME_MAP.get(ext, "application/octet-stream")
            uploaded[file_name] = _upload_file_bytes_to_minio(file_name, file_data, mime)
            print(f"  Uploaded: {file_name} ({len(file_data)} bytes)")

        # Create link-type sample documents
        for i, doc_data in enumerate(SAMPLE_DOCUMENTS):
            cat_name = doc_data.pop("category")
            cat_id = category_map.get(cat_name)

            # Assign uploader to a relevant user
            uploader = admin
            if "器械" in cat_name or "注册" in doc_data.get("tags", []):
                uploader = demo_user_objects.get("zhangsan", admin)
            elif "临床" in cat_name or "CER" in cat_name:
                uploader = demo_user_objects.get("lisi", admin)
            elif "CRO" in cat_name or "GCP" in cat_name:
                uploader = demo_user_objects.get("wangwu", admin)

            file_type = doc_data.get("file_type", "link")
            doc = Document(
                title=doc_data["title"],
                category_id=cat_id,
                file_type=file_type,
                original_filename=doc_data["source_url"] if file_type == "link" else doc_data["title"],
                original_path=doc_data["source_url"] if file_type == "link" else f"sample:{doc_data['title']}",
                file_ext="link" if file_type == "link" else "pdf",
                mime_type="text/html" if file_type == "link" else "application/pdf",
                tags=doc_data.get("tags", []),
                summary=doc_data.get("summary", ""),
                source=doc_data.get("source", ""),
                source_url=doc_data.get("source_url"),
                uploader_id=uploader.id,
                version=doc_data.get("version"),
                view_count=i * 7 % 200,
            )
            db.add(doc)

        link_count = len(SAMPLE_DOCUMENTS)

        # Create file-type sample documents (uploaded to MinIO)
        for doc_data in FILE_SAMPLE_DOCUMENTS:
            cat_name = doc_data.pop("category")
            demo_file = doc_data.pop("demo_file")
            cat_id = category_map.get(cat_name)

            minio_info = uploaded[demo_file]

            uploader = admin
            if "注册" in cat_name or "器械" in cat_name:
                uploader = demo_user_objects.get("zhangsan", admin)
            elif "临床" in cat_name or "CER" in cat_name:
                uploader = demo_user_objects.get("lisi", admin)

            doc = Document(
                title=doc_data["title"],
                category_id=cat_id,
                file_type="file",
                original_filename=minio_info["original_filename"],
                original_path=minio_info["original_path"],
                file_size=minio_info["file_size"],
                file_ext=minio_info["file_ext"],
                mime_type=minio_info["mime_type"],
                tags=doc_data.get("tags", []),
                summary=doc_data.get("summary", ""),
                source=doc_data.get("source", ""),
                source_url=None,
                uploader_id=uploader.id,
                version=doc_data.get("version"),
                view_count=0,
            )
            db.add(doc)

        await db.commit()
        print(
            f"Seed complete: 1 admin + {len(demo_users)} demo users + "
            f"{len(category_map)} categories + {link_count} link docs + "
            f"{len(FILE_SAMPLE_DOCUMENTS)} file docs"
        )


if __name__ == "__main__":
    asyncio.run(seed())
