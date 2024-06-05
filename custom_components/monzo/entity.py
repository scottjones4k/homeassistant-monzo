"""Support for Monzo sensors."""
from __future__ import annotations

import voluptuous as vol

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from typing import Any

from .const import (
    DOMAIN
)


ATTR_NATIVE_BALANCE = "Balance in native currency"

DEFAULT_COIN_ICON = "mdi:cash"

ATTRIBUTION = "Data provided by Monzo"

POT_SERVICE_SCHEMA = {
    vol.Required('amount_in_minor_units'): vol.All(vol.Coerce(int), vol.Range(0, 65535)),
}

class MonzoBaseEntity(CoordinatorEntity):
    """Common base for Monzo entities."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = DEFAULT_COIN_ICON

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        idx,
        device_model: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, context=idx)
        self.idx = idx

        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, str(self.idx))},
            manufacturer="Monzo",
            model=device_model,
            name=self.data.name,
        )

    @property
    def data(self) -> dict[str, Any]:
        """Shortcut to access coordinator data for the entity."""
        return self.coordinator.data[self.idx]
