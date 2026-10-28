/** Mirrors `app/schemas/job.py` on the backend. */

import type { ApplicationBrief, ApplicationStatus } from "@/types/application";

export type Seniority = "internship" | "entry" | "mid" | "senior" | "unknown";

export interface SkillMatch {
  skill: string;
  evidence: string;
  /** false = matched through related experience (a verified quote from the profile). */
  direct: boolean;
}

export interface MatchBreakdown {
  required_matched: number;
  required_total: number;
  nice_matched: number;
  nice_total: number;
  seniority: Seniority;
  seniority_fit: number;
}

export interface GapItem {
  skill: string;
  priority: number;
  why: string;
  first_steps: string[];
  estimated_time: string;
}

export interface MatchResult {
  score: number;
  matched_skills: SkillMatch[];
  missing_required: string[];
  missing_nice: string[];
  breakdown: MatchBreakdown;
  explanation: string;
  gap_plan: GapItem[];
  profile_updated_at: string;
  scored_at: string;
  profile_fingerprint: string;
}

export type Tone = "professional" | "friendly" | "confident";
export type BulletStatus = "pending" | "accepted" | "rejected";

export interface BulletSuggestion {
  id: string;
  section: "experience" | "project";
  context: string;
  original: string;
  tailored: string;
  reason: string;
  status: BulletStatus;
  /** Set when the honesty check rejected the AI's rewrite and kept the original. */
  guard_note: string;
}

export interface RankedProject {
  name: string;
  rank: number;
  reason: string;
}

export interface TailoringResult {
  bullets: BulletSuggestion[];
  projects: RankedProject[];
  generated_at: string;
  profile_fingerprint: string;
}

export interface CoverLetter {
  tone: Tone;
  body: string;
  warnings: string[];
  edited: boolean;
  generated_at: string;
  updated_at: string;
  profile_fingerprint: string;
}

export interface InterviewQuestion {
  question: string;
  category: "technical" | "behavioral" | "project" | "role";
  hint: string;
  project: string;
}

export interface InterviewPrep {
  questions: InterviewQuestion[];
  generated_at: string;
  profile_fingerprint: string;
}

export interface Job {
  id: number;
  title: string;
  company: string;
  location: string;
  employment_type: string;
  seniority: Seniority;
  required_skills: string[];
  nice_to_have_skills: string[];
  responsibilities: string[];
  summary: string;
  source_url: string | null;
  created_at: string;
  match: MatchResult | null;
  tailoring: TailoringResult | null;
  cover_letters: Partial<Record<Tone, CoverLetter>>;
  interview_prep: InterviewPrep | null;
  /** The tracker card for this job, if it's on the board. */
  application: ApplicationBrief | null;
}

export interface JobSummary {
  id: number;
  title: string;
  company: string;
  seniority: Seniority;
  match_score: number | null;
  created_at: string;
  has_tailoring: boolean;
  has_cover_letter: boolean;
  has_interview_prep: boolean;
  application_status: ApplicationStatus | null;
}
