import voluptuous as vol

from .const import DOMAIN, SERVICE_UPDATE, SERVICE_CATEGORY_UPDATE
from .monzo_update_coordinator import MonzoUpdateCoordinator
from .monzo_category_update_coordinator import MonzoCategoryUpdateCoordinator
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

SERVICE_UPDATE_SCHEMA = vol.Schema(
    {
    }
)

def setup_services(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Set up the services for the Monzo integration."""

    async def update():
        coordinator: MonzoUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
        await coordinator.async_force_update()

    async def category_update():
        coordinator: MonzoCategoryUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["category_coordinator"]
        await coordinator.async_force_update()

    hass.services.async_register(
        DOMAIN,
        SERVICE_UPDATE,
        update,
        schema=SERVICE_UPDATE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_CATEGORY_UPDATE,
        category_update,
        schema=SERVICE_UPDATE_SCHEMA,
    )