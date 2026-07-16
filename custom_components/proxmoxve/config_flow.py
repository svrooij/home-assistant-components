"""Configuration stuff for Proxmox VE."""

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import (
    CONF_HOST,
    CONF_PORT,
    CONF_TOKEN,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_CONTAINERS,
    CONF_NODE,
    CONF_NODES,
    CONF_REALM,
    CONF_TOKEN_ID,
    CONF_VMS,
    DEFAULT_PORT,
    DEFAULT_REALM,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
)

CONF_ADDITIONAL_NODE = "additional_node"
CONF_NODE_SELECTION = "node_selection"
NODE_SELECTION_NEW = "new"

SCHEMA_HOST = vol.Schema(
    {
        vol.Required(CONF_HOST, default="192.168.200.28"): str,
        vol.Required(CONF_USERNAME, default="hass"): str,
        vol.Optional(CONF_REALM, default=DEFAULT_REALM): str,
        vol.Required(CONF_TOKEN): str,
        vol.Required(CONF_TOKEN_ID, default="hass-api"): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.TEXT,
                        ),
                    ),
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,
    },
    extra=vol.ALLOW_EXTRA,
)

SCHEMA_NODE = vol.Schema(
    {
        vol.Required(CONF_NODE, default="proxmox"): str,
        vol.Optional(CONF_VMS, default="100"): str,
        vol.Optional(CONF_CONTAINERS, default="101,103"): str,
        vol.Optional(CONF_ADDITIONAL_NODE, default=False): bool,
    }
)


def _parse_id_list(value: str) -> list[int]:
    """
    Parse a comma-separated string of IDs into a list of ints, ignoring blanks.

    Raises ValueError if any token cannot be converted to an integer.
    """
    try:
        return [int(x.strip()) for x in value.split(",") if x.strip()]
    except ValueError as err:
        msg = "IDs must be positive integers separated by commas."
        raise ValueError(msg) from err


class ProxmoxConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Proxmox VE config flow."""

    VERSION = 1
    MINOR_VERSION = 0

    _data: Mapping[str, Any] | None

    @staticmethod
    @callback
    def async_get_options_flow(
        _config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the options flow handler."""
        return ProxmoxOptionsFlowHandler()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle a flow start."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._data = user_input
            self._data[CONF_NODES] = []
            return await self.async_step_node()
        return self.async_show_form(
            step_id="user", data_schema=SCHEMA_HOST, errors=errors
        )

    async def async_step_node(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle adding a node."""
        errors: dict[str, str] = {}
        if user_input is not None:
            # validate that we have at least one VM or container
            if not user_input[CONF_VMS] and not user_input[CONF_CONTAINERS]:
                errors["base"] = "no_vms_or_containers"
            else:
                try:
                    self._data[CONF_NODES].append(
                        {
                            CONF_NODE: user_input[CONF_NODE],
                            CONF_VMS: _parse_id_list(user_input[CONF_VMS] or ""),
                            CONF_CONTAINERS: _parse_id_list(
                                user_input[CONF_CONTAINERS] or ""
                            ),
                        }
                    )
                except ValueError:
                    errors["base"] = "invalid_id_format"

            if not errors and self._data:
                if user_input[CONF_ADDITIONAL_NODE]:
                    return await self.async_step_node()
                return self.async_create_entry(
                    title=f"{self._data[CONF_HOST]}:{self._data[CONF_PORT]}",
                    data=self._data,
                )

        return self.async_show_form(
            step_id="node", data_schema=SCHEMA_NODE, errors=errors
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle reconfiguration of connection details."""
        reconfigure_entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            return self.async_update_reload_and_abort(
                reconfigure_entry,
                data_updates=user_input,
            )

        current = reconfigure_entry.data
        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=current.get(CONF_HOST, "")): str,
                vol.Required(
                    CONF_USERNAME, default=current.get(CONF_USERNAME, "")
                ): str,
                vol.Optional(
                    CONF_REALM, default=current.get(CONF_REALM, DEFAULT_REALM)
                ): str,
                vol.Required(
                    CONF_TOKEN, default=current.get(CONF_TOKEN, "")
                ): str,
                vol.Required(
                    CONF_TOKEN_ID, default=current.get(CONF_TOKEN_ID, "hass-api")
                ): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    ),
                ),
                vol.Optional(
                    CONF_PORT, default=current.get(CONF_PORT, DEFAULT_PORT)
                ): int,
                vol.Optional(
                    CONF_VERIFY_SSL,
                    default=current.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
                ): bool,
            }
        )

        return self.async_show_form(
            step_id="reconfigure", data_schema=schema, errors=errors
        )


class ProxmoxOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Proxmox VE options (manage nodes/containers/VMs)."""

    _nodes: list[dict[str, Any]]
    _selected_node_index: int | None

    def __init__(self) -> None:
        """Initialize options flow."""
        self._nodes = []
        self._selected_node_index = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Show node selection: edit an existing node or add a new one."""
        # Always refresh nodes from the current entry state
        self._nodes = list(
            self.config_entry.options.get(
                CONF_NODES,
                self.config_entry.data.get(CONF_NODES, []),
            )
        )

        if user_input is not None:
            selection = user_input[CONF_NODE_SELECTION]
            if selection == NODE_SELECTION_NEW:
                self._selected_node_index = None
            else:
                self._selected_node_index = int(selection)
            return await self.async_step_node()

        options = [
            selector.SelectOptionDict(
                value=str(i),
                label=f"Edit: {node[CONF_NODE]}",
            )
            for i, node in enumerate(self._nodes)
        ]
        options.append(
            selector.SelectOptionDict(value=NODE_SELECTION_NEW, label="Add new node")
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NODE_SELECTION): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=options)
                    )
                }
            ),
        )

    async def async_step_node(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Edit an existing node or add a new one."""
        errors: dict[str, str] = {}

        is_editing = (
            self._selected_node_index is not None
            and self._selected_node_index < len(self._nodes)
        )
        current_node: dict[str, Any] = (
            self._nodes[self._selected_node_index] if is_editing else {}
        )

        if user_input is not None:
            if not user_input.get(CONF_VMS) and not user_input.get(CONF_CONTAINERS):
                errors["base"] = "no_vms_or_containers"
            else:
                try:
                    node_data = {
                        CONF_NODE: user_input[CONF_NODE],
                        CONF_VMS: _parse_id_list(user_input.get(CONF_VMS) or ""),
                        CONF_CONTAINERS: _parse_id_list(
                            user_input.get(CONF_CONTAINERS) or ""
                        ),
                    }
                except ValueError:
                    errors["base"] = "invalid_id_format"
                else:
                    if is_editing:
                        self._nodes[self._selected_node_index] = node_data
                    else:
                        self._nodes.append(node_data)

            if not errors:
                return self.async_create_entry(data={CONF_NODES: self._nodes})

        default_node = current_node.get(CONF_NODE, "proxmox")
        default_vms = ",".join(str(x) for x in current_node.get(CONF_VMS, []))
        default_containers = ",".join(
            str(x) for x in current_node.get(CONF_CONTAINERS, [])
        )

        schema = vol.Schema(
            {
                vol.Required(CONF_NODE, default=default_node): str,
                vol.Optional(CONF_VMS, default=default_vms): str,
                vol.Optional(CONF_CONTAINERS, default=default_containers): str,
            }
        )

        return self.async_show_form(
            step_id="node", data_schema=schema, errors=errors
        )
