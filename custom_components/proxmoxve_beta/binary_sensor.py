"""Binary sensor to read Proxmox VE data."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import _LOGGER
from .coordinator import ProxmoxDataUpdateCoordinator
from .entity import ProxmoxEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entries: AddEntitiesCallback
) -> None:
    """Set up the Proxmox VE component."""
    _LOGGER.debug("setup %s with config:%s", entry.title, entry.data)
    # await entry.coordinator.async_config_entry_first_refresh()
    binary_sensors = []
    coordinator: ProxmoxDataUpdateCoordinator = entry.coordinator
    for node_name, data in coordinator.data.nodes.items():
        _LOGGER.debug("node_name: %s data: %s", node_name, data)
        for vm_id in data.vms:
            binary_sensors.append(
                ProxmoxVmBinarySensor(
                    coordinator=coordinator,
                    unique_id=f"proxmox_{node_name}_vm_{vm_id}_running",
                    name="Running",
                    icon="mdi:server",
                    host_name=entry.title,
                    node_name=node_name,
                    vm_id=vm_id,
                    qemu=True,
                    agent=False,
                )
            )
            binary_sensors.append(
                ProxmoxVmBinarySensor(
                    coordinator=coordinator,
                    unique_id=f"proxmox_{node_name}_vm_{vm_id}_agent",
                    name="Agent running",
                    icon="mdi:access-point-check",
                    host_name=entry.title,
                    node_name=node_name,
                    vm_id=vm_id,
                    qemu=True,
                    agent=True,
                )
            )

        binary_sensors.extend(
            [
                ProxmoxVmBinarySensor(
                    coordinator=coordinator,
                    unique_id=f"proxmox_{node_name}_lxc_{vm_id}_running",
                    name="Running",
                    icon="mdi:server",
                    host_name=entry.title,
                    node_name=node_name,
                    vm_id=vm_id,
                    qemu=False,
                    agent=False,
                )
                for vm_id in data.containers
            ]
        )

    async_add_entries(binary_sensors)


class ProxmoxVmBinarySensor(ProxmoxEntity, BinarySensorEntity):
    """A binary sensor for reading Proxmox VE data.

    Args:
        coordinator (ProxmoxDataUpdateCoordinator): The coordinator.
        unique_id (str): The unique id.
        name (str): The name of the entity.
        icon (str): The icon of the entity.
        host_name (str): The host name.
        node_name (str): The node name.
        vm_id (int): The vm id.
        qemu (bool): The vm is a qemu vm.
        agent (bool): Sensor is for agent.

    """

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ProxmoxDataUpdateCoordinator,
        unique_id: str,
        name: str,
        icon: str,
        host_name: str,
        node_name: str,
        vm_id: int,
        qemu: bool,
        agent: bool,
    ) -> None:
        """Create the binary sensor for vms."""
        self._agent = agent
        super().__init__(
            coordinator, unique_id, name, icon, host_name, node_name, qemu, vm_id
        )

    @property
    def is_on(self) -> bool | None:
        """Return the state of the binary sensor."""
        if (data := self.get_coordinator_data()) is None:
            return None
        if self._agent:
            return data.agent_running
        return data.running

    @property
    def available(self) -> bool:
        """Return sensor availability."""

        return super().available and self.get_coordinator_data() is not None

    @property
    def entity_category(self) -> EntityCategory | None:
        """Return the entity category."""
        return EntityCategory.DIAGNOSTIC if self._agent else None
