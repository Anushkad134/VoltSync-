import { Badge } from "./ui/Badge";
import { Clock, Zap, CheckCircle, XCircle, AlertTriangle, Calendar } from "lucide-react";

const statusConfig = {
  // Backend status values
  QUEUED: {
    variant: "warning",
    label: "Queued",
    icon: Clock,
    description: "Waiting in queue",
  },
  PENDING: {
    variant: "warning",
    label: "Pending",
    icon: Clock,
    description: "Waiting for AI Orchestrator decision",
  },
  CREATED: {
    variant: "info",
    label: "Created",
    icon: Clock,
    description: "Session created, waiting for scheduling",
  },
  SCHEDULED: {
    variant: "info",
    label: "Scheduled",
    icon: Calendar,
    description: "Plan generated, waiting for scheduled window",
  },
  IN_PROGRESS: {
    variant: "success",
    label: "In Progress",
    icon: Zap,
    description: "Charging in progress",
  },
  CHARGING: {
    variant: "success",
    label: "Charging",
    icon: Zap,
    description: "Actively pulling power",
  },
  OCCUPIED: {
    variant: "info",
    label: "Occupied",
    icon: Zap,
    description: "Station occupied",
  },
  PAUSED_GRID_STRESS: {
    variant: "warning",
    label: "Paused",
    icon: AlertTriangle,
    description: "Paused due to grid curtailment",
  },
  COMPLETED: {
    variant: "secondary",
    label: "Completed",
    icon: CheckCircle,
    description: "Target SOC reached or session ended",
  },
  CANCELLED: {
    variant: "destructive",
    label: "Cancelled",
    icon: XCircle,
    description: "Cancelled by driver or operator",
  },
  CANCELLED_BY_DRIVER: {
    variant: "destructive",
    label: "Cancelled",
    icon: XCircle,
    description: "Cancelled by driver",
  },
  CANCELLED_BY_OPERATOR: {
    variant: "destructive",
    label: "Cancelled",
    icon: XCircle,
    description: "Cancelled by operator",
  },
  FAILED: {
    variant: "destructive",
    label: "Failed",
    icon: XCircle,
    description: "Session failed",
  },
};

export function StatusBadge({ status, showIcon = true, className }) {
  const config = statusConfig[status] || statusConfig.PENDING;
  const Icon = config.icon;

  return (
    <Badge variant={config.variant} className={className}>
      {showIcon && <Icon className="w-3 h-3 mr-1" />}
      {config.label}
    </Badge>
  );
}

export function getStatusDescription(status) {
  return statusConfig[status]?.description || "Unknown status";
}
