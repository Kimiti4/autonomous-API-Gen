export const BASE_COMMAND_ACTIONS = [
  "request_authorization",
  "request_evolution_definition",
  "safe_mode_enable",
  "safe_mode_disable"
] as const;

export const ARCHITECT_COMMAND_ACTIONS = [
  ...BASE_COMMAND_ACTIONS,
  "request_implementation",
  "request_runtime",
  "stop_runtime",
  "restart_runtime"
] as const;

export type CommandAction =
  | (typeof BASE_COMMAND_ACTIONS)[number]
  | (typeof ARCHITECT_COMMAND_ACTIONS)[number];

export function allowedActionsForClearance(
  clearance: string
): CommandAction[] {
  switch (clearance) {
    case "architect":
    case "admin":
      return [...ARCHITECT_COMMAND_ACTIONS];

    case "operator":
      return [...BASE_COMMAND_ACTIONS];

    default:
      return [];
  }
}
