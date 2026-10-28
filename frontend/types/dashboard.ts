/** Mirrors backend/app/schemas/dashboard.py. */

import type { ApplicationStatus } from "@/types/application";
import type { JobSummary } from "@/types/job";

export interface DashboardStats {
  applications: number;
  active: number;
  sent: number;
  interviews: number;
  offers: number;
  interview_rate: number | null;
  jobs_analyzed: number;
  jobs_scored: number;
  average_match: number | null;
  documents_ready: number;
}

export interface PipelineStage {
  status: ApplicationStatus;
  label: string;
  count: number;
}

export interface UpcomingDeadline {
  application_id: number;
  title: string;
  company: string;
  status: ApplicationStatus;
  deadline: string;
}

export interface SkillGap {
  skill: string;
  jobs: number;
}

export interface ScorePoint {
  job_id: number;
  title: string;
  company: string;
  score: number;
  created_at: string;
}

export interface ActivityItem {
  kind: string;
  message: string;
  title: string;
  company: string;
  created_at: string;
  application_id: number | null;
  job_id: number | null;
}

export interface Dashboard {
  profile_name: string;
  has_profile: boolean;
  stats: DashboardStats;
  pipeline: PipelineStage[];
  deadlines: UpcomingDeadline[];
  skill_gaps: SkillGap[];
  score_history: ScorePoint[];
  recent_jobs: JobSummary[];
  activity: ActivityItem[];
}
