"""Agents REST API for dashboard."""
from datetime import date, datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_

from app.database import get_async_db
from app.models.agent import Agent, AgentStatus
from app.schemas.agent import (
    AgentResponse,
    AgentListResponse,
    AgentCreate,
    AgentUpdate,
    AgentStatusUpdate,
    AgentExport,
)
from app.services.websocket import websocket_manager

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get(
    "",
    response_model=AgentListResponse,
    summary="List all agents",
    description="Get paginated list of agents with optional filtering.",
)
async def list_agents(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search in name, category, language"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    category: Optional[str] = Query(None, description="Filter by category"),
    language: Optional[str] = Query(None, description="Filter by language"),
    sort: Optional[str] = Query("created_at:desc", description="Sort field:direction"),
    db: AsyncSession = Depends(get_async_db),
) -> AgentListResponse:
    query = select(Agent)
    count_query = select(func.count(Agent.id))

    if search:
        term = f"%{search}%"
        query = query.where(
            or_(
                Agent.name.ilike(term),
                Agent.category.ilike(term),
                Agent.language.ilike(term),
                Agent.info.ilike(term),
                Agent.token.ilike(term),
            )
        )
        count_query = count_query.where(
            or_(
                Agent.name.ilike(term),
                Agent.category.ilike(term),
                Agent.language.ilike(term),
                Agent.info.ilike(term),
                Agent.token.ilike(term),
            )
        )

    if is_active is not None:
        query = query.where(Agent.is_active == is_active)
        count_query = count_query.where(Agent.is_active == is_active)

    if category:
        query = query.where(Agent.category == category)
        count_query = count_query.where(Agent.category == category)

    if language:
        query = query.where(Agent.language == language)
        count_query = count_query.where(Agent.language == language)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    if sort:
        try:
            sort_field, sort_direction = sort.split(":")
            order_col = {
                "name": Agent.name,
                "category": Agent.category,
                "language": Agent.language,
                "created_at": Agent.created_at,
                "updated_at": Agent.updated_at,
            }.get(sort_field, Agent.created_at)
            if sort_direction.lower() == "asc":
                query = query.order_by(order_col.asc())
            else:
                query = query.order_by(order_col.desc())
        except ValueError:
            query = query.order_by(Agent.created_at.desc())
    else:
        query = query.order_by(Agent.created_at.desc())

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    agents = result.scalars().all()
    total_pages = (total + page_size - 1) // page_size

    return AgentListResponse(
        items=[AgentResponse.model_validate(a) for a in agents],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/filters",
    summary="Get filter options",
    description="Get all unique categories and languages for filter dropdowns.",
)
async def get_filter_options(
    db: AsyncSession = Depends(get_async_db),
) -> dict:
    category_result = await db.execute(select(Agent.category).distinct().order_by(Agent.category))
    categories = [row[0] for row in category_result.all() if row[0]]

    language_result = await db.execute(select(Agent.language).distinct().order_by(Agent.language))
    languages = [row[0] for row in language_result.all() if row[0]]

    return {"categories": categories, "languages": languages}


@router.get(
    "/{agent_id}",
    response_model=AgentResponse,
    summary="Get single agent",
    description="Get detailed information about a specific agent.",
)
async def get_agent(
    agent_id: int,
    db: AsyncSession = Depends(get_async_db),
) -> AgentResponse:
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return AgentResponse.model_validate(agent)


@router.post(
    "",
    response_model=AgentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create agent",
    description="Create a new agent configuration.",
)
async def create_agent(
    agent_create: AgentCreate,
    db: AsyncSession = Depends(get_async_db),
) -> AgentResponse:
    agent = Agent(**agent_create.model_dump())
    db.add(agent)
    await db.commit()
    await db.refresh(agent)

    agent_response = AgentResponse.model_validate(agent)
    await websocket_manager.broadcast({
        "type": "agent_created",
        "data": agent_response.model_dump(mode="json"),
    })
    return agent_response


@router.patch(
    "/{agent_id}",
    response_model=AgentResponse,
    summary="Update agent",
    description="Update agent details.",
)
async def update_agent(
    agent_id: int,
    agent_update: AgentUpdate,
    db: AsyncSession = Depends(get_async_db),
) -> AgentResponse:
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    update_data = agent_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(agent, field, value)

    await db.commit()
    await db.refresh(agent)

    agent_response = AgentResponse.model_validate(agent)
    await websocket_manager.broadcast({
        "type": "agent_updated",
        "data": agent_response.model_dump(mode="json"),
    })
    return agent_response


@router.patch(
    "/{agent_id}/status",
    response_model=AgentResponse,
    summary="Update agent status",
    description="Toggle agent active/inactive status.",
)
async def update_agent_status(
    agent_id: int,
    status_update: AgentStatusUpdate,
    db: AsyncSession = Depends(get_async_db),
) -> AgentResponse:
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    agent.is_active = status_update.is_active
    await db.commit()
    await db.refresh(agent)

    agent_response = AgentResponse.model_validate(agent)
    await websocket_manager.broadcast({
        "type": "agent_updated",
        "data": agent_response.model_dump(mode="json"),
    })
    return agent_response


@router.post(
    "/{agent_id}/duplicate",
    response_model=AgentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Duplicate agent",
    description="Create a copy of an existing agent with a new name suffix.",
)
async def duplicate_agent(
    agent_id: int,
    db: AsyncSession = Depends(get_async_db),
) -> AgentResponse:
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    new_agent = Agent(
        token=agent.token,
        endpoint=agent.endpoint,
        environment=agent.environment,
        js_source=agent.js_source,
        script=agent.script,
        category=agent.category,
        language=agent.language,
        name=f"{agent.name} (copy)",
        finger_hole=agent.finger_hole,
        scrollable_agent_card=agent.scrollable_agent_card,
        info=agent.info,
        is_active=True,
    )
    db.add(new_agent)
    await db.commit()
    await db.refresh(new_agent)

    agent_response = AgentResponse.model_validate(new_agent)
    await websocket_manager.broadcast({
        "type": "agent_duplicated",
        "data": agent_response.model_dump(mode="json"),
    })
    return agent_response


@router.delete(
    "/{agent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete agent",
    description="Permanently delete an agent.",
)
async def delete_agent(
    agent_id: int,
    db: AsyncSession = Depends(get_async_db),
) -> Response:
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    await db.delete(agent)
    await db.commit()

    await websocket_manager.broadcast({
        "type": "agent_deleted",
        "data": {"id": agent_id},
    })
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/export/all",
    response_model=List[AgentExport],
    summary="Export all agents as JSON",
    description="Download all agents as JSON array.",
)
async def export_agents_json(
    db: AsyncSession = Depends(get_async_db),
) -> List[AgentExport]:
    result = await db.execute(select(Agent).order_by(Agent.created_at.desc()))
    agents = result.scalars().all()
    return [AgentExport.model_validate(a) for a in agents]


@router.get(
    "/export/csv",
    summary="Export all agents as CSV",
    description="Download all agents as CSV file.",
)
async def export_agents_csv(
    db: AsyncSession = Depends(get_async_db),
) -> Response:
    import csv
    import io

    result = await db.execute(select(Agent).order_by(Agent.created_at.desc()))
    agents = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Name", "Token", "Endpoint", "Environment", "JS Source",
        "Script", "Category", "Language", "Active", "Info", "Finger Hole",
        "Scrollable Card", "Created At", "Updated At",
    ])
    for a in agents:
        writer.writerow([
            a.id,
            a.name,
            a.token,
            a.endpoint,
            a.environment,
            a.js_source,
            a.script,
            a.category,
            a.language,
            "yes" if a.is_active else "no",
            a.info or "",
            a.finger_hole or "",
            a.scrollable_agent_card or "",
            a.created_at.isoformat() if a.created_at else "",
            a.updated_at.isoformat() if a.updated_at else "",
        ])

    csv_content = output.getvalue()
    output.close()
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=agents_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"},
    )


@router.get(
    "/stats/summary",
    summary="Get agent statistics summary",
    description="Get summary statistics for agents.",
)
async def get_agent_stats(
    db: AsyncSession = Depends(get_async_db),
) -> dict:
    total_result = await db.execute(select(func.count(Agent.id)))
    total = total_result.scalar_one()

    active_result = await db.execute(select(func.count(Agent.id)).where(Agent.is_active == True))
    active = active_result.scalar_one()

    inactive_result = await db.execute(select(func.count(Agent.id)).where(Agent.is_active == False))
    inactive = inactive_result.scalar_one()

    category_result = await db.execute(
        select(Agent.category, func.count(Agent.id)).group_by(Agent.category)
    )
    category_counts = {row[0]: row[1] for row in category_result.all()}

    language_result = await db.execute(
        select(Agent.language, func.count(Agent.id)).group_by(Agent.language)
    )
    language_counts = {row[0]: row[1] for row in language_result.all()}

    return {
        "total_agents": total,
        "active_agents": active,
        "inactive_agents": inactive,
        "category_counts": category_counts,
        "language_counts": language_counts,
    }
