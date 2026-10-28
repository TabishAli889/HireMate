/** Application tracker types (mirror backend/app/schemas/application.py). */

export type ApplicationStatus = "saved" | "applied" | "interview" | "offer" | "rejected";

export interface ApplicationEvent {
  id: number;
  kind: "created" | "status" | "deadline" | "notes" | "details" | string;
  message: string;
  created_at: string;
}

export interface Application {
  id: number;
  job_id: number | null;
  title: string;
  company: string;
  link: string;
  status: ApplicationStatus;
  position: number;
  notes: string;
  /** "YYYY-MM-DD" (a calendar date, no time zone). */
  deadline: string | null;
  created_at: string;
  updated_at: string;
  match_score: number | null;
  has_tailoring: boolean;
  has_cover_letter: boolean;
  has_interview_prep: boolean;
  events: ApplicationEvent[];
}

export interface ApplicationBrief {
  id: number;
  status: ApplicationStatus;
}

export interface ApplicationCreateBody {
  job_id?: number;
  title?: string;
  company?: string;
  link?: string;
  status?: ApplicationStatus;
  deadline?: string | null;
  notes?: string;
}

export type ApplicationUpdateBody = Partial<Pick<Application, "title" | "company" | "link" | "notes" | "deadline">>;
