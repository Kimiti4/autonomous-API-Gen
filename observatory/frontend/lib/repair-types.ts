export interface RepairNotification {
  id: string;
  severity: string;
  title: string;
  message: string;
  repair_id: string;
  action_required: boolean;
  deployment_authorization_required: boolean;
}

export interface RepairState {
  repair_id: string;
  status: string;
  report: Record<string, unknown> | null;
  events: number;
  updated_at: string | null;
}
