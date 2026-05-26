from fastapi import APIRouter

from ..schemas import ConfigOut, ConfigUpdate
from ..config import load_config, save_config

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("", response_model=ConfigOut)
def get_config():
    """Get current application configuration."""
    config = load_config()
    return ConfigOut(**config)


@router.patch("", response_model=ConfigOut)
def update_config(update: ConfigUpdate):
    """Update application configuration."""
    config = load_config()

    for field, value in update.model_dump(exclude_unset=True).items():
        if value is not None:
            config[field] = value

    save_config(config)
    return ConfigOut(**config)
