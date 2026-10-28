import type { EducationItem, ExperienceItem, Profile, ProfileData, ProjectItem } from "@/types/profile";

/** Keep in sync with the backend's MAX_UPLOAD_MB. On Vercel use 4: its functions reject bodies over 4.5 MB. */
export const MAX_UPLOAD_MB = Number(process.env.NEXT_PUBLIC_MAX_UPLOAD_MB) || 5;
export const MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024;

export const newEducation = (): EducationItem => ({
  institution: "",
  degree: "",
  field_of_study: "",
  start_date: "",
  end_date: "",
  details: "",
});

export const newExperience = (): ExperienceItem => ({
  company: "",
  title: "",
  location: "",
  start_date: "",
  end_date: "",
  bullets: [],
});

export const newProject = (): ProjectItem => ({ name: "", description: "", tech_stack: [], bullets: [], link: "" });

/** Strip server-only fields so the object can be edited and sent to PUT /profile. */
export function toProfileData(profile: Profile): ProfileData {
  const { full_name, headline, email, phone, location, links, summary, skills, education, experience, projects } = profile;
  return { full_name, headline, email, phone, location, links, summary, skills, education, experience, projects };
}

/** Returns a copy of `list` with item `index` shallow-merged with `patch`. */
export function updateAt<T>(list: T[], index: number, patch: Partial<T>): T[] {
  return list.map((item, i) => (i === index ? { ...item, ...patch } : item));
}

export function removeAt<T>(list: T[], index: number): T[] {
  return list.filter((_, i) => i !== index);
}

interface Check {
  tip: string;
  weight: number;
  /** 0..1 */
  progress: number;
}

export interface Completeness {
  score: number;
  tips: string[];
}

/** Weighted 0-100 completeness score plus the most valuable missing pieces. */
export function profileCompleteness(p: ProfileData): Completeness {
  const roles = [...p.experience, ...p.projects];
  const checks: Check[] = [
    { tip: "Add your full name", weight: 10, progress: p.full_name ? 1 : 0 },
    { tip: "Add an email or phone number", weight: 10, progress: p.email || p.phone ? 1 : 0 },
    { tip: "Write a 2–3 sentence summary", weight: 15, progress: p.summary.length >= 40 ? 1 : 0 },
    { tip: "List at least 8 skills", weight: 20, progress: Math.min(p.skills.length / 8, 1) },
    { tip: "Add your education", weight: 15, progress: p.education.length > 0 ? 1 : 0 },
    { tip: "Add experience, an internship or volunteering", weight: 10, progress: p.experience.length > 0 ? 1 : 0 },
    { tip: "Add at least 2 projects", weight: 10, progress: Math.min(p.projects.length / 2, 1) },
    {
      tip: "Give every role and project bullet points",
      weight: 5,
      progress: roles.length > 0 && roles.every((r) => r.bullets.length > 0) ? 1 : 0,
    },
    { tip: "Add a GitHub, LinkedIn or portfolio link", weight: 5, progress: p.links.length > 0 ? 1 : 0 },
  ];

  const score = Math.round(checks.reduce((sum, c) => sum + c.weight * c.progress, 0));
  const tips = checks
    .filter((c) => c.progress < 1)
    .sort((a, b) => b.weight * (1 - b.progress) - a.weight * (1 - a.progress))
    .map((c) => c.tip);
  return { score, tips };
}
