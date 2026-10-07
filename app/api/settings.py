"""Settings API for webhook configuration."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_async_db
from app.models.setting import Setting
from app.schemas.setting import SettingResponse, SettingUpdate, WebhookUrlResponse
from app.config import get_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])

# Setting keys for webhook configuration
WEBHOOK_SETTINGS = {
    "webhook_host": "0.0.0.0",
    "webhook_port": "5687",
    "webhook_path": "/webhook/agents",
}


@router.get(
    "",
    response_model=list[SettingResponse],
    summary="Get all settings",
    description="Get all application settings including webhook configuration.",
)
async def get_settings_list(
    db: AsyncSession = Depends(get_async_db),
) -> list[SettingResponse]:
    """Get all settings."""
    result = await db.execute(select(Setting).order_by(Setting.key))
    settings = result.scalars().all()
    return [SettingResponse.model_validate(s) for s in settings]


@router.get(
    "/webhook-url",
    response_model=WebhookUrlResponse,
    summary="Get full webhook URL",
    description="Get the complete webhook URL based on current configuration.",
)
async def get_webhook_url(
    db: AsyncSession = Depends(get_async_db),
) -> WebhookUrlResponse:
    """Get the full webhook URL from database settings."""
    # Get settings from database
    result = await db.execute(
        select(Setting).where(Setting.key.in_(WEBHOOK_SETTINGS.keys()))
    )
    db_settings = {s.key: s.value for s in result.scalars().all()}

    # Use database values or defaults
    host = db_settings.get("webhook_host", WEBHOOK_SETTINGS["webhook_host"])
    port = db_settings.get("webhook_port", WEBHOOK_SETTINGS["webhook_port"])
    path = db_settings.get("webhook_path", WEBHOOK_SETTINGS["webhook_path"])

    # Build URL - for display, replace 0.0.0.0 with localhost
    display_host = host if host != "0.0.0.0" else "localhost"
    webhook_url = f"http://{display_host}:{port}{path}"

    return WebhookUrlResponse(
        webhook_url=webhook_url,
        host=host,
        port=int(port),
        path=path,
    )


@router.post(
    "/initialize-defaults",
    response_model=list[SettingResponse],
    summary="Initialize default settings",
    description="Create default webhook settings if they don't exist.",
)
async def initialize_defaults(
    db: AsyncSession = Depends(get_async_db),
) -> list[SettingResponse]:
    """Initialize default webhook settings."""
    created = []

    for key, default_value in WEBHOOK_SETTINGS.items():
        result = await db.execute(select(Setting).where(Setting.key == key))
        existing = result.scalar_one_or_none()

        if not existing:
            description = {
                "webhook_host": "IP address to bind webhook server",
                "webhook_port": "Port for webhook server",
                "webhook_path": "Webhook endpoint path for agents",
                "training_webhook_path": "Webhook endpoint path for training sessions",
            }.get(key, "")

            setting = Setting(
                key=key,
                value=default_value,
                description=description,
            )
            db.add(setting)
            created.append(setting)

    if created:
        await db.commit()
        for s in created:
            await db.refresh(s)

    return [SettingResponse.model_validate(s) for s in created]


@router.get(
    "/{key}",
    response_model=SettingResponse,
    summary="Get setting by key",
    description="Get a specific setting by its key.",
)
async def get_setting(
    key: str,
    db: AsyncSession = Depends(get_async_db),
) -> SettingResponse:
    """Get a setting by key."""
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()

    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Setting with key '{key}' not found",
        )

    return SettingResponse.model_validate(setting)


@router.put(
    "/{key}",
    response_model=SettingResponse,
    summary="Update setting",
    description="Update a setting value. Creates if not exists.",
)
async def update_setting(
    key: str,
    setting_update: SettingUpdate,
    db: AsyncSession = Depends(get_async_db),
) -> SettingResponse:
    """Update a setting."""
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()

    if not setting:
        # Create new setting
        setting = Setting(
            key=key,
            value=setting_update.value,
            description=setting_update.description,
        )
        db.add(setting)
    else:
        # Update existing
        setting.value = setting_update.value
        if setting_update.description is not None:
            setting.description = setting_update.description

    await db.commit()
    await db.refresh(setting)

    return SettingResponse.model_validate(setting)