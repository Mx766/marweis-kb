# -*- coding: utf-8 -*-
"""运维任务中心：数据更新任务（网页触发 + 维护机代理执行）。"""
import asyncio
import uuid as _uuid
from datetime import datetime, timezone
from datetime import timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_role
from app.config import settings
from app.database import async_session_maker, get_db
from app.models.ops_task import OpsTask
from app.models.user import User

router = APIRouter(prefix="/ops", tags=["运维任务"])
agent_router = APIRouter(prefix="/ops/agent", tags=["运维任务代理"])

TASK_LABELS = {
    "cmde": "CMDE 一键更新",
    "nmpa": "NMPA 补采导入",
    "qa": "省级 Q&A 更新",
    "all": "自动更新全流程",
    "nifdc": "NIFDC 增量",
}

SERVER_CMDS = {
    "qa": "cd {project} && python3 ops/autoupdate/collect_qa.py && python3 ops/autoupdate/import_updates.py && python3 scripts/rebuild_indexes.py",
    "all": "cd {project} && bash ops/autoupdate/run_autoupdate.sh",
    "nifdc": "cd {project} && python3 ops/autoupdate/collect_nifdc.py && python3 ops/autoupdate/import_updates.py && python3 scripts/rebuild_indexes.py",
}

AGENT_STALE_HOURS = 24
SERVER_STALE_HOURS = 3


async def _recover_stale_tasks(db: AsyncSession) -> None:
    """回收卡死的任务：代理任务超时重新排队，服务器任务超时标记失败。"""
    now = datetime.now(timezone.utc)
    agent_stale = now - timedelta(hours=AGENT_STALE_HOURS)
    server_stale = now - timedelta(hours=SERVER_STALE_HOURS)
    agent_rows = (
        await db.execute(
            select(OpsTask).where(
                OpsTask.status == "running",
                OpsTask.task_type.in_(["cmde", "nmpa"]),
                OpsTask.heartbeat_at.is_(None),
                OpsTask.started_at < agent_stale,
            )
        )
    ).scalars().all()
    for t in agent_rows:
        t.status = "pending"
        t.started_at = None
    if agent_rows:
        await db.flush()
    agent_rows2 = (
        await db.execute(
            select(OpsTask).where(
                OpsTask.status == "running",
                OpsTask.task_type.in_(["cmde", "nmpa"]),
                OpsTask.heartbeat_at.is_not(None),
                OpsTask.heartbeat_at < agent_stale,
            )
        )
    ).scalars().all()
    for t in agent_rows2:
        t.status = "pending"
        t.started_at = None
    if agent_rows2:
        await db.flush()
    server_rows = (
        await db.execute(
            select(OpsTask).where(
                OpsTask.status == "running",
                OpsTask.task_type.notin_(["cmde", "nmpa"]),
                OpsTask.started_at < server_stale,
            )
        )
    ).scalars().all()
    for t in server_rows:
        t.status = "failed"
        t.finished_at = now
    if server_rows or agent_rows or agent_rows2:
        await db.commit()


async def _append_log(task_id: _uuid.UUID, line: str) -> None:
    async with async_session_maker() as db:
        task = await db.get(OpsTask, task_id)
        if task:
            task.log = (task.log + line + "\n")[-200_000:]
            task.heartbeat_at = datetime.now(timezone.utc)
            await db.commit()


async def _run_server_task(task_id: _uuid.UUID, task_type: str) -> None:
    project = "/opt/enterprise-kb"
    cmd = SERVER_CMDS[task_type].format(project=project)
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    assert proc.stdout is not None
    while True:
        line = await proc.stdout.readline()
        if not line:
            break
        text = line.decode("utf-8", errors="replace").rstrip()
        if text:
            await _append_log(task_id, text)
    rc = await proc.wait()
    async with async_session_maker() as db:
        task = await db.get(OpsTask, task_id)
        if task:
            task.status = "success" if rc == 0 else "failed"
            task.finished_at = datetime.now(timezone.utc)
            await db.commit()


def _task_item(t: OpsTask) -> dict:
    return {
        "id": str(t.id),
        "task_type": t.task_type,
        "label": TASK_LABELS.get(t.task_type, t.task_type),
        "status": t.status,
        "agent": t.agent,
        "created_by": t.created_by,
        "log": t.log,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "started_at": t.started_at.isoformat() if t.started_at else None,
        "finished_at": t.finished_at.isoformat() if t.finished_at else None,
        "heartbeat_at": t.heartbeat_at.isoformat() if t.heartbeat_at else None,
    }


@router.get("/tasks")
async def list_tasks(
    status: str | None = Query(None),
    limit: int = Query(30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("super_admin")),
):
    await _recover_stale_tasks(db)
    conds = []
    if status:
        conds.append(OpsTask.status == status)
    rows = (
        await db.execute(
            select(OpsTask).where(*conds).order_by(OpsTask.created_at.desc()).limit(limit)
        )
    ).scalars().all()
    return {"items": [_task_item(t) for t in rows]}


@router.get("/tasks/{task_id}")
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("super_admin")),
):
    task = await db.get(OpsTask, _uuid.UUID(task_id))
    if not task:
        raise HTTPException(404, "任务不存在")
    return _task_item(task)


@router.post("/tasks")
async def create_task(
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("super_admin")),
):
    task_type = (body.get("task_type") or "").strip()
    if task_type not in TASK_LABELS:
        raise HTTPException(400, f"未知任务类型，可选：{', '.join(TASK_LABELS)}")
    task = OpsTask(
        task_type=task_type,
        status="pending",
        created_by=current_user.username,
    )
    existing = (
        await db.execute(
            select(OpsTask).where(
                OpsTask.task_type == task_type,
                OpsTask.status.in_(["pending", "running"]),
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(409, f"同类型任务已在排队/执行中（id={existing.id}）")
    db.add(task)
    await db.commit()
    await db.refresh(task)
    if task_type in SERVER_CMDS:
        # 服务器直接执行
        task.status = "running"
        task.started_at = datetime.now(timezone.utc)
        task.heartbeat_at = datetime.now(timezone.utc)
        await db.commit()
        asyncio.create_task(_run_server_task(task.id, task_type))
    return _task_item(task)


def _check_agent_key(x_agent_key: str | None) -> None:
    expected = getattr(settings, "OPS_AGENT_KEY", "") or ""
    if not expected or x_agent_key != expected:
        raise HTTPException(403, "无效的代理密钥")


@agent_router.get("/tasks/pending")
async def agent_pending(
    x_agent_key: str | None = Header(default=None, alias="X-Agent-Key"),
    db: AsyncSession = Depends(get_db),
):
    _check_agent_key(x_agent_key)
    await _recover_stale_tasks(db)
    row = (
        await db.execute(
            select(OpsTask)
            .where(OpsTask.status == "pending", OpsTask.task_type.in_(["cmde", "nmpa"]))
            .order_by(OpsTask.created_at.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
        )
    ).scalar_one_or_none()
    if not row:
        return {"task": None}
    row.status = "running"
    row.started_at = datetime.now(timezone.utc)
    row.heartbeat_at = datetime.now(timezone.utc)
    await db.commit()
    return {"task": _task_item(row)}


@agent_router.post("/tasks/{task_id}/log")
async def agent_append_log(
    task_id: str,
    body: dict,
    x_agent_key: str | None = Header(default=None, alias="X-Agent-Key"),
):
    _check_agent_key(x_agent_key)
    line = (body.get("line") or "").strip()
    if line:
        await _append_log(_uuid.UUID(task_id), line)
    return {"ok": True}


@agent_router.post("/tasks/{task_id}/finish")
async def agent_finish(
    task_id: str,
    body: dict,
    x_agent_key: str | None = Header(default=None, alias="X-Agent-Key"),
    db: AsyncSession = Depends(get_db),
):
    _check_agent_key(x_agent_key)
    task = await db.get(OpsTask, _uuid.UUID(task_id))
    if not task:
        raise HTTPException(404, "任务不存在")
    task.status = "success" if body.get("status") == "success" else "failed"
    task.finished_at = datetime.now(timezone.utc)
    task.agent = body.get("agent") or task.agent
    await db.commit()
    return {"ok": True}
