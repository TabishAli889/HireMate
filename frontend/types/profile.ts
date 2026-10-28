/** Mirrors `app/schemas/profile.py` on the backend. */

export interface EducationItem {
  institution: string;
  degree: string;
  field_of_study: string;
  start_date: string;
  end_date: string;
  details: string;
}

export interface ExperienceItem {
  company: string;
  title: string;
  location: string;
  start_date: string;
  end_date: string;
  bullets: string[];
}

export interface ProjectItem {
  name: string;
  description: string;
  tech_stack: string[];
  bullets: string[];
  link: string;
}

export interface ProfileData {
  full_name: string;
  headline: string;
  email: string;
  phone: string;
  location: string;
  links: string[];
  summary: string;
  skills: string[];
  education: EducationItem[];
  experience: ExperienceItem[];
  projects: ProjectItem[];
}

export interface Profile extends ProfileData {
  id: number;
  is_demo: boolean;
  source_filename: string | null;
  updated_at: string;
}
